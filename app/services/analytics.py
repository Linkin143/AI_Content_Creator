"""Analytics and summary generation.

Engagement metrics are only reported when the platform API actually returns
them. Missing metrics stay empty - never fabricated.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlmodel import func, select

from app.database.models import Article, Draft, DraftStatus, PublishedPost
from app.database.session import async_session_factory


async def overview_stats() -> dict:
    """Counts for the dashboard Overview page."""
    since = datetime.now(UTC) - timedelta(hours=24)
    async with async_session_factory() as session:
        articles_today = (await session.execute(
            select(func.count()).select_from(Article).where(Article.fetched_at >= since)
        )).scalar() or 0
        total_drafts = (await session.execute(
            select(func.count()).select_from(Draft)
        )).scalar() or 0
        pending = (await session.execute(
            select(func.count()).select_from(Draft).where(
                Draft.status == DraftStatus.PENDING_REVIEW)
        )).scalar() or 0
        scheduled = (await session.execute(
            select(func.count()).select_from(Draft).where(
                Draft.status == DraftStatus.SCHEDULED)
        )).scalar() or 0
        published = (await session.execute(
            select(func.count()).select_from(PublishedPost).where(
                PublishedPost.status.in_(["published", "manual"]))
        )).scalar() or 0
        failed = (await session.execute(
            select(func.count()).select_from(Draft).where(
                Draft.status == DraftStatus.FAILED)
        )).scalar() or 0
    return {
        "articles_today": articles_today,
        "total_drafts": total_drafts,
        "pending_approvals": pending,
        "scheduled_posts": scheduled,
        "published_posts": published,
        "failed_publications": failed,
    }


async def daily_summary() -> str:
    stats = await overview_stats()
    return (
        f"Daily summary — {datetime.now(UTC):%Y-%m-%d}\n"
        f"Articles (24h): {stats['articles_today']}\n"
        f"Drafts total: {stats['total_drafts']}\n"
        f"Pending approvals: {stats['pending_approvals']}\n"
        f"Scheduled: {stats['scheduled_posts']}\n"
        f"Published: {stats['published_posts']}"
    )


async def fetch_engagement_metrics(published_post: PublishedPost) -> dict:
    """Placeholder for real metric collection.

    Returns empty metrics unless a connected API provides them. We do NOT
    fabricate engagement numbers.
    """
    return {"likes": 0, "comments": 0, "shares": 0, "impressions": 0,
            "note": "metrics unavailable without authorized analytics access"}
