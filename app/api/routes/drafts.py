"""Draft CRUD + approval/publish actions (all admin-authenticated)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException

from app.api.auth import require_api_key
from app.database import repositories as repo
from app.services import approvals, publishing

router = APIRouter(dependencies=[Depends(require_api_key)])


def _draft_dict(d) -> dict:
    return {
        "id": d.id, "platform": d.platform.value, "status": d.status.value,
        "version": d.current_version, "content": d.content,
        "sources": d.sources, "evidence": d.evidence,
        "quality_score": d.quality_score,
    }


@router.get("/drafts", tags=["drafts"])
async def list_drafts(limit: int = 100) -> list[dict]:
    return [_draft_dict(d) for d in await repo.list_drafts(limit=limit)]


@router.get("/drafts/{draft_id}", tags=["drafts"])
async def get_draft(draft_id: int) -> dict:
    d = await repo.get_draft(draft_id)
    if not d:
        raise HTTPException(404, "draft not found")
    return _draft_dict(d)


@router.patch("/drafts/{draft_id}", tags=["drafts"])
async def edit_draft(draft_id: int, content: str = Body(..., embed=True)) -> dict:
    """Edit a draft's text. This creates a new version and needs new approval."""
    new_version = await repo.add_draft_version(draft_id, content, "manual edit")
    if not new_version:
        raise HTTPException(404, "draft not found")
    d = await repo.get_draft(draft_id)
    return _draft_dict(d)


@router.post("/drafts/{draft_id}/regenerate", tags=["drafts"])
async def regenerate(draft_id: int, feedback: str = Body("", embed=True)) -> dict:
    d = await repo.get_draft(draft_id)
    if not d:
        raise HTTPException(404, "draft not found")
    result = await approvals.request_rewrite(draft_id, d.current_version, None,
                                             feedback or "regenerate")
    return result


@router.post("/drafts/{draft_id}/approve", tags=["drafts"])
async def approve(draft_id: int) -> dict:
    d = await repo.get_draft(draft_id)
    if not d:
        raise HTTPException(404, "draft not found")
    try:
        return await approvals.approve_draft(draft_id, d.current_version, None)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/drafts/{draft_id}/reject", tags=["drafts"])
async def reject(draft_id: int, reason: str = Body("", embed=True)) -> dict:
    d = await repo.get_draft(draft_id)
    if not d:
        raise HTTPException(404, "draft not found")
    return await approvals.reject_draft(draft_id, d.current_version, None, reason)


@router.post("/drafts/{draft_id}/schedule", tags=["drafts"])
async def schedule(draft_id: int, scheduled_for: str = Body(..., embed=True)) -> dict:
    d = await repo.get_draft(draft_id)
    if not d:
        raise HTTPException(404, "draft not found")
    try:
        when = datetime.fromisoformat(scheduled_for)
    except ValueError as exc:
        raise HTTPException(400, "scheduled_for must be ISO-8601") from exc
    try:
        return await approvals.schedule_draft(draft_id, d.current_version, when, None)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/drafts/{draft_id}/publish", tags=["drafts"])
async def publish(draft_id: int, mock: bool = Body(True, embed=True)) -> dict:
    d = await repo.get_draft(draft_id)
    if not d:
        raise HTTPException(404, "draft not found")
    try:
        return await publishing.publish_draft(draft_id, d.current_version, None, mock=mock)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/drafts/{draft_id}/mark-manual", tags=["drafts"])
async def mark_manual(draft_id: int) -> dict:
    d = await repo.get_draft(draft_id)
    if not d:
        raise HTTPException(404, "draft not found")
    return await publishing.mark_manually_published(draft_id, d.current_version, None)
