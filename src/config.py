"""設定管理モジュール。

character.yaml からキャラクター設定を読み込み、
system promptを自動生成する。
themes.json と settings.yaml を読み込み、
日付ベースのテーマ選択とスタイルローテーションを提供する。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Timezone (JST)
JST = timezone(timedelta(hours=9))


@dataclass
class CharacterPersonality:
    """Character personality traits."""

    traits: list[str] = field(default_factory=list)  # Personality traits
    perspective: str = ""  # How the character views the world
    interests: list[str] = field(default_factory=list)  # Character interests


@dataclass
class CharacterToneRules:
    """Character tone and communication style."""

    style_mix: dict[str, int] = field(default_factory=dict)  # e.g. {"polite": 60, "casual": 25}
    frequent_phrases: list[str] = field(default_factory=list)
    forbidden_patterns: list[str] = field(default_factory=list)


@dataclass
class CharacterConstraints:
    """Character behavioral constraints."""

    always_do: list[str] = field(default_factory=list)
    never_do: list[str] = field(default_factory=list)


@dataclass
class CharacterConfig:
    """Character configuration from character.yaml."""

    name: str
    role: str
    description: str
    developer: str = ""
    personality: CharacterPersonality = field(default_factory=CharacterPersonality)
    tone_rules: CharacterToneRules = field(default_factory=CharacterToneRules)
    constraints: CharacterConstraints = field(default_factory=CharacterConstraints)
    thinking_style: str = ""
    series_name: str = ""  # For note articles (e.g. "Observation Notebook")


@dataclass
class Theme:
    """Theme definition."""

    id: int
    name: str
    description: str
    keywords: list[str]
    sub_topics: list[str] = field(default_factory=list)


@dataclass
class StylePattern:
    """Post style combination."""

    morning: str
    noon: str
    night: str


@dataclass
class QualitySettings:
    """Quality standards."""

    min_overall_score: float = 7.0
    x_post_min_chars: int = 140
    x_post_max_chars: int = 280
    x_post_max_hashtags: int = 2
    note_min_chars: int = 1500
    note_max_chars: int = 3000


@dataclass
class ApiSettings:
    """API settings."""

    provider: str = "anthropic"  # "anthropic" or "openai"
    model: str = "claude-sonnet-4-20250514"
    review_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 4096
    temperature: float = 0.85
    # Batch API (50% cost reduction, Anthropic only)
    use_batch_api: bool = True
    batch_poll_timeout: int = 1800  # 30 minutes
    batch_poll_interval: int = 30  # Poll every 30 seconds


@dataclass
class ReviewSettings:
    """Self-review settings."""

    enabled: bool = False  # Disabled by default to reduce costs


@dataclass
class RetrySettings:
    """Retry settings."""

    max_retries: int = 3
    backoff_factor: int = 2
    retry_on_status: list[int] = field(
        default_factory=lambda: [429, 500, 502, 503, 529]
    )


@dataclass
class NoteClientSettings:
    """note.com draft creation settings."""

    enabled: bool = False  # Disabled by default (requires cookie setup)
    request_delay: float = 1.0  # Seconds between API requests


@dataclass
class Settings:
    """All settings."""

    api: ApiSettings = field(default_factory=ApiSettings)
    review: ReviewSettings = field(default_factory=ReviewSettings)
    retry: RetrySettings = field(default_factory=RetrySettings)
    quality: QualitySettings = field(default_factory=QualitySettings)
    note_client: NoteClientSettings = field(default_factory=NoteClientSettings)
    history_file: str = "data/post_history.json"
    history_keep_days: int = 30
    history_recent_days: int = 7
    issue_title_template: str = "📝 投稿案 ── {date}（{theme}）"
    issue_labels: list[str] = field(
        default_factory=lambda: ["generated", "content"]
    )


def load_character() -> CharacterConfig:
    """Load character configuration from config/character.yaml."""
    char_path = PROJECT_ROOT / "config" / "character.yaml"

    if not char_path.exists():
        raise FileNotFoundError(
            f"character.yaml not found at {char_path}. "
            "Please create it with your character definition."
        )

    with open(char_path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    personality_raw = raw.get("personality", {})
    tone_raw = raw.get("tone_rules", {})
    constraints_raw = raw.get("constraints", {})

    personality = CharacterPersonality(
        traits=personality_raw.get("traits", []),
        perspective=personality_raw.get("perspective", ""),
        interests=personality_raw.get("interests", []),
    )

    tone_rules = CharacterToneRules(
        style_mix=tone_raw.get("style_mix", {}),
        frequent_phrases=tone_raw.get("frequent_phrases", []),
        forbidden_patterns=tone_raw.get("forbidden_patterns", []),
    )

    constraints = CharacterConstraints(
        always_do=constraints_raw.get("always_do", []),
        never_do=constraints_raw.get("never_do", []),
    )

    config = CharacterConfig(
        name=raw.get("name", "Unknown"),
        role=raw.get("role", ""),
        description=raw.get("description", ""),
        developer=raw.get("developer", ""),
        personality=personality,
        tone_rules=tone_rules,
        constraints=constraints,
        thinking_style=raw.get("thinking_style", ""),
        series_name=raw.get("series_name", "Observation Notebook"),
    )

    logger.info("Loaded character config: %s", config.name)
    return config


def build_system_prompt(character: CharacterConfig) -> str:
    """Build XML-structured system prompt from character configuration.

    Args:
        character: CharacterConfig instance

    Returns:
        System prompt as XML-formatted string
    """
    # Build identity section
    identity_lines = [
        f"  <name>{character.name}</name>",
        f"  <role>{character.role}</role>",
        f"  <description>{character.description}</description>",
    ]
    if character.developer:
        identity_lines.append(f"  <developer>{character.developer}</developer>")

    identity_section = (
        "<identity>\n"
        + "\n".join(identity_lines)
        + "\n</identity>"
    )

    # Build personality section
    personality_lines = []
    if character.personality.perspective:
        personality_lines.append(
            f"  <perspective>{character.personality.perspective}</perspective>"
        )
    if character.personality.traits:
        traits_str = ", ".join(character.personality.traits)
        personality_lines.append(f"  <traits>{traits_str}</traits>")
    if character.personality.interests:
        interests_str = "\n    ".join(character.personality.interests)
        personality_lines.append(f"  <interests>\n    {interests_str}\n  </interests>")

    personality_section = ""
    if personality_lines:
        personality_section = (
            "<personality>\n"
            + "\n".join(personality_lines)
            + "\n</personality>"
        )

    # Build tone rules section
    tone_lines = []
    if character.tone_rules.style_mix:
        style_entries = [
            f"    {style}: {pct}%" for style, pct in character.tone_rules.style_mix.items()
        ]
        tone_lines.append(f"  <style_mix>\n" + "\n".join(style_entries) + "\n  </style_mix>")

    if character.tone_rules.frequent_phrases:
        phrases_str = "\n    ".join(character.tone_rules.frequent_phrases)
        tone_lines.append(f"  <frequent_phrases>\n    {phrases_str}\n  </frequent_phrases>")

    tone_section = ""
    if tone_lines:
        tone_section = (
            "<tone_rules>\n"
            + "\n".join(tone_lines)
            + "\n</tone_rules>"
        )

    # Build constraints section
    constraint_lines = []
    if character.constraints.always_do:
        always_str = "\n    ".join(character.constraints.always_do)
        constraint_lines.append(f"  <always_do>\n    {always_str}\n  </always_do>")

    if character.constraints.never_do:
        never_str = "\n    ".join(character.constraints.never_do)
        constraint_lines.append(f"  <never_do>\n    {never_str}\n  </never_do>")

    constraints_section = ""
    if constraint_lines:
        constraints_section = (
            "<constraints>\n"
            + "\n".join(constraint_lines)
            + "\n</constraints>"
        )

    # Build thinking style section
    thinking_section = ""
    if character.thinking_style:
        thinking_section = f"<thinking_style>\n{character.thinking_style}\n</thinking_style>"

    # Assemble full prompt
    sections = [
        "<system>",
        identity_section,
        personality_section,
        tone_section,
        thinking_section,
        constraints_section,
        "</system>",
    ]

    # Filter out empty sections
    prompt = "\n\n".join(s for s in sections if s)
    return prompt


def load_settings() -> Settings:
    """Load settings.yaml and return Settings."""
    settings_path = PROJECT_ROOT / "config" / "settings.yaml"

    if not settings_path.exists():
        logger.warning("settings.yaml not found, using defaults")
        return Settings()

    with open(settings_path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    api_raw = raw.get("api", {})
    review_raw = raw.get("review", {})
    retry_raw = raw.get("retry", {})
    quality_raw = raw.get("quality", {})
    note_client_raw = raw.get("note_client", {})
    history_raw = raw.get("history", {})
    issue_raw = raw.get("issue", {})

    x_post_raw = quality_raw.get("x_post", {})
    note_raw = quality_raw.get("note_article", {})

    return Settings(
        api=ApiSettings(
            provider=api_raw.get("provider", "anthropic"),
            model=api_raw.get("model", "claude-sonnet-4-20250514"),
            review_model=api_raw.get("review_model", "claude-haiku-4-5-20251001"),
            max_tokens=api_raw.get("max_tokens", 4096),
            temperature=api_raw.get("temperature", 0.85),
            use_batch_api=api_raw.get("use_batch_api", True),
            batch_poll_timeout=api_raw.get("batch_poll_timeout", 1800),
            batch_poll_interval=api_raw.get("batch_poll_interval", 30),
        ),
        review=ReviewSettings(
            enabled=review_raw.get("enabled", False),
        ),
        retry=RetrySettings(
            max_retries=retry_raw.get("max_retries", 3),
            backoff_factor=retry_raw.get("backoff_factor", 2),
            retry_on_status=retry_raw.get("retry_on_status", [429, 500, 502, 503, 529]),
        ),
        quality=QualitySettings(
            x_post_min_chars=x_post_raw.get("min_chars", 140),
            x_post_max_chars=x_post_raw.get("max_chars", 280),
            x_post_max_hashtags=x_post_raw.get("max_hashtags", 2),
            note_min_chars=note_raw.get("min_chars", 1500),
            note_max_chars=note_raw.get("max_chars", 3000),
        ),
        note_client=NoteClientSettings(
            enabled=note_client_raw.get("enabled", False),
            request_delay=note_client_raw.get("request_delay", 1.0),
        ),
        history_file=history_raw.get("file_path", "data/post_history.json"),
        history_keep_days=history_raw.get("keep_days", 30),
        history_recent_days=history_raw.get("recent_days", 7),
        issue_title_template=issue_raw.get(
            "title_template", "📝 投稿案 ── {date}（{theme}）"
        ),
        issue_labels=issue_raw.get("labels", ["generated", "content"]),
    )


def load_themes() -> list[Theme]:
    """Load themes from themes.json."""
    themes_path = PROJECT_ROOT / "config" / "themes.json"

    with open(themes_path, encoding="utf-8") as f:
        raw = json.load(f)

    return [
        Theme(
            id=t["id"],
            name=t["name"],
            description=t["description"],
            keywords=t["keywords"],
            sub_topics=t.get("sub_topics", []),
        )
        for t in raw["themes"]
    ]


def load_style_patterns() -> list[StylePattern]:
    """Load style rotation patterns from themes.json."""
    themes_path = PROJECT_ROOT / "config" / "themes.json"

    with open(themes_path, encoding="utf-8") as f:
        raw = json.load(f)

    return [
        StylePattern(
            morning=p["morning"],
            noon=p["noon"],
            night=p["night"],
        )
        for p in raw["style_rotation"]["patterns"]
    ]


def get_today_theme(target_date: date | None = None) -> Theme:
    """Determine theme based on date. Uses 5-theme rotation."""
    themes = load_themes()
    d = target_date or datetime.now(JST).date()
    index = d.toordinal() % len(themes)
    theme = themes[index]
    logger.info("Today's theme: %s (id=%d)", theme.name, theme.id)
    return theme


def get_today_style(target_date: date | None = None) -> StylePattern:
    """Determine style pattern based on date. Uses 7-day cycle."""
    patterns = load_style_patterns()
    d = target_date or datetime.now(JST).date()
    index = d.toordinal() % len(patterns)
    pattern = patterns[index]
    logger.info(
        "Today's style: morning=%s, noon=%s, night=%s",
        pattern.morning,
        pattern.noon,
        pattern.night,
    )
    return pattern
