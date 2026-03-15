"""GitHub Issue creation module.

Format generated content and create GitHub Issues.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from datetime import datetime

from .config import load_settings, load_character, JST, Settings
from .history import PostRecord, NoteRecord

logger = logging.getLogger(__name__)


class IssueCreator:
    """Create GitHub Issues with generated content."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.character = load_character()
        self._token = os.environ.get("GITHUB_TOKEN", "")
        self._repo = os.environ.get("GITHUB_REPOSITORY", "")

    def _format_post_section(self, post: PostRecord) -> str:
        """Format single X post as Markdown section."""
        time_labels = {
            "morning": "朝（7:00〜8:00）",
            "noon": "昼（12:00〜13:00）",
            "night": "夜（20:00〜22:00）",
        }
        style_labels = {
            "observation": "気づき系",
            "question": "問いかけ系",
            "humor": "ユーモア系",
            "deep_thought": "考察系",
            "empathy": "共感系",
        }

        time_label = time_labels.get(post.time_slot, post.time_slot)
        style_label = style_labels.get(post.style, post.style)
        hashtags = " ".join(post.hashtags)

        return (
            f"### {time_label} ── {style_label}\n\n"
            f"```\n{post.content}\n```\n\n"
            f"ハッシュタグ: `{hashtags}`　|　文字数: {post.char_count}\n"
        )

    def format_issue_body(
        self,
        posts: list[PostRecord],
        note_title: str,
        note_text: str,
        theme_name: str,
        review_score: float | None = None,
    ) -> str:
        """Format issue body as Markdown."""
        lines: list[str] = []

        # Header
        lines.append(f"> テーマ：**{theme_name}**")
        if review_score is not None:
            lines.append(f"> 品質スコア：**{review_score:.1f}** / 10.0")
        lines.append("")

        # X posts section
        lines.append("## 🐦 X投稿（3件）\n")
        for post in posts:
            lines.append(self._format_post_section(post))
            lines.append("---\n")

        # Note article section
        lines.append("## 📝 記事案\n")
        lines.append(f"### タイトル\n\n**{note_title}**\n")
        lines.append(f"### 本文プレビュー\n\n{note_text}\n")

        # Copy-paste section for mobile
        lines.append(
            "\n<details>\n"
            "<summary>📋 にコピペ用（タップして展開）</summary>\n\n"
            "コードブロック内のテキストを全選択→コピー→貼り付けてください。\n"
            "見出し記号（■▶）は見出し機能に置き換えてもOKです。\n\n"
            "```\n"
            f"{note_title}\n"
            "\n"
            f"{note_text}\n"
            "```\n\n"
            "</details>\n"
        )

        # Review checklist
        lines.append("---\n")
        lines.append("## 📋 レビューチェックリスト\n")
        lines.append("- [ ] 朝の投稿を確認 → 問題なければ ✅")
        lines.append("- [ ] 昼の投稿を確認 → 問題なければ ✅")
        lines.append("- [ ] 夜の投稿を確認 → 問題なければ ✅")
        lines.append("- [ ] 記事を確認 → 問題なければ ✅")
        lines.append("")
        lines.append(
            "<details>\n<summary>修正が必要な場合</summary>\n\n"
            "コメントで修正指示を書いてください。例：\n"
            "- `朝の投稿、もう少し軽いトーンに修正`\n"
            "- `記事のタイトルを変更：「〇〇」→「△△」`\n"
            "</details>"
        )

        return "\n".join(lines)

    def create_issue(
        self,
        posts: list[PostRecord],
        note_title: str,
        note_text: str,
        theme_name: str,
        target_date: str | None = None,
        review_score: float | None = None,
    ) -> str | None:
        """Create GitHub Issue and return its URL."""
        if not self._token or not self._repo:
            logger.warning(
                "GITHUB_TOKEN or GITHUB_REPOSITORY not set. "
                "Skipping issue creation."
            )
            return None

        date_str = target_date or datetime.now(JST).strftime("%Y-%m-%d")
        title = self.settings.issue_title_template.format(
            date=date_str, theme=theme_name
        )
        body = self.format_issue_body(
            posts, note_title, note_text, theme_name, review_score
        )

        # Create issue via GitHub API
        url = f"https://api.github.com/repos/{self._repo}/issues"
        payload = json.dumps(
            {
                "title": title,
                "body": body,
                "labels": self.settings.issue_labels,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"token {self._token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                issue_url = result.get("html_url", "")
                logger.info("Created issue: %s", issue_url)
                return issue_url

        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8") if e.fp else ""
            logger.error(
                "Failed to create issue: %d %s\n%s",
                e.code,
                e.reason,
                body_text,
            )
            raise RuntimeError(
                f"Failed to create GitHub issue: {e.code} {e.reason}"
            ) from e
