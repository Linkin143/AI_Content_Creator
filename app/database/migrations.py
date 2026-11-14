"""Schema creation and lightweight migration/seed logic.

For this single-instance SQLite app we use SQLModel ``create_all`` plus a
small, idempotent seed step. A clear upgrade path to Alembic/PostgreSQL
exists if concurrency or scale grows.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlmodel import SQLModel, select

from app.database import models  # noqa: F401 - ensures models are registered
from app.database.models import BrandProfile, Source
from app.database.session import async_session_factory, engine
from app.research.sources_seed import DEFAULT_SOURCES


async def create_db_and_tables() -> None:
    """Create all tables and enable SQLite foreign keys + WAL."""
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.run_sync(SQLModel.metadata.create_all)


async def seed_initial_data() -> dict[str, int]:
    """Seed the default source registry and a default brand profile."""
    added_sources = 0
    deactivated = 0
    async with async_session_factory() as session:
        # Seed sources (idempotent by name).
        existing_rows = (await session.execute(select(Source))).scalars().all()
        existing_names = {s.name for s in existing_rows}
        seed_names = {src["name"] for src in DEFAULT_SOURCES}
        for src in DEFAULT_SOURCES:
            if src["name"] not in existing_names:
                session.add(Source(**src))
                added_sources += 1

        # Deactivate DB sources that are no longer in the seed (e.g. dead feeds
        # that were renamed/replaced). We deactivate rather than delete so any
        # historical articles keep their foreign key.
        for row in existing_rows:
            if row.name not in seed_names and row.active:
                row.active = False
                session.add(row)
                deactivated += 1

        # Seed one brand profile if none exists.
        profile = (await session.execute(select(BrandProfile))).scalars().first()
        if profile is None:
            session.add(_default_brand_profile())

        await session.commit()
    return {"sources_added": added_sources, "sources_deactivated": deactivated}


def _default_brand_profile() -> BrandProfile:
    return BrandProfile(
        name="Prince Kumar",
        biography=(
            "Senior Software Engineer, AI builder, entrepreneur, and founder of AEVRIX. "
            "Builds full-stack products, agentic AI systems and intelligent automation."
        ),
        technical_expertise=[
            "Full-stack software development", "JavaScript", "TypeScript", "React",
            "Node.js", "Python", "Software testing", "Test automation",
            "Browser automation", "APIs", "Agentic AI", "AI product engineering",
        ],
        preferred_subjects=[
            "AI agents", "LangGraph", "LangChain", "developer productivity",
            "Indian AI ecosystem", "software engineering", "startup building",
        ],
        writing_preferences=(
            "Clear, confident, human, practical and technical. Avoid hype, buzzword "
            "overload, engagement bait and fake personal experiences."
        ),
        approved_viewpoints=[],
        real_projects=["AEVRIX Content Intelligence Engine"],
        verified_achievements=[],
        audience_interests=[
            "AI engineering", "software development", "startups", "automation",
        ],
        restricted_topics=["politics", "religion", "unverified benchmarks"],
        project_notes=[],
    )
