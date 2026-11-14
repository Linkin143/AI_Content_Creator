"""Typed async repositories wrapping common database operations.

Keeping queries here keeps nodes, services and the API thin and testable.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import select

from app.database.models import (
    Approval,
    Article,
    AuditEvent,
    BrandProfile,
    Draft,
    DraftStatus,
    DraftVersion,
    PublishedPost,
    RankedStory,
    ResearchRun,
    Schedule,
    Source,
)
from app.database.session import async_session_factory


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
async def list_active_sources() -> list[dict]:
    async with async_session_factory() as session:
        rows = (await session.execute(select(Source).where(Source.active))).scalars().all()
        return [
            {
                "id": s.id, "name": s.name, "url": s.url, "category": s.category,
                "region": s.region, "source_type": s.source_type,
                "reliability_tier": s.reliability_tier,
            }
            for s in rows
        ]


async def mark_source_fetched(source_id: int, error: str | None = None) -> None:
    async with async_session_factory() as session:
        src = await session.get(Source, source_id)
        if src:
            src.last_fetched = datetime.now(UTC)
            src.last_error = error
            session.add(src)
            await session.commit()


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------
async def existing_article_keys() -> tuple[set[str], set[str]]:
    """Return (canonical_urls, fingerprints) already stored, for dedup."""
    async with async_session_factory() as session:
        urls = (await session.execute(select(Article.canonical_url))).scalars().all()
        fps = (await session.execute(select(Article.content_fingerprint))).scalars().all()
        return {u for u in urls if u}, {f for f in fps if f}


async def save_article(data: dict) -> int:
    async with async_session_factory() as session:
        article = Article(**data)
        session.add(article)
        await session.commit()
        await session.refresh(article)
        return article.id


async def get_article(article_id: int) -> Article | None:
    async with async_session_factory() as session:
        return await session.get(Article, article_id)


async def list_recent_articles(limit: int = 100) -> list[Article]:
    async with async_session_factory() as session:
        stmt = select(Article).order_by(Article.fetched_at.desc()).limit(limit)
        return list((await session.execute(stmt)).scalars().all())


# ---------------------------------------------------------------------------
# Research runs
# ---------------------------------------------------------------------------
async def create_research_run(run_id: str, window_hours: int) -> int:
    async with async_session_factory() as session:
        run = ResearchRun(run_id=run_id, window_hours=window_hours)
        session.add(run)
        await session.commit()
        await session.refresh(run)
        return run.id


async def finalize_research_run(run_id: str, **fields) -> None:
    async with async_session_factory() as session:
        stmt = select(ResearchRun).where(ResearchRun.run_id == run_id)
        run = (await session.execute(stmt)).scalars().first()
        if run:
            for k, v in fields.items():
                setattr(run, k, v)
            run.finished_at = datetime.now(UTC)
            session.add(run)
            await session.commit()


async def save_ranked_story(data: dict) -> int:
    async with async_session_factory() as session:
        row = RankedStory(**data)
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row.id


# ---------------------------------------------------------------------------
# Drafts
# ---------------------------------------------------------------------------
async def save_draft(data: dict) -> int:
    async with async_session_factory() as session:
        draft = Draft(**data)
        session.add(draft)
        await session.commit()
        await session.refresh(draft)
        session.add(DraftVersion(draft_id=draft.id, version=draft.current_version,
                                 content=draft.content, change_reason="initial"))
        await session.commit()
        return draft.id


async def get_draft(draft_id: int) -> Draft | None:
    async with async_session_factory() as session:
        return await session.get(Draft, draft_id)


async def list_drafts(status: DraftStatus | None = None, limit: int = 100) -> list[Draft]:
    async with async_session_factory() as session:
        if status:
            stmt = select(Draft).where(Draft.status == status).order_by(
                Draft.created_at.desc()).limit(limit)
        else:
            stmt = select(Draft).order_by(Draft.created_at.desc()).limit(limit)
        return list((await session.execute(stmt)).scalars().all())


async def update_draft(draft_id: int, **fields) -> Draft | None:
    async with async_session_factory() as session:
        draft = await session.get(Draft, draft_id)
        if not draft:
            return None
        for k, v in fields.items():
            setattr(draft, k, v)
        draft.updated_at = datetime.now(UTC)
        session.add(draft)
        await session.commit()
        await session.refresh(draft)
        return draft


async def add_draft_version(draft_id: int, content: str, reason: str) -> int:
    """Create a new version, bump draft, and reset approval status."""
    async with async_session_factory() as session:
        draft = await session.get(Draft, draft_id)
        if not draft:
            return 0
        new_version = draft.current_version + 1
        draft.current_version = new_version
        draft.content = content
        draft.status = DraftStatus.NEEDS_REVISION
        draft.updated_at = datetime.now(UTC)
        session.add(draft)
        session.add(DraftVersion(draft_id=draft_id, version=new_version,
                                 content=content, change_reason=reason))
        await session.commit()
        return new_version


# ---------------------------------------------------------------------------
# Approvals / schedules / published
# ---------------------------------------------------------------------------
async def record_approval(draft_id: int, version: int, decision: str,
                          decided_by: int | None, feedback: str = "") -> None:
    async with async_session_factory() as session:
        session.add(Approval(draft_id=draft_id, version=version, decision=decision,
                             decided_by=decided_by, feedback=feedback))
        await session.commit()


async def create_schedule(draft_id: int, version: int, scheduled_for: datetime) -> int:
    async with async_session_factory() as session:
        sched = Schedule(draft_id=draft_id, version=version, scheduled_for=scheduled_for)
        session.add(sched)
        await session.commit()
        await session.refresh(sched)
        return sched.id


async def list_due_schedules(now: datetime | None = None) -> list[Schedule]:
    now = now or datetime.now(UTC)
    async with async_session_factory() as session:
        stmt = select(Schedule).where(
            Schedule.status == "pending", Schedule.scheduled_for <= now)
        return list((await session.execute(stmt)).scalars().all())


async def record_published(data: dict) -> int:
    async with async_session_factory() as session:
        post = PublishedPost(**data)
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post.id


async def published_exists(draft_id: int, version: int) -> bool:
    """Idempotency guard: has this exact draft+version already been published?"""
    async with async_session_factory() as session:
        stmt = select(PublishedPost).where(
            PublishedPost.draft_id == draft_id,
            PublishedPost.version == version,
            PublishedPost.status.in_(["published", "manual"]),
        )
        return (await session.execute(stmt)).scalars().first() is not None


async def list_published(limit: int = 100) -> list[PublishedPost]:
    async with async_session_factory() as session:
        stmt = select(PublishedPost).order_by(PublishedPost.published_at.desc()).limit(limit)
        return list((await session.execute(stmt)).scalars().all())


# ---------------------------------------------------------------------------
# Brand / audit
# ---------------------------------------------------------------------------
async def get_brand_profile() -> BrandProfile | None:
    async with async_session_factory() as session:
        return (await session.execute(select(BrandProfile))).scalars().first()


async def record_audit(actor: str, action: str, entity_type: str = "",
                       entity_id: str = "", detail: dict | None = None) -> None:
    async with async_session_factory() as session:
        session.add(AuditEvent(actor=actor, action=action, entity_type=entity_type,
                              entity_id=entity_id, detail=detail or {}))
        await session.commit()
