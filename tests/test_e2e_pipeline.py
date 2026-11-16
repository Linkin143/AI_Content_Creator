"""End-to-end pipeline tests with mocked network + mocked LLM.

Covers: news -> dedup -> freshness -> research -> verify -> rank -> analyze ->
select -> generate -> quality -> persist, both WITH a mocked AI provider and
WITHOUT any provider (graceful degradation / Foundry-unavailable scenario).
"""

from datetime import UTC, datetime

from app.agents import nodes
from app.research.rss import RawArticle, SourceFetchResult


def _fake_articles(n=3, tag="a"):
    out = []
    for i in range(n):
        out.append(RawArticle(
            title=f"AI agent framework release {tag}{i} for Python developers",
            url=f"https://example.com/{tag}/story-{i}",
            canonical_url=f"https://example.com/{tag}/story-{i}",
            publisher="Example",
            summary="LangGraph and LangChain update with developer implications.",
            published_at=datetime.now(UTC),
            source_name="Example", source_id=1,
            category="ai_engineering", region="global",
            fingerprint=f"fp-{tag}-{i}",
        ))
    return out


def _mock_fetch_factory(tag):
    async def fake_fetch_all(sources, concurrency=8):
        return [SourceFetchResult(source_name="Example", source_id=1,
                                  articles=_fake_articles(3, tag=tag))]
    return fake_fetch_all


async def _no_booster():
    return []


async def test_pipeline_without_llm(monkeypatch):
    """No LLM provider -> articles flow through, no drafts, no crash."""
    monkeypatch.setattr(nodes.rss, "fetch_all", _mock_fetch_factory("nollm"))
    # Isolate from the optional NewsData booster (no real network in tests).
    import app.research.search as _search
    monkeypatch.setattr(_search, "newsdata_india_boost", _no_booster)

    async def no_structured(*a, **k):
        return None
    monkeypatch.setattr(nodes, "call_structured", no_structured)

    state = {
        "run_id": "e2e-no-llm", "research_window_hours": 48,
        "max_articles": 50, "max_posts": 3, "llm_calls": 0, "errors": [],
        "metadata": {},
    }
    state.update(await nodes.discover_news(state))
    assert len(state["raw_articles"]) == 3
    state.update(await nodes.deduplicate_stories(state))
    state.update(await nodes.filter_freshness(state))
    assert len(state["fresh"]) == 3
    state.update(await nodes.research_stories(state))
    state.update(await nodes.verify_claims(state))
    # Without AI, everything is REQUIRES_REVIEW (not fabricated as VERIFIED).
    assert all(s["verification_status"] == "REQUIRES_REVIEW" for s in state["verified"])
    state.update(await nodes.rank_stories_node(state))
    state.update(await nodes.technical_analysis(state))
    state.update(await nodes.select_content(state))
    state.update(await nodes.generate_x_posts(state))
    state.update(await nodes.generate_linkedin_posts(state))
    # No provider -> no drafts generated.
    assert state["x_drafts"] == []
    state.update(await nodes.editorial_quality_check(state))
    state.update(await nodes.persist_drafts(state))
    assert state["persisted_draft_ids"] == []


async def test_pipeline_with_mock_llm(monkeypatch):
    """Mocked AI provider -> drafts are generated and persisted."""
    monkeypatch.setattr(nodes.rss, "fetch_all", _mock_fetch_factory("withllm"))
    import app.research.search as _search
    monkeypatch.setattr(_search, "newsdata_india_boost", _no_booster)
    from app.schemas.content import (
        ExtractedClaims,
        LinkedInPostOutput,
        QualityReview,
        TechnicalAnalysis,
        VerificationOutput,
        XPostOutput,
    )

    async def fake_structured(system_prompt, content, schema, max_retries=2):
        if schema is ExtractedClaims:
            return ExtractedClaims(summary="s", key_claims=["c1"], entities=["LangGraph"])
        if schema is VerificationOutput:
            return VerificationOutput(status="VERIFIED", confidence=0.8,
                                      supporting_sources=["https://example.com/story-0"])
        if schema is TechnicalAnalysis:
            return TechnicalAnalysis(technical_depth="deep",
                                     developer_implications=["use it"])
        if schema is XPostOutput:
            return XPostOutput(content="A useful X post about LangGraph.",
                               evidence=["https://example.com/story-0"])
        if schema is LinkedInPostOutput:
            return LinkedInPostOutput(content="A longer LinkedIn post about agents.",
                                      evidence=["https://example.com/story-0"])
        if schema is QualityReview:
            return QualityReview(approved=True, score=88.0)
        return None

    monkeypatch.setattr(nodes, "call_structured", fake_structured)

    state = {
        "run_id": "e2e-llm", "research_window_hours": 48,
        "max_articles": 50, "max_posts": 2, "llm_calls": 0, "errors": [],
        "metadata": {},
    }
    state.update(await nodes.discover_news(state))
    state.update(await nodes.deduplicate_stories(state))
    state.update(await nodes.filter_freshness(state))
    state.update(await nodes.research_stories(state))
    state.update(await nodes.verify_claims(state))
    assert any(s["verification_status"] == "VERIFIED" for s in state["verified"])
    state.update(await nodes.rank_stories_node(state))
    state.update(await nodes.technical_analysis(state))
    state.update(await nodes.select_content(state))
    state.update(await nodes.generate_x_posts(state))
    assert len(state["x_drafts"]) >= 1
    state.update(await nodes.generate_linkedin_posts(state))
    state.update(await nodes.editorial_quality_check(state))
    state.update(await nodes.persist_drafts(state))
    assert len(state["persisted_draft_ids"]) >= 1
