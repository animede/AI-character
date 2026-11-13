from __future__ import annotations

import base64
import json
import urllib.request

from fastapi import APIRouter, HTTPException, Request

from .llm_client import create_async_client
from .settings import LLM_BASE_URL, LLM_MODEL


router = APIRouter(prefix="/api", tags=["voice"])

# 押している間だけ録音する使い方なので、長くても 1 分ほど。16kHz・16bit・モノラルの WAV で約 2MB。
MAX_AUDIO_BYTES = 4 * 1024 * 1024

TRANSCRIBE_PROMPT = (
    "この音声を、話されたとおりに文字に起こしてください。句読点を付けてください。"
    "説明や前置きは書かず、文字起こしの結果だけを出力してください。"
)


def llm_supports_audio() -> bool | None:
    """llama-server が音声を受け取れるか(mmproj を読み込んだか)を /props で調べる。わからなければ None。"""
    root = LLM_BASE_URL[:-3] if LLM_BASE_URL.rstrip("/").endswith("/v1") else LLM_BASE_URL
    try:
        with urllib.request.urlopen(f"{root.rstrip('/')}/props", timeout=3) as response:
            props = json.loads(response.read().decode("utf-8"))
        return bool(props.get("modalities", {}).get("audio"))
    except Exception:
        return None


@router.get("/voice/status")
def voice_status() -> dict:
    return {"audio_input": llm_supports_audio(), "model": LLM_MODEL}


@router.post("/transcribe")
async def transcribe(request: Request) -> dict:
    """ブラウザで 16kHz・モノラルの WAV にした録音を受け取り、Gemma 4 に聞かせて文字にする。"""
    audio = await request.body()
    if not audio or len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="録音が空か、長すぎます。")
    if audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
        raise HTTPException(status_code=400, detail="WAV 形式の音声を送ってください。")

    client = create_async_client()
    try:
        completion = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "input_audio", "input_audio": {"data": base64.b64encode(audio).decode("ascii"), "format": "wav"}},
                    {"type": "text", "text": TRANSCRIBE_PROMPT},
                ],
            }],
            max_tokens=300,
            temperature=0,  # 文字起こしは答えが 1 つなので、毎回同じ結果にする
            stream=False,
        )
    except Exception as exc:
        if llm_supports_audio() is False:
            raise HTTPException(
                status_code=503,
                detail="いまの llama-server は音声を扱えません。--no-mmproj を付けずに、Gemma 4 の E2B か E4B で起動し直してください。",
            ) from exc
        raise HTTPException(status_code=502, detail=f"文字起こしに失敗しました: {exc}") from exc

    return {"text": (completion.choices[0].message.content or "").strip()}
