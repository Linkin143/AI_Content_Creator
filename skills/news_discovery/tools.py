"""Tools for the news_discovery skill (thin, reusable wrappers)."""

from __future__ import annotations

from app.research import rss, search


async def fetch_all_sources(sources: list[dict]):
    """Concurrently fetch all registry sources. Returns SourceFetchResult list."""
    return await rss.fetch_all(sources)


async def search_news(query: str, max_results: int = 10):
    """Optional keyword discovery (empty if no search API configured)."""
    return await search.search_news(query, max_results)
