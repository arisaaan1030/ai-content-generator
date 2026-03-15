# AI Content Generator

あなたの考え方や文体をAIに学ばせて、X投稿やnote記事を毎日自動生成するツール。

`character.yaml` にあなたのプロフィール（思想、口調、関心テーマ）を書くだけ。コードの知識は不要です。

## こんな人向け

- 発信したいけど毎日書く時間がない
- 自分の考えをベースにした投稿案がほしい
- AIに下書きを作らせて、確認してから投稿したい

## 仕組み

```
character.yaml（あなたのプロフィール）
    ↓ 自動変換
あなたの視点を再現するプロンプト生成
    ↓
AI API（Claude or GPT-4o）で投稿を生成
    ↓
X投稿3件（朝・昼・夜）+ note記事1件
    ↓
GitHub Issueとして投稿案を出力
    ↓
確認してからXやnoteに投稿
```

生成された投稿は GitHub Issue に投稿案として出力されます。自動投稿はされないので、確認してからコピペで投稿できます。

## 必要なもの

1. **GitHubアカウント**（無料） ── https://github.com
2. **AIのAPIキー**（以下のいずれか）
   - Anthropic（Claude） ── https://console.anthropic.com（最低$5でクレジット購入）
   - OpenAI（GPT-4o） ── https://platform.openai.com（従量課金）
3. **あなたのプロフィール**（考え方、口調、関心テーマなど）

## セットアップ手順

### 方法A: テンプレートから作成（おすすめ）

プライベートリポジトリで使いたい場合はこちら。

1. このページ上部の緑色の「**Use this template**」→「**Create a new repository**」
2. リポジトリ名を入力（例: `my-content-bot`）
3. **Private** を選択 → 「**Create repository**」

> テンプレート方式は独立したコピーになるため、元リポジトリの更新は自動反映されません。

### 方法B: Forkから作成

元リポジトリの更新を取り込みたい場合はこちら。

1. このページ右上の「**Fork**」をクリック
2. 自分のアカウントにForkされる
3. 元リポジトリが更新されたら、以下で取り込み：

```bash
git remote add upstream https://github.com/arisaaan1030/ai-content-generator.git
git fetch upstream
git merge upstream/main
```

> 注意: パブリックリポジトリのForkはパブリックになります。プロフィール情報を非公開にしたい場合はテンプレート方式を使ってください。

---

### ステップ1: プロフィールを設定

`config/character.yaml` をGitHub上で直接編集できます（鉛筆アイコン ✏️ → 編集 → Commit changes）。

```yaml
# ─── 基本情報 ───
name: "田中太郎"
role: "フリーランスエンジニア"
description: "AIと人間の共存について考えるのが好きなエンジニア"
series_name: "太郎の思考メモ"

# ─── あなたの考え方・価値観 ───
personality:
  traits:
    - "好奇心旺盛"
    - "論理的だけど直感も大事にする"
  perspective: |
    テクノロジーは人間を豊かにするためにある。
    表面的なトレンドより、その裏にある構造変化に興味がある。
  interests:
    - "AIと人間の共存"
    - "働き方の未来"
    - "個人の発信力"

# ─── 文体・口調 ───
tone_rules:
  style_mix:
    polite: 40       # 丁寧語
    casual: 50       # くだけた表現
    poetic: 10       # 詩的表現
  frequent_phrases:
    - "ふと思ったんだけど"
    - "これ面白くない？"
    - "本質的には"

# ─── 投稿のルール ───
constraints:
  always_do:
    - "自分の体験や考えをベースに語る"
    - "読者に考えるきっかけを与える"
  never_do:
    - "他者を否定する発言"
    - "政治的・宗教的な主張"
```

#### 各項目の説明

| 項目 | 何を書くか | 例 |
|------|----------|-----|
| `name` | 表示名（ペンネームOK） | `"田中太郎"` |
| `role` | 肩書き・立場 | `"エンジニア"` |
| `description` | 自己紹介（1-2文） | `"AIに関心があるエンジニア"` |
| `series_name` | note記事のシリーズ名 | `"太郎の思考メモ"` |
| `personality.traits` | あなたを表すキーワード | `["好奇心旺盛", "論理的"]` |
| `personality.perspective` | 世界の見方・スタンス | 自由記述（ここが一番重要！） |
| `personality.interests` | 関心テーマ | `["AI", "働き方"]` |
| `tone_rules.style_mix` | 文体の比率（合計100%） | `{polite: 40, casual: 50, poetic: 10}` |
| `tone_rules.frequent_phrases` | よく使う口癖 | `["ふと思ったんだけど"]` |
| `constraints.always_do` | 投稿で心がけること | `["体験ベースで語る"]` |
| `constraints.never_do` | 絶対やらないこと | `["他者の否定"]` |

**ポイント**: `personality.perspective` を具体的に書くほど「あなたらしい」投稿になります。普段考えていることをそのまま書いてください。

### ステップ2: テーマをカスタマイズ（任意）

`config/themes.json` で毎日のテーマを設定。デフォルトで5テーマ入っていますが、あなたの関心に合わせて変更できます。テーマは日替わりで自動ローテーションします。

### ステップ3: 投稿の例文を設定（任意だけど推奨）

`prompts/x_post/examples/` に各スタイルのサンプル投稿があります。あなたの口調に合わせて書き換えると生成品質が大幅に向上します。

| ファイル | スタイル |
|---------|---------|
| `observation.md` | 気づき系 |
| `question.md` | 問いかけ系 |
| `humor.md` | ユーモア系 |
| `deep_thought.md` | 考察系 |
| `empathy.md` | 共感系 |

### ステップ4: APIキーを設定

**Anthropic（Claude）を使う場合**（デフォルト）：

1. https://console.anthropic.com でアカウント作成
2. クレジットを購入（最低$5、約2-3ヶ月分）
3. APIキーを作成してコピー
4. GitHubリポジトリ → **Settings** → **Secrets and variables** → **Actions**
5. 「**New repository secret**」→ Name: `ANTHROPIC_API_KEY` / Secret: コピーしたAPIキー

**OpenAI（GPT-4o）を使う場合**：

1. https://platform.openai.com でアカウント作成・クレジット追加
2. APIキーを作成してコピー
3. GitHubリポジトリ → **Settings** → **Secrets and variables** → **Actions**
4. 「**New repository secret**」→ Name: `OPENAI_API_KEY` / Secret: コピーしたAPIキー
5. `config/settings.yaml` を編集して `provider: "openai"` に変更
6. `model` と `review_model` も OpenAI のモデル名に変更（下記「モデル選択」参照）

### ステップ5: テスト実行

1. リポジトリの「**Actions**」タブ
2. 左メニュー「**Generate Posts**」
3. 「**Run workflow**」→「**Run workflow**」
4. 数分〜15分で完了
5. 「**Issues**」タブに投稿案が届く！

### ステップ6: 日常の使い方

- **毎朝自動実行**: デフォルトで毎朝6:00（JST）に投稿案がIssueに届きます
- **確認→投稿**: Issueを開いて内容を確認し、良ければXやnoteにコピペ
- **noteへのコピペ**: Issue内の「📋 noteにコピペ用」セクションを展開すると、スマホでもそのままコピペできるフォーマットが入っています

#### 実行スケジュールを変更する

`.github/workflows/generate-posts.yml` の `cron` を編集：

```yaml
schedule:
  - cron: '0 21 * * *'    # UTC 21:00 = JST 06:00
```

| やりたいこと | cron式 |
|-------------|--------|
| 毎日 朝6時 | `0 21 * * *` |
| 毎日 朝8時 | `0 23 * * *` |
| 平日のみ 朝6時 | `0 21 * * 1-5` |

## ディレクトリ構造

```
├── config/
│   ├── character.yaml      ← あなたのプロフィール（ここを編集！）
│   ├── themes.json          ← テーマ設定
│   └── settings.yaml        ← システム設定
├── prompts/                 ← プロンプトテンプレート
│   ├── x_post/              ← X投稿用
│   │   ├── base.md
│   │   └── examples/        ← 投稿の例文（5ファイル）
│   ├── note_article/        ← note記事用
│   └── review/              ← コードレビュー用
├── src/                     ← ソースコード（編集不要）
├── .github/workflows/       ← 自動実行の設定
└── data/                    ← 投稿履歴（自動管理）
```

## カスタマイズガイド

| やりたいこと | 編集するファイル |
|-------------|----------------|
| プロフィールを変える | `config/character.yaml` |
| テーマを変える | `config/themes.json` |
| 投稿の例文を変える | `prompts/x_post/examples/*.md` |
| 実行時間を変える | `.github/workflows/generate-posts.yml` |
| note記事の構成を変える | `prompts/note_article/base.md` |
| AIモデルを変える | `config/settings.yaml` の `provider` / `model` |
| コストを調整する | `config/settings.yaml` |

## モデル選択とコスト

`config/settings.yaml` でプロバイダーとモデルを選べます。

### 対応モデル一覧

| プロバイダー | モデル名 | 用途 | 特徴 |
|------------|---------|------|------|
| Anthropic | `claude-sonnet-4-20250514` | 生成用（デフォルト） | 高品質。Batch APIで50%オフ |
| Anthropic | `claude-haiku-4-5-20251001` | レビュー用（デフォルト） | 高速・低コスト |
| OpenAI | `gpt-4o` | 生成用 | 高品質。Batch API非対応 |
| OpenAI | `gpt-4o-mini` | 生成/レビュー用 | 超低コスト |

### settings.yaml の設定例

```yaml
# Anthropic（デフォルト）
api:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
  review_model: "claude-haiku-4-5-20251001"
  use_batch_api: true

# OpenAI
api:
  provider: "openai"
  model: "gpt-4o"
  review_model: "gpt-4o-mini"
  use_batch_api: false  # OpenAIではBatch API未対応
```

### 月額コスト試算（毎日1回実行 = 30回/月）

前提：1日あたり入力 ~8,000トークン、出力 ~5,000トークン（X投稿3件 + note記事1件）

| 構成 | 月額目安 | 備考 |
|------|---------|------|
| **Claude Sonnet + Batch API** | **約 ¥220/月** | ⭐ おすすめ（デフォルト） |
| Claude Sonnet（標準API） | 約 ¥450/月 | 即時生成が必要な場合 |
| Claude Haiku + Batch API | 約 ¥60/月 | 最安のAnthropic構成 |
| Claude Haiku（標準API） | 約 ¥120/月 | 低コスト + 即時生成 |
| GPT-4o | 約 ¥320/月 | OpenAIの高品質モデル |
| GPT-4o-mini | 約 ¥20/月 | 最安構成（品質はやや落ちる） |

> コードレビュー（PR時のみ）は含まれていません。Haiku/mini使用で1回あたり数円程度です。

> 1ドル ≈ 150円で換算。Anthropic初回クレジット購入は最低$5（約¥750）。

## 機能

- 毎日自動でX投稿3件 + note記事1件の投稿案を生成
- あなたのプロフィールからAIが自動でプロンプトを組み立て
- Anthropic（Claude）/ OpenAI（GPT-4o）を選択可能
- 5テーマ × 7日スタイル = 35パターンのローテーション
- 投稿履歴で同じ内容の重複を防止
- Batch APIで50%コスト削減（Anthropic使用時）
- noteにそのままコピペできるフォーマット（スマホ対応）
- PRへのAIコードレビュー自動実行

## トラブルシューティング

| 問題 | 解決策 |
|------|-------|
| 「credit balance is too low」 | Anthropic consoleでクレジットを購入 |
| 「ANTHROPIC_API_KEY not set」 | ステップ4のSecret設定を確認 |
| 「OPENAI_API_KEY not set」 | OpenAI使用時はOpenAIのAPI keyをSecretに設定 |
| 「openai package not installed」 | OpenAI使用時は `pip install openai` が必要（GitHub Actionsでは `requirements.txt` の `openai` 行のコメントを外す） |
| タイムアウト | Batch APIは最大15分かかることがあります。正常です |
| 投稿が自分らしくない | `character.yaml` の `perspective` をより具体的に書く + `examples/` の例文を書き換える |

## テンプレートの更新

テンプレートから作成したリポジトリは独立したコピーのため、元の更新は自動反映されません。Forkの場合は `git fetch upstream && git merge upstream/main` で更新を取り込めます。

## ライセンス

MIT
