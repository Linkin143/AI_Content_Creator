"""Tests for approval state transitions and mock publishing idempotency."""

from datetime import UTC

import pytest

from app.database import repositories as repo
from app.database.models import DraftStatus, Platform
from app.services import approvals, publishing


async def _make_draft(content="Hello world draft") -> int:
    return await repo.save_draft({
        "run_id": "t", "platform": Platform.X, "content": content,
        "sources": ["https://e.com/1"], "evidence": ["fact"], "quality_score": 70,
    })


async def test_approve_then_publish_mock():
    did = await _make_draft()
    draft = await repo.get_draft(did)
    res = await approvals.approve_draft(did, draft.current_version, actor=1)
    assert res["status"] == "APPROVED"

    pub = await publishing.publish_draft(did, draft.current_version, actor=1, mock=True)
    assert pub["status"] == "PUBLISHED"

    updated = await repo.get_draft(did)
    assert updated.status == DraftStatus.PUBLISHED


async def test_publish_idempotent():
    did = await _make_draft()
    draft = await repo.get_draft(did)
    await approvals.approve_draft(did, draft.current_version, actor=1)
    await publishing.publish_draft(did, draft.current_version, actor=1, mock=True)
    # Second attempt must not double-publish.
    second = await publishing.publish_draft(did, draft.current_version, actor=1, mock=True)
    assert second["status"] == "ALREADY_PUBLISHED"


async def test_cannot_publish_unapproved():
    did = await _make_draft()
    draft = await repo.get_draft(did)
    with pytest.raises(publishing.PublishError):
        await publishing.publish_draft(did, draft.current_version, actor=1, mock=True)


async def test_reject_blocks_publish():
    did = await _make_draft()
    draft = await repo.get_draft(did)
    await approvals.reject_draft(did, draft.current_version, actor=1)
    with pytest.raises(publishing.PublishError):
        await publishing.publish_draft(did, draft.current_version, actor=1, mock=True)


async def test_new_version_invalidates_approval():
    did = await _make_draft()
    draft = await repo.get_draft(did)
    await approvals.approve_draft(did, draft.current_version, actor=1)
    # A manual new version resets status to NEEDS_REVISION.
    new_version = await repo.add_draft_version(did, "edited content", "edit")
    updated = await repo.get_draft(did)
    assert updated.status == DraftStatus.NEEDS_REVISION
    # Approving the OLD version must fail (stale).
    with pytest.raises(approvals.ApprovalError):
        await approvals.approve_draft(did, new_version - 1, actor=1)


async def test_schedule_requires_approval():
    from datetime import datetime, timedelta
    did = await _make_draft()
    draft = await repo.get_draft(did)
    when = datetime.now(UTC) + timedelta(hours=1)
    with pytest.raises(approvals.ApprovalError):
        await approvals.schedule_draft(did, draft.current_version, when, actor=1)
    await approvals.approve_draft(did, draft.current_version, actor=1)
    res = await approvals.schedule_draft(did, draft.current_version, when, actor=1)
    assert res["status"] == "SCHEDULED"


async def test_manual_publish_fallback():
    did = await _make_draft()
    draft = await repo.get_draft(did)
    await approvals.approve_draft(did, draft.current_version, actor=1)
    res = await publishing.mark_manually_published(did, draft.current_version, actor=1)
    assert res["status"] == "PUBLISHED" and res["manual"] is True
