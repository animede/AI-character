# coding: utf_8
"""LLMストリーミングテスト（履歴なし） - ももちゃんシステムロール"""
from openai import OpenAI
import sys

# LLMサーバー設定　起動しているLLMサーバーのURLとAPIキーを指定、ローカルで動かすならキーとモデルは適当で良いです。
LLM_BASE_URL = "http://0.0.0.0:8080/v1"
LLM_API_KEY = "YOUR_OPENAI_API_KEY"
LLM_MODEL = "unsloth/gemma-4-E2B-it-GGUF"

# システムロール（ももちゃん）
SYSTEM_ROLE = """# Role
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


def stream_chat(user_message):
    """ストリーミングでLLMとチャット（履歴なし・毎回独立）"""
    # OpenAIクライアントの初期化
    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

    messages = [
        {"role": "system", "content": SYSTEM_ROLE},
        {"role": "user", "content": user_message},
    ]

    print(f"\n[User] {user_message}")
    print("[もも] ", end="", flush=True)
    # LLMにStreamingでチャットリクエストを送信
    stream = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        max_tokens=300,
        temperature=0.7,
        stream=True,
    )
    # ストリームからチャンクを受け取りながら表示
    full_response = ""
    for chunk in stream:
        content = chunk.choices[0].delta.content or ""
        print(content, end="", flush=True)
        full_response += content

    print("\n")
    return full_response


if __name__ == "__main__":
    print("=" * 50)
    print("ももちゃん ストリーミングチャット（履歴なし）")
    print(f"Server: {LLM_BASE_URL}")
    print(f"Model:  {LLM_MODEL}")
    print("=" * 50)
    #   コマンドライン引数があればそれをメッセージとしてチャット、なければ対話モード
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        stream_chat(user_input)
    else:
        print("メッセージを入力してください（'q'で終了）\n")
        # 対話モード（履歴なし）　ユーザーが入力したメッセージをももちゃんが回答します。'q'で終了。
        while True:
            user_input = input("[入力] ").strip()
            if user_input.lower() in ("q", "quit", "exit"):
                print("終了します。")
                break
            if not user_input:
                continue
            stream_chat(user_input)
