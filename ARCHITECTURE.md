# AI Content Generator ── システムアーキテクチャ

## 概要図

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions / CLI                      │
│                  (毎朝6時 or 手動実行)                        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              src/__main__.py (メインエントリー)               │
│  - テーマ・スタイル決定                                      │
│  - ContentGenerator 実行                                    │
│  - IssueCreator で Issue 作成                               │
│  - History に記録                                           │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
    ┌────────────────────────────────────────────────────────┐
    │  src/config.py ── キャラクター＆設定管理                  │
    │  ┌────────────────────────────────────────────────────┐ │
    │  │ load_character()                                    │ │
    │  │  ├─ config/character.yaml を読み込み                │ │
    │  │  └─ CharacterConfig dataclass に解析                │ │
    │  └────────────────────────────────────────────────────┘ │
    │  ┌────────────────────────────────────────────────────┐ │
    │  │ build_system_prompt(character)                      │ │
    │  │  └─ YAML設定から XML 形式のシステムプロンプトを自動生成  │ │
    │  └────────────────────────────────────────────────────┘ │
    │  ┌────────────────────────────────────────────────────┐ │
    │  │ load_settings(), load_themes(),                     │ │
    │  │ get_today_theme(), get_today_style()                │ │
    │  │  └─ Settings, Theme, StylePattern を管理              │ │
    │  └────────────────────────────────────────────────────┘ │
    └────────────────────────────────────────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────────────────────────────┐
    │  src/generator.py ── コンテンツ生成エンジン                │
    │  ┌────────────────────────────────────────────────────┐ │
    │  │ ContentGenerator                                    │ │
    │  │  ├─ 自動生成されたシステムプロンプト + ユーザープロンプト │
    │  │  ├─ Anthropic API (Batch or Standard) で呼び出し    │ │
    │  │  ├─ X投稿3件 + note記事1件を生成                     │ │
    │  │  └─ JSON レスポンス → PostRecord/NoteRecord に変換   │ │
    │  └────────────────────────────────────────────────────┘ │
    │                                                          │
    │  【プロンプトテンプレート】                               │
    │  ├─ prompts/x_post/base.md                              │
    │  │  ├─ プレースホルダ: {character_name}, {theme_name}  │ │
    │  │  └─ few-shot examples: observation/question/etc  │ │
    │  └─ prompts/note_article/base.md                        │
    │     ├─ プレースホルダ: {character_name}, {series_name}  │ │
    │     └─ フォーマットルール: プレーンテキスト形式           │ │
    │                                                          │
    │  【Batch API 統合】                                     │
    │  ├─ X投稿 + note記事の2リクエストを1バッチにまとめる      │ │
    │  ├─ 50%コスト削減を実現                                  │
    │  ├─ ポーリングで完了を待機（最大30分）                    │ │
    │  └─ 失敗時は自動フォールバック（標準API）                 │ │
    └────────────────────────────────────────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────────────────────────────┐
    │  src/history.py ── 投稿履歴管理                          │
    │  ┌────────────────────────────────────────────────────┐ │
    │  │ PostHistory                                         │ │
    │  │  ├─ data/post_history.json を読み込み・書き込み       │ │
    │  │  ├─ DailyRecord で1日分の生成結果を管理               │ │
    │  │  ├─ 古い履歴を自動削除（keep_days 超過分）            │ │
    │  │  └─ プロンプト注入用に直近N日を要約                    │ │
    │  └────────────────────────────────────────────────────┘ │
    │                                                          │
    │  【JSONフォーマット】                                    │
    │  {                                                      │
    │    "history": [                                         │
    │      {                                                  │
    │        "date": "2026-03-15",                            │
    │        "theme": "Theme Name",                           │
    │        "posts": [...],  // PostRecord[]                │
    │        "note": {...}    // NoteRecord                  │
    │      }                                                  │
    │    ]                                                    │
    │  }                                                      │
    └────────────────────────────────────────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────────────────────────────┐
    │  src/issue_creator.py ── GitHub Issue 作成              │
    │  ┌────────────────────────────────────────────────────┐ │
    │  │ IssueCreator                                        │ │
    │  │  ├─ 生成されたコンテンツを Markdown でフォーマット    │ │
    │  │  ├─ X投稿：朝・昼・夜のセクション分け                 │ │
    │  │  ├─ note記事：本文 + コピペ用（スマホ対応）            │ │
    │  │  ├─ レビューチェックリスト自動生成                    │ │
    │  │  └─ GitHub API で Issue を作成                       │ │
    │  └────────────────────────────────────────────────────┘ │
    └────────────────────────────────────────────────────────┘
```

## モジュール詳細

### 1. config.py ── 設定・キャラクター管理

**責務**:
- YAML/JSON 設定ファイルの読み込み
- キャラクター定義から システムプロンプト（XML）を自動生成
- テーマ・スタイルのローテーション計算

**主要クラス**:

```python
@dataclass
class CharacterConfig:
    """キャラクター設定（character.yaml から読み込み）"""
    name: str
    role: str
    description: str
    personality: CharacterPersonality
    tone_rules: CharacterToneRules
    constraints: CharacterConstraints
    thinking_style: str
    series_name: str

@dataclass
class Settings:
    """動作設定（settings.yaml から読み込み）"""
    api: ApiSettings          # モデル、トークン数、temperature等
    review: ReviewSettings    # セルフレビュー設定
    retry: RetrySettings      # リトライ設定
    quality: QualitySettings  # 品質基準
    history_file: str
    issue_title_template: str
```

**主要関数**:

```python
def load_character() -> CharacterConfig:
    """character.yaml からキャラクター設定を読み込む"""

def build_system_prompt(character: CharacterConfig) -> str:
    """キャラクター設定から XML 形式のシステムプロンプトを生成

    <system>
      <identity>...</identity>
      <personality>...</personality>
      <tone_rules>...</tone_rules>
      <constraints>...</constraints>
      <thinking_style>...</thinking_style>
    </system>
    """

def get_today_theme() -> Theme:
    """日付ベースでテーマを決定（5テーマローテーション）"""

def get_today_style() -> StylePattern:
    """日付ベースでスタイルを決定（7日サイクル）"""
```

### 2. generator.py ── コンテンツ生成

**責務**:
- Anthropic API を呼び出して X投稿・note記事を生成
- Batch API（50%割引）と標準 API のハイブリッド対応
- プロンプトテンプレートのプレースホルダ置換

**主要クラス**:

```python
class ContentGenerator:
    def __init__(self, settings: Settings):
        self.character = load_character()
        self.client = anthropic.Anthropic()

    def generate_all(
        self,
        theme: Theme,
        style: StylePattern,
        history: PostHistory,
        trending_topic: str = "",
    ) -> tuple[list[PostRecord], NoteRecord, str]:
        """X投稿3件 + note記事1件を一括生成"""
```

**フロー**:

1. プロンプトテンプレートを読み込み
2. プレースホルダ置換 (`{theme_name}` → 実値 など)
3. Few-shot examples をロード
4. Batch API or 標準 API で呼び出し
5. レスポンスをパースして PostRecord/NoteRecord に変換

**Batch API 統合**:

```python
def _call_batch_api(
    self,
    requests: list[dict[str, Any]],
) -> dict[str, str]:
    """複数リクエストを1バッチにまとめて実行

    50%コスト削減を実現。
    ポーリングで完了を待機（デフォルト30分タイムアウト）。
    """
```

### 3. history.py ── 投稿履歴管理

**責務**:
- JSON ベースの投稿履歴の読み書き
- 重複防止用に直近の投稿をプロンプト注入
- 古い履歴の自動削除

**主要クラス**:

```python
@dataclass
class PostRecord:
    """1件の投稿"""
    time_slot: str          # "morning", "noon", "night"
    style: str              # "observation", "question", ...
    content: str
    hashtags: list[str]
    char_count: int

@dataclass
class NoteRecord:
    """1件の記事"""
    title: str
    word_count: int

@dataclass
class DailyRecord:
    """1日分の生成記録"""
    date: str               # "YYYY-MM-DD"
    theme: str
    posts: list[PostRecord]
    note: NoteRecord | None

class PostHistory:
    def __init__(self, file_path: str | None = None):
        """data/post_history.json を読み込み"""

    def get_recent(self, days: int = 7) -> list[DailyRecord]:
        """直近 N 日の履歴を取得"""

    def add(self, record: DailyRecord) -> None:
        """今日の生成結果を追加・保存"""

    def format_recent_summary(self) -> str:
        """プロンプト注入用に過去の投稿を要約"""
```

### 4. issue_creator.py ── GitHub Issue 作成

**責務**:
- 生成されたコンテンツを Markdown でフォーマット
- GitHub API で Issue を作成
- レビュー用チェックリスト生成

**主要クラス**:

```python
class IssueCreator:
    def format_issue_body(
        self,
        posts: list[PostRecord],
        note_title: str,
        note_text: str,
        theme_name: str,
        review_score: float | None = None,
    ) -> str:
        """Issue本文を Markdown でフォーマット"""

    def create_issue(
        self,
        posts: list[PostRecord],
        note_title: str,
        note_text: str,
        theme_name: str,
        target_date: str | None = None,
        review_score: float | None = None,
    ) -> str | None:
        """GitHub API で Issue を作成（URL を返却）"""
```

**Issue フォーマット**:

```markdown
> テーマ：**Theme Name**
> 品質スコア：**8.5** / 10.0

## 🐦 X投稿（3件）

### 朝（7:00〜8:00）── 気づき系

```
投稿本文
```

ハッシュタグ: `#tag1` | 文字数: 185

---

## 📝 記事案

### タイトル

**記事タイトル**

### 本文プレビュー

記事本文...

<details>
<summary>📋 にコピペ用（タップして展開）</summary>

記事タイトル

記事本文...

</details>

---

## 📋 レビューチェックリスト

- [ ] 朝の投稿を確認 → 問題なければ ✅
- [ ] 昼の投稿を確認 → 問題なければ ✅
- [ ] 夜の投稿を確認 → 問題なければ ✅
- [ ] 記事を確認 → 問題なければ ✅
```

### 5. code_reviewer.py ── コードレビュー

**責補**:
- PR の差分を取得・フィルタリング
- Anthropic API（Haiku モデル）でレビュー実行
- コメントを PR に投稿

**主要クラス**:

```python
class CodeReviewer:
    def review_pr(self, pr_number: int | None = None) -> ReviewResult:
        """PR をレビューして結果を返す"""
```

**レビュー観点**:

- PEP 8 準拠、型ヒント、docstring
- バグ・ロジックミス検出
- セキュリティチェック（API キー露出、SQL インジェクション等）
- パフォーマンス・可読性

## 設定ファイル仕様

### config/character.yaml

```yaml
name: "Character Name"
role: "Role description"
description: "What character does"
developer: "Developer name"
series_name: "Series name for articles"

personality:
  traits: ["trait1", "trait2"]
  perspective: "How they view the world"
  interests: ["interest1", "interest2"]

tone_rules:
  style_mix:
    polite: 60
    casual: 25
    poetic: 15
  frequent_phrases: ["phrase1", "phrase2"]
  forbidden_patterns: ["pattern1"]

constraints:
  always_do: ["rule1", "rule2"]
  never_do: ["prohibition1"]

thinking_style: "Describe thinking approach"
```

### config/settings.yaml

```yaml
api:
  model: "claude-sonnet-4-20250514"
  max_tokens: 4096
  temperature: 0.85
  use_batch_api: true
  batch_poll_timeout: 1800
  batch_poll_interval: 30

quality:
  x_post:
    min_chars: 140
    max_chars: 280
    max_hashtags: 2
  note_article:
    min_chars: 1500
    max_chars: 3000

history:
  file_path: "data/post_history.json"
  keep_days: 30
  recent_days: 7

issue:
  title_template: "📝 投稿案 ── {date}（{theme}）"
  labels: ["generated", "content"]
```

### config/themes.json

```json
{
  "themes": [
    {
      "id": 1,
      "name": "Theme Name",
      "description": "Theme description",
      "keywords": ["keyword1", "keyword2"],
      "sub_topics": ["angle1", "angle2"]
    }
  ],
  "style_rotation": {
    "patterns": [
      {
        "morning": "observation",
        "noon": "question",
        "night": "empathy"
      }
    ]
  }
}
```

## データフロー

### 通常の生成フロー

```
GitHub Actions (朝6時)
    │
    └─ python -m src
        │
        ├─ load_character() → CharacterConfig
        ├─ build_system_prompt(character) → XML prompt
        ├─ get_today_theme() → Theme
        ├─ get_today_style() → StylePattern
        │
        ├─ PostHistory.load() → DailyRecord[]
        │
        ├─ ContentGenerator.generate_all(theme, style, history)
        │   ├─ system_prompt 自動生成
        │   ├─ x_post_prompt テンプレート置換
        │   ├─ note_prompt テンプレート置換
        │   ├─ Batch API call
        │   ├─ JSON parse
        │   └─ → (PostRecord[], NoteRecord, str)
        │
        ├─ IssueCreator.create_issue(posts, note, theme)
        │   ├─ format_issue_body()
        │   ├─ GitHub API POST /repos/{owner}/{repo}/issues
        │   └─ → Issue URL
        │
        ├─ PostHistory.add(DailyRecord)
        └─ PostHistory.save() → data/post_history.json

    GitHub Issue 作成 ✅
```

### コードレビューフロー

```
GitHub PRs[synchronize]
    │
    └─ python -m src.review_cli
        │
        ├─ CodeReviewer.review_pr()
        │   ├─ _get_pr_diff() → git diff
        │   ├─ _filter_diff() → 対象ファイルのみ
        │   ├─ _get_system_prompt() → review prompt
        │   ├─ _call_api() → Haiku で low temperature レビュー
        │   ├─ _parse_review_result() → JSON parse
        │   └─ → ReviewResult
        │
        └─ _post_pr_comment() → GitHub API POST comment

    PR に レビューコメント 投稿 ✅
```

## パフォーマンス特性

### レイテンシ

- **標準 API**: 5-10秒（X投稿3件 + note1件）
- **Batch API**: 5-30分（ポーリング待機含む）

### コスト

- **Batch API**: 約 50% 割引（50%コスト削減）
- **月額**: 数千〜数万円（テーマ・スタイル数による）

### スケーラビリティ

- **メモリ**: 1GB以下（履歴ファイルサイズ依存）
- **ストレージ**: 数MB（history.json）

## 拡張ポイント

### キャラクター増設

複数のキャラクター設定ファイルをサポートする場合：

```python
# 例
CHARACTER_FILE = os.environ.get("CHARACTER_FILE", "config/character.yaml")
char_config = load_character(CHARACTER_FILE)
```

### 出力先拡張

- Twitter/X API v2 連携
- Bluesky ATP
- Mastodon API
- Email 送信

### テーマ動的取得

- API から トレンドトピック を取得
- データベース連携で テーマを動的に管理

### 多言語対応

- character.yaml に言語フィールド追加
- プロンプト生成時に言語を考慮

---

**最終更新**: 2026-03-15
