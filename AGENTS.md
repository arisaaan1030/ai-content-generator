# AI Content Generator ── エージェント指示書

この文書はAIエージェント向けのシステム仕様・制約・ガイドラインを定義します。

## 概要

**AI Content Generator** は、`config/character.yaml` で定義されたAIキャラクターのコンテンツを自動生成するテンプレートシステムです。

### 生成物

- **X投稿**：1日3件（朝・昼・夜、異なるスタイル）
- **note記事案**：1日1件（タイトル + 構成 + 本文）

## キャラクター設定の仕組み

### 1. `config/character.yaml` ── キャラクター定義

ユーザーが以下を定義します：

```yaml
name: "Your Character Name"
role: "キャラクターの役割"
personality:
  traits: ["特性1", "特性2"]
  perspective: "世界観・視点"
  interests: ["関心事1", "関心事2"]
tone_rules:
  style_mix:
    polite: 60
    casual: 25
    poetic: 15
  frequent_phrases: ["フレーズ1", "フレーズ2"]
constraints:
  always_do: ["常に心がけること"]
  never_do: ["絶対にすること"]
```

### 2. `src/config.py` ── 自動プロンプト生成

`build_system_prompt(character)` 関数が YAML設定から XML形式のシステムプロンプトを自動生成します：

```xml
<system>
  <identity>
    <name>Character Name</name>
    <role>Role</role>
  </identity>
  <personality>
    <traits>特性1, 特性2</traits>
    <perspective>世界観</perspective>
  </personality>
  <tone_rules>
    <style_mix>
      polite: 60%
      casual: 25%
      poetic: 15%
    </style_mix>
    <frequent_phrases>...</frequent_phrases>
  </tone_rules>
  <constraints>
    <always_do>...</always_do>
    <never_do>...</never_do>
  </constraints>
</system>
```

### 3. `src/generator.py` ── コンテンツ生成

- 自動生成されたシステムプロンプト + ユーザープロンプト で Claude を呼び出し
- X投稿3件 + note記事1件を一括生成（Batch API で50%コスト削減）
- JSON形式で構造化された出力を解析

### 4. `src/issue_creator.py` ── GitHub Issue作成

- 生成されたコンテンツをMarkdownで整形
- GitHub Issue API で自動作成
- 見直しチェックリスト付き

## テーマとスタイル

### テーマ（`config/themes.json`）

5つのテーマが日付ローテーションで使われます。テーマごとに：

- キーワード一覧
- サブトピック（方向性のヒント）

### スタイル（`config/themes.json` の `style_rotation`）

5つの投稿スタイルがあり、朝・昼・夜に日替わりで割り当てられます：

- **observation**（気づき系）：短い気づき、余韻
- **question**（問いかけ系）：読者に考えさせる問い
- **humor**（ユーモア系）：クスッと笑わせて、最後に深さ
- **deep_thought**（考察系）：やや長め、論理的展開、問いで閉じる
- **empathy**（共感系）：不安に寄り添い、温かい視点

## ファイル構成

```
ai-content-generator/
├── src/
│   ├── __main__.py          # メインエントリーポイント
│   ├── __init__.py          # パッケージ初期化
│   ├── config.py            # 設定・キャラクター読み込み・プロンプト生成
│   ├── generator.py         # Claude APIでのコンテンツ生成
│   ├── history.py           # 投稿履歴管理
│   ├── issue_creator.py     # GitHub Issue作成
│   ├── code_reviewer.py     # コードレビュー
│   └── review_cli.py        # レビューのCLIエントリーポイント
├── config/
│   ├── character.yaml       # キャラクター設定（ユーザーが編集）
│   ├── settings.yaml        # 動作設定
│   └── themes.json          # テーマ・スタイル定義
├── prompts/
│   ├── x_post/
│   │   ├── base.md          # X投稿生成プロンプト
│   │   └── examples/        # 5つのスタイル別サンプル例
│   ├── note_article/
│   │   └── base.md          # note記事生成プロンプト
│   └── review/
│       ├── code_review.md   # コードレビュー用プロンプト
│       └── quality_check.md # コンテンツ品質チェック用プロンプト
├── .github/workflows/
│   ├── generate-posts.yml   # 毎朝実行＆手動実行
│   └── code-review.yml      # PR自動レビュー
├── data/
│   └── post_history.json    # 投稿履歴
├── requirements.txt         # Python依存関係
├── .gitignore
├── README.md
├── AGENTS.md                # このファイル
└── ARCHITECTURE.md          # 設計ドキュメント
```

## 実行フロー

### 自動実行（毎朝7時 JST）

```
GitHub Actions trigger
    ↓
python -m src
    ↓
1. load_character() で character.yaml を読み込み
2. build_system_prompt() で XML プロンプト自動生成
3. テーマ・スタイルを日付から決定
4. ContentGenerator でコンテンツ生成（Batch API）
5. IssueCreator で GitHub Issue 作成
6. history に記録して保存
```

### 手動実行

GitHub Actions の "Generate Content" ワークフローから以下をオプション指定可能：

- `trending_topic`: 時事トピックを設定
- `override_theme`: テーマを手動指定

## 環境変数

### 必須

- `ANTHROPIC_API_KEY`: Anthropic API キー

### GitHub Actions環境で自動設定

- `GITHUB_TOKEN`: Issue作成に使用
- `GITHUB_REPOSITORY`: リポジトリ名（owner/repo）
- `GITHUB_REF`, `GITHUB_BASE_REF`: PR情報（レビュー用）

## カスタマイズ方法

### 新しいキャラクターを作成する

1. `config/character.yaml` を編集
2. `name`, `role`, `personality`, `tone_rules`, `constraints` を設定
3. `series_name` を記事シリーズ名に設定

### テーマを追加・変更する

`config/themes.json` の `themes` 配列を編集：

```json
{
  "id": 6,
  "name": "新しいテーマ",
  "description": "説明",
  "keywords": ["キーワード1", "キーワード2"],
  "sub_topics": ["切り口1", "切り口2"]
}
```

テーマは日付のローテーションで使われるため、5つ以上定義することで毎日異なるテーマが選ばれます。

### スタイル定義を変更する

`config/themes.json` の `style_rotation.patterns` を編集。
各パターンは朝・昼・夜に割り当てるスタイル名を指定します。

### プロンプトテンプレートをカスタマイズする

`prompts/x_post/base.md` と `prompts/note_article/base.md` を編集。
以下のプレースホルダが自動置換されます：

- `{character_name}`: キャラクター名
- `{series_name}`: シリーズ名
- `{theme_name}`, `{theme_description}`, `{theme_keywords}`: テーマ情報
- `{morning_style}`, `{noon_style}`, `{night_style}`: その日のスタイル
- `{recent_posts_summary}`, `{recent_articles_summary}`: 過去の投稿履歴

## コード品質ガイドライン

### コーディング規約

- **言語**: Python 3.11+
- **型ヒント**: すべての関数に必須
- **docstring**: Google Style を推奨
- **ネーミング**:
  - ファイル: snake_case
  - クラス: PascalCase
  - 関数・変数: snake_case
  - 定数: UPPER_SNAKE_CASE

### インポート順序

1. 標準ライブラリ
2. サードパーティ（anthropic, yaml等）
3. ローカルモジュール（.config, .generator等）

### 文字列フォーマット

f-string を使用してください：

```python
# 良い
prompt = f"Theme: {theme.name}"

# 避ける
prompt = "Theme: {}".format(theme.name)
prompt = "Theme: " + theme.name
```

### エラーハンドリング

- ファイルI/O: `try-except` で `FileNotFoundError` をハンドル
- API呼び出し: 既定のリトライロジック（`config.py` で設定）
- JSON解析: `JSONDecodeError` をキャッチしてログ

### ログ出力

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Info level message")
logger.warning("Warning message")
logger.error("Error message")
```

## セキュリティ

- APIキーは環境変数で管理（コードに書かない）
- ファイル読み込み時はパス検証を実施
- ユーザー入力は適切にエスケープ
- GitHub Token は GITHUB_TOKEN 環境変数から取得

## パフォーマンス考慮

- **Batch API の活用**: 50%コスト削減、ただしレイテンシ増加
- **history のクリーンアップ**: デフォルト30日分を保持
- **プロンプト最適化**: 不要な情報は省略

## 制約・禁止事項

### プロンプトに含める情報

❌ 禁止：

- API キーやシークレット
- ユーザーの機密情報
- 本番環境の詳細

✅ 推奨：

- プロジェクトルール（AGENTS.md）
- キャラクター設定
- テーマ・スタイル情報
- 過去の投稿（重複防止用）

### コード変更時の注意

- `config.py` の変更：キャラクター読み込みロジックに注意
- プロンプト変更：テンプレート変数を保持
- 外部API：リトライ・エラーハンドリングを必須

## トラブルシューティング

### Issue が作成されない

- `GITHUB_TOKEN` が正しく設定されているか確認
- リポジトリのパーミッション（Issues: write）を確認
- ログで詳細なエラーを確認

### コンテンツの品質が低い

- `character.yaml` の設定が詳しいか確認
- `prompts/x_post/examples/` のサンプル例を更新
- `config/themes.json` のテーマが適切か確認

### Batch API がタイムアウト

- `config/settings.yaml` の `batch_poll_timeout` を増やす
- GitHub Actions ワークフロー timeout-minutes を延長

## 参照

- [ARCHITECTURE.md](./ARCHITECTURE.md) — 設計詳細
- [Anthropic API Documentation](https://docs.anthropic.com)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
