"""Tests for RSS parsing, normalization, dedup, freshness and ranking."""

from datetime import UTC, datetime, timedelta

from app.research.deduplicate import deduplicate, filter_by_freshness
from app.research.parser import canonicalize_url, content_fingerprint, normalize_title
from app.research.ranking import rank_stories, select_diverse
from app.research.rss import _entries_from_feed
from tests.conftest import make_raw_article

RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Feed</title>
<item><title>OpenAI releases a new model</title>
<link>https://openai.com/blog/new-model?utm_source=rss</link>
<description>A big AI model release for developers.</description>
<pubDate>Wed, 01 Jan 2025 10:00:00 GMT</pubDate></item>
<item><title>LangGraph 1.0 ships</title>
<link>https://blog.langchain.dev/langgraph-1</link>
<description>Agent framework update.</description></item>
</channel></rss>"""


def test_canonicalize_strips_tracking():
    url = "https://x.com/a/b/?utm_source=rss&id=5"
    assert "utm_source" not in canonicalize_url(url)
    assert "id=5" in canonicalize_url(url)


def test_fingerprint_stable():
    a = content_fingerprint("Title Here", "Body text")
    b = content_fingerprint("Title  Here", "Body text")
    assert a == b


def test_normalize_title():
    assert normalize_title("Hello, World!!") == "hello world"


def test_parse_feed():
    arts = _entries_from_feed(RSS_SAMPLE, {"name": "Feed", "id": 1,
                                           "category": "global_ai", "region": "global"})
    assert len(arts) == 2
    assert arts[0].title == "OpenAI releases a new model"
    assert arts[0].published_at is not None


def test_deduplicate_within_batch():
    a1 = make_raw_article(title="Same news item", url="https://e.com/1")
    a2 = make_raw_article(title="Same news item", url="https://e.com/1")  # dup url
    a3 = make_raw_article(title="Totally different story about Rust", url="https://e.com/2")
    result = deduplicate([a1, a2, a3])
    assert len(result) == 2


def test_deduplicate_against_known():
    a1 = make_raw_article(url="https://e.com/known")
    known = {a1.canonical_url}
    assert deduplicate([a1], known_canonical_urls=known) == []


def test_freshness_filter():
    old = make_raw_article(url="https://e.com/old",
                           published=datetime.now(UTC) - timedelta(days=10))
    new = make_raw_article(url="https://e.com/new",
                           published=datetime.now(UTC))
    fresh = filter_by_freshness([old, new], window_hours=24)
    assert new in fresh and old not in fresh


def test_ranking_orders_and_scores():
    arts = [make_raw_article(title="AI agent LangGraph release for Python developers",
                             url="https://e.com/a"),
            make_raw_article(title="Unrelated cooking recipe", url="https://e.com/b",
                             )]
    scored = rank_stories(arts, window_hours=48)
    assert scored[0].score >= scored[1].score
    assert 0 <= scored[0].score <= 100


def test_select_diverse_limits():
    arts = [make_raw_article(title=f"AI story {i}", url=f"https://e.com/{i}")
            for i in range(10)]
    scored = rank_stories(arts, window_hours=48)
    selected = select_diverse(scored, limit=3)
    assert len(selected) == 3
