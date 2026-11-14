"""Deterministic deduplication and freshness filtering.

Prefers cheap deterministic checks (URL match, title similarity, fingerprint)
before any LLM is involved. LLM-based clustering is optional and only applied
to high-value survivors elsewhere.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.research.parser import normalize_title
from app.research.rss import RawArticle


def _title_similarity(a: str, b: str) -> float:
    """Jaccard similarity over normalized title tokens (0..1)."""
    ta, tb = set(normalize_title(a).split()), set(normalize_title(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def deduplicate(
    articles: list[RawArticle],
    known_canonical_urls: set[str] | None = None,
    known_fingerprints: set[str] | None = None,
    title_threshold: float = 0.82,
) -> list[RawArticle]:
    """Return a deduplicated list of articles.

    Stages:
      1. Drop articles whose canonical URL or fingerprint already exists in DB.
      2. Drop exact canonical-URL duplicates within this batch.
      3. Drop fingerprint duplicates within this batch.
      4. Drop near-duplicate titles (Jaccard >= threshold).
    """
    known_urls = known_canonical_urls or set()
    known_fps = known_fingerprints or set()

    seen_urls: set[str] = set()
    seen_fps: set[str] = set()
    kept: list[RawArticle] = []

    for art in articles:
        cu = art.canonical_url
        fp = art.fingerprint
        if cu and (cu in known_urls or cu in seen_urls):
            continue
        if fp and (fp in known_fps or fp in seen_fps):
            continue
        # Near-duplicate title check against already-kept items.
        if any(_title_similarity(art.title, k.title) >= title_threshold for k in kept):
            continue
        kept.append(art)
        if cu:
            seen_urls.add(cu)
        if fp:
            seen_fps.add(fp)
    return kept


def filter_by_freshness(articles: list[RawArticle], window_hours: int) -> list[RawArticle]:
    """Keep only articles published within the research window.

    Articles missing a publish date are kept (flagged downstream) so that we do
    not silently discard real stories from feeds with poor date metadata.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    fresh: list[RawArticle] = []
    for art in articles:
        if art.published_at is None or art.published_at >= cutoff:
            fresh.append(art)
    return fresh
