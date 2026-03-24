"""Code review CLI entry point.

Called from GitHub Actions via `python -m src.review_cli`
"""

from __future__ import annotations

import logging
import sys

from .code_reviewer import CodeReviewer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Execute review."""
    logger.info("=== AI Code Review START ===")

    try:
        reviewer = CodeReviewer()
        result = reviewer.review_pr()
    except Exception as e:
        logger.error("Code review failed: %s", e)
        logger.info("=== AI Code Review END (error) ===")
        # Don't fail CI when review itself errors out
        return

    logger.info(
        "Review result: score=%.1f, approved=%s, %d comments",
        result.score,
        result.approved,
        len(result.comments),
    )

    if not result.approved:
        logger.warning("Review NOT approved (score: %.1f)", result.score)
        # Don't block CI even if not approved
        # Uncomment to block:
        # sys.exit(1)

    logger.info("=== AI Code Review END ===")


if __name__ == "__main__":
    main()
