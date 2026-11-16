"""Telegram notification helpers used by the pipeline and scheduler.

All sends are best-effort: if Telegram is unavailable the draft is still
preserved in the database. Social tokens are never included in messages.
"""

from __future__ import annotations

import html
import logging

from app.config import get_settings
from app.database import repositories as repo
from app.security.signing import make_callback_token

logger = logging.getLogger("aevrix.notifications")

_PLATFORM_BADGE = {"x": "📱 X", "linkedin": "💼 LinkedIn"}


def _esc(text: str) -> str:
    """HTML-escape untrusted text for safe Telegram HTML rendering."""
    return html.escape(text or "")


def draft_preview_html(draft) -> str:
    """Build a rich, safe HTML draft card for Telegram."""
    badge = _PLATFORM_BADGE.get(draft.platform.value, draft.platform.value.upper())
    sources = (draft.sources or [])
    src_line = _esc(sources[0]) if sources else "(none)"
    chars = len(draft.content or "")
    return (
        f"<b>{badge}  ·  Draft #{draft.id}</b> (v{draft.current_version})\n"
        f"Status: <b>{_esc(draft.status.value)}</b>  ·  "
        f"Quality: <b>{draft.quality_score:.0f}/100</b>  ·  {chars} chars\n"
        f"────────────────────\n"
        f"{_esc(draft.content)}\n"
        f"────────────────────\n"
        f"🔗 Source: {src_line}"
    )


# IST time slots offered by the 📅 Schedule button (24h hours, ascending).
# Only slots still in the future *today* (Asia/Kolkata) are shown.
SLOT_HOURS = [2, 3, 8, 9, 10, 11, 12, 14, 18, 20, 21, 22]


def _slot_label(hour24: int) -> str:
    """Human 12-hour IST label, e.g. 14 -> '2 PM', 12 -> '12 PM', 2 -> '2 AM'."""
    suffix = "AM" if hour24 < 12 else "PM"
    h12 = hour24 % 12 or 12
    return f"{h12} {suffix}"


def slot_to_utc(hour24: int):
    """Convert an IST hour today into a timezone-aware UTC datetime."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    ist = ZoneInfo("Asia/Kolkata")
    now = datetime.now(ist)
    slot = now.replace(hour=hour24, minute=0, second=0, microsecond=0)
    from datetime import UTC
    return slot.astimezone(UTC)


def _future_slot_hours() -> list[int]:
    """IST slot hours that are still ahead of 'now' today."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    return [h for h in SLOT_HOURS
            if now.replace(hour=h, minute=0, second=0, microsecond=0) > now]


def kb_pending(draft_id: int, version: int):
    """Keyboard for a draft awaiting approval (PENDING_REVIEW / NEEDS_REVISION)."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    mk = make_callback_token
    rows = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=mk(draft_id, version, "approve")),
            InlineKeyboardButton("❌ Reject", callback_data=mk(draft_id, version, "reject")),
        ],
        [
            InlineKeyboardButton("✏️ Rewrite", callback_data=mk(draft_id, version, "rewrite")),
            InlineKeyboardButton("🔗 Sources", callback_data=mk(draft_id, version, "sources")),
        ],
        [
            InlineKeyboardButton("📅 Schedule", callback_data=mk(draft_id, version, "schedule")),
            InlineKeyboardButton("🚀 Publish Now", callback_data=mk(draft_id, version, "publish")),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def kb_approved(draft_id: int, version: int):
    """Keyboard shown after a draft is APPROVED (ready to publish or schedule)."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    mk = make_callback_token
    rows = [
        [
            InlineKeyboardButton("🚀 Publish Now", callback_data=mk(draft_id, version, "publish")),
            InlineKeyboardButton("📅 Schedule", callback_data=mk(draft_id, version, "schedule")),
        ],
        [
            InlineKeyboardButton("🔗 Sources", callback_data=mk(draft_id, version, "sources")),
            InlineKeyboardButton("❌ Reject", callback_data=mk(draft_id, version, "reject")),
        ],
        [
            InlineKeyboardButton("📝 Mark Posted Manually",
                                 callback_data=mk(draft_id, version, "manual")),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def kb_schedule_slots(draft_id: int, version: int):
    """Keyboard of today's remaining IST time slots. Returns (markup, n_slots)."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    mk = make_callback_token
    hours = _future_slot_hours()
    slot_buttons = [
        InlineKeyboardButton(f"🕐 {_slot_label(h)} IST",
                             callback_data=mk(draft_id, version, f"sch{h}"))
        for h in hours
    ]
    rows = [slot_buttons[i:i + 3] for i in range(0, len(slot_buttons), 3)]
    rows.append([InlineKeyboardButton("⬅️ Back",
                                      callback_data=mk(draft_id, version, "back"))])
    return InlineKeyboardMarkup(rows), len(hours)


def _inline_keyboard(draft_id: int, version: int, status=None):
    """Dispatch to the right keyboard for a draft's status.

    APPROVED/SCHEDULED show the publish/schedule menu; everything else shows
    the approve/reject review menu.
    """
    from app.database.models import DraftStatus
    if status in (DraftStatus.APPROVED, DraftStatus.SCHEDULED):
        return kb_approved(draft_id, version)
    return kb_pending(draft_id, version)


async def _send(chat_id: int, text: str, reply_markup=None) -> None:
    from telegram import Bot
    from telegram.constants import ParseMode
    settings = get_settings()
    bot = Bot(settings.telegram_bot_token)
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup,
                           parse_mode=ParseMode.HTML, disable_web_page_preview=True)


async def notify_new_drafts(draft_ids: list[int]) -> None:
    settings = get_settings()
    if not settings.feature_enabled("telegram"):
        logger.info("Telegram not configured; skipping draft notifications.")
        return
    for chat_id in settings.allowed_telegram_ids:
        for draft_id in draft_ids:
            draft = await repo.get_draft(draft_id)
            if not draft:
                continue
            try:
                await _send(chat_id, draft_preview_html(draft),
                            _inline_keyboard(draft_id, draft.current_version,
                                             draft.status))
            except Exception as exc:  # preserve draft even if send fails
                logger.warning("Failed to notify chat %s for draft %s: %s",
                               chat_id, draft_id, exc)


async def summarize_pending_drafts(limit: int = 50) -> int:
    """Send a ONE-LINE summary of how many drafts await review (no full cards).

    Used on bot startup so a deploy/restart does not re-post every draft card.
    Returns the number of pending drafts found.
    """
    from app.database.models import DraftStatus
    settings = get_settings()
    if not settings.feature_enabled("telegram"):
        return 0
    pending = await repo.list_drafts(status=DraftStatus.PENDING_REVIEW, limit=limit)
    revision = await repo.list_drafts(status=DraftStatus.NEEDS_REVISION, limit=limit)
    count = len(pending) + len(revision)
    if count == 0:
        return 0
    for chat_id in settings.allowed_telegram_ids:
        await _send(
            chat_id,
            f"🔔 You have <b>{count}</b> draft(s) awaiting review. "
            f"Tap /pending to view and approve them.",
        )
    return count


async def notify_pending_drafts(limit: int = 10) -> int:
    """Send all drafts currently awaiting review. Used on bot startup.

    Returns the number of draft cards sent.
    """
    from app.database.models import DraftStatus
    settings = get_settings()
    if not settings.feature_enabled("telegram"):
        return 0
    pending = await repo.list_drafts(status=DraftStatus.PENDING_REVIEW, limit=limit)
    revision = await repo.list_drafts(status=DraftStatus.NEEDS_REVISION, limit=limit)
    queue = pending + revision
    if not queue:
        return 0
    sent = 0
    for chat_id in settings.allowed_telegram_ids:
        await _send(chat_id, f"🔔 You have <b>{len(queue)}</b> draft(s) awaiting review:")
        for draft in queue:
            try:
                await _send(chat_id, draft_preview_html(draft),
                            _inline_keyboard(draft.id, draft.current_version,
                                             draft.status))
                sent += 1
            except Exception as exc:
                logger.warning("Failed to send pending draft %s: %s", draft.id, exc)
    return sent


async def broadcast(text: str) -> None:
    settings = get_settings()
    if not settings.feature_enabled("telegram"):
        return
    for chat_id in settings.allowed_telegram_ids:
        try:
            await _send(chat_id, text)
        except Exception as exc:
            logger.warning("Broadcast to %s failed: %s", chat_id, exc)
