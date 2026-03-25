"""Content generation module.

Call Anthropic or OpenAI API to generate X posts and note articles.
Supports both Batch API (50% cost reduction, Anthropic only) and standard API.
"""

from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path
from typing import Any

from .config import (
    PROJECT_ROOT,
    Theme,
    StylePattern,
    load_settings,
    load_character,
    build_system_prompt,
    Settings,
)
from .history import PostHistory, PostRecord, NoteRecord

logger = logging.getLogger(__name__)


def _create_client(provider: str) -> Any:
    """Create API client based on provider setting."""
    if provider == "openai":
        try:
            import openai
            return openai.OpenAI()
        except ImportError:
            raise ImportError(
                "OpenAI provider selected but 'openai' package not installed. "
                "Run: pip install openai"
            )
    else:
        import os

        import anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        if not api_key and not auth_token:
            raise RuntimeError(
                "Anthropic authentication not configured. "
                "Set the ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN "
                "environment variable."
            )
        return anthropic.Anthropic()


class ContentGenerator:
    """Generate content based on character configuration."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.character = load_character()
        self.provider = self.settings.api.provider
        self.client = _create_client(self.provider)
        self._prompts_dir = PROJECT_ROOT / "prompts"

    def _read_prompt(self, relative_path: str) -> str:
        """Read prompt template file."""
        path = self._prompts_dir / relative_path
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {path}")
        return path.read_text(encoding="utf-8")

    def _load_examples(self, style: str) -> str:
        """Load few-shot examples for specified style."""
        path = self._prompts_dir / "x_post" / "examples" / f"{style}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _build_x_post_prompt(
        self,
        theme: Theme,
        style: StylePattern,
        history: PostHistory,
        trending_topic: str = "",
    ) -> str:
        """Build user prompt for X post generation."""
        template = self._read_prompt("x_post/base.md")

        # Load few-shot examples for all styles
        examples_parts: list[str] = []
        for s in set([style.morning, style.noon, style.night]):
            ex = self._load_examples(s)
            if ex:
                examples_parts.append(ex)
        examples = "\n\n".join(examples_parts)

        # Random 3 sub-topics as hints
        sub_topic_hint = ""
        if theme.sub_topics:
            selected = random.sample(
                theme.sub_topics, min(3, len(theme.sub_topics))
            )
            sub_topic_hint = (
                "\n\n今日の切り口のヒント（参考。必ず使う必要はない）：\n"
                + "\n".join(f"- {t}" for t in selected)
            )

        # Trending topic injection
        trending_section = ""
        if trending_topic:
            trending_section = (
                f"\n\n<trending_topic>\n"
                f"今日のトレンド：{trending_topic}\n"
                f"通常テーマに絡めつつ、時事ネタを織り込んでください。\n"
                f"</trending_topic>"
            )

        prompt = template.replace("{theme_name}", theme.name)
        prompt = prompt.replace("{theme_description}", theme.description)
        prompt = prompt.replace("{theme_keywords}", ", ".join(theme.keywords))
        prompt = prompt.replace("{morning_style}", style.morning)
        prompt = prompt.replace("{noon_style}", style.noon)
        prompt = prompt.replace("{night_style}", style.night)
        prompt = prompt.replace(
            "{recent_posts_summary}", history.format_recent_summary()
        )
        prompt = prompt.replace("{few_shot_examples}", examples)
        prompt = prompt.replace("{character_name}", self.character.name)
        prompt += sub_topic_hint
        prompt += trending_section

        return prompt

    def _build_note_prompt(
        self, theme: Theme, history: PostHistory
    ) -> str:
        """Build user prompt for note article generation."""
        template = self._read_prompt("note_article/base.md")

        prompt = template.replace("{theme_name}", theme.name)
        prompt = prompt.replace("{theme_description}", theme.description)
        prompt = prompt.replace("{theme_keywords}", ", ".join(theme.keywords))
        prompt = prompt.replace(
            "{recent_articles_summary}",
            history.format_recent_articles_summary(),
        )
        prompt = prompt.replace("{character_name}", self.character.name)
        prompt = prompt.replace("{series_name}", self.character.series_name)

        return prompt

    # ─── Standard API calls ───

    def _call_api(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Make standard API call with retry support.

        Supports both Anthropic and OpenAI providers.
        """
        if self.provider == "openai":
            return self._call_openai_api(system_prompt, user_prompt)
        return self._call_anthropic_api(system_prompt, user_prompt)

    def _call_anthropic_api(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Make Anthropic API call with retry support."""
        import anthropic

        last_error: Exception | None = None

        for attempt in range(self.settings.retry.max_retries + 1):
            try:
                response = self.client.messages.create(
                    model=self.settings.api.model,
                    max_tokens=self.settings.api.max_tokens,
                    temperature=self.settings.api.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                text = response.content[0].text
                usage = response.usage
                logger.info(
                    "API call: input=%d, output=%d tokens",
                    usage.input_tokens,
                    usage.output_tokens,
                )
                return text

            except anthropic.RateLimitError as e:
                last_error = e
                wait = self.settings.retry.backoff_factor ** attempt
                logger.warning("Rate limited, waiting %ds: %s", wait, e)
                time.sleep(wait)

            except anthropic.APIStatusError as e:
                if e.status_code in self.settings.retry.retry_on_status:
                    last_error = e
                    wait = self.settings.retry.backoff_factor ** attempt
                    logger.warning("API error %d, waiting %ds", e.status_code, wait)
                    time.sleep(wait)
                else:
                    raise

        raise RuntimeError(f"API call failed after retries: {last_error}")

    def _call_openai_api(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Make OpenAI API call with retry support."""
        import openai

        last_error: Exception | None = None

        for attempt in range(self.settings.retry.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.settings.api.model,
                    max_tokens=self.settings.api.max_tokens,
                    temperature=self.settings.api.temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                text = response.choices[0].message.content
                usage = response.usage
                logger.info(
                    "API call: input=%d, output=%d tokens",
                    usage.prompt_tokens,
                    usage.completion_tokens,
                )
                return text

            except openai.RateLimitError as e:
                last_error = e
                wait = self.settings.retry.backoff_factor ** attempt
                logger.warning("Rate limited, waiting %ds: %s", wait, e)
                time.sleep(wait)

            except openai.APIStatusError as e:
                if e.status_code in self.settings.retry.retry_on_status:
                    last_error = e
                    wait = self.settings.retry.backoff_factor ** attempt
                    logger.warning("API error %d, waiting %ds", e.status_code, wait)
                    time.sleep(wait)
                else:
                    raise

        raise RuntimeError(f"API call failed after retries: {last_error}")

    # ─── Batch API calls (50% cost reduction) ───

    def _call_batch_api(
        self,
        requests: list[dict[str, Any]],
    ) -> dict[str, str]:
        """Execute multiple requests via Batch API with 50% cost discount.

        Args:
            requests: [{"custom_id": "x_posts", "system": "...", "user": "..."}]

        Returns:
            {"custom_id": "response_text", ...}
        """
        batch_requests = []
        for req in requests:
            batch_requests.append({
                "custom_id": req["custom_id"],
                "params": {
                    "model": self.settings.api.model,
                    "max_tokens": self.settings.api.max_tokens,
                    "temperature": self.settings.api.temperature,
                    "system": req["system"],
                    "messages": [{"role": "user", "content": req["user"]}],
                },
            })

        logger.info("Creating batch with %d requests...", len(batch_requests))
        batch = self.client.messages.batches.create(requests=batch_requests)
        batch_id = batch.id
        logger.info("Batch created: %s", batch_id)

        # Poll for completion
        timeout = self.settings.api.batch_poll_timeout
        interval = self.settings.api.batch_poll_interval
        elapsed = 0

        while elapsed < timeout:
            batch = self.client.messages.batches.retrieve(batch_id)
            status = batch.processing_status

            if status == "ended":
                logger.info("Batch completed: %s", batch_id)
                break

            logger.info(
                "Batch %s: status=%s, elapsed=%ds/%ds",
                batch_id, status, elapsed, timeout,
            )
            time.sleep(interval)
            elapsed += interval
        else:
            raise RuntimeError(
                f"Batch {batch_id} timed out after {timeout}s (status: {status})"
            )

        # Retrieve results
        results: dict[str, str] = {}
        for result in self.client.messages.batches.results(batch_id):
            custom_id = result.custom_id
            if result.result.type == "succeeded":
                message = result.result.message
                text = message.content[0].text
                usage = message.usage
                logger.info(
                    "Batch result [%s]: input=%d, output=%d tokens",
                    custom_id,
                    usage.input_tokens,
                    usage.output_tokens,
                )
                results[custom_id] = text
            else:
                error = getattr(result.result, "error", "unknown error")
                logger.error("Batch result [%s] failed: %s", custom_id, error)
                raise RuntimeError(f"Batch request '{custom_id}' failed: {error}")

        return results

    # ─── JSON parsing ───

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """Extract and parse JSON from API response."""
        if "```json" in text:
            start = text.index("```json") + len("```json")
            end = text.index("```", start)
            json_str = text[start:end].strip()
        elif "```" in text:
            start = text.index("```") + len("```")
            end = text.index("```", start)
            json_str = text[start:end].strip()
        else:
            json_str = text.strip()

        return json.loads(json_str)

    def _parse_x_posts(self, text: str) -> list[PostRecord]:
        """Parse X post API response."""
        data = self._parse_json_response(text)
        posts = []
        for p in data["posts"]:
            posts.append(
                PostRecord(
                    time_slot=p["time_slot"],
                    style=p["style"],
                    content=p["content"],
                    hashtags=p.get("hashtags", []),
                    char_count=p.get("char_count", len(p["content"])),
                )
            )
        return posts

    def _parse_note_article(self, text: str) -> tuple[NoteRecord, str]:
        """Parse note article API response."""
        data = self._parse_json_response(text)
        record = NoteRecord(
            title=data["title"],
            word_count=data.get("word_count", 0),
        )
        full_text = data.get("full_text", "")
        return record, full_text

    # ─── Public methods ───

    def generate_all(
        self,
        theme: Theme,
        style: StylePattern,
        history: PostHistory,
        trending_topic: str = "",
    ) -> tuple[list[PostRecord], NoteRecord, str]:
        """Generate 3 X posts + 1 note article.

        Uses Batch API for 50% cost discount if enabled,
        otherwise uses standard API with sequential calls.

        Returns:
            (posts, note_record, note_full_text)
        """
        system_prompt = build_system_prompt(self.character)
        x_post_prompt = self._build_x_post_prompt(
            theme, style, history, trending_topic
        )
        note_prompt = self._build_note_prompt(theme, history)

        if self.settings.api.use_batch_api and self.provider == "anthropic":
            logger.info("Using Batch API (50%% cost reduction)")
            results = self._call_batch_api([
                {
                    "custom_id": "x_posts",
                    "system": system_prompt,
                    "user": x_post_prompt,
                },
                {
                    "custom_id": "note_article",
                    "system": system_prompt,
                    "user": note_prompt,
                },
            ])

            posts = self._parse_x_posts(results["x_posts"])
            note_record, note_full_text = self._parse_note_article(
                results["note_article"]
            )
        else:
            logger.info("Using standard API")
            x_response = self._call_api(system_prompt, x_post_prompt)
            posts = self._parse_x_posts(x_response)

            note_response = self._call_api(system_prompt, note_prompt)
            note_record, note_full_text = self._parse_note_article(note_response)

        logger.info(
            "Generated %d X posts + note article '%s'",
            len(posts),
            note_record.title,
        )
        return posts, note_record, note_full_text
