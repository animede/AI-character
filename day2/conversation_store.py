from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_conversation_id() -> str:
    return f"conv_{uuid4().hex[:8]}"


def new_message_id() -> str:
    return f"msg_{uuid4().hex[:10]}"


class ConversationStore:
    def __init__(self) -> None:
        self._conversations: dict[str, dict] = {}
        self._lock = Lock()

    def create_conversation(self, character_id: str, greeting: str | None = None) -> dict:
        timestamp = utc_now_iso()
        conversation_id = new_conversation_id()
        messages: list[dict] = []
        if greeting:
            messages.append(
                {
                    "message_id": new_message_id(),
                    "role": "assistant",
                    "content": greeting,
                    "timestamp": timestamp,
                }
            )

        conversation = {
            "conversation_id": conversation_id,
            "character_id": character_id,
            "messages": messages,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        with self._lock:
            self._conversations[conversation_id] = conversation
        return deepcopy(conversation)

    def get_conversation(self, conversation_id: str) -> dict | None:
        with self._lock:
            conversation = self._conversations.get(conversation_id)
            return deepcopy(conversation) if conversation else None

    def has_conversation(self, conversation_id: str) -> bool:
        with self._lock:
            return conversation_id in self._conversations

    def delete_conversation(self, conversation_id: str) -> None:
        with self._lock:
            self._conversations.pop(conversation_id, None)

    def append_user_message(self, conversation_id: str, content: str) -> dict:
        return self._append_message(conversation_id, "user", content)

    def append_assistant_message(
        self,
        conversation_id: str,
        content: str,
        *,
        message_id: str | None = None,
    ) -> dict:
        return self._append_message(conversation_id, "assistant", content, message_id=message_id)

    def _append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        *,
        message_id: str | None = None,
    ) -> dict:
        timestamp = utc_now_iso()
        message = {
            "message_id": message_id or new_message_id(),
            "role": role,
            "content": content,
            "timestamp": timestamp,
        }
        with self._lock:
            conversation = self._conversations[conversation_id]
            conversation["messages"].append(message)
            conversation["updated_at"] = timestamp
        return deepcopy(message)

    def recent_messages(self, conversation_id: str, max_messages: int) -> list[dict]:
        with self._lock:
            messages = self._conversations[conversation_id]["messages"]
            return deepcopy(messages[-max_messages:])


conversation_store = ConversationStore()
