# day2 AIキャラ会話Webアプリ

## 概要

`day2` は、`llama.cpp` の OpenAI 互換 API を利用して AIキャラと会話するための Webアプリです。
FastAPI をバックエンドに使い、フロントエンドはシンプルな静的 HTML/CSS/JavaScript で構成しています。

主な特徴は次のとおりです。

- 軽量な会話管理
- キャラクター定義の分離
- ストリーミング応答
- 文字単位に近い逐次表示
- キャラクター画像の表示

## ディレクトリ構成

### バックエンド

- `webapp_main.py`
  - FastAPI アプリの起動入口です。
  - API ルータを登録し、`static` ディレクトリを配信します。

- `api_chat.py`
  - 会話関連 API を定義します。
  - 会話作成、会話取得、会話クリア、ストリーミング会話を担当します。

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
  - ストリーミング応答の受信、描画キュー、会話表示更新を行います。

### アセット

- `static/assets/characters/momo_music.jpg`
  - もものキャラクター画像です。

## パスの扱い

- `visual_path` には、OS の実ファイルパスではなく、ブラウザから参照する URL パスを設定します
- 例: `/static/assets/characters/momo_music.jpg`
- `C:\\images\\momo.jpg` や `/home/user/image.jpg` のようなローカルファイルパスは設定しません
- サーバ内部のファイル参照は `pathlib.Path` を使っているため、Windows と Linux の両方で扱えます

## ストリーミング仕様

会話 API は HTTP ストリームで NDJSON を返します。
イベントは次の 4 種類です。

- `start`
  - 応答開始通知
- `delta`
  - 追記文字列
- `end`
  - 応答完了通知
- `error`
  - エラー通知

フロントエンド側では、`delta` を描画キューに積み、文字単位に近い形で表示します。

## 起動方法

`day2` ディレクトリで次を実行します。

Linux / macOS:

```bash
.venv/bin/python webapp_main.py
```

Windows PowerShell:

```powershell
.venv\Scripts\python.exe webapp_main.py
```

Windows コマンドプロンプト:

```bat
.venv\Scripts\python.exe webapp_main.py
```

起動後、ブラウザで次を開きます。

```text
http://127.0.0.1:8001
```

## 前提条件

- `llama.cpp` のサーバが起動していること
- 既定では `http://127.0.0.1:8080/v1` を利用します
- 必要な Python パッケージ
  - `fastapi`
  - `uvicorn`
  - `openai`

## 補足

- 会話履歴はメモリ保持のみです
- サーバ再起動で履歴は消えます
- 認証や永続化はまだ入れていません
- 将来的に画像、動画、音声名を使ったキャラ拡張が可能です
