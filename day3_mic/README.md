# day3_mic AIキャラ会話Webアプリ(マイク対応)

`day3` に、マイクで話しかける機能を足したものです。`day3` はそのまま残しています。
セットアップや AivisSpeech の使い方など、そのほかは `day3` と同じです(`README_day3.md`)。

## 追加したこと

- 入力欄の横に「🎤 押して話す」ボタン。押している間だけ録音し、離すと声を文字にして入力欄に入れます
- 文字を確かめてから「送信」を押します。「話し終わったら自動で送る」にチェックを入れると、そのまま送ります
- 声を文字にするのは、会話と同じ llama-server(Gemma 4)です。文字起こし専用の AI は使いません

## しくみ

1. ブラウザで録音し、16kHz・モノラルの WAV に変換する(`static/mic.js`)
2. `POST /api/transcribe` に WAV を送る
3. サーバーが WAV を llama-server に `input_audio` として渡し、文字にしてもらう(`app/api_voice.py`)
4. 返ってきた文字を入力欄に入れる

## 動かし方

llama-server は、`--no-mmproj` を付けずに起動します(mmproj が音声を受け取る部分です)。

```powershell
llama-server -hf unsloth/gemma-4-E4B-it-GGUF:Q4_K_M --reasoning off -c 8192 --host 127.0.0.1 --port 8080
```

そのあと、`day3` と同じ手順でアプリを起動します。

```powershell
cd day3_mic
python webapp_main.py
```

ブラウザで http://127.0.0.1:8001 を開きます。初めて録音するときは、マイクを使ってよいかを聞かれるので「許可」を選びます。

llama-server が音声を扱えないとき(`--no-mmproj` を付けたときなど)は、マイクのボタンが「マイクは使えません」になります。

## day3 から変えたファイル

| ファイル | 変えたこと |
|---|---|
| `app/api_voice.py` | 新規。`/api/transcribe` と `/api/voice/status` |
| `static/mic.js` | 新規。録音、WAV への変換、送信 |
| `webapp_main.py` | `api_voice` のルーターを追加 |
| `static/index.html` | マイクのボタンと自動送信のチェック、`mic.js` の読み込み |
| `static/style.css` | マイクのボタンの見た目 |
