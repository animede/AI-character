from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

from settings import TTS_AUDIO_FORMAT, TTS_ENABLED, TTS_SPEAKER_ID, TTS_TIMEOUT_SECONDS, TTS_URL


def sanitize_tts_text(text: str) -> str:
    # Markdown 記号や絵文字だけを落として、日本語本文はそのまま残す。
    cleaned = text.replace("#", " ").replace("*", " ").replace("`", " ")
    # 文字ごとのフィルタで、読み上げを崩す絵文字系コードポイントを落とす。
    cleaned = "".join(_sanitize_char(char) for char in cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _sanitize_char(char: str) -> str:
    # 結合絵文字や装飾記号は TTS が崩れやすいので空白へ逃がす。
    codepoint = ord(char)
    if codepoint in {0x200D, 0xFE0F}:
        return " "
    if 0x1F300 <= codepoint <= 0x1FAFF:
        return " "
    if 0x2600 <= codepoint <= 0x27BF:
        return " "
    return char


class TTSClient:
    def __init__(
        self,
        *,
        base_url: str = TTS_URL,
        speaker_id: str = TTS_SPEAKER_ID,
        timeout_seconds: float = TTS_TIMEOUT_SECONDS,
        enabled: bool = TTS_ENABLED,
    ) -> None:
        # settings.py の既定値を受けつつ、テストでは差し替えられるようにしている。
        self.base_url = base_url.rstrip("/")
        self.speaker_id = str(speaker_id)
        self.timeout_seconds = timeout_seconds
        self.enabled = enabled
        self.audio_format = TTS_AUDIO_FORMAT

    def is_available(self) -> bool:
        # 有効フラグ、接続先 URL、speaker の 3 条件がそろったときだけ利用可能とみなす。
        return self.enabled and bool(self.base_url) and bool(self.speaker_id)

    def synthesize(self, text: str) -> bytes:
        if not self.is_available():
            raise RuntimeError("TTS is disabled")

        sanitized = sanitize_tts_text(text)
        if not sanitized:
            # 記号除去の結果、読む本文が残らなければ無音として返す。
            return b""

        # audio_query と synthesis の 2 段 API を順に呼び、最終的な音声 bytes を返す。
        params = urllib.parse.urlencode({"text": sanitized, "speaker": self.speaker_id})
        query_request = urllib.request.Request(
            f"{self.base_url}/audio_query?{params}",
            data=sanitized.encode("utf-8"),
            method="POST",
        )
        with urllib.request.urlopen(query_request, timeout=self.timeout_seconds) as response:
            # 音声そのものではなく、まず合成パラメータ JSON を受け取る。
            query_data = json.loads(response.read().decode("utf-8"))

        synthesis_request = urllib.request.Request(
            f"{self.base_url}/synthesis?{params}",
            data=json.dumps(query_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(synthesis_request, timeout=self.timeout_seconds) as response:
            # 最終レスポンスは wav などの生 bytes としてそのまま返す。
            return response.read()