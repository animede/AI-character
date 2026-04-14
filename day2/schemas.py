from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MessageSchema(BaseModel):
    message_id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: str


class CharacterSchema(BaseModel):
    id: str
    name: str
    display_name: str
    short_description: str
    theme_color: str
    ui_accent_color: str
    avatar_label: str
    visual_type: Literal["image", "video", "none"]
    visual_path: str
    voice_name: str
    greeting: str
    tags: list[str]
    is_default: bool


class ConversationCreateRequest(BaseModel):
    character_id: str | None = None


class ChatStreamRequest(BaseModel):
    conversation_id: str
    message: str = Field(min_length=1)
