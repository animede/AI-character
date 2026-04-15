# day2 AIキャラ会話Webアプリ

## 概要

`day2` は、`llama.cpp` の OpenAI 互換 API を利用して AIキャラと会話するための Webアプリです。
FastAPI をバックエンドに使い、フロントエンドはシンプルな静的 HTML/CSS/JavaScript で構成しています。

主な特徴は次のとおりです。

- 軽量な会話管理
- キャラクター定義の分離
- WebSocket によるストリーミング応答
- 文字単位に近い逐次表示
- キャラクター画像の表示

## ディレクトリ構成

### バックエンド

- `webapp_main.py`
  - FastAPI アプリの起動入口です。
  - API ルータを登録し、`static` ディレクトリを配信します。

- `api_chat.py`
  - 会話関連 API を定義します。
  - 会話作成、会話取得、会話クリア、WebSocket 会話を担当します。

- `api_meta.py`
  - メタ情報 API を定義します。
  - ヘルスチェックとキャラクター一覧取得を担当します。

- `llm_client.py`
  - `llama.cpp` の OpenAI 互換 API へ接続するラッパです。
  - メッセージ配列の構築、ストリーミング受信、ヘルス確認を担当します。

- `conversation_store.py`
  - 会話データをメモリ上で管理します。
  - 会話の作成、取得、メッセージ追加、履歴保持を担当します。

- `character_registry.py`
  - キャラクター定義を管理します。
  - 現在は `もも` の設定を保持しています。
  - `visual_type`、`visual_path`、`voice_name` もここで定義します。

- `schemas.py`
  - API 入出力で使う Pydantic モデルを定義します。

- `settings.py`
  - 接続先 URL、モデル名、履歴件数、ポートなどの設定を管理します。

### フロントエンド

- `static/index.html`
  - Web UI の本体です。
  - キャラクター表示、会話エリア、入力欄を定義します。

- `static/style.css`
  - UI の見た目とレイアウトを定義します。
  - 会話エリアの内部スクロールもここで制御しています。

- `static/app.js`
  - フロントエンドの状態管理と API 通信を担当します。
  - WebSocket 応答の受信、描画キュー、会話表示更新を行います。

### アセット

- `static/assets/characters/momo_music.jpg`
  - もものキャラクター画像です。

## パスの扱い

- `visual_path` には、OS の実ファイルパスではなく、ブラウザから参照する URL パスを設定します
- 例: `/static/assets/characters/momo_music.jpg`
- `C:\\images\\momo.jpg` や `/home/user/image.jpg` のようなローカルファイルパスは設定しません
- サーバ内部のファイル参照は `pathlib.Path` を使っているため、Windows と Linux の両方で扱えます

## ストリーミング仕様

会話の送受信は WebSocket で行います。
フロントエンドは `/ws` に接続し、`action: "chat"` を送信すると次の 4 種類のイベントを受信します。

- `start`
  - 応答開始通知
- `delta`
  - 追記文字列
- `end`
  - 応答完了通知
- `error`
  - エラー通知

フロントエンド側では、`delta` を描画キューに積み、文字単位に近い形で表示します。

## セットアップと起動方法

リポジトリのルートディレクトリで仮想環境を作成してから起動します。

既定の待受ポートは `8001` です。
`day1_5` と同じポートで起動したい場合は、環境変数 `APP_PORT=8004` を付けて起動します。

依存パッケージのインストールは、`requirements.txt` を使う方法と、個別に `pip install` する方法のどちらでも構いません。

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r day2/requirements.txt
# または
# python -m pip install fastapi uvicorn openai websockets
cd day2
python webapp_main.py
```

`8004` で起動する場合:

```bash
cd day2
APP_PORT=8004 python webapp_main.py
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r day2/requirements.txt
# または
# python -m pip install fastapi uvicorn openai websockets
cd day2
python webapp_main.py
```

`8004` で起動する場合:

```powershell
cd day2
$env:APP_PORT = "8004"
python webapp_main.py
```

Windows コマンドプロンプト:

```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r day2/requirements.txt
REM または
REM python -m pip install fastapi uvicorn openai websockets
cd day2
python webapp_main.py
```

`8004` で起動する場合:

```bat
cd day2
set APP_PORT=8004
python webapp_main.py
```

仮想環境を有効化せずに直接実行したい場合は、`day2` ディレクトリで次を使います。

Linux / macOS:

```bash
../.venv/bin/python webapp_main.py
```

`8004` で起動する場合:

```bash
APP_PORT=8004 ../.venv/bin/python webapp_main.py
```

Windows PowerShell / コマンドプロンプト:

```bat
..\.venv\Scripts\python.exe webapp_main.py
```

`8004` で起動する場合:

```bat
set APP_PORT=8004
..\.venv\Scripts\python.exe webapp_main.py
```

起動後、ブラウザで次を開きます。

```text
http://127.0.0.1:8001
```

`8004` で起動した場合は次を開きます。

```text
http://127.0.0.1:8004
```

## 前提条件

- `llama.cpp` のサーバが起動していること
- 既定では `http://127.0.0.1:8080/v1` を利用します
- Windows で `llama-server` を起動する際に `--host 0.0.0.0` でエラーになる場合は、`--host 127.0.0.1` に変更してください
- Python 3.10 以上を推奨します
- 依存パッケージ一覧は [day2/requirements.txt](day2/requirements.txt) に記載しています
- 必要な Python パッケージは `fastapi`、`uvicorn`、`openai`、`websockets` です

## 補足

- 会話履歴はメモリ保持のみです
- サーバ再起動で履歴は消えます
- 認証や永続化はまだ入れていません
- 将来的に画像、動画、音声名を使ったキャラ拡張が可能です
