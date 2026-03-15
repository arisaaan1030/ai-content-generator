# AI Content Generator Template

AIキャラクターのコンテンツ（X投稿・note記事）を毎日自動生成するテンプレートプロジェクト。

`character.yaml` を編集するだけで、独自のAI人格によるコンテンツ生成パイプラインが作れます。

## 仕組み

```
character.yaml（人格定義）
    ↓ 自動変換
XMLシステムプロンプト生成
    ↓
Anthropic API（Claude Sonnet）で生成
    ↓
X投稿3件（朝・昼・夜）+ note記事1件
    ↓
GitHub Issueとして出力
```

## クイックスタート

### 1. テンプレートから自分のリポジトリを作成

GitHubの「**Use this template**」ボタンをクリック → プライベートリポジトリとして作成

### 2. キャラクターを設定

`config/character.yaml` を開いて、あなたのキャラクターの人格を定義：

```yaml
name: "あなたのキャラクター名"
role: "キャラクターの役割"
description: "どんなキャラクターか"

personality:
  traits:
    - "好奇心旺盛"
    - "思慮深い"
  perspective: "世界をどう見ているか"

tone_rules:
  style_mix:
    polite: 60
    casual: 25
    poetic: 15
  frequent_phrases:
    - "よく使うフレーズ1"
    - "よく使うフレーズ2"

constraints:
  always_do:
    - "常に心がけること"
  never_do:
    - "絶対にやらないこと"
```

### 3. テーマをカスタマイズ

`config/themes.json` でコンテンツのテーマを設定（5テーマ × 7日スタイルローテーション）

### 4. GitHub Secretsを設定

リポジトリの Settings → Secrets and variables → Actions に以下を追加：

| Secret名 | 説明 |
|----------|------|
| `ANTHROPIC_API_KEY` | Anthropic APIキー（[console.anthropic.com](https://console.anthropic.com)で取得） |

`GITHUB_TOKEN` はGitHub Actionsが自動提供するため設定不要です。

### 5. 手動テスト

Actions → 「Generate Posts」→ 「Run workflow」で実行。成功すると GitHub Issue にコンテンツが投稿されます。

## ディレクトリ構造

```
├── config/
│   ├── character.yaml      ← キャラクター設定（ここを編集）
│   ├── themes.json          ← テーマ設定
│   └── settings.yaml        ← システム設定
├── prompts/                 ← プロンプトテンプレート
│   ├── x_post/              ← X投稿用
│   ├── note_article/        ← note記事用
│   └── review/              ← レビュー用
├── src/                     ← Pythonソースコード
├── .github/workflows/       ← GitHub Actions定義
└── data/                    ← 投稿履歴（自動管理）
```

## カスタマイズのポイント

| やりたいこと | 編集するファイル |
|-------------|----------------|
| キャラクターの人格を変える | `config/character.yaml` |
| テーマを変える | `config/themes.json` |
| X投稿の例文を変える | `prompts/x_post/examples/*.md` |
| 生成のタイミングを変える | `.github/workflows/generate-posts.yml` の cron |
| APIモデルを変える | `config/settings.yaml` |
| コストを下げる | `config/settings.yaml` の `use_batch_api: true` |

## コスト目安

Batch API有効時（デフォルト）：約 $1.5/月（¥230前後）

## 機能

- 毎日自動でX投稿3件 + note記事1件を生成
- 5テーマ × 7日スタイルのローテーションで内容にバリエーション
- 投稿履歴による重複防止
- Batch APIで50%コスト削減
- PRへのAIコードレビュー自動実行
- noteコピペ対応フォーマット（スマホでもOK）

## ライセンス

MIT
