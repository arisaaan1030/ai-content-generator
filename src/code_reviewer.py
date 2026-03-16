"""AI Code Review module.

Send PR diff to API and review code
from code quality, bug, and security perspectives.
Supports both Anthropic and OpenAI providers.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, Settings, load_settings

logger = logging.getLogger(__name__)

# Reviewable file extensions
REVIEWABLE_EXTENSIONS = {
    ".py", ".yml", ".yaml", ".json", ".md", ".toml", ".cfg", ".ini",
}

# Paths to exclude from review
EXCLUDED_PATHS = {
    "data/post_history.json",
}


@dataclass
class ReviewComment:
    """Single review comment."""

    file: str
    line: int
    severity: str  # error, warning, info
    category: str  # quality, bug, security, performance, readability
    message: str
    suggestion: str = ""


@dataclass
class ReviewResult:
    """Overall review result."""

    summary: str
    score: float
    comments: list[ReviewComment] = field(default_factory=list)
    approved: bool = True


class CodeReviewer:
    """Review PR diff with AI."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.provider = self.settings.api.provider
        if self.provider == "openai":
            try:
                import openai
            except ImportError:
                raise ImportError(
                    "OpenAI provider selected but 'openai' package not installed. "
                    "Run: pip install openai"
                )
            if not os.environ.get("OPENAI_API_KEY"):
                raise RuntimeError(
                    "OPENAI_API_KEY environment variable is not set. "
                    "Please set it in GitHub Repository Settings → Secrets and variables → Actions, "
                    "or export it locally before running."
                )
            self.client = openai.OpenAI()
        else:
            import anthropic
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError(
                    "ANTHROPIC_API_KEY environment variable is not set. "
                    "Please set it in GitHub Repository Settings → Secrets and variables → Actions, "
                    "or export it locally before running."
                )
            self.client = anthropic.Anthropic()
        self._prompt_path = PROJECT_ROOT / "prompts" / "review" / "code_review.md"
        self._token = os.environ.get("GITHUB_TOKEN", "")
        self._repo = os.environ.get("GITHUB_REPOSITORY", "")

    def _get_system_prompt(self) -> str:
        """Load system prompt for code review."""
        if not self._prompt_path.exists():
            raise FileNotFoundError(
                f"Review prompt not found: {self._prompt_path}"
            )
        return self._prompt_path.read_text(encoding="utf-8")

    def _get_agents_md(self) -> str:
        """Load AGENTS.md for project conventions."""
        agents_path = PROJECT_ROOT / "AGENTS.md"
        if agents_path.exists():
            return agents_path.read_text(encoding="utf-8")
        return ""

    def _get_pr_diff(self) -> str:
        """Get PR diff.

        In GitHub Actions environment, use git diff to compute
        difference from base branch.
        """
        base_ref = os.environ.get("GITHUB_BASE_REF", "main")

        try:
            # Fetch base branch after checkout
            subprocess.run(
                ["git", "fetch", "origin", base_ref],
                capture_output=True,
                text=True,
                check=True,
                cwd=str(PROJECT_ROOT),
            )

            result = subprocess.run(
                ["git", "diff", f"origin/{base_ref}...HEAD", "--", "."],
                capture_output=True,
                text=True,
                check=True,
                cwd=str(PROJECT_ROOT),
            )
            return result.stdout

        except subprocess.CalledProcessError as e:
            logger.error("Failed to get diff: %s", e.stderr)
            raise RuntimeError(f"Failed to get PR diff: {e.stderr}") from e

    def _filter_diff(self, diff: str) -> str:
        """Filter diff to only reviewable files."""
        filtered_parts: list[str] = []
        current_file = ""
        current_section: list[str] = []

        for line in diff.split("\n"):
            if line.startswith("diff --git"):
                # Save previous file
                if current_file and current_section:
                    filtered_parts.append("\n".join(current_section))

                # Parse new file
                parts = line.split(" b/")
                if len(parts) >= 2:
                    current_file = parts[-1]
                else:
                    current_file = ""

                current_section = []

                # Filter check
                if current_file in EXCLUDED_PATHS:
                    current_file = ""
                    continue

                ext = Path(current_file).suffix
                if ext not in REVIEWABLE_EXTENSIONS:
                    current_file = ""
                    continue

                current_section.append(line)
            elif current_file:
                current_section.append(line)

        # Last file
        if current_file and current_section:
            filtered_parts.append("\n".join(current_section))

        return "\n".join(filtered_parts)

    def _truncate_diff(self, diff: str, max_chars: int = 30000) -> str:
        """Truncate diff if too large."""
        if len(diff) <= max_chars:
            return diff

        logger.warning(
            "Diff too large (%d chars), truncating to %d",
            len(diff),
            max_chars,
        )
        return diff[:max_chars] + "\n\n... (truncated due to size limit)"

    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """Call API for code review.

        Uses standard API (not Batch) for immediate feedback.
        Uses review_model from settings to reduce costs.
        Supports both Anthropic and OpenAI providers.
        """
        review_model = self.settings.api.review_model

        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=review_model,
                max_tokens=4096,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = response.choices[0].message.content
            usage = response.usage
            logger.info(
                "Review API call: input=%d, output=%d tokens",
                usage.prompt_tokens,
                usage.completion_tokens,
            )
        else:
            response = self.client.messages.create(
                model=review_model,
                max_tokens=4096,
                temperature=0.2,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = response.content[0].text
            usage = response.usage
            logger.info(
                "Review API call: input=%d, output=%d tokens",
                usage.input_tokens,
                usage.output_tokens,
            )
        return text

    def _parse_review_result(self, text: str) -> ReviewResult:
        """Parse review result from API response."""
        # Extract JSON
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

        data = json.loads(json_str)

        comments = [
            ReviewComment(
                file=c.get("file", ""),
                line=c.get("line", 0),
                severity=c.get("severity", "info"),
                category=c.get("category", "quality"),
                message=c.get("message", ""),
                suggestion=c.get("suggestion", ""),
            )
            for c in data.get("comments", [])
        ]

        return ReviewResult(
            summary=data.get("summary", ""),
            score=data.get("score", 0.0),
            comments=comments,
            approved=data.get("approved", True),
        )

    def _post_pr_comment(self, pr_number: int, body: str) -> None:
        """Post comment on PR."""
        if not self._token or not self._repo:
            logger.warning("GitHub credentials not set, skipping PR comment")
            return

        url = f"https://api.github.com/repos/{self._repo}/issues/{pr_number}/comments"
        payload = json.dumps({"body": body}).encode("utf-8")

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
                logger.info("Posted review comment: %s", result.get("html_url", ""))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8") if e.fp else ""
            logger.error("Failed to post comment: %d %s\n%s", e.code, e.reason, body_text)

    def _format_review_comment(self, result: ReviewResult) -> str:
        """Format review result as Markdown comment."""
        lines: list[str] = []

        # Header
        status = "✅ Approved" if result.approved else "❌ Changes Requested"
        lines.append(f"## 🤖 Code Review ── {status}")
        lines.append("")
        lines.append(f"> **Score**: {result.score:.1f} / 10.0")
        lines.append(f"> {result.summary}")
        lines.append("")

        if not result.comments:
            lines.append("No issues found. Great code!")
            return "\n".join(lines)

        # Group by severity
        errors = [c for c in result.comments if c.severity == "error"]
        warnings = [c for c in result.comments if c.severity == "warning"]
        infos = [c for c in result.comments if c.severity == "info"]

        for label, icon, group in [
            ("Error (Must Fix)", "🔴", errors),
            ("Warning (Recommended)", "🟡", warnings),
            ("Info (Suggestions)", "🔵", infos),
        ]:
            if not group:
                continue

            lines.append(f"### {icon} {label}\n")
            for c in group:
                location = f"`{c.file}"
                if c.line > 0:
                    location += f":{c.line}"
                location += "`"

                lines.append(f"- **{location}** [{c.category}]")
                lines.append(f"  {c.message}")
                if c.suggestion:
                    lines.append(f"  ```python\n  {c.suggestion}\n  ```")
                lines.append("")

        # Footer
        lines.append("---")
        review_model = self.settings.api.review_model
        lines.append(
            f"<sub>🤖 Reviewed by AI Code Reviewer "
            f"({review_model} · `prompts/review/code_review.md`)</sub>"
        )

        return "\n".join(lines)

    def review_pr(self, pr_number: int | None = None) -> ReviewResult:
        """Review PR and post comment.

        Args:
            pr_number: PR number. If not specified, get from environment.

        Returns:
            ReviewResult: Review result
        """
        # Get PR number
        if pr_number is None:
            pr_ref = os.environ.get("GITHUB_REF", "")
            # refs/pull/123/merge → 123
            if "/pull/" in pr_ref:
                pr_number = int(pr_ref.split("/pull/")[1].split("/")[0])
            else:
                logger.warning("Could not determine PR number from GITHUB_REF: %s", pr_ref)
                pr_number = 0

        logger.info("Reviewing PR #%d", pr_number)

        # Get and filter diff
        raw_diff = self._get_pr_diff()
        filtered_diff = self._filter_diff(raw_diff)

        if not filtered_diff.strip():
            logger.info("No reviewable changes found")
            return ReviewResult(
                summary="No reviewable changes found.",
                score=10.0,
                approved=True,
            )

        truncated_diff = self._truncate_diff(filtered_diff)

        # Build prompt
        system_prompt = self._get_system_prompt()
        agents_md = self._get_agents_md()

        user_prompt = (
            f"<project_rules>\n{agents_md}\n</project_rules>\n\n"
            f"<pull_request_diff>\n{truncated_diff}\n</pull_request_diff>\n\n"
            "Review the PR diff above. Check compliance with project_rules as well."
        )

        # Call API
        response_text = self._call_api(system_prompt, user_prompt)

        # Parse result
        try:
            result = self._parse_review_result(response_text)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to parse review result: %s", e)
            logger.debug("Raw response: %s", response_text)
            result = ReviewResult(
                summary=f"Failed to parse review result: {e}",
                score=0.0,
                approved=False,
            )

        # Post PR comment
        if pr_number > 0:
            comment_body = self._format_review_comment(result)
            self._post_pr_comment(pr_number, comment_body)

        logger.info(
            "Review complete: score=%.1f, approved=%s, comments=%d",
            result.score,
            result.approved,
            len(result.comments),
        )

        return result
