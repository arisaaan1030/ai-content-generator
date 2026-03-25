"""note.com draft creation module.

Create article drafts on note.com via unofficial API.
Authentication uses the _note_session_v5 cookie.
Supports automatic cookie refresh via email/password login.
Final publishing is done manually via browser.
"""

from __future__ import annotations

import http.cookiejar
import json
import logging
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass

logger = logging.getLogger(__name__)

NOTE_API_BASE = "https://note.com/api/v1"
NOTE_LOGIN_URL = "https://note.com/api/v1/sessions/sign_in"


@dataclass
class NoteDraftResult:
    """Result of draft creation."""

    note_id: str
    status: str  # "draft" or "error"
    edit_url: str = ""
    error_message: str = ""


class NoteClient:
    """Create article drafts on note.com via unofficial API.

    Authentication priority:
        1. NOTE_SESSION_COOKIE env var (direct cookie)
        2. NOTE_EMAIL + NOTE_PASSWORD env vars (auto-login)

    Auto-login: If email/password are set, the client will
    automatically log in to get a session cookie and refresh
    it on 401 errors.

    Usage:
        Option A (manual cookie):
            1. Log in to note.com in your browser
            2. Extract the _note_session_v5 cookie value
            3. Set it as NOTE_SESSION_COOKIE environment variable

        Option B (auto-login, recommended):
            1. Set NOTE_EMAIL and NOTE_PASSWORD environment variables
            2. Cookie is obtained and refreshed automatically
    """

    def __init__(self, request_delay: float = 1.0) -> None:
        self._session_cookie = os.environ.get("NOTE_SESSION_COOKIE", "")
        self._email = os.environ.get("NOTE_EMAIL", "")
        self._password = os.environ.get("NOTE_PASSWORD", "")
        self._request_delay = request_delay

        if not self._session_cookie and self._email and self._password:
            logger.info("No session cookie set, attempting auto-login...")
            self._login()
        elif not self._session_cookie:
            logger.warning(
                "NOTE_SESSION_COOKIE (or NOTE_EMAIL + NOTE_PASSWORD) not set. "
                "note.com draft creation will be skipped."
            )

    @property
    def is_configured(self) -> bool:
        """Check if the client has valid credentials."""
        return bool(self._session_cookie)

    def _login(self) -> None:
        """Log in to note.com and obtain a session cookie.

        Uses email/password to authenticate and extracts
        the _note_session_v5 cookie from the response.
        """
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookie_jar)
        )

        payload = json.dumps({
            "login": self._email,
            "password": self._password,
        }).encode("utf-8")

        req = urllib.request.Request(
            NOTE_LOGIN_URL,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        )

        try:
            opener.open(req)
        except urllib.error.HTTPError as e:
            logger.error("note.com login failed: %d %s", e.code, e.reason)
            return

        for cookie in cookie_jar:
            if cookie.name == "_note_session_v5":
                self._session_cookie = cookie.value
                logger.info("note.com login successful, session cookie obtained")
                return

        logger.error("Login succeeded but _note_session_v5 cookie not found")

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with session cookie."""
        return {
            "Content-Type": "application/json",
            "Cookie": f"_note_session_v5={self._session_cookie}",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://note.com",
            "Referer": "https://note.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

    def _api_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict | None = None,
        *,
        _retried: bool = False,
    ) -> dict:
        """Make API request to note.com.

        On 401 errors, automatically re-login and retry once
        if email/password credentials are available.

        Args:
            endpoint: API endpoint path (e.g., "/text_notes")
            method: HTTP method
            data: Request body (JSON-serializable)

        Returns:
            Parsed JSON response
        """
        url = f"{NOTE_API_BASE}{endpoint}"
        headers = self._build_headers()

        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(
            url, data=body, headers=headers, method=method
        )

        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # Auto-refresh cookie on 401 if credentials are available
            if e.code == 401 and not _retried and self._email and self._password:
                logger.warning("Session expired, attempting re-login...")
                self._login()
                if self._session_cookie:
                    return self._api_request(
                        endpoint, method, data, _retried=True
                    )

            body_text = e.read().decode("utf-8") if e.fp else ""
            logger.error(
                "note.com API error: %d %s\n%s", e.code, e.reason, body_text
            )
            raise

    def create_draft(
        self, title: str, body_text: str
    ) -> NoteDraftResult:
        """Create a new article draft on note.com.

        The note.com API requires two steps:
        1. POST /text_notes — create article entry (title only)
        2. POST /text_notes/draft_save?id={id} — save body content

        Args:
            title: Article title
            body_text: Article body (plain text or basic HTML)

        Returns:
            NoteDraftResult with draft ID and edit URL
        """
        if not self.is_configured:
            return NoteDraftResult(
                note_id="",
                status="error",
                error_message="NOTE_SESSION_COOKIE not configured",
            )

        try:
            # Step 1: Create article entry
            logger.info("Creating note.com draft: %s", title)
            create_resp = self._api_request(
                "/text_notes",
                method="POST",
                data={"name": title},
            )

            note_data = create_resp.get("data", {})
            note_id = str(note_data.get("id", ""))

            if not note_id:
                return NoteDraftResult(
                    note_id="",
                    status="error",
                    error_message=f"No note ID in response: {create_resp}",
                )

            logger.info("Draft entry created: id=%s", note_id)

            # Courtesy delay between requests
            time.sleep(self._request_delay)

            # Step 2: Save body content
            # Convert plain text to note.com format (paragraph tags)
            formatted_body = self._format_body(body_text)

            self._api_request(
                f"/text_notes/draft_save?id={note_id}",
                method="POST",
                data={"body": formatted_body},
            )

            logger.info("Draft body saved: id=%s", note_id)

            edit_url = f"https://note.com/notes/{note_id}/edit"

            return NoteDraftResult(
                note_id=note_id,
                status="draft",
                edit_url=edit_url,
            )

        except urllib.error.HTTPError as e:
            return NoteDraftResult(
                note_id="",
                status="error",
                error_message=f"HTTP {e.code}: {e.reason}",
            )
        except Exception as e:
            return NoteDraftResult(
                note_id="",
                status="error",
                error_message=str(e),
            )

    def _format_body(self, text: str) -> str:
        """Convert plain text / Markdown-like text to note.com HTML format.

        note.com expects body as HTML with <p> tags for paragraphs.
        Lines starting with ■ or ▶ are treated as headings (<h3>).
        """
        lines = text.strip().split("\n")
        html_parts: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                # Empty line → empty paragraph (spacing)
                html_parts.append("<p><br></p>")
            elif stripped.startswith("■") or stripped.startswith("▶"):
                # Heading markers used in generated note articles
                html_parts.append(f"<h3>{stripped}</h3>")
            else:
                html_parts.append(f"<p>{stripped}</p>")

        return "\n".join(html_parts)
