"""Optional web-search discovery.

RSS works fully without this. When SEARCH_PROVIDER + SEARCH_API_KEY are set
(tavily / brave / serpapi / newsdata), this adds keyword-based discovery. If not
configured, functions return empty results cleanly.

NewsData.io is used as a *supplement* to RSS — a small number of targeted India /
AI queries per research run (see newsdata_india_boost), kept well under the free
tier's 200 credits/day. Each request returns up to 10 articles and costs 1 credit.
"""

from __future__ import annotations

from datetime import UTC, datetime

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
    if provider == "newsdata":
        return await _newsdata(query, settings.search_api_key)
    # serpapi and others can be added here.
    return []


def _mk_article(title: str, url: str, snippet: str, published_at: datetime | None = None,
                publisher: str = "", category: str = "search",
                region: str = "global") -> RawArticle:
    return RawArticle(
        title=title.strip(),
        url=url.strip(),
        canonical_url=canonicalize_url(url),
        publisher=publisher or publisher_from_url(url),
        summary=clean_summary(snippet),
        published_at=published_at,
        source_name="newsdata" if category != "search" else "web_search",
        source_id=None,
        category=category,
        region=region,
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


# ---------------------------------------------------------------------------
# NewsData.io adapter
# ---------------------------------------------------------------------------
NEWSDATA_URL = "https://newsdata.io/api/1/latest"


def _parse_newsdata_date(value: str | None) -> datetime | None:
    """NewsData returns 'YYYY-MM-DD HH:MM:SS' in UTC."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


async def _newsdata(query: str, api_key: str, country: str = "",
                    category: str = "india_tech_news",
                    region: str = "india") -> list[RawArticle]:
    """One NewsData.io request = 1 credit, up to 10 articles.

    Never raises: on any error (quota, network) returns [] so the pipeline
    continues on RSS alone.
    """
    params = {"apikey": api_key, "q": query, "language": "en"}
    if country:
        params["country"] = country
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(NEWSDATA_URL, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return []
    if data.get("status") != "success":
        return []
    out: list[RawArticle] = []
    for r in data.get("results", []):
        url = r.get("link") or ""
        title = r.get("title") or ""
        if not url or not title:
            continue
        out.append(_mk_article(
            title, url,
            r.get("description") or r.get("content") or "",
            published_at=_parse_newsdata_date(r.get("pubDate")),
            publisher=r.get("source_id") or "",
            category=category,
            region=region,
        ))
    return out


# Targeted India / AI queries run as a small supplement to RSS each research run.
# Each query = 1 credit. 6 queries x a couple runs/day stays well under 200/day.
# India first (3 queries), US market second (2 queries), world third (1 query).
# Each query = 1 credit; 6/run stays well under the free tier's 200/day.
NEWSDATA_INDIA_QUERIES: list[tuple[str, str, str, str]] = [
    # (query, country, category, region)
    # --- INDIA (first priority) ---
    ("Jio OR Reliance OR TRAI OR telecom India", "in", "india_tech_news", "india"),
    ("India AI OR IndiaAI OR India startup funding", "in", "india_tech_news", "india"),
    ("India IT OR Infosys OR TCS OR semiconductor India OR ISRO", "in",
     "india_tech_news", "india"),
    # --- US (second priority) ---
    ("OpenAI OR Nvidia OR Microsoft OR Google AI OR US tech funding", "us",
     "us_tech_news", "us"),
    ("US AI policy OR Silicon Valley startup OR Wall Street tech", "us",
     "us_tech_news", "us"),
    # --- WORLD (third priority) ---
    ("artificial intelligence OR new AI model OR chip breakthrough", "",
     "ai_news", "global"),
    # --- CHINA / JAPAN (small third-tier slice) ---
    ("China tech OR Huawei OR Alibaba OR DeepSeek OR Japan tech OR Sony", "",
     "china_japan_tech", "global"),
]


async def newsdata_india_boost() -> list[RawArticle]:
    """Run the targeted NewsData query set. Empty unless provider=newsdata is set.

    Credit-safe: bounded to len(NEWSDATA_INDIA_QUERIES) credits per call.
    """
    settings = get_settings()
    if not settings.feature_enabled("search"):
        return []
    if settings.search_provider.lower() != "newsdata":
        return []
    key = settings.search_api_key
    collected: list[RawArticle] = []
    for query, country, category, region in NEWSDATA_INDIA_QUERIES:
        collected.extend(await _newsdata(query, key, country, category, region))
    return collected
