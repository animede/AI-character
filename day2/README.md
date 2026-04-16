# day2 AIキャラ会話Webアプリ

## 概要

`day2` は、`llama.cpp` の OpenAI 互換 API を利用して AIキャラと会話するための Webアプリです。
FastAPI をバックエンドに使い、フロントエンドはシンプルな静的 HTML/CSS/JavaScript で構成しています。

主な特徴は次のとおりです。

- 軽量な会話管理
- キャラクター定義の分離
- WebSocket によるストリーミング応答
- 文字単位に近い逐次表示
- 文区切りごとの音声ストリーミング
- キャラクター画像の表示

## day1_5 からの追加機能

`day1_5` は、day1 の履歴付き会話を GUI 化した Web アプリでした。
`day2` では、その構成を土台にして次の機能を追加しています。

- 会話管理の強化
  - 会話の新規作成、取得、クリアを API として扱えるようにしています
  - 履歴管理をメモリ上の会話ストアに切り出しています
- キャラクター表示の追加
  - キャラクター画像に加えて、動画素材による状態表示を扱えるようにしています
  - 応答中、待機中、初期状態に応じて見た目を切り替えます
- TTS 連携
  - Aivis / VOICEVOX 互換エンジンに接続して音声を生成できます
  - 文区切りごとに音声セグメントを生成し、順番に再生します
- ボイスとモデルの可視化
  - 利用可能な話者、style ID、インストール済みモデルを一覧表示します
  - 現在使う読み上げボイスを UI から切り替えられます
- メタ情報 API の追加
  - LLM / TTS の health 状態を返す API を追加しています
  - キャラクター一覧や TTS カタログも API として取得できます
- UI / UX の拡張
  - 音声再生キュー、拡大表示、フッタークレジットなどの表示要素を追加しています
  - day1_5 よりも運用確認しやすい情報パネルを持たせています

位置づけとしては、`day1_5` の GUI 会話アプリを、音声対応と状態表示を備えたアプリへ発展させた段階です。

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

- `stream_segmenter.py`
  - LLM の `delta` を文区切り単位にまとめます。
  - TTS に渡す短いセグメントを切り出します。

- `tts_client.py`
  - Aivis / VOICEVOX 互換 TTS API を呼び出します。
  - `audio_query` と `synthesis` を使って WAV を生成します。

### フロントエンド

- `static/index.html`
  - Web UI の本体です。
  - キャラクター表示、会話エリア、入力欄を定義します。

- `static/style.css`
  - UI の見た目とレイアウトを定義します。
  - 会話エリアの内部スクロールもここで制御しています。

- `static/app.js`
  - フロントエンドの状態管理と API 通信を担当します。
  - WebSocket 応答の受信、描画キュー、音声再生キュー、会話表示更新を行います。

### アセット

- `static/assets/characters/character.jpg`
  - もものキャラクター画像です。

## パスの扱い

- `visual_path` には、OS の実ファイルパスではなく、ブラウザから参照する URL パスを設定します
- 例: `/static/assets/characters/character.jpg`
- `C:\\images\\momo.jpg` や `/home/user/image.jpg` のようなローカルファイルパスは設定しません
- サーバ内部のファイル参照は `pathlib.Path` を使っているため、Windows と Linux の両方で扱えます

## ストリーミング仕様

会話の送受信は WebSocket で行います。
フロントエンドは `/ws` に接続し、`action: "chat"` を送信すると次のイベントを受信します。

- `start`
  - 応答開始通知
- `delta`
  - 追記文字列
- `audio`
  - 文区切りで生成された音声セグメント
- `end`
  - 応答完了通知
- `error`
  - エラー通知

フロントエンド側では、`delta` を描画キューに積み、文字単位に近い形で表示します。
`audio` は再生キューに積まれ、前の音声が終わり次第順番に再生されます。

`audio` イベントの例:

```json
{
  "type": "audio",
  "message_id": "msg_xxx",
  "segment_index": 0,
  "text": "うち、ももやで。",
  "audio_format": "wav",
  "audio_b64": "UklGR..."
}
```

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

現在このリポジトリでよく使う起動例は次のとおりです。

- LLM サーバ: `http://127.0.0.1:8080/v1`
- Web アプリ: `http://127.0.0.1:8001`
- TTS サーバ: `http://127.0.0.1:10101`

Linux / macOS で、リポジトリルートから直接起動する例:

```bash
cd day2
TTS_ENABLED=true APP_PORT=8001 ../.venv/bin/python webapp_main.py
```

起動確認は、別ターミナルから次で行えます。

```bash
curl -s http://127.0.0.1:8001/api/health
```

応答例:

```json
{
  "status": "ok",
  "llm_status": "ok",
  "model": "unsloth/gemma-4-E4B-it-GGUF:Q4_K_M",
  "default_character_id": "momo",
  "tts_available": true,
  "tts_status": {
    "configured": true,
    "available": true,
    "base_url": "http://127.0.0.1:10101",
    "protocol": "voicevox-compatible",
    "audio_format": "wav",
    "default_style_id": "888753760",
    "version": "1.0.0",
    "error": null
  }
}
```

利用可能な AivisSpeech Engine の話者・スタイル・インストール済みモデル一覧は、次で確認できます。

```bash
curl -s http://127.0.0.1:8001/api/tts/voices
```

この API では主に次の情報を返します。

- `speakers`: `/speakers` をもとにした話者一覧と style ID 一覧
- `models`: `/aivm_models` をもとにしたインストール済み AIVM モデル一覧
- `selected_voice`: 現在の `TTS_SPEAKER_ID` に一致する既定スタイル
- `version`: 接続先 AivisSpeech Engine のバージョン

## 前提条件

- `llama.cpp` のサーバが起動していること
- 既定では `http://127.0.0.1:8080/v1` を利用します
- 音声ストリーミングを有効にするには、Aivis / VOICEVOX 互換 TTS サーバを別途起動してください。`TTS_ENABLED=true` を付けると明示的に TTS 有効設定で起動できます
- TTS エンジンは [Aivis Project](https://aivis-project.com/) の AivisSpeech Engine を利用します。このアプリには同梱していないため、別途インストールが必要です
- 既定の TTS 接続先は `http://127.0.0.1:10101`、話者 ID は `888753760` です
- AivisSpeech Engine では、利用可能な話者 ID は `/speakers`、インストール済みモデル情報は `/aivm_models` から取得できます。このアプリでは `/api/tts/voices` にまとめて公開しています
- Windows / macOS では、AivisSpeech 本体に同梱された AivisSpeech Engine をそのまま起動する方法が簡単です
- 引用元: Aivis-Project / AivisSpeech-Engine README の「導入方法 > Windows / macOS」

> Windows / macOS では、AivisSpeech Engine を単独でインストールすることもできますが、AivisSpeech 本体に付属する AivisSpeech Engine を単独で起動させた方がより簡単です。
>
> AivisSpeech に同梱されている AivisSpeech Engine の実行ファイル (`run.exe` / `run`) のパスは以下のとおりです。
>
> - Windows: `C:\Program Files\AivisSpeech\AivisSpeech-Engine\run.exe`（導入先によってパスは異なります）
> - Windows (ユーザー権限インストール): `C:\Users\(ユーザー名)\AppData\Local\Programs\AivisSpeech\AivisSpeech-Engine\run.exe`
> - macOS: `/Applications/AivisSpeech.app/Contents/Resources/AivisSpeech-Engine/run`（導入先によってパスは異なります）
> - macOS (ユーザー権限インストール): `~/Applications/AivisSpeech.app/Contents/Resources/AivisSpeech-Engine/run`
>
> 出典: [Aivis-Project/AivisSpeech-Engine README](https://github.com/Aivis-Project/AivisSpeech-Engine) 「導入方法 > Windows / macOS」

- Windows で `llama-server` を起動する際に `--host 0.0.0.0` でエラーになる場合は、`--host 127.0.0.1` に変更してください
- Python 3.10 以上を推奨します
- 依存パッケージ一覧は [day2/requirements.txt](day2/requirements.txt) に記載しています
- 必要な Python パッケージは `fastapi`、`uvicorn`、`openai`、`websockets` です

TTS を有効にした起動例:

```bash
cd day2
TTS_ENABLED=true python webapp_main.py
```

## 操作方法

基本的な使い方は次の流れです。

1. ブラウザで `http://127.0.0.1:8001` を開きます。
2. 左側の「キャラクター」で会話相手を選びます。
3. 必要なら「キャラクタロール」を編集して、口調や設定を調整します。
4. 「会話ターン記憶数」で、直近何ターンぶん履歴を渡すかを調整します。
5. TTS サーバが接続されている場合は、「音声ストリーミング」を ON/OFF します。
6. 左側の「読み上げボイスを選ぶ」で、AivisSpeech Engine の style ID を切り替えられます。
7. 「現在のTTSボイス」には、次の送信で使われる話者 / スタイルが表示されます。
8. 「利用可能なボイスとモデル」を開くと、取得済みの話者一覧・style ID 一覧・インストール済みモデル一覧を確認できます。
9. 下部の入力欄にメッセージを入れて「送信」します。

補足:

- 初回の health チェックで TTS が未接続表示でも、その後にボイス一覧の取得に成功した場合は、自動で TTS 接続済みとして音声ストリーミングを有効化します。

送信後の画面挙動:

- assistant の返答は WebSocket でストリーミング表示されます
- 音声ストリーミングが ON のときは、文区切りごとに順番再生されます
- 読み上げボイスを切り替えると、次の送信ターンから新しい style ID で音声合成されます
- 音声再生中はキャラクター表示が `talking.mp4` に切り替わります
- 応答後の待機中は `waiting.mp4` に切り替わります
- 初期状態では `character.jpg` を表示します

キャラクター表示の操作:

- 左側の小さいキャラクター画像・動画をクリックすると、右側上部に拡大表示します
- 拡大表示中は左側の小表示パネルを隠します
- 右上の `×` ボタンで拡大表示を閉じます

会話操作:

- 「新しい会話」: 同じキャラクターのまま新しい会話 ID を作成します
- 「履歴クリア」: 現在の履歴を破棄し、初期状態の会話に戻します
- Enter: 送信します
- Shift + Enter: 改行します

音声まわりの注意:

- `audio_enabled` は現行クライアントが常に送信します
- `TTS_ENABLED=true` でも、TTS サーバに接続できなければ backend 側で音声送信は無効になります
- ブラウザの自動再生制限がある場合、最初のユーザー操作後に音声再生が安定します

## 補足

- 会話履歴はメモリ保持のみです
- サーバ再起動で履歴は消えます
- 認証や永続化はまだ入れていません
- 将来的に画像、動画、音声名を使ったキャラ拡張が可能です
