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


def _inline_keyboard(draft_id: int, version: int):
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
        [
            InlineKeyboardButton("📝 Mark Posted Manually",
                                 callback_data=mk(draft_id, version, "manual")),
        ],
    ]
    return InlineKeyboardMarkup(rows)


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
                            _inline_keyboard(draft_id, draft.current_version))
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
                            _inline_keyboard(draft.id, draft.current_version))
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
