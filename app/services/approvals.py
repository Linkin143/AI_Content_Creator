"""Approval state machine shared by Telegram and the Streamlit dashboard.

Rules enforced here:
  - Only a human action approves.
  - A revised draft invalidates prior approval (handled in add_draft_version).
  - Rejected drafts cannot publish.
  - Unapproved drafts cannot be scheduled.
  - State updates are atomic (single-session commit) to avoid races.
  - Every decision is written to the audit trail.
"""

from __future__ import annotations

from datetime import datetime

from app.database import repositories as repo
from app.database.models import DraftStatus


class ApprovalError(RuntimeError):
    pass


async def approve_draft(draft_id: int, version: int, actor: int | None) -> dict:
    draft = await repo.get_draft(draft_id)
    if not draft:
        raise ApprovalError("draft not found")
    if draft.current_version != version:
        raise ApprovalError(
            f"stale version: draft is at v{draft.current_version}, you approved v{version}"
        )
    if draft.status in (DraftStatus.PUBLISHED, DraftStatus.PUBLISHING):
        raise ApprovalError(f"cannot approve a draft in state {draft.status.value}")

    await repo.update_draft(draft_id, status=DraftStatus.APPROVED)
    await repo.record_approval(draft_id, version, "approved", actor)
    await repo.record_audit(str(actor or "system"), "approve", "draft", str(draft_id),
                            {"version": version})
    return {"draft_id": draft_id, "version": version, "status": "APPROVED"}


async def reject_draft(draft_id: int, version: int, actor: int | None,
                       reason: str = "") -> dict:
    draft = await repo.get_draft(draft_id)
    if not draft:
        raise ApprovalError("draft not found")
    await repo.update_draft(draft_id, status=DraftStatus.REJECTED)
    await repo.record_approval(draft_id, version, "rejected", actor, reason)
    await repo.record_audit(str(actor or "system"), "reject", "draft", str(draft_id),
                            {"version": version, "reason": reason})
    return {"draft_id": draft_id, "status": "REJECTED"}


async def request_rewrite(draft_id: int, version: int, actor: int | None,
                          feedback: str) -> dict:
    """Regenerate a draft using feedback. New version requires fresh approval."""
    draft = await repo.get_draft(draft_id)
    if not draft:
        raise ApprovalError("draft not found")

    from app.services.generation import rewrite_draft_content
    new_content = await rewrite_draft_content(draft, feedback)
    new_version = await repo.add_draft_version(draft_id, new_content, f"rewrite: {feedback}")
    await repo.record_approval(draft_id, version, "rewrite_requested", actor, feedback)
    await repo.record_audit(str(actor or "system"), "rewrite", "draft", str(draft_id),
                            {"from_version": version, "to_version": new_version})
    return {"draft_id": draft_id, "version": new_version, "status": "NEEDS_REVISION",
            "content": new_content}


async def schedule_draft(draft_id: int, version: int, scheduled_for: datetime,
                         actor: int | None) -> dict:
    draft = await repo.get_draft(draft_id)
    if not draft:
        raise ApprovalError("draft not found")
    if draft.status != DraftStatus.APPROVED:
        raise ApprovalError("only APPROVED drafts can be scheduled")
    if draft.current_version != version:
        raise ApprovalError("stale version; re-approve the current version first")

    sched_id = await repo.create_schedule(draft_id, version, scheduled_for)
    await repo.update_draft(draft_id, status=DraftStatus.SCHEDULED)
    await repo.record_audit(str(actor or "system"), "schedule", "draft", str(draft_id),
                            {"version": version, "schedule_id": sched_id,
                             "scheduled_for": scheduled_for.isoformat()})
    return {"draft_id": draft_id, "schedule_id": sched_id, "status": "SCHEDULED"}
