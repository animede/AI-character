# Day1: llama.cpp サーバ導入と最初のキャラ会話

このフォルダーは、ローカルで動かす llama.cpp サーバに OpenAI 互換 API として接続し、キャラ会話の基本を試すためのサンプルです。

以下の内容は、次の記事を参考に整理しています。

- 参考記事: [連載:AIキャラの作り方ー（Ｄay-1）](https://note.com/ai_meg/n/n67ae053a9598)
- 公式ドキュメント: [ggml-org/llama.cpp install.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/install.md)

この README では、記事の流れを踏まえつつ、このリポジトリの Day1 サンプルに合わせて手順をまとめています。

## 前提

- Windows PC を使う想定です
- コマンドプロンプト、PowerShell、または Windows Terminal を開けること
- Python と pip が使えること
- Visual C++ 再頒布可能パッケージが入っていること

Visual C++ 再頒布可能パッケージは Microsoft 公式の配布ページから導入できます。

- 参考: [最新の Visual C++ 再頒布可能パッケージ](https://learn.microsoft.com/ja-jp/cpp/windows/latest-supported-vc-redist?view=msvc-170)

## 1. llama.cpp をインストールする

記事では、Windows では `winget` を使った導入が簡単と紹介されています。まずターミナルを開いて次を実行します。

```powershell
winget install llama.cpp
```

途中で利用規約への同意を求められたら `Y` で進めます。

これで `llama-cli` や `llama-server` など、ビルド済みの llama.cpp コマンドが入ります。

## 2. llama.cpp 単体で動作確認する

まずは CLI でモデルが起動するか確認します。

記事では Gemma 4 系の量子化モデルが例として使われています。軽めなら E2B、少し賢さを優先するなら E4B が候補です。

```powershell
llama-cli -hf unsloth/gemma-4-E2B-it-GGUF:Q4_K_M --reasoning off
```

余力がある PC ならこちらでも構いません。

```powershell
llama-cli -hf unsloth/gemma-4-E4B-it-GGUF:Q4_K_M --reasoning off
```

初回はモデルが自動ダウンロードされます。プロンプトが出て会話できれば準備完了です。

## 3. llama.cpp サーバを起動する

Day1 の Python サンプルは OpenAI 互換 API として llama.cpp サーバへ接続します。別ターミナルで次を実行してください。

```powershell
llama-server -hf unsloth/gemma-4-E2B-it-GGUF:Q4_K_M --reasoning off --host 0.0.0.0 --port 8080
```

ポイント:

- `--reasoning off`: キャラ会話では応答を速くしやすい設定です
- `--host 0.0.0.0`: 他の端末やブラウザからも接続しやすくなります
- `--port 8080`: Day1 の各スクリプトが想定しているポートです

Windows で `--host 0.0.0.0` により問題が出る場合は、ローカル利用に絞って次のように `127.0.0.1` を指定して構いません。

```powershell
llama-server -hf unsloth/gemma-4-E2B-it-GGUF:Q4_K_M --reasoning off --host 127.0.0.1 --port 8080
```

起動できたら、`0.0.0.0:8080` で待受している旨のログが出ます。

## 4. Python パッケージを入れる

Day1 サンプルは OpenAI 互換 API クライアントとして `openai` パッケージを使います。

```powershell
python -m pip install openai
```

## 5. Day1 サンプルを試す

このフォルダーには次の 4 本があります。

- `test_llm_no_history.py`: 非ストリーミング、履歴なし
- `test_llm_stream_no_history.py`: ストリーミング、履歴なし
- `test_llm_history.py`: 非ストリーミング、履歴あり
- `test_llm_stream.py`: ストリーミング、履歴あり

既定では `http://0.0.0.0:8080/v1` を LLM サーバとして参照します。Windows で `127.0.0.1` で起動した場合は、各スクリプト内の `LLM_BASE_URL` も `http://127.0.0.1:8080/v1` に合わせてください。

### もっとも簡単な確認

```powershell
cd day1
python test_llm_no_history.py
```

### 返答を少しずつ表示したい場合

```powershell
cd day1
python test_llm_stream_no_history.py
```

### 数ターンぶん履歴を持たせたい場合

```powershell
cd day1
python test_llm_history.py
```

### 履歴あり + ストリーミング

```powershell
cd day1
python test_llm_stream.py
```

## 6. 1 行コマンドで試す

引数を渡せば単発実行もできます。

```powershell
python test_llm_no_history.py こんにちは
python test_llm_stream_no_history.py 千里中央ってどんな場所？
python test_llm_history.py さっきの話を覚えてる？
python test_llm_stream.py 今日の気分は？
```

## スクリプトの見どころ

記事の Day1 と同様に、このサンプルでも次の基本を押さえています。

- システムロールでキャラクターの性格や話し方を固定する
- `system` と `user` のメッセージを OpenAI 互換 API に渡す
- 履歴あり版では `user` / `assistant` の会話を配列に積んで短期記憶を再現する
- ストリーミング版では、生成された文字を順次表示して体感速度を上げる

## 詰まりやすい点

- `python test_llm_*.py` 実行時に接続エラーになる
  - `llama-server` が起動しているか確認してください
  - `8080` ポートで待受しているか確認してください
- `llama-server` コマンドが見つからない
  - `winget install llama.cpp` が成功しているか確認してください
  - 新しいターミナルを開き直してください
- 返答が遅い
  - E2B モデルに切り替える
  - `--reasoning off` を付ける

## 補足

- 記事内のコード例では E2B と E4B の両方が紹介されています
- この Day1 フォルダー内のサンプルは、既定で `unsloth/gemma-4-E2B-it-GGUF` を使う設定です
- もっと賢いモデルにしたい場合は、各スクリプトの `LLM_MODEL` を変更してください
