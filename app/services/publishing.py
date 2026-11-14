"""Publishing service: the authorization-controlled workflow.

Separate from the research graph. A publish only runs for an APPROVED draft at a
matching version, is idempotent (never double-publishes a draft+version), and
falls back to a fully usable manual workflow when the API cannot post.

It never reports success unless the API confirmed it, and never blindly retries
a request whose outcome is unknown.
"""

from __future__ import annotations

from app.database import repositories as repo
from app.database.models import DraftStatus, Platform
from app.integrations import linkedin as li
from app.integrations import x_api
from app.security.encryption import decrypt
from app.services.social_store import get_active_connection


class PublishError(RuntimeError):
    pass


async def publish_draft(draft_id: int, version: int, actor: int | None,
                        mock: bool = False) -> dict:
    """Publish an approved draft. Returns a result dict describing the outcome."""
    draft = await repo.get_draft(draft_id)
    if not draft:
        raise PublishError("draft not found")

    # Idempotency guard FIRST: repeated button presses / retries must not
    # double-publish, even though the draft is already in PUBLISHED state.
    if draft.status == DraftStatus.PUBLISHED or await repo.published_exists(draft_id, version):
        return {"draft_id": draft_id, "status": "ALREADY_PUBLISHED"}

    # Authorization + version + approval gates.
    if draft.status not in (DraftStatus.APPROVED, DraftStatus.SCHEDULED):
        raise PublishError(f"draft is {draft.status.value}; must be APPROVED/SCHEDULED")
    if draft.current_version != version:
        raise PublishError("stale version; re-approve current version before publishing")

    await repo.update_draft(draft_id, status=DraftStatus.PUBLISHING)

    platform = draft.platform
    try:
        if mock:
            result = _mock_result(platform, draft.content)
        else:
            result = await _publish_live(platform, draft.content)
    except Exception as exc:
        # Known failure: preserve draft, fall back to manual, surface error.
        await repo.update_draft(draft_id, status=DraftStatus.APPROVED)
        await repo.record_audit(str(actor or "system"), "publish_failed",
                                "draft", str(draft_id), {"error": str(exc)})
        return {"draft_id": draft_id, "status": "FAILED", "error": str(exc),
                "manual": _manual_payload(platform, draft.content)}

    await repo.record_published({
        "draft_id": draft_id,
        "version": version,
        "platform": platform,
        "platform_post_id": result.get("id", ""),
        "url": result.get("url", ""),
        "manual": result.get("manual", False),
        "status": result.get("status", "published"),
        "platform_response": result.get("response", {}),
    })
    await repo.update_draft(draft_id, status=DraftStatus.PUBLISHED)
    await repo.record_audit(str(actor or "system"), "publish", "draft", str(draft_id),
                            {"version": version, "platform": platform.value,
                             "mock": mock})
    return {"draft_id": draft_id, "status": "PUBLISHED",
            "platform_post_id": result.get("id", ""), "mock": mock}


async def _publish_live(platform: Platform, text: str) -> dict:
    conn = await get_active_connection(platform)
    if not conn:
        raise PublishError(f"no active {platform.value} connection; connect the account first")

    access_token = decrypt(conn.access_token_enc)
    if platform == Platform.X:
        data = await x_api.create_post(access_token, text)
        return {"id": data.get("id", ""), "status": "published", "response": data}
    else:
        info = await li.get_member_info(access_token)
        sub = info.get("sub", conn.account_id)
        data = await li.create_post(access_token, sub, text)
        return {"id": data.get("id", ""), "status": "published", "response": data}


def _mock_result(platform: Platform, text: str) -> dict:
    return {"id": f"mock-{platform.value}-{abs(hash(text)) % 10_000_000}",
            "status": "published", "manual": False,
            "response": {"mock": True, "platform": platform.value}}


def _manual_payload(platform: Platform, text: str) -> dict:
    url = (x_api.manual_compose_url(text) if platform == Platform.X
           else li.manual_compose_url(text))
    return {"compose_url": url, "text": text}


async def mark_manually_published(draft_id: int, version: int, actor: int | None) -> dict:
    """Record that the owner published a draft by hand (fallback workflow)."""
    draft = await repo.get_draft(draft_id)
    if not draft:
        raise PublishError("draft not found")
    if await repo.published_exists(draft_id, version):
        return {"draft_id": draft_id, "status": "ALREADY_PUBLISHED"}
    await repo.record_published({
        "draft_id": draft_id, "version": version, "platform": draft.platform,
        "platform_post_id": "", "url": "", "manual": True, "status": "manual",
        "platform_response": {"manual": True},
    })
    await repo.update_draft(draft_id, status=DraftStatus.PUBLISHED)
    await repo.record_audit(str(actor or "system"), "manual_publish", "draft",
                            str(draft_id), {"version": version})
    return {"draft_id": draft_id, "status": "PUBLISHED", "manual": True}
