"""Main entry point.

Run via GitHub Actions or manually.
1. Determine theme and style
2. Generate 3 X posts + 1 note article (50% cost reduction with Batch API)
3. Create GitHub Issue
4. Update post history
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime

from .config import (
    JST,
    get_today_theme,
    get_today_style,
    load_settings,
    load_themes,
    load_character,
)
from .generator import ContentGenerator
from .issue_creator import IssueCreator
from .history import PostHistory, DailyRecord
from .note_client import NoteClient

# ─── Logging configuration ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main process."""
    character = load_character()
    logger.info("=== %s Content Generator START ===", character.name)

    settings = load_settings()
    today = datetime.now(JST)
    date_str = today.strftime("%Y-%m-%d")

    # ─── Determine theme and style ───
    override_theme_name = os.environ.get("OVERRIDE_THEME", "").strip()
    trending_topic = os.environ.get("TRENDING_TOPIC", "").strip()

    if override_theme_name:
        themes = load_themes()
        matched = [t for t in themes if t.name == override_theme_name]
        if matched:
            theme = matched[0]
            logger.info("Using override theme: %s", theme.name)
        else:
            logger.warning(
                "Override theme '%s' not found, falling back to rotation",
                override_theme_name,
            )
            theme = get_today_theme(today.date())
    else:
        theme = get_today_theme(today.date())

    style = get_today_style(today.date())

    if trending_topic:
        logger.info("Trending topic: %s", trending_topic)

    # ─── Load history ───
    history = PostHistory()

    # ─── Generate content (Batch API or standard API) ───
    generator = ContentGenerator(settings)

    try:
        posts, note_record, note_full_text = generator.generate_all(
            theme, style, history, trending_topic
        )
    except Exception as e:
        logger.error("Content generation failed: %s", e)
        sys.exit(1)

    # ─── Create note.com draft ───
    if settings.note_client.enabled:
        note_client = NoteClient(
            request_delay=settings.note_client.request_delay,
        )
        if note_client.is_configured:
            result = note_client.create_draft(
                title=note_record.title, body_text=note_full_text
            )
            if result.status == "draft":
                logger.info(
                    "note.com draft created: %s (edit: %s)",
                    result.note_id,
                    result.edit_url,
                )
            else:
                logger.warning(
                    "note.com draft creation failed: %s",
                    result.error_message,
                )
        else:
            logger.warning(
                "note.com draft skipped: NOTE_SESSION_COOKIE not set"
            )

    # ─── Create GitHub Issue ───
    issue_creator = IssueCreator(settings)
    issue_url = issue_creator.create_issue(
        posts=posts,
        note_title=note_record.title,
        note_text=note_full_text,
        theme_name=theme.name,
        target_date=date_str,
    )

    if issue_url:
        logger.info("Issue created: %s", issue_url)
    else:
        # Issue creation skipped (local execution)
        body = issue_creator.format_issue_body(
            posts, note_record.title, note_full_text, theme.name
        )
        logger.info("Issue creation skipped. Output:\n%s", body)

    # ─── Update post history ───
    daily_record = DailyRecord(
        date=date_str,
        theme=theme.name,
        posts=posts,
        note=note_record,
    )
    history.add(daily_record)
    logger.info("Post history updated for %s", date_str)

    logger.info("=== %s Content Generator END ===", character.name)


if __name__ == "__main__":
    main()
