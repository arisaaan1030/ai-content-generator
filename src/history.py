"""Post history management module.

Manage post history in JSON format and provide
context injection to prevent duplication.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, JST, load_settings

logger = logging.getLogger(__name__)


@dataclass
class PostRecord:
    """Record of single post."""

    time_slot: str  # morning / noon / night
    style: str  # observation / question / humor / deep_thought / empathy
    content: str
    hashtags: list[str] = field(default_factory=list)
    char_count: int = 0


@dataclass
class NoteRecord:
    """Record of single note article."""

    title: str
    word_count: int = 0


@dataclass
class DailyRecord:
    """Record of one day's generation."""

    date: str  # YYYY-MM-DD
    theme: str
    posts: list[PostRecord] = field(default_factory=list)
    note: NoteRecord | None = None


class PostHistory:
    """Manage post history reading and writing."""

    def __init__(self, file_path: str | None = None) -> None:
        settings = load_settings()
        self._path = PROJECT_ROOT / (file_path or settings.history_file)
        self._keep_days = settings.history_keep_days
        self._recent_days = settings.history_recent_days
        self._records: list[DailyRecord] = []
        self._load()

    def _load(self) -> None:
        """Load history from JSON file."""
        if not self._path.exists():
            logger.info("History file not found, starting fresh: %s", self._path)
            self._records = []
            return

        try:
            with open(self._path, encoding="utf-8") as f:
                raw = json.load(f)

            self._records = []
            for entry in raw.get("history", []):
                posts = [
                    PostRecord(
                        time_slot=p["time_slot"],
                        style=p["style"],
                        content=p["content"],
                        hashtags=p.get("hashtags", []),
                        char_count=p.get("char_count", 0),
                    )
                    for p in entry.get("posts", [])
                ]
                note_raw = entry.get("note")
                note = (
                    NoteRecord(
                        title=note_raw["title"],
                        word_count=note_raw.get("word_count", 0),
                    )
                    if note_raw
                    else None
                )
                self._records.append(
                    DailyRecord(
                        date=entry["date"],
                        theme=entry["theme"],
                        posts=posts,
                        note=note,
                    )
                )
            logger.info("Loaded %d history records", len(self._records))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load history, starting fresh: %s", e)
            self._records = []

    def _save(self) -> None:
        """Write history to JSON file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "history": [asdict(r) for r in self._records],
            "last_updated": datetime.now(JST).isoformat(),
        }

        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("Saved %d history records to %s", len(self._records), self._path)

    def get_recent(self, days: int | None = None) -> list[DailyRecord]:
        """Get recent N days of history."""
        n = days or self._recent_days
        cutoff = (datetime.now(JST).date() - timedelta(days=n)).isoformat()
        recent = [r for r in self._records if r.date >= cutoff]
        return sorted(recent, key=lambda r: r.date, reverse=True)

    def add(self, record: DailyRecord) -> None:
        """Add today's generation result and clean old records."""
        # Overwrite if same date exists
        self._records = [r for r in self._records if r.date != record.date]
        self._records.append(record)
        self._cleanup()
        self._save()

    def _cleanup(self) -> None:
        """Remove history older than keep_days."""
        cutoff = (
            datetime.now(JST).date() - timedelta(days=self._keep_days)
        ).isoformat()
        before = len(self._records)
        self._records = [r for r in self._records if r.date >= cutoff]
        removed = before - len(self._records)
        if removed > 0:
            logger.info("Cleaned up %d old history records", removed)

    def format_recent_summary(self, days: int | None = None) -> str:
        """Format recent posts for prompt injection."""
        recent = self.get_recent(days)

        if not recent:
            return "（過去の投稿履歴はありません。初回生成です。）"

        lines: list[str] = []
        for record in recent:
            lines.append(f"### {record.date}（テーマ：{record.theme}）")
            for post in record.posts:
                preview = post.content[:60].replace("\n", " ")
                lines.append(
                    f"- {post.time_slot} [{post.style}]: {preview}..."
                )
            if record.note:
                lines.append(f"- 記事: 「{record.note.title}」")
            lines.append("")

        return "\n".join(lines)

    def format_recent_articles_summary(self, days: int | None = None) -> str:
        """Format recent articles for prompt injection."""
        recent = self.get_recent(days)
        articles = [r for r in recent if r.note]

        if not articles:
            return "（過去の記事履歴はありません。）"

        lines: list[str] = []
        for record in articles:
            if record.note:
                lines.append(
                    f"- {record.date}（{record.theme}）: 「{record.note.title}」"
                )

        return "\n".join(lines)
