"""Shared pytest fixtures.

Uses an isolated on-disk SQLite database per test session (temp file) so the
real data/aevrix.db is never touched. External APIs are always mocked.
"""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime

import pytest

# Configure environment BEFORE importing app modules (settings are cached).
_TMP_DB = os.path.join(tempfile.gettempdir(), "aevrix_test.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)

os.environ.update({
    "DATABASE_URL": f"sqlite+aiosqlite:///{_TMP_DB}",
    "LLM_PROVIDER": "ollama",
    "APP_ENCRYPTION_KEY": "dGVzdC1rZXktMzItYnl0ZXMtZm9yLWZlcm5ldC1vayE=",
    "APP_SESSION_SECRET": "test-session-secret-abcdefghijklmnop",
    "TELEGRAM_BOT_TOKEN": "",
    "RESEARCH_WINDOW_HOURS": "48",
})


@pytest.fixture(scope="session", autouse=True)
async def _init_db():
    from app.database.migrations import create_db_and_tables, seed_initial_data
    await create_db_and_tables()
    await seed_initial_data()
    yield


def make_raw_article(title="Test title about AI agents and LangGraph",
                     url="https://example.com/post-1", published=None):
    from app.research.parser import canonicalize_url, content_fingerprint
    from app.research.rss import RawArticle
    return RawArticle(
        title=title,
        url=url,
        canonical_url=canonicalize_url(url),
        publisher="Example",
        summary="A summary mentioning Python, LangChain and developer tools.",
        published_at=published or datetime.now(UTC),
        source_name="Example",
        source_id=1,
        category="ai_engineering",
        region="global",
        fingerprint=content_fingerprint(title, "summary"),
    )
