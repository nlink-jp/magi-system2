# magi-system2

動的ペルソナ生成、デュアルメモリ、適応的ファシリテーションを備えたマルチペルソナ AI 議論システム — Vertex AI Gemini 搭載。

[English README is here](README.md)

## コンセプト

ファシリテーターの下で、動的に生成された3つの AI ペルソナがトピックについて議論します。各ペルソナは公開発言とは別に非公開の内心（本音、疑念、戦略）を持ち、豊かな議論ダイナミクスと自然な合意形成を実現します。

[magi-system](https://github.com/nlink-jp/magi-system)（v1）をベースに、Gemini の 1M コンテキストウィンドウと高度な推論能力を活かしてゼロから再設計。

## 機能

- **動的ペルソナ生成** — ファシリテーターがトピックを分析し、豊かな性格プロファイルを持つ3ペルソナを設計
- **デュアルメモリ** — 各ペルソナに非公開の内心（本音、疑念、戦略）と公開発言
- **適応的ファシリテーター** — 内心を読んで議論をガイドする独立した LLM エージェント
- **ストリーミング + CoT 表示** — リアルタイム出力と Gemini の思考過程（Chain of Thought）表示
- **マルチモーダル入力** — テキスト、Markdown、PDF、画像、音声、動画
- **グラデーション収束** — 二値投票ではなく 0.0〜1.0 の連続的な収束シグナル
- **Web UI** — WebSocket によるリアルタイム議論可視化、内心表示トグル
- **ハイブリッド言語** — 内部推論は英語（品質最大化）、出力時に翻訳
- **コンソールモニタリング** — API 呼び出し、トークン量、レイテンシ、コスト
- **リプレイモード** — 保存済み議論を LLM なしで再生

## クイックスタート

```bash
# インストール
git clone https://github.com/nlink-jp/magi-system2.git
cd magi-system2
uv sync

# 設定
export GOOGLE_CLOUD_PROJECT="your-project-id"
gcloud auth application-default login

# 議論を開始
magi2 discuss "ゼロトラストセキュリティアーキテクチャを採用すべきか？"
# ブラウザで http://127.0.0.1:8080 を開く
```

## CLI

```bash
# シンプルなトピック
magi2 discuss "トピック"

# Markdown + 添付ファイル
magi2 discuss --file proposal.md --attach spec.pdf --attach diagram.png

# 言語・表示オプション
magi2 discuss --file topic.md --lang ja --show-thoughts

# 出力ディレクトリ指定
magi2 discuss "トピック" --output ./results

# リプレイ（LLM 不要）
magi2 replay --state magi2_20260401_030000.json

# レポート＋議事録エクスポート
magi2 export --state magi2_20260401_030000.json --markdown
magi2 export --state magi2_20260401_030000.json --html --lang ja

# 別言語でレンダリング
magi2 render --state magi2_20260401_030000.json --lang ko
```

## 出力

議論完了時に JSON 状態ファイル（`magi2_YYYYMMDD_HHMMSS.json`）が自動保存されます。

- **リプレイ** — `magi2 replay --state file.json`（LLM 不要）
- **エクスポート** — レポート＋議事録（全内心情報付き）
- **再レンダリング** — 別言語でレポート生成

### Markdown レポート内容

| セクション | 内容 |
|-----------|------|
| Participants | ペルソナ設計（名前、背景、価値観、初期立場） |
| Discussion | 全会話ログ＋各ターンの内心 |
| Inner Thoughts | 本音、疑念、抑制意見、戦略思考、感情、他者評価 |
| Synthesis | LLM 生成の統合レポート |
| Final Positions | 各ペルソナの最終 readiness と立場 |
| Facilitator Analysis | 隠れたダイナミクス、戦略的意図 |
| Convergence History | ターン毎の収束推移テーブル |
| Metadata | Pro/Flash/Total トークン数 |

## Web UI

| 機能 | 説明 |
|------|------|
| 議論タイムライン | ペルソナ発言のリアルタイムストリーミング |
| ペルソナパネル | 名前、アーキタイプ、収束度バー、立場の変遷 |
| 内心バブル | 非公開の内心表示トグル（💭） |
| CoT 表示 | ストリーミング中の Gemini 思考過程（🧠） |
| 収束ゲージ | ファシリテーター評価の 0.0〜1.0 プログレスバー |
| トークンカウンター | Pro/Flash/Total リアルタイム表示 |
| アクティビティ表示 | 誰が現在思考中か表示 |
| テーマ切替 | ライト（デフォルト）/ ダーク |

## 設定

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"   # 必須
export GOOGLE_CLOUD_LOCATION="us-central1"       # 任意
export MAGI2_PRO_MODEL="gemini-2.5-pro"          # ペルソナモデル
export MAGI2_FLASH_MODEL="gemini-2.5-flash"      # ファシリテーターモデル
```

## v1 との主な違い

| 観点 | v1 | v2 |
|------|----|----|
| LLM | ローカル（OpenAI 互換） | Vertex AI Gemini（1M コンテキスト） |
| ペルソナ | 固定3体 | トピック最適化された動的生成 |
| 性格 | 3行の記述 | 豊かなプロファイル（認知、感情、対人） |
| メモリ | 切り詰め履歴（16ターン） | 全履歴 + 非公開の内心 |
| ファシリテーター | 固定ターンのシステムメッセージ | 内心を読む独立 LLM エージェント |
| 入力 | 1行テキスト | マルチモーダル |
| 出力 | TUI（Rich） | Web UI + コンソール |
| ストリーミング | なし | リアルタイム + CoT |

## 設計資料

- [アーキテクチャ](docs/design/architecture.md) — システム設計、データモデル、言語戦略

## ライセンス

MIT — [LICENSE](LICENSE) 参照
