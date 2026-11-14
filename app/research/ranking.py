"""Deterministic weighted ranking of stories (no LLM required).

Weights (configurable):
  technical_relevance     30%
  engineering_significance 25%
  freshness               15%
  audience_relevance      15%
  insight_opportunity     15%

Each story is scored 0-100. The deterministic scorer uses keyword signals,
source reliability and recency so the pipeline still ranks usefully when no
LLM provider is available.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.research.rss import RawArticle

DEFAULT_WEIGHTS = {
    "technical_relevance": 0.30,
    "engineering_significance": 0.25,
    "freshness": 0.15,
    "audience_relevance": 0.15,
    "insight_opportunity": 0.15,
}

_TECH_TERMS = {
    "ai", "llm", "model", "agent", "langgraph", "langchain", "rag", "mcp",
    "python", "javascript", "typescript", "react", "node", "api", "framework",
    "open-source", "opensource", "release", "benchmark", "gpu", "training",
    "inference", "fine-tune", "transformer", "automation", "testing",
    # business / deals / geopolitics tech signals
    "funding", "acquisition", "merger", "ipo", "valuation", "chip", "semiconductor",
    "cloud", "data center", "datacenter", "robotics", "quantum", "cybersecurity",
}
_ENGINEERING_TERMS = {
    "release", "launch", "version", "sdk", "library", "tool", "update",
    "deprecated", "breaking", "performance", "architecture", "security",
    "partnership", "deal", "investment", "raise", "round", "billion", "million",
}
_AUDIENCE_TERMS = {
    "developer", "engineer", "startup", "founder", "india", "indian",
    "enterprise", "business", "product", "market", "economy", "regulation",
    "policy", "government", "global", "trade", "sanctions",
}
_INSIGHT_TERMS = {
    "how", "why", "lessons", "guide", "deep", "explained", "analysis",
    "comparison", "tutorial", "case study", "report", "trend", "impact",
    "strategy", "outlook",
}


@dataclass
class ScoredStory:
    article: RawArticle
    score: float
    technical_relevance: float
    engineering_significance: float
    freshness: float
    audience_relevance: float
    insight_opportunity: float
    rationale: str


def _term_score(text: str, terms: set[str]) -> float:
    tl = text.lower()
    hits = sum(1 for t in terms if t in tl)
    # Normalise: 0 hits -> 0, 5+ hits -> 100.
    return min(100.0, (hits / 5.0) * 100.0)


def _freshness_score(published_at: datetime | None, window_hours: int) -> float:
    if published_at is None:
        return 50.0  # unknown date -> neutral
    age_h = (datetime.now(UTC) - published_at).total_seconds() / 3600.0
    if age_h <= 0:
        return 100.0
    if age_h >= window_hours:
        return 10.0
    return max(10.0, 100.0 * (1 - age_h / window_hours))


def score_story(
    article: RawArticle,
    window_hours: int = 24,
    weights: dict[str, float] | None = None,
    reliability_tier: int = 2,
) -> ScoredStory:
    w = weights or DEFAULT_WEIGHTS
    text = f"{article.title} {article.summary}"

    tech = _term_score(text, _TECH_TERMS)
    eng = _term_score(text, _ENGINEERING_TERMS)
    fresh = _freshness_score(article.published_at, window_hours)
    audience = _term_score(text, _AUDIENCE_TERMS)
    insight = _term_score(text, _INSIGHT_TERMS)

    # Reliability bonus: tier 1 sources get a small boost.
    reliability_bonus = {1: 10.0, 2: 3.0, 3: 0.0}.get(reliability_tier, 0.0)

    base = (
        tech * w["technical_relevance"]
        + eng * w["engineering_significance"]
        + fresh * w["freshness"]
        + audience * w["audience_relevance"]
        + insight * w["insight_opportunity"]
    )
    score = min(100.0, base + reliability_bonus)

    rationale = (
        f"tech={tech:.0f} eng={eng:.0f} fresh={fresh:.0f} "
        f"aud={audience:.0f} insight={insight:.0f} tier={reliability_tier}"
    )
    return ScoredStory(
        article=article,
        score=round(score, 1),
        technical_relevance=round(tech, 1),
        engineering_significance=round(eng, 1),
        freshness=round(fresh, 1),
        audience_relevance=round(audience, 1),
        insight_opportunity=round(insight, 1),
        rationale=rationale,
    )


def rank_stories(
    articles: list[RawArticle],
    window_hours: int = 24,
    weights: dict[str, float] | None = None,
    tier_lookup: dict[int, int] | None = None,
) -> list[ScoredStory]:
    """Score and sort stories descending by score."""
    tier_lookup = tier_lookup or {}
    scored = [
        score_story(
            a, window_hours, weights,
            reliability_tier=tier_lookup.get(a.source_id, 2),
        )
        for a in articles
    ]
    return sorted(scored, key=lambda s: s.score, reverse=True)


def select_diverse(scored: list[ScoredStory], limit: int = 5) -> list[ScoredStory]:
    """Select top stories while enforcing category diversity."""
    selected: list[ScoredStory] = []
    seen_categories: dict[str, int] = {}
    for story in scored:
        cat = story.article.category or "other"
        if seen_categories.get(cat, 0) >= 2 and len(selected) < limit:
            continue  # cap 2 per category until we run low on choices
        selected.append(story)
        seen_categories[cat] = seen_categories.get(cat, 0) + 1
        if len(selected) >= limit:
            break
    # Fill remaining slots if diversity cap left us short.
    if len(selected) < limit:
        for story in scored:
            if story not in selected:
                selected.append(story)
                if len(selected) >= limit:
                    break
    return selected
