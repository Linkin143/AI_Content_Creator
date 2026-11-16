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

# Weights tuned for "catch trending stories fast". Freshness is weighted heavily
# so breaking/hot items rise to the top; technical relevance still dominates so we
# stay on-brand for an AI/engineering audience.
DEFAULT_WEIGHTS = {
    "technical_relevance": 0.28,
    "engineering_significance": 0.17,
    "freshness": 0.30,
    "audience_relevance": 0.13,
    "insight_opportunity": 0.12,
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
# Words that signal a story is high-interest / likely to spread. Used as a bonus
# so genuinely newsworthy items (launches, records, breakthroughs) rank higher.
_TRENDING_TERMS = {
    "launches", "launch", "announces", "announced", "unveils", "releases",
    "released", "introducing", "now available", "breakthrough", "first",
    "fastest", "record", "beats", "outperforms", "open-source", "open source",
    "free", "leaked", "exclusive", "raises", "acquires", "shuts down", "bans",
    "gpt-5", "gpt-6", "claude", "gemini", "llama", "deepseek", "o3", "o4",
}
# India-relevance signals. The audience is Indian; stories with an India angle
# (telecom, Jio/Reliance, IT majors, startups, policy) get a strong boost.
_INDIA_TERMS = {
    "india", "indian", "jio", "reliance", "airtel", "trai", "bharat",
    "bengaluru", "bangalore", "mumbai", "delhi", "hyderabad", "isro",
    "infosys", "tcs", "wipro", "hcl", "zoho", "ola", "paytm", "zomato",
    "flipkart", "meity", "indiaai", "rupee", "crore", "upi", "aadhaar",
    "startup india", "make in india", "semiconductor mission",
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
    """Sharper recency curve so very fresh (hot/trending) items win decisively.

    < 2h  -> ~100, 6h -> ~85, 12h -> ~70, 24h -> ~45, then tapering to 10.
    """
    if published_at is None:
        return 45.0  # unknown date -> slightly below a confirmed-recent item
    age_h = (datetime.now(UTC) - published_at).total_seconds() / 3600.0
    if age_h <= 2:
        return 100.0
    if age_h >= window_hours:
        return 10.0
    # Linear-ish decay but front-loaded: newest hours barely lose points.
    frac = (age_h - 2) / max(1.0, (window_hours - 2))
    return max(10.0, 100.0 - (frac * 90.0))


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

    # Trending bonus: +4 per hit (cap 12) for launch/record/model-name signals
    # that indicate a high-interest, shareable story.
    trending_hits = sum(1 for t in _TRENDING_TERMS if t in text.lower())
    trending_bonus = min(12.0, trending_hits * 4.0)

    # India bonus: audience is Indian, so an India angle is a strong signal.
    india_hits = sum(1 for t in _INDIA_TERMS if t in text.lower())
    india_bonus = min(18.0, india_hits * 9.0)
    # Indian-region sources (Jio/TRAI/startup feeds) get the boost even if the
    # title doesn't literally contain an India keyword.
    if getattr(article, "region", "") == "india":
        india_bonus = max(india_bonus, 12.0)

    base = (
        tech * w["technical_relevance"]
        + eng * w["engineering_significance"]
        + fresh * w["freshness"]
        + audience * w["audience_relevance"]
        + insight * w["insight_opportunity"]
    )
    score = min(100.0, base + reliability_bonus + trending_bonus + india_bonus)

    rationale = (
        f"tech={tech:.0f} eng={eng:.0f} fresh={fresh:.0f} "
        f"aud={audience:.0f} insight={insight:.0f} trend+{trending_bonus:.0f} "
        f"india+{india_bonus:.0f} tier={reliability_tier}"
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
