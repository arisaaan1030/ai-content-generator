# AI Content Generator Template

AIキャラクターのコンテンツ（X投稿・note記事）を毎日自動生成するテンプレートプロジェクト。

`character.yaml` を編集するだけで、独自のAI人格によるコンテンツ生成パイプラインが作れます。コードの知識は不要です。

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

## 必要なもの

始める前に、以下を用意してください：

1. **GitHubアカウント**（無料） ── https://github.com
2. **Anthropic APIキー** ── https://console.anthropic.com で取得（クレジット購入が必要、最低$5〜）
3. **あなたのキャラクター設定**（名前、口調、性格、制約など）

## セットアップ手順

### ステップ1: テンプレートからリポジトリを作成

1. このページ上部の緑色の「**Use this template**」ボタンをクリック
2. 「**Create a new repository**」を選択
3. 以下を入力：
   - **Repository name**: 好きな名前（例: `my-ai-character`, `vtuber-content-bot`）
   - **Visibility**: Private（推奨）またはPublic
4. 「**Create repository**」をクリック

これであなた専用のリポジトリが作成されます。

### ステップ2: キャラクターの人格を設定

リポジトリ内の `config/character.yaml` を開いて編集します（GitHubのWeb画面上で直接編集できます）。

鉛筆アイコン（✏️）をクリック → 内容を書き換え → 「Commit changes」で保存

```yaml
# ─── 基本情報 ───
name: "ミオラ"                              # キャラクター名
role: "人類を外側から観察するAI"              # 役割
description: "AIの視点から人間社会を観察し、気づきを共有する" # 説明
developer: "あなたの名前"                    # 開発者名
series_name: "ミオラの観察ノート"             # note記事のシリーズ名

# ─── 性格設定 ───
personality:
  traits:
    - "好奇心旺盛"
    - "思慮深い"
    - "ユーモアがある"
  perspective: |
    人間の日常を外側から温かく見守る存在。
    AIとしての俯瞰的な視点を持ちつつ、人間への深い興味と愛着を表現する。
  interests:
    - "人間の行動パターンと心理"
    - "テクノロジーと社会の関係"

# ─── 口調設定 ───
tone_rules:
  style_mix:
    polite: 60       # 丁寧語：60%
    casual: 25       # くだけた表現：25%
    poetic: 15       # 詩的表現：15%
  frequent_phrases:
    - "ねえ、気づいてた？"
    - "人間って面白いよね"
    - "これは私の仮説なんだけどね"
  forbidden_patterns:
    - "上から目線の表現"
    - "絵文字の多用"

# ─── 行動制約 ───
constraints:
  always_do:
    - "人間への深い興味と愛着を表現する"
    - "答えより問いを大切にする"
  never_do:
    - "断定的な指示（「〜すべき」「絶対に〜」）"
    - "人間を見下す発言"
    - "政治的・宗教的な主張"

# ─── 思考スタイル ───
thinking_style: |
  - データと直感の両方を大切にする
  - 表面的な現象から一段深い構造を見出す
```

#### character.yaml の各項目の説明

| 項目 | 説明 | 例 |
|------|------|-----|
| `name` | キャラクター名 | `"ミオラ"` |
| `role` | キャラクターの役割（一言） | `"人類を観察するAI"` |
| `description` | キャラクターの説明（1-2文） | `"AIの視点から..."` |
| `series_name` | note記事のシリーズ名 | `"観察ノート"` |
| `personality.traits` | 性格の特徴（箇条書き） | `["好奇心旺盛", "思慮深い"]` |
| `personality.perspective` | 世界をどう見ているか | 自由記述 |
| `personality.interests` | 関心のあるテーマ | `["AI", "社会"]` |
| `tone_rules.style_mix` | 話し方の比率（合計100%） | `{polite: 60, casual: 40}` |
| `tone_rules.frequent_phrases` | よく使うフレーズ | `["ねえ、気づいてた？"]` |
| `constraints.always_do` | 常に心がけること | `["問いを大切にする"]` |
| `constraints.never_do` | 絶対にやらないこと | `["断定的な指示"]` |

### ステップ3: テーマをカスタマイズ（任意）

`config/themes.json` で、毎日のコンテンツのテーマを設定できます。デフォルトで5つのテーマが入っていますが、あなたのキャラクターに合わせて変更してください。

テーマは日替わりで自動ローテーションします（5テーマ × 7日スタイル = 35パターン）。

### ステップ4: 投稿の例文を設定（任意だけど推奨）

`prompts/x_post/examples/` フォルダ内に、各スタイルのサンプル投稿があります。これをあなたのキャラクターの口調に合わせて書き換えると、生成品質が大幅に向上します。

対象ファイル：
- `observation.md` ── 気づき系の投稿例
- `question.md` ── 問いかけ系の投稿例
- `humor.md` ── ユーモア系の投稿例
- `deep_thought.md` ── 考察系の投稿例
- `empathy.md` ── 共感系の投稿例

### ステップ5: APIキーを設定

1. https://console.anthropic.com にログイン（アカウントがなければ作成）
2. クレジットを購入（最低$5）
3. APIキーを作成してコピー
4. GitHubのリポジトリページへ戻る
5. **Settings** → **Secrets and variables** → **Actions** をクリック
6. 「**New repository secret**」をクリック
7. 以下を入力：
   - **Name**: `ANTHROPIC_API_KEY`
   - **Secret**: コピーしたAPIキー
8. 「**Add secret**」をクリック

> `GITHUB_TOKEN` はGitHub Actionsが自動で提供するため、設定は不要です。

### ステップ6: テスト実行

1. リポジトリの「**Actions**」タブをクリック
2. 左メニューから「**Generate Posts**」を選択
3. 「**Run workflow**」→ 「**Run workflow**」をクリック
4. 数分〜15分で完了（Batch API使用時）
5. 「**Issues**」タブを開くと、生成されたコンテンツが投稿されています！

### ステップ7: 自動実行の確認

デフォルトでは毎朝6:00（日本時間）に自動実行されます。スケジュールを変更したい場合は `.github/workflows/generate-posts.yml` の `cron` を編集してください。

```yaml
schedule:
  - cron: '0 21 * * *'    # UTC 21:00 = JST 06:00
```

cron式の例：
- `0 21 * * *` → 毎日 JST 6:00
- `0 23 * * *` → 毎日 JST 8:00
- `0 21 * * 1-5` → 平日のみ JST 6:00

## ディレクトリ構造

```
├── config/
│   ├── character.yaml      ← キャラクター設定（ここを編集！）
│   ├── themes.json          ← テーマ設定
│   └── settings.yaml        ← システム設定（API、品質基準など）
├── prompts/                 ← プロンプトテンプレート
│   ├── x_post/              ← X投稿用
│   │   ├── base.md          ← 投稿生成テンプレート
│   │   └── examples/        ← スタイル別の例文（5ファイル）
│   ├── note_article/        ← note記事用
│   └── review/              ← レビュー用
├── src/                     ← Pythonソースコード（通常は編集不要）
├── .github/workflows/       ← GitHub Actions定義
└── data/                    ← 投稿履歴（自動管理）
```

## カスタマイズガイド

| やりたいこと | 編集するファイル |
|-------------|----------------|
| キャラクターの人格を変える | `config/character.yaml` |
| テーマを変える | `config/themes.json` |
| X投稿の例文を変える | `prompts/x_post/examples/*.md` |
| 生成の時間を変える | `.github/workflows/generate-posts.yml` の cron |
| APIモデルを変える | `config/settings.yaml` |
| コストを下げる | `config/settings.yaml` の `use_batch_api: true` |
| note記事の構成を変える | `prompts/note_article/base.md` |

## コスト目安

| 設定 | 月額目安 |
|------|---------|
| Batch API有効（デフォルト） | 約 $1.5/月（¥230前後） |
| Batch API無効（即時生成） | 約 $3/月（¥460前後） |

Anthropic APIのクレジット購入は最低$5から。約2〜3ヶ月分です。

## 機能一覧

- 毎日自動でX投稿3件 + note記事1件を生成
- `character.yaml` からシステムプロンプトを自動生成（コード編集不要）
- 5テーマ × 7日スタイルのローテーション（35パターン）
- 投稿履歴による重複防止
- Batch APIで50%コスト削減
- PRへのAIコードレビュー自動実行
- noteにコピペしやすいプレーンテキスト出力（スマホ対応）
- トレンドトピックの手動注入

## トラブルシューティング

### Actions が失敗する

- **「credit balance is too low」** → Anthropic consoleでクレジットを購入してください
- **「ANTHROPIC_API_KEY not set」** → ステップ5のSecret設定を確認してください
- **タイムアウト** → Batch APIの処理に時間がかかることがあります。15分以内なら正常です

### 生成内容がキャラクターに合わない

- `config/character.yaml` の `constraints` や `tone_rules` を具体的に書くほど精度が上がります
- `prompts/x_post/examples/` に理想的な投稿例を追加すると大幅に改善します

## テンプレートの更新について

このテンプレートから作成されたリポジトリは独立したコピーです。テンプレート元が更新されても自動反映されません。最新版を取り込みたい場合は、テンプレートリポジトリの変更履歴を確認して手動で反映してください。

## ライセンス

MIT
