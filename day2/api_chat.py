from __future__ import annotations

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from character_registry import get_character, get_default_character
from conversation_store import conversation_store, new_message_id
from llm_client import build_messages, stream_chat_chunks
from schemas import ChatStreamRequest, ConversationCreateRequest
from settings import MAX_HISTORY_PAIRS


router = APIRouter(tags=["chat"])


def conversation_payload(conversation: dict) -> dict:
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
    try:
        character = get_default_character() if not payload.character_id else get_character(payload.character_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    conversation = conversation_store.create_conversation(character.id, greeting=character.greeting)
    return conversation_payload(conversation)


@router.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str) -> dict:
    conversation = conversation_store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation_payload(conversation)


@router.post("/api/conversations/{conversation_id}/clear")
def clear_conversation(conversation_id: str) -> dict:
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
    await websocket.accept()

    while True:
        try:
            raw_payload = await websocket.receive_json()
        except WebSocketDisconnect:
            break
        except Exception:
            await websocket.send_json({"type": "error", "error": "不正なJSONを受信しました。"})
            continue

        action = raw_payload.get("action")
        if action != "chat":
            await websocket.send_json({"type": "error", "error": "未対応のアクションです。"})
            continue

        try:
            payload = ChatStreamRequest.model_validate(raw_payload)
        except ValidationError:
            await websocket.send_json({"type": "error", "error": "メッセージ形式が不正です。"})
            continue

        conversation = conversation_store.get_conversation(payload.conversation_id)
        if not conversation:
            await websocket.send_json({"type": "error", "error": "Conversation not found"})
            continue

        message_text = payload.message.strip()
        if not message_text:
            await websocket.send_json({"type": "error", "error": "Message must not be empty"})
            continue

        character = get_character(conversation["character_id"])
        user_message = conversation_store.append_user_message(payload.conversation_id, message_text)
        assistant_message_id = new_message_id()
        full_response = ""
        system_prompt = payload.role.strip() if payload.role else character.system_prompt
        max_history_pairs = payload.max_history if payload.max_history is not None else MAX_HISTORY_PAIRS

        try:
            recent_messages = conversation_store.recent_messages(
                payload.conversation_id,
                max_history_pairs * 2,
            )
            llm_messages = build_messages(system_prompt, recent_messages)
            await websocket.send_json(
                {
                    "type": "start",
                    "conversation_id": payload.conversation_id,
                    "character_id": character.id,
                    "message_id": assistant_message_id,
                }
            )
            async for chunk in stream_chat_chunks(llm_messages):
                full_response += chunk
                await websocket.send_json(
                    {
                        "type": "delta",
                        "message_id": assistant_message_id,
                        "delta": chunk,
                    }
                )

            if full_response:
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
            conversation_store.pop_last_message(
                payload.conversation_id,
                expected_role="user",
                expected_message_id=user_message["message_id"],
            )
            break
        except Exception as exc:
            conversation_store.pop_last_message(
                payload.conversation_id,
                expected_role="user",
                expected_message_id=user_message["message_id"],
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "message_id": assistant_message_id,
                    "error": str(exc),
                }
            )
