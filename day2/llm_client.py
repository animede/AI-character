from __future__ import annotations

import urllib.error
import urllib.request

from openai import OpenAI

from settings import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, OPENAI_TIMEOUT_SECONDS


def create_client() -> OpenAI:
    return OpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        timeout=OPENAI_TIMEOUT_SECONDS,
    )


def build_messages(system_prompt: str, messages: list[dict]) -> list[dict]:
    payload = [{"role": "system", "content": system_prompt}]
    for message in messages:
        payload.append({"role": message["role"], "content": message["content"]})
    return payload


def stream_chat_chunks(messages: list[dict]):
    client = create_client()
    stream = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        max_tokens=400,
        temperature=0.7,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta


def llm_health_status() -> str:
    health_url = LLM_BASE_URL.rstrip("/")
    if health_url.endswith("/v1"):
        health_url = health_url[:-3]
    health_url = f"{health_url}/health"
    try:
        with urllib.request.urlopen(health_url, timeout=5) as response:
            if response.status == 200:
                return "ok"
    except (urllib.error.URLError, TimeoutError, ValueError):
        return "error"
    return "error"
