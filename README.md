# AI-character

AI キャラクタ会話アプリの学習用リポジトリです。

このリポジトリは、段階的に実装を学べるように複数のディレクトリで構成されています。

## ディレクトリ構成

- `day1/`
  - CLI ベースで LLM の role 設定、履歴管理、ストリーミングを試すためのサンプルです
- `day1_5/`
  - day1 の対話ロジックをブラウザ GUI に載せ替えた中間段階のアプリです
  - day1 から day2 へ進むための橋渡し的な位置づけです
- `day2/`
  - Web アプリとして整理した AI キャラクタ会話アプリです
  - 既定ポートは `8001` ですが、必要に応じて `APP_PORT=8004` で `day1_5` と同じポートでも起動できます

## 参照ドキュメント

- [day1_5/README.md](day1_5/README.md)
- [day1_5/IMPLEMENTATION.md](day1_5/IMPLEMENTATION.md)
- [day2/README.md](day2/README.md)

## 補足

- `day1_5` と `day2` はローカルまたは外部の OpenAI 互換 API を前提にしています
- 既定では `LLM_BASE_URL=http://127.0.0.1:8080/v1` を参照します
