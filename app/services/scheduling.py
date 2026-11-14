"""APScheduler-based scheduling for a single-instance local deployment.

Default timezone Asia/Kolkata. Research runs daily at 08:00 IST, followed by
draft generation and Telegram notifications. Due scheduled publications are
processed on a short interval. Quiet hours suppress auto-publishing.

Single-instance only: do not run multiple schedulers against one database.
"""

from __future__ import annotations

import logging
from datetime import datetime, time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.database import repositories as repo

logger = logging.getLogger("aevrix.scheduler")

QUIET_START = time(22, 0)  # 22:00 IST
QUIET_END = time(7, 0)     # 07:00 IST


def _in_quiet_hours(now: datetime) -> bool:
    t = now.time()
    if QUIET_START <= QUIET_END:
        return QUIET_START <= t <= QUIET_END
    return t >= QUIET_START or t <= QUIET_END


async def scheduled_research_job() -> None:
    """Daily research + generation + notification."""
    from app.agents.graph import run_pipeline
    logger.info("Scheduled research starting")
    try:
        state = await run_pipeline()
        ids = state.get("persisted_draft_ids", [])
        await repo.finalize_research_run(
            state.get("run_id", ""), status="complete",
            articles_found=len(state.get("raw_articles", [])),
            drafts_generated=len(ids))
        logger.info("Scheduled research complete: %d drafts", len(ids))
    except Exception as exc:
        logger.exception("Scheduled research failed: %s", exc)


async def process_due_publications() -> None:
    """Publish scheduled drafts whose time has arrived (respects quiet hours)."""
    settings = get_settings()
    if not settings.auto_publish:
        return
    now = datetime.now()
    if _in_quiet_hours(now):
        return
    from app.services.publishing import publish_draft
    due = await repo.list_due_schedules()
    for sched in due:
        try:
            await publish_draft(sched.draft_id, sched.version, actor=None,
                                mock=not settings.feature_enabled("x"))
        except Exception as exc:
            logger.warning("Scheduled publish of draft %s failed: %s", sched.draft_id, exc)


def build_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone=settings.app_timezone)
    scheduler.add_job(
        scheduled_research_job, CronTrigger(hour=8, minute=0),
        id="daily_research", replace_existing=True, misfire_grace_time=3600,
    )
    scheduler.add_job(
        process_due_publications, IntervalTrigger(minutes=5),
        id="process_publications", replace_existing=True, misfire_grace_time=300,
    )
    return scheduler
