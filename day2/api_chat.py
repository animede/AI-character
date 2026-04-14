from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from character_registry import get_character, get_default_character
from conversation_store import conversation_store, new_message_id
from llm_client import build_messages, stream_chat_chunks
from schemas import ChatStreamRequest, ConversationCreateRequest
from settings import MAX_HISTORY_PAIRS, STREAM_MEDIA_TYPE


router = APIRouter(prefix="/api", tags=["chat"])


def conversation_payload(conversation: dict) -> dict:
    character = get_character(conversation["character_id"])
    return {
        "conversation_id": conversation["conversation_id"],
        "character": character.public_dict(),
        "messages": conversation["messages"],
        "created_at": conversation["created_at"],
        "updated_at": conversation["updated_at"],
    }


def ndjson(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False) + "\n"


@router.post("/conversations")
def create_conversation(payload: ConversationCreateRequest) -> dict:
    try:
        character = get_default_character() if not payload.character_id else get_character(payload.character_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    conversation = conversation_store.create_conversation(character.id, greeting=character.greeting)
    return conversation_payload(conversation)


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str) -> dict:
    conversation = conversation_store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation_payload(conversation)


@router.post("/conversations/{conversation_id}/clear")
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


@router.post("/chat/stream")
def chat_stream(payload: ChatStreamRequest) -> StreamingResponse:
    conversation = conversation_store.get_conversation(payload.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty")

    character = get_character(conversation["character_id"])
    conversation_store.append_user_message(payload.conversation_id, payload.message.strip())
    assistant_message_id = new_message_id()

    def event_stream():
        full_response = ""
        try:
            recent_messages = conversation_store.recent_messages(
                payload.conversation_id,
                MAX_HISTORY_PAIRS * 2,
            )
            llm_messages = build_messages(character.system_prompt, recent_messages)
            yield ndjson(
                {
                    "type": "start",
                    "conversation_id": payload.conversation_id,
                    "character_id": character.id,
                    "message_id": assistant_message_id,
                }
            )
            for chunk in stream_chat_chunks(llm_messages):
                full_response += chunk
                yield ndjson(
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
            yield ndjson(
                {
                    "type": "end",
                    "message_id": assistant_message_id,
                    "finish_reason": "stop",
                }
            )
        except Exception as exc:
            yield ndjson(
                {
                    "type": "error",
                    "message_id": assistant_message_id,
                    "error": str(exc),
                }
            )

    return StreamingResponse(event_stream(), media_type=STREAM_MEDIA_TYPE)
