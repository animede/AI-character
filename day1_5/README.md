# day1_5 LINE風チャットアプリ

この記事の構成をベースにした、FastAPI + WebSocket + 単一 HTML のシンプルな LINE 風チャットアプリです。

day1_5 は、day1 の role / 履歴付き対話ロジックをブラウザ GUI に載せ替えたアプリです。
位置づけとしては、day1 から day2 へ進むための橋渡し的な段階にあります。

## ファイル構成

- `openai_gui_m4A.py`
  - FastAPI バックエンドです
  - `/` で HTML を返し、`/ws` で LLM ストリームを中継します
- `static/index4A.html`
  - HTML / JavaScript / CSS を 1 ファイルにまとめたフロントエンドです
- `requirements.txt`
  - 必要な Python パッケージ一覧です
  - WebSocket 接続用の `websockets` も含みます

## 起動方法

リポジトリルートで仮想環境を有効化してから実行します。

```bash
python -m pip install -r day1_5/requirements.txt
cd day1_5
python openai_gui_m4A.py
```

ブラウザで次を開きます。

```text
http://127.0.0.1:8004
```

## Windows での利用手順

Windows でこのアプリを使う場合は、まず Git と Python を入れてからリポジトリをクローンします。

事前準備:

- Git for Windows をインストールする
  - 公式サイト: <https://gitforwindows.org/>
- Python 3.11 前後をインストールする
- ターミナルを開いたときに PowerShell が起動した場合は、必要に応じて実行ポリシーを調整する
- LLM 用の OpenAI 互換 API を別途起動しておく

Git のインストール確認:

```powershell
git --version
```

バージョンが表示されれば、Git コマンドは使える状態です。

ターミナルを開いたときに PowerShell が起動した場合の例:

```powershell
git clone https://github.com/animede/AI-character.git
cd AI-character
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r day1_5\requirements.txt
cd day1_5
python openai_gui_m4A.py
```

ターミナルを開いたときにコマンドプロンプトが起動した場合の例:

```bat
git clone https://github.com/animede/AI-character.git
cd AI-character
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r day1_5\requirements.txt
cd day1_5
python openai_gui_m4A.py
```

起動後はブラウザで次を開きます。

```text
http://127.0.0.1:8004
```

補足:

- Git を使うのは、リポジトリを Windows 環境へ取得するためです
- このアプリは LLM 本体を内蔵していないため、`LLM_BASE_URL` で指す OpenAI 互換 API が別途必要です
- 既定値では `http://127.0.0.1:8080/v1` を参照するため、Windows 側でも同等の API を起動するか、環境変数を書き換えてください

## 環境変数

- `LLM_BASE_URL`
  - 既定値: `http://127.0.0.1:8080/v1`
- `LLM_API_KEY`
  - 既定値: `YOUR_OPENAI_API_KEY`
- `LLM_MODEL`
  - 既定値: `unsloth/gemma-4-E4B-it-GGUF:Q4_K_M`
- `APP_HOST`
  - 既定値: `127.0.0.1`
- `APP_PORT`
  - 既定値: `8004`

## 記事からの調整点

- ロール入力は、そのまま OpenAI API の `system` メッセージとして扱うようにしています
- WebSocket 接続先は固定 URL ではなく、ブラウザの現在ホストから自動生成します
- 接続先は現在の llama.cpp サーバ設定に合わせて `127.0.0.1:8080/v1` を既定にしています
