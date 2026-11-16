"""Tests for Telegram authorization, X/LinkedIn helpers and OAuth state."""

from app.config import Settings
from app.integrations import linkedin as li
from app.integrations import x_api


def test_telegram_allowlist_parsing():
    s = Settings(telegram_allowed_user_ids="111, 222 ,abc,333",
                 app_encryption_key="x")
    assert s.allowed_telegram_ids == {111, 222, 333}


def test_x_pkce_generation():
    verifier, challenge = x_api.generate_pkce()
    assert len(verifier) >= 43
    assert challenge and challenge != verifier


def test_x_manual_compose_url():
    url = x_api.manual_compose_url("hello world")
    assert url.startswith("https://twitter.com/intent/tweet?")
    assert "hello" in url


def test_x_post_length_check():
    from skills.x_content.tools import check_post_length
    assert check_post_length("short") is True
    assert check_post_length("x" * 281) is False


def test_linkedin_authorize_url():
    Settings(linkedin_client_id="abc", linkedin_client_secret="def",
                 app_encryption_key="x")
    # build_authorize_url reads settings via get_settings; just ensure it builds.
    url = li.build_authorize_url("state123")
    assert url.startswith("https://www.linkedin.com/oauth/v2/authorization")


async def test_mock_x_publish_records(monkeypatch):
    """Mock X publishing path should store a published post (no real API call)."""
    from app.database import repositories as repo
    from app.database.models import Platform
    from app.services import approvals, publishing

    did = await repo.save_draft({
        "run_id": "t", "platform": Platform.X, "content": "mock post",
        "sources": [], "evidence": [], "quality_score": 50,
    })
    draft = await repo.get_draft(did)
    await approvals.approve_draft(did, draft.current_version, actor=1)
    res = await publishing.publish_draft(did, draft.current_version, actor=1, mock=True)
    assert res["status"] == "PUBLISHED"
    assert await repo.published_exists(did, draft.current_version)


def test_schedule_slot_labels():
    from app.services.notifications import _slot_label
    assert _slot_label(2) == "2 AM"
    assert _slot_label(11) == "11 AM"
    assert _slot_label(12) == "12 PM"
    assert _slot_label(14) == "2 PM"
    assert _slot_label(18) == "6 PM"
    assert _slot_label(22) == "10 PM"


def test_slot_to_utc_is_ist_hour_today():
    """A slot hour should map to that IST wall-clock hour, returned in UTC."""
    from zoneinfo import ZoneInfo

    from app.services.notifications import slot_to_utc
    when = slot_to_utc(14)  # 2 PM IST
    ist = when.astimezone(ZoneInfo("Asia/Kolkata"))
    assert ist.hour == 14 and ist.minute == 0
    assert when.tzinfo is not None  # timezone-aware (UTC)
