# Skill: news_ranking

## Purpose
Rank verified stories so the most valuable, teachable items are drafted first.
Ranking is primarily deterministic (see app/research/ranking.py); this skill
documents the weighting and the rules an LLM assist must also follow.

## Weighted model (configurable)
- Technical relevance: 30%
- Engineering significance: 25%
- Freshness: 15%
- Indian/global audience relevance: 15%
- Original insight opportunity: 15%
Each story scored 0-100.

## Required inputs
- Verified stories with claims, freshness, source tier.

## Expected outputs
- A score (0-100) and per-dimension sub-scores with a short rationale.

## Operational constraints
- Reject stories that fail basic verification even if popular.
- Prefer diverse topics; avoid multiple posts about one announcement.
- Do not reward misleading or clickbait headlines.

## When to run
- After verification, before technical analysis and selection.

## When NOT to run
- Never to rank unverified or contradicted stories above verified ones.

## Rules preventing unsupported claims
- Ranking must not alter the factual content or verification status of a story.
