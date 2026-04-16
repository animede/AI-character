# day1_5 LINE風チャットアプリ

以下の記事を参照して構成した、FastAPI + WebSocket + 単一 HTML のシンプルな LINE 風チャットアプリです。

- 参照記事: [連載:AIキャラの作り方ー（Ｄay-1.5）](https://note.com/ai_meg/n/n521427b622d2)

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

## llama.cpp サーバ起動例

`day1_5` は、OpenAI 互換 API として `llama.cpp` の `llama-server` を利用できます。

Linux / macOS での基本起動例:

```bash
cd /home/animede/llama.cpp/build/bin
LD_LIBRARY_PATH=. ./llama-server \
  -hf unsloth/gemma-4-E4B-it-GGUF:Q4_K_M \
  --host 0.0.0.0 \
  --port 8080 \
  --reasoning off
```

Windows では、環境によって `--host 0.0.0.0` を付けると起動エラーになる場合があります。
その場合は `--host 127.0.0.1` に変更してください。

Windows での例:

```powershell
cd C:\path\to\llama.cpp\build\bin
$env:LD_LIBRARY_PATH = "."
.\llama-server.exe `
  -hf unsloth/gemma-4-E4B-it-GGUF:Q4_K_M `
  --host 127.0.0.1 `
  --port 8080 `
  --reasoning off
```

コンテキスト長を大きめに固定したい場合の例:

```bash
cd /home/animede/llama.cpp/build/bin
LD_LIBRARY_PATH=. ./llama-server \
  -hf unsloth/gemma-4-E4B-it-GGUF:Q4_K_M \
  --host 0.0.0.0 \
  --port 8080 \
  --reasoning off \
  --ctx-size 131072
```

### `--threads` の付け方

- `--threads N`
  - トークン生成時に使う CPU スレッド数です
- `--threads-batch N`
  - プロンプト投入やバッチ処理に使う CPU スレッド数です
- どちらも省略すると、`llama-server` の既定値で動きます

例: 生成とバッチ処理を 10 スレッドずつにしたい場合

```bash
cd /home/animede/llama.cpp/build/bin
LD_LIBRARY_PATH=. ./llama-server \
  -hf unsloth/gemma-4-E4B-it-GGUF:Q4_K_M \
  --host 0.0.0.0 \
  --port 8080 \
  --reasoning off \
  --threads 10 \
  --threads-batch 10
```

まずはスレッド指定なしで試し、必要な場合だけ `--threads` と `--threads-batch` を付けて比較するのが安全です。

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
