# coding: utf_8
"""LLMテスト（非ストリーミング） - ももちゃんシステムロール"""
from openai import OpenAI
import sys

# LLMサーバー設定
LLM_BASE_URL = "http://192.168.100.12:8080/v1"
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

MAX_HISTORY = 10  # 記憶する対話数（user+assistantのペア）

# 対話履歴
conversation_history = []


def chat(user_message):
    """非ストリーミングでLLMとチャット（履歴付き）"""
    # OpenAIクライアントの初期化
    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

    # ユーザーメッセージを履歴に追加
    conversation_history.append({"role": "user", "content": user_message})

    # 履歴がMAX_HISTORYペア（20メッセージ）を超えたら古いものを削除
    while len(conversation_history) > MAX_HISTORY * 2:
        conversation_history.pop(0)

    # メッセージ構築: system + 履歴
    messages = [{"role": "system", "content": SYSTEM_ROLE}] + conversation_history

    print(f"\n[User] {user_message}")
    # LLMにチャットリクエストを送信
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        max_tokens=300,
        temperature=0.7,
    )
    # LLMの回答を取得して表示
    full_response = response.choices[0].message.content
    print(f"[もも] {full_response}\n")

    # アシスタントの返答を履歴に追加
    conversation_history.append({"role": "assistant", "content": full_response})

    return full_response


if __name__ == "__main__":
    print("=" * 50)
    print("ももちゃん チャット テスト（非ストリーミング）")
    print(f"Server: {LLM_BASE_URL}")
    print(f"Model:  {LLM_MODEL}")
    print(f"履歴:   最大{MAX_HISTORY}ペア")
    print("=" * 50)
    # コマンドライン引数があればそれをメッセージとしてチャット、なければ対話モード
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        chat(user_input)
    else:
        print("メッセージを入力してください（'q'で終了 / 'clear'で履歴クリア）\n")
        # 対話モード（履歴あり）　ユーザーが入力したメッセージをももちゃんが回答します。'q'で終了、'clear'で履歴クリア。
        while True:
            user_input = input("[入力] ").strip()
            if user_input.lower() in ("q", "quit", "exit"):
                print("終了します。")
                break
            if user_input.lower() == "clear":
                conversation_history.clear()
                print("[履歴をクリアしました]\n")
                continue
            if not user_input:
                continue
            chat(user_input)
