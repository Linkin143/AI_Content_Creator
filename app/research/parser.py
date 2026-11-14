"""Normalization helpers for fetched articles.

Produces clean canonical URLs, publisher names, UTC timestamps and content
fingerprints. All content is treated as untrusted (sanitized downstream).
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from urllib.parse import urlparse, urlunparse

from app.security.sanitization import strip_html

_TRACKING_PARAMS = re.compile(r"(utm_[^=]+|fbclid|gclid|ref|cmpid|mc_cid|mc_eid)")


def canonicalize_url(url: str) -> str:
    """Strip query/fragment tracking noise to get a canonical URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return url.strip()
    # Drop tracking query params but keep meaningful ones.
    query = parsed.query
    if query:
        kept = [
            kv for kv in query.split("&")
            if kv and not _TRACKING_PARAMS.match(kv.split("=", 1)[0])
        ]
        query = "&".join(kept)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((scheme, netloc, path, "", query, ""))


def publisher_from_url(url: str, fallback: str = "") -> str:
    """Derive a readable publisher name from a URL host."""
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return fallback
    host = host.removeprefix("www.")
    return host or fallback


def normalize_title(title: str) -> str:
    """Lowercase, collapse whitespace and strip punctuation for matching."""
    t = (title or "").lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def content_fingerprint(title: str, summary: str) -> str:
    """Stable fingerprint of a story used for near-duplicate detection."""
    basis = normalize_title(title) + " " + normalize_title(strip_html(summary))[:400]
    return hashlib.sha1(basis.encode()).hexdigest()


def to_utc(dt: datetime | None) -> datetime | None:
    """Coerce a datetime to timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def clean_summary(raw: str, max_chars: int = 800) -> str:
    text = strip_html(raw or "")
    return text if len(text) <= max_chars else text[:max_chars].rstrip() + " …"
