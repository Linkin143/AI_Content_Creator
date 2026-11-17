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


async def test_delete_stale_pending_drafts():
    from datetime import datetime, timedelta

    # Fresh pending draft (today) must survive.
    fresh = await _make_draft("fresh pending")
    # Old pending draft (10 days ago) must be deleted.
    old = await _make_draft("old pending")
    await repo.update_draft(old, created_at=datetime.now(UTC) - timedelta(days=10))
    # Old but APPROVED draft must NOT be deleted (only pending/revision expire).
    kept = await _make_draft("old approved")
    k = await repo.get_draft(kept)
    await approvals.approve_draft(kept, k.current_version, actor=1)
    await repo.update_draft(kept, created_at=datetime.now(UTC) - timedelta(days=10))

    deleted = await repo.delete_stale_pending_drafts(older_than_days=7)
    assert deleted == 1
    assert await repo.get_draft(old) is None
    assert await repo.get_draft(fresh) is not None
    assert await repo.get_draft(kept) is not None


async def test_delete_all_pending_drafts_ignores_age():
    # Two fresh pending drafts + one approved.
    p1 = await _make_draft("pending one")
    p2 = await _make_draft("pending two")
    approved = await _make_draft("approved one")
    a = await repo.get_draft(approved)
    await approvals.approve_draft(approved, a.current_version, actor=1)

    # older_than_days=None wipes ALL pending regardless of age, keeps approved.
    deleted = await repo.delete_stale_pending_drafts(older_than_days=None)
    assert deleted >= 2  # at least our two fresh pending drafts
    assert await repo.get_draft(p1) is None
    assert await repo.get_draft(p2) is None
    assert await repo.get_draft(approved) is not None
    # And nothing pending/needs-revision remains at all.
    assert await repo.list_drafts(status=DraftStatus.PENDING_REVIEW) == []
    assert await repo.list_drafts(status=DraftStatus.NEEDS_REVISION) == []


async def test_manual_publish_fallback():
    did = await _make_draft()
    draft = await repo.get_draft(did)
    await approvals.approve_draft(did, draft.current_version, actor=1)
    res = await publishing.mark_manually_published(did, draft.current_version, actor=1)
    assert res["status"] == "PUBLISHED" and res["manual"] is True
