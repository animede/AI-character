from __future__ import annotations

import asyncio
import base64

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from character_registry import get_character, get_default_character
from conversation_store import conversation_store, new_message_id
from llm_client import build_messages, stream_chat_chunks
from schemas import ChatStreamRequest, ConversationCreateRequest
from settings import MAX_HISTORY_PAIRS
from stream_segmenter import SentenceSegmenter
from tts_client import TTSClient


router = APIRouter(tags=["chat"])
tts_client = TTSClient()


async def validate_chat_request(websocket: WebSocket, raw_payload: dict) -> tuple[ChatStreamRequest, dict, str] | None:
    # WebSocket で受けた生 payload を、会話処理に使える形まで正規化する。
    action = raw_payload.get("action")
    if action != "chat":
        # 現在の WebSocket では chat 以外の操作は受け付けない。
        await send_stream_error(websocket, "未対応のアクションです。")
        return None

    try:
        payload = ChatStreamRequest.model_validate(raw_payload)
    except ValidationError:
        # 必須フィールドや型が合わない場合は、履歴を触らずに弾く。
        await send_stream_error(websocket, "メッセージ形式が不正です。")
        return None

    conversation = conversation_store.get_conversation(payload.conversation_id)
    if not conversation:
        # 存在しない会話 ID には紐付けできないので、この要求は破棄する。
        await send_stream_error(websocket, "Conversation not found")
        return None

    message_text = payload.message.strip()
    if not message_text:
        # 空文字は履歴にも LLM 入力にも乗せない。
        await send_stream_error(websocket, "Message must not be empty")
        return None

    return payload, conversation, message_text


async def send_stream_error(
    websocket: WebSocket,
    error: str,
    *,
    message_id: str | None = None,
    stage: str | None = None,
    fatal: bool | None = None,
) -> None:
    # error イベントの組み立てを 1 箇所に寄せ、分岐側の見通しを保つ。
    payload = {"type": "error", "error": error}
    if message_id is not None:
        payload["message_id"] = message_id
    if stage is not None:
        payload["stage"] = stage
    if fatal is not None:
        payload["fatal"] = fatal
    await websocket.send_json(payload)


def resolve_audio_enabled(payload: ChatStreamRequest) -> bool:
    # クライアント指定の ON/OFF に加え、実サーバへ疎通できるときだけ音声送信を有効化する。
    return payload.audio_enabled and tts_client.has_live_engine()


def rollback_user_message(conversation_id: str, user_message_id: str) -> None:
    # assistant 応答が未確定のまま失敗したときだけ、直前の user 発話を巻き戻す。
    conversation_store.pop_last_message(
        conversation_id,
        expected_role="user",
        expected_message_id=user_message_id,
    )


async def send_audio_segment(
    websocket: WebSocket,
    *,
    assistant_message_id: str,
    segment_index: int,
    segment: str,
    selected_style_id: int | None,
) -> bool:
    # 1 文ぶんの TTS 合成と audio イベント送信を 1 つの責務として切り出す。
    try:
        # 同期 HTTP 呼び出しなので、イベントループを塞がないよう別スレッドへ逃がす。
        audio_bytes = await asyncio.to_thread(tts_client.synthesize, segment, selected_style_id)
    except Exception as exc:
        # TTS 失敗はターン全体を落とさず、音声だけ欠落させて継続する。
        await send_stream_error(
            websocket,
            str(exc),
            message_id=assistant_message_id,
            stage="tts",
            fatal=False,
        )
        return False

    if not audio_bytes:
        # sanitize 後に空になった断片などは、そのまま捨てて次へ進む。
        return False

    await websocket.send_json(
        {
            "type": "audio",
            "message_id": assistant_message_id,
            "segment_index": segment_index,
            "text": segment,
            "audio_format": tts_client.audio_format,
            "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
        }
    )
    return True


async def stream_audio_segments(
    websocket: WebSocket,
    *,
    assistant_message_id: str,
    segments: list[str],
    start_index: int,
    selected_style_id: int | None,
) -> int:
    # 複数文の TTS 送信をまとめ、採番の進み方だけ呼び出し元へ返す。
    segment_index = start_index
    for segment in segments:
        sent = await send_audio_segment(
            websocket,
            assistant_message_id=assistant_message_id,
            segment_index=segment_index,
            segment=segment,
            selected_style_id=selected_style_id,
        )
        if sent:
            segment_index += 1
    return segment_index


async def handle_chat_turn(
    websocket: WebSocket,
    *,
    payload: ChatStreamRequest,
    conversation: dict,
    message_text: str,
) -> None:
    # 1 ターンぶんの履歴保存、LLM ストリーム、TTS 送信、完了通知を担当する。
    character = get_character(conversation["character_id"])
    # user メッセージは先に永続化し、失敗時だけ巻き戻す。
    user_message = conversation_store.append_user_message(payload.conversation_id, message_text)
    assistant_message_id = new_message_id()
    full_response = ""
    system_prompt = payload.role.strip() if payload.role else character.system_prompt
    max_history_pairs = payload.max_history if payload.max_history is not None else MAX_HISTORY_PAIRS
    # audio_enabled の最終判定は helper に寄せ、TTS 利用条件を 1 箇所に固定する。
    audio_enabled = resolve_audio_enabled(payload)
    selected_style_id = payload.selected_style_id
    segmenter = SentenceSegmenter()
    segment_index = 0

    try:
        recent_messages = conversation_store.recent_messages(
            payload.conversation_id,
            max_history_pairs * 2,
        )
        # system prompt と直近履歴から、そのターン専用の LLM 入力を組み立てる。
        llm_messages = build_messages(system_prompt, recent_messages)
        await websocket.send_json(
            {
                "type": "start",
                "conversation_id": payload.conversation_id,
                "character_id": character.id,
                "message_id": assistant_message_id,
                "audio_enabled": audio_enabled,
                "selected_style_id": selected_style_id,
            }
        )
        async for chunk in stream_chat_chunks(llm_messages):
            full_response += chunk
            # 文字ストリームは常に先に返し、音声化はその後段で追従させる。
            await websocket.send_json(
                {
                    "type": "delta",
                    "message_id": assistant_message_id,
                    "delta": chunk,
                }
            )
            if not audio_enabled:
                # text-only ターンでは segmenter/TTS には進まない。
                continue

            segment_index = await stream_audio_segments(
                websocket,
                assistant_message_id=assistant_message_id,
                segments=segmenter.push(chunk),
                start_index=segment_index,
                selected_style_id=selected_style_id,
            )

        if audio_enabled:
            # ストリーム末尾に句読点が無い場合でも、残バッファを最後に音声化する。
            segment_index = await stream_audio_segments(
                websocket,
                assistant_message_id=assistant_message_id,
                segments=segmenter.flush(),
                start_index=segment_index,
                selected_style_id=selected_style_id,
            )

        if full_response:
            # assistant 本文は、ストリーム完了後に 1 件の確定メッセージとして保存する。
            conversation_store.append_assistant_message(
                payload.conversation_id,
                full_response,
                message_id=assistant_message_id,
            )
        await websocket.send_json(
            {
                "type": "end",
                "message_id": assistant_message_id,
                "finish_reason": "stop",
            }
        )
    except WebSocketDisconnect:
        # 切断時は、まだ assistant 応答が確定していないユーザー発話だけ巻き戻す。
        rollback_user_message(payload.conversation_id, user_message["message_id"])
        raise
    except Exception as exc:
        # LLM 系の失敗は fatal として返し、フロント側でターンを閉じさせる。
        rollback_user_message(payload.conversation_id, user_message["message_id"])
        await send_stream_error(
            websocket,
            str(exc),
            message_id=assistant_message_id,
            stage="llm",
            fatal=True,
        )


def conversation_payload(conversation: dict) -> dict:
    # REST 返却用に、会話本体とキャラ公開情報をまとめ直す。
    character = get_character(conversation["character_id"])
    return {
        "conversation_id": conversation["conversation_id"],
        "character": character.public_dict(),
        "messages": conversation["messages"],
        "created_at": conversation["created_at"],
        "updated_at": conversation["updated_at"],
    }


@router.post("/api/conversations")
def create_conversation(payload: ConversationCreateRequest) -> dict:
    # 指定キャラ、または既定キャラで新しい会話 1 本を作る。
    try:
        character = get_default_character() if not payload.character_id else get_character(payload.character_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    conversation = conversation_store.create_conversation(character.id, greeting=character.greeting)
    return conversation_payload(conversation)


@router.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str) -> dict:
    # 既存会話をそのまま再表示するための取得 API。
    conversation = conversation_store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation_payload(conversation)


@router.post("/api/conversations/{conversation_id}/clear")
def clear_conversation(conversation_id: str) -> dict:
    # 履歴クリアは削除ではなく、同じキャラで新規会話を作り直して返す。
    conversation = conversation_store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    character = get_character(conversation["character_id"])
    conversation_store.delete_conversation(conversation_id)
    new_conversation = conversation_store.create_conversation(character.id, greeting=character.greeting)
    return {
        "success": True,
        "new_conversation_id": new_conversation["conversation_id"],
        "character": character.public_dict(),
        "messages": new_conversation["messages"],
        "created_at": new_conversation["created_at"],
        "updated_at": new_conversation["updated_at"],
    }


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket) -> None:
    # 1 本の WebSocket 接続で、複数ターンの chat アクションを順に処理する。
    await websocket.accept()

    while True:
        try:
            raw_payload = await websocket.receive_json()
        except WebSocketDisconnect:
            break
        except Exception:
            # JSON として解釈できない入力は、そのターンを開始せずに弾く。
            await send_stream_error(websocket, "不正なJSONを受信しました。")
            continue

        validated = await validate_chat_request(websocket, raw_payload)
        if not validated:
            # バリデーション失敗時は、その要求だけ破棄して次の受信を待つ。
            continue

        try:
            payload, conversation, message_text = validated
            await handle_chat_turn(
                websocket,
                payload=payload,
                conversation=conversation,
                message_text=message_text,
            )
        except WebSocketDisconnect:
            # ターン処理中に切断されたら、その接続自体を閉じる。
            break
