from __future__ import annotations

from fastapi import APIRouter

from character_registry import get_default_character, list_public_characters
from llm_client import llm_health_status
from settings import LLM_MODEL


router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health() -> dict:
    default_character = get_default_character()
    llm_status = llm_health_status()
    return {
        "status": "ok",
        "llm_status": llm_status,
        "model": LLM_MODEL,
        "default_character_id": default_character.id,
    }


@router.get("/characters")
def characters() -> dict:
    return {"characters": list_public_characters()}
