"""Async RSS/Atom discovery using HTTPX + feedparser.

One failing source never aborts the run: errors are captured per source and
reported back so the pipeline can continue.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

import feedparser
import httpx

from app.research.parser import (
    canonicalize_url,
    clean_summary,
    content_fingerprint,
    publisher_from_url,
    to_utc,
)
from app.security.sanitization import is_safe_url

USER_AGENT = "AEVRIX-ContentEngine/0.1 (+https://aevrix.in)"
FETCH_TIMEOUT = 15.0


@dataclass
class RawArticle:
    title: str
    url: str
    canonical_url: str
    publisher: str
    summary: str
    published_at: datetime | None
    source_name: str
    source_id: int | None
    category: str
    region: str
    fingerprint: str


@dataclass
class SourceFetchResult:
    source_name: str
    source_id: int | None
    articles: list[RawArticle] = field(default_factory=list)
    error: str | None = None


def _parse_entry_date(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = getattr(entry, key, None) or (entry.get(key) if hasattr(entry, "get") else None)
        if value:
            try:
                return datetime(*value[:6], tzinfo=UTC)
            except (TypeError, ValueError):
                continue
    return None


def _entries_from_feed(text: str, source: dict) -> list[RawArticle]:
    parsed = feedparser.parse(text)
    articles: list[RawArticle] = []
    for entry in parsed.entries:
        link = getattr(entry, "link", "") or ""
        title = getattr(entry, "title", "") or ""
        if not link or not title:
            continue
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
        canonical = canonicalize_url(link)
        articles.append(
            RawArticle(
                title=title.strip(),
                url=link.strip(),
                canonical_url=canonical,
                publisher=source.get("name") or publisher_from_url(link),
                summary=clean_summary(summary),
                published_at=to_utc(_parse_entry_date(entry)),
                source_name=source.get("name", ""),
                source_id=source.get("id"),
                category=source.get("category", ""),
                region=source.get("region", ""),
                fingerprint=content_fingerprint(title, summary),
            )
        )
    return articles


async def fetch_source(client: httpx.AsyncClient, source: dict) -> SourceFetchResult:
    """Fetch and parse a single source. Never raises; returns error in result."""
    url = source.get("url", "")
    result = SourceFetchResult(source_name=source.get("name", ""), source_id=source.get("id"))
    if not is_safe_url(url):
        result.error = "unsafe or invalid URL"
        return result
    try:
        resp = await client.get(url, timeout=FETCH_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        result.articles = _entries_from_feed(resp.text, source)
    except httpx.HTTPError as exc:
        result.error = f"{type(exc).__name__}: {exc}"
    except Exception as exc:  # pragma: no cover - defensive
        result.error = f"parse error: {exc}"
    return result


async def fetch_all(sources: list[dict], concurrency: int = 8) -> list[SourceFetchResult]:
    """Fetch many sources concurrently with bounded parallelism."""
    semaphore = asyncio.Semaphore(concurrency)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml, */*"}

    async with httpx.AsyncClient(headers=headers) as client:
        async def _guarded(src: dict) -> SourceFetchResult:
            async with semaphore:
                return await fetch_source(client, src)

        return await asyncio.gather(*[_guarded(s) for s in sources])
