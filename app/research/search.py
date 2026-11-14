"""Optional web-search discovery.

RSS works fully without this. When SEARCH_PROVIDER + SEARCH_API_KEY are set
(tavily / brave / serpapi), this adds keyword-based discovery. If not
configured, functions return empty results cleanly.
"""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.research.parser import (
    canonicalize_url,
    clean_summary,
    content_fingerprint,
    publisher_from_url,
)
from app.research.rss import RawArticle


async def search_news(query: str, max_results: int = 10) -> list[RawArticle]:
    """Run a keyword search via the configured provider. Empty if unconfigured."""
    settings = get_settings()
    if not settings.feature_enabled("search"):
        return []
    provider = settings.search_provider.lower()
    if provider == "tavily":
        return await _tavily(query, max_results, settings.search_api_key)
    if provider == "brave":
        return await _brave(query, max_results, settings.search_api_key)
    # serpapi and others can be added here.
    return []


def _mk_article(title: str, url: str, snippet: str) -> RawArticle:
    return RawArticle(
        title=title.strip(),
        url=url.strip(),
        canonical_url=canonicalize_url(url),
        publisher=publisher_from_url(url),
        summary=clean_summary(snippet),
        published_at=None,
        source_name="web_search",
        source_id=None,
        category="search",
        region="global",
        fingerprint=content_fingerprint(title, snippet),
    )


async def _tavily(query: str, max_results: int, api_key: str) -> list[RawArticle]:
    url = "https://api.tavily.com/search"
    payload = {"api_key": api_key, "query": query, "max_results": max_results}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return []
    return [
        _mk_article(r.get("title", ""), r.get("url", ""), r.get("content", ""))
        for r in data.get("results", [])
        if r.get("url")
    ]


async def _brave(query: str, max_results: int, api_key: str) -> list[RawArticle]:
    url = "https://api.search.brave.com/res/v1/news/search"
    headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
    params = {"q": query, "count": max_results}
    try:
        async with httpx.AsyncClient(timeout=20, headers=headers) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return []
    results = data.get("results", []) or data.get("news", {}).get("results", [])
    return [
        _mk_article(r.get("title", ""), r.get("url", ""), r.get("description", ""))
        for r in results
        if r.get("url")
    ]
