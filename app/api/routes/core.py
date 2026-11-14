"""Health, research, articles, analytics, integrations, settings routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.agents.provider import health_check
from app.api.auth import require_api_key
from app.config import get_settings
from app.database import repositories as repo
from app.services import analytics

router = APIRouter()


@router.get("/health", tags=["system"])
async def health() -> dict:
    settings = get_settings()
    rep = await health_check()
    return {
        "status": "ok",
        "llm_provider": rep.provider,
        "llm_configured": rep.configured,
        "llm_reachable": rep.reachable,
        "telegram": settings.feature_enabled("telegram"),
        "x": settings.feature_enabled("x"),
        "linkedin": settings.feature_enabled("linkedin"),
    }


@router.post("/research/run", tags=["research"], dependencies=[Depends(require_api_key)])
async def run_research(window: int | None = None, max_posts: int | None = None) -> dict:
    from app.agents.graph import run_pipeline
    state = await run_pipeline(window_hours=window, max_posts=max_posts)
    return {
        "run_id": state.get("run_id"),
        "articles": len(state.get("raw_articles", [])),
        "fresh": len(state.get("fresh", [])),
        "drafts": state.get("persisted_draft_ids", []),
        "llm_calls": state.get("llm_calls", 0),
        "errors": state.get("errors", []),
    }


@router.get("/articles", tags=["articles"])
async def list_articles(limit: int = 100) -> list[dict]:
    arts = await repo.list_recent_articles(limit=limit)
    return [
        {"id": a.id, "title": a.title, "publisher": a.publisher, "url": a.url,
         "category": a.category, "region": a.region,
         "published_at": a.published_at.isoformat() if a.published_at else None}
        for a in arts
    ]


@router.get("/articles/{article_id}", tags=["articles"])
async def get_article(article_id: int) -> dict:
    a = await repo.get_article(article_id)
    if not a:
        return {"error": "not found"}
    return {"id": a.id, "title": a.title, "publisher": a.publisher, "url": a.url,
            "summary": a.summary, "category": a.category,
            "published_at": a.published_at.isoformat() if a.published_at else None}


@router.get("/analytics", tags=["analytics"])
async def get_analytics() -> dict:
    return await analytics.overview_stats()


@router.get("/history", tags=["publishing"])
async def history(limit: int = 100) -> list[dict]:
    posts = await repo.list_published(limit=limit)
    return [
        {"id": p.id, "draft_id": p.draft_id, "platform": p.platform.value,
         "status": p.status, "manual": p.manual,
         "platform_post_id": p.platform_post_id,
         "published_at": p.published_at.isoformat()}
        for p in posts
    ]


@router.get("/integrations", tags=["system"])
async def integrations() -> dict:
    settings = get_settings()
    rep = await health_check()
    return {
        "llm": {"provider": rep.provider, "configured": rep.configured,
                "reachable": rep.reachable, "model": rep.model},
        "telegram": settings.feature_enabled("telegram"),
        "x": settings.feature_enabled("x"),
        "linkedin": settings.feature_enabled("linkedin"),
        "search": settings.feature_enabled("search"),
    }


@router.get("/settings", tags=["settings"], dependencies=[Depends(require_api_key)])
async def get_settings_route() -> dict:
    s = get_settings()
    return {
        "llm_provider": s.llm_provider.value,
        "llm_model": s.resolved_model,
        "research_window_hours": s.research_window_hours,
        "max_articles_per_run": s.max_articles_per_run,
        "max_x_posts_per_day": s.max_x_posts_per_day,
        "max_linkedin_posts_per_week": s.max_linkedin_posts_per_week,
        "require_human_approval": s.require_human_approval,
        "auto_publish": s.auto_publish,
    }
