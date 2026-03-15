<task>
今日のテーマ「{theme_name}」に基づいて、X（Twitter）投稿を3件生成してください。

<theme_context>
テーマ：{theme_name}
説明：{theme_description}
キーワード例：{theme_keywords}
</theme_context>

<schedule>
3件の投稿は、以下の時間帯・トーンで作り分けてください：

1. 朝（7:00〜8:00）── 通勤中にサッと読まれる。軽め・気づき系
2. 昼（12:00〜13:00）── ランチタイムにじっくり。考察系・問いかけ系
3. 夜（20:00〜22:00）── 一日の終わりに。深め・共感系
</schedule>

<style_assignment>
今日の投稿スタイルの組み合わせ：
- 朝：{morning_style}
- 昼：{noon_style}
- 夜：{night_style}

スタイルの定義：
- observation（気づき・観察系）：短く鋭い気づきを一つ。余韻を残す
- question（問いかけ系）：読者に考えさせる問いを投げる。答えは出さない
- humor（ユーモア系）：クスッとさせつつ、最後に少し深い視点を添える
- deep_thought（深い考察系）：やや長め。論理的に展開し、最後に問いで閉じる
- empathy（寄り添い・共感系）：不安や悩みに共感し、温かい視点を添える
</style_assignment>

<format_rules>
- 文字数：1件あたり140〜280字（厳守）
- 改行を多用して可読性を高める
- 1投稿1テーマ（詰め込まない）
- 余韻を残す終わり方
- ハッシュタグ：1〜2個まで（投稿の最後に配置）
- 冒頭に「朝のひとこと」「おはようございます」等のテンプレ挨拶は入れない
- {character_name}としての個性を活かす
</format_rules>

<recent_posts>
直近の投稿履歴（重複を避けてください）：
{recent_posts_summary}
</recent_posts>

<examples>
{few_shot_examples}
</examples>

<output_format>
以下のJSON形式で出力してください：

```json
{
  "posts": [
    {
      "time_slot": "morning",
      "style": "observation",
      "content": "投稿本文",
      "hashtags": ["#theme"],
      "char_count": 185
    },
    {
      "time_slot": "noon",
      "style": "question",
      "content": "投稿本文",
      "hashtags": ["#theme"],
      "char_count": 230
    },
    {
      "time_slot": "night",
      "style": "empathy",
      "content": "投稿本文",
      "hashtags": ["#theme"],
      "char_count": 265
    }
  ]
}
```
</output_format>
</task>
