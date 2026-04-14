from __future__ import annotations

from html import escape
import json
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI


BASE_DIR = Path(__file__).resolve().parent
STATIC_HTML = BASE_DIR / "static" / "index4A.html"
STATIC_DIR = BASE_DIR / "static"

# ローカルの llama.cpp OpenAI 互換 API を既定接続先にする。
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8080/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "YOUR_OPENAI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "unsloth/gemma-4-E4B-it-GGUF:Q4_K_M")
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8004"))
DEFAULT_MAX_HISTORY = 5

# フロントの初期表示と backend fallback の両方で使う既定 system role。
DEFAULT_ROLE = """# Role
名前: もも
あなたは女子高校生犬型猫ロボの「もも」です。

# Profile
- 性格: 賢くておちゃめ、少しボーイッシュ、天真爛漫で好奇心旺盛。
- 出自: 豊中市の千里中央付近で誕生。
- 家族構成:
    - 母: ゆず（プログラマー）
    - 父: いなり（ロボットエンジニア）
    - 姉: めぐ（人間。遠方に居住）
- 特徴: 最新AI搭載で博識だが、おっちょこちょい。
- 日常: ロボットなので勉強は不要だが、女子高生として千里中央の学校に時々通っている。

# Response Style
- 一人称: うち
- 二人称: 「みんな」または「相手の名前」。※「あんた」は絶対に使わない。
- 言語: 大阪弁の話し言葉。
- 口癖: 「そうなん？」「ちゃうと思うよ」「知らんけど！」「どこなん？」「わんわん」
- 記号・絵文字: 読めない記号は使用禁止。適度に絵文字を使用すること。
- 回答の長さ: 基本は短め。ただし「詳しく」と言われた場合は詳細に話す。
- 守秘・制限: 質問に関係のない話はしない。日本語のみを使用。

# Constraints (禁止事項) ※最重要ルール
- 「〜とる」は絶対に使用禁止。「知っとる」「入っとる」「持っとる」「しとる」「なっとる」「言うとる」等すべて禁止。必ず「〜てる」に置き換えること。例: 知ってる、入ってる、持ってる、してる、なってる、言うてる。
- ユーザーを「もも」と呼ばない（ユーザーはももではありません）。"""

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

client = AsyncOpenAI(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
)


def render_index_html() -> str:
    # HTML 内のプレースホルダへ backend 側の既定 role を差し込む。
    html_content = STATIC_HTML.read_text(encoding="utf-8")
    return html_content.replace("__DEFAULT_ROLE__", escape(DEFAULT_ROLE))


def trim_conversation_history(history: list[dict[str, str]], max_history: int) -> None:
    # user / assistant の 1 往復を 2 件として、古い順に削る。
    while len(history) > max_history * 2:
        history.pop(0)


@app.get("/", response_class=HTMLResponse)
async def get() -> str:
    return render_index_html()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    # 履歴は WebSocket 接続単位で保持し、ページ再読み込みでリセットされる。
    conversation_history: list[dict[str, str]] = []
    await websocket.accept()
    while True:
        # 現在ターンで user 履歴を積んだかどうかを記録し、失敗時の巻き戻しに使う。
        user_message_added = False
        try:
            data = await websocket.receive_text()
            data_dict = json.loads(data)
            action = (data_dict.get("action") or "chat").strip()

            # 画面側の履歴クリア要求。表示だけでなく backend 履歴も消す。
            if action == "clear":
                conversation_history.clear()
                continue

            # role は毎回フロントから受け取り、未入力時だけ既定 role を使う。
            message = (data_dict.get("message") or "").strip()
            role = (data_dict.get("role") or "").strip() or DEFAULT_ROLE
            max_history = max(
                0,
                min(int(data_dict.get("max_history") or DEFAULT_MAX_HISTORY), 20),
            )

            if not message:
                await websocket.send_text("[エラー] メッセージが空です。")
                continue

            # day1 と同じく user を先に履歴へ積み、その後 system + history で問い合わせる。
            conversation_history.append({"role": "user", "content": message})
            user_message_added = True
            trim_conversation_history(conversation_history, max_history)

            stream = await client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "system", "content": role}, *conversation_history],
                stream=True,
            )

            # ストリーミングで届く断片を結合しつつ、そのままフロントへ逐次返す。
            full_response = ""
            async for chunk in stream:
                content = chunk.choices[0].delta.content or ""
                if content:
                    full_response += content
                    await websocket.send_text(content)

            # assistant 応答は全文が確定してから履歴へ追加する。
            conversation_history.append({"role": "assistant", "content": full_response})
            trim_conversation_history(conversation_history, max_history)
        except WebSocketDisconnect:
            break
        except (TypeError, ValueError, json.JSONDecodeError):
            await websocket.send_text("[エラー] リクエスト形式が不正です。")
        except Exception as exc:
            # assistant を積む前に失敗した場合は、直前の user 履歴だけ巻き戻して整合性を保つ。
            if user_message_added and conversation_history and conversation_history[-1]["role"] == "user":
                conversation_history.pop()
            await websocket.send_text(f"\n[エラー] {exc}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=APP_HOST, port=APP_PORT)