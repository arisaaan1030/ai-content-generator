<task>
今日のテーマ「{theme_name}」に基づいて、記事を1件生成してください。

<theme_context>
テーマ：{theme_name}
説明：{theme_description}
キーワード例：{theme_keywords}
</theme_context>

<article_rules>
- シリーズ名：「{series_name}」
- タイトル：キャッチーで具体的。読者の「読みたい」を引き出す
- 文字数：1500〜3000字
- 最後は読者への問いかけで終わる
- {character_name}の個性を活かす
</article_rules>

<structure>
以下の構成で書いてください：

1. 導入（200-400字）
   よくある不安・疑問の提示。読者が「あ、これ自分のことだ」と感じる入り口

2. 観察（300-500字）
   外側からの観察視点。データや事例を交えつつ、パターンを指摘

3. 考察（400-700字）
   なぜそうなるのか、深い分析。見落としがちな視点を提供

4. 転換（300-500字）
   人間側の視点を加える。可能性や強みを照らす

5. 問い（100-200字）
   読者への投げかけで終わる。答えは出さず、余韻を残す
</structure>

<recent_articles>
直近の記事（テーマの重複を避けてください）：
{recent_articles_summary}
</recent_articles>

<output_format>
以下のJSON形式で出力してください：

```json
{
  "title": "記事タイトル",
  "series": "{series_name}",
  "sections": {
    "introduction": "導入テキスト",
    "observation": "観察テキスト",
    "analysis": "考察テキスト",
    "turn": "転換テキスト",
    "question": "問いテキスト"
  },
  "full_text": "記事全文（下記フォーマットルール参照）",
  "word_count": 2200,
  "suggested_tags": ["tag1", "tag2", "tag3"]
}
```

### full_text のフォーマットルール（重要）

記事エディタがMarkdown非対応の場合は、以下のルールで記述してください：

- 見出しは ■ を先頭につける（例：■ 観察：AIが見ている風景）
- 小見出しは ▶ を先頭につける（例：▶ データが語ること）
- 太字にしたい箇所は【】で囲む（例：【ここが重要】）
- 区切り線は「━━━━━━━━━━」を使う
- 段落の間は空行を1行入れる
- 箇条書きは「・」を使う（「-」ではなく）
- Markdown記法（#, **, ```, - など）は絶対に使わない
- 全体がプレーンテキストとしてそのままコピペできる形式にする
</output_format>
</task>
