# Day4で進める waiting 動画ベースの口パク試作

Day4 では、Day3 の会話アプリ構成を維持したまま、waiting 動画に限定した口パク表現の試作を進めます。

## 目的

- `day3` の既存会話体験を壊さずに、見た目の没入感を上げる
- `talking.mp4` への単純切替より、音声と口の動きの一致感を高める
- 実装負担を抑えるため、まずは waiting 動画だけに範囲を絞る

## Day4 の前提

- ベースアプリは `day3` をそのまま複製している
- 既定ポートは `8005` に変更して、`day3` の `8001` と分離する
- 既存の会話処理、TTS、キャラクタ管理は基本的にそのまま使う

## 試作方針

1. waiting 用の口なしループ動画を常時再生する
2. 音声の実再生開始をトリガとして口パクを開始する
3. `mouth_track.json` に基づいて口スプライトを重ねる
4. 音声停止後は closed 口形へ戻し、waiting 表示を維持する

## 必要素材

- waiting 用 mouthless 動画
- waiting 用 `mouth_track.json`
- 口スプライト一式
  - `closed.png`
  - `half.png`
  - `open.png`
  - 必要なら `e.png`, `u.png`

## 実装メモ

- まずは 1 キャラ限定でよい
- まずは 3 段階口形で十分
- `Audio` 要素の再生開始イベントに合わせて口パク開始する
- 文区切りの無音ギャップ対策として短い hold を入れる余地がある
- talking 動画側への展開は Day4 の後半か Day5 で検討する

## 現在の実装状態

- backend に waiting lipsync 用 manifest API を追加済み
- frontend で waiting 動画 + mouth sprite overlay を再生可能
- 音声再生中のレベルを Web Audio API で拾い、mouth shape を切り替える
- waiting lipsync 素材があるキャラは音声再生中も `talking.mp4` に切り替えない
