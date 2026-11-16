"""Telegram bot: the primary mobile command + approval interface.

Security:
  - Every command and callback is checked against the user-ID allowlist.
  - Callback tokens are HMAC-signed and reference a specific draft id + version,
    so stale/forged buttons cannot publish old drafts.
  - Social tokens are never shown.

Supports long polling (default) for local dev; webhook mode is available via
config. Never both at once.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import get_settings
from app.database import repositories as repo
from app.database.models import DraftStatus
from app.security.signing import verify_callback_token
from app.services import analytics, approvals, publishing

logger = logging.getLogger("aevrix.telegram")

# Tracks users mid-rewrite: user_id -> (draft_id, version)
_PENDING_REWRITE: dict[int, tuple[int, int]] = {}


def _authorized(update: Update) -> bool:
    settings = get_settings()
    user = update.effective_user
    return bool(user and user.id in settings.allowed_telegram_ids)


async def _deny(update: Update) -> None:
    if update.message:
        await update.message.reply_text("⛔ Not authorized.")
    elif update.callback_query:
        await update.callback_query.answer("Not authorized", show_alert=True)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    await update.message.reply_text(
        "👋 AEVRIX Content Intelligence Engine.\n"
        "I research tech news, draft X/LinkedIn posts and wait for your approval.\n"
        "Use /help to see all commands."
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    await update.message.reply_text(
        "Commands:\n"
        "/status - system status\n/news - latest discovered articles\n"
        "/research - run research now\n/drafts - list drafts\n"
        "/pending - show drafts awaiting review (with buttons)\n"
        "/today - today's summary\n/approve <id> /reject <id> /rewrite <id> <text>\n"
        "/schedule <id> <ISO time> /publish <id>\n/queue - scheduled posts\n"
        "/connect_status - X / LinkedIn connection status\n"
        "/stats - analytics\n/pause /resume /settings /health"
    )


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    settings = get_settings()
    stats = await analytics.overview_stats()
    await update.message.reply_text(
        f"Provider: {settings.llm_provider.value} ({settings.resolved_model or 'default'})\n"
        f"Pending approvals: {stats['pending_approvals']}\n"
        f"Scheduled: {stats['scheduled_posts']}\n"
        f"Published: {stats['published_posts']}"
    )


async def cmd_news(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    articles = await repo.list_recent_articles(limit=8)
    if not articles:
        return await update.message.reply_text("No articles yet. Run /research.")
    lines = [f"• {a.title} — {a.publisher}" for a in articles]
    await update.message.reply_text("Latest articles:\n" + "\n".join(lines))


async def cmd_research(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    await update.message.reply_text("🔍 Research started; I'll notify you with drafts.")
    from app.agents.graph import run_pipeline
    try:
        state = await run_pipeline()
        ids = state.get("persisted_draft_ids", [])
        await update.message.reply_text(
            f"Done. {len(state.get('raw_articles', []))} articles, {len(ids)} drafts."
        )
    except Exception as exc:
        await update.message.reply_text(f"Research failed: {exc}")


async def cmd_drafts(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    drafts = await repo.list_drafts(limit=10)
    if not drafts:
        return await update.message.reply_text("No drafts yet.")
    lines = [f"#{d.id} v{d.current_version} [{d.platform.value}] {d.status.value}"
             for d in drafts]
    await update.message.reply_text("Drafts:\n" + "\n".join(lines))


async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    await update.message.reply_text(await analytics.daily_summary())


async def _id_arg(update: Update, ctx) -> int | None:
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("Usage: provide a numeric draft id.")
        return None
    return int(ctx.args[0])


async def cmd_approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    draft_id = await _id_arg(update, ctx)
    if draft_id is None:
        return
    draft = await repo.get_draft(draft_id)
    if not draft:
        return await update.message.reply_text("Draft not found.")
    try:
        await approvals.approve_draft(draft_id, draft.current_version,
                                      update.effective_user.id)
        await update.message.reply_text(f"✅ Draft #{draft_id} approved.")
    except Exception as exc:
        await update.message.reply_text(f"Could not approve: {exc}")


async def cmd_reject(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    draft_id = await _id_arg(update, ctx)
    if draft_id is None:
        return
    draft = await repo.get_draft(draft_id)
    if not draft:
        return await update.message.reply_text("Draft not found.")
    await approvals.reject_draft(draft_id, draft.current_version, update.effective_user.id)
    await update.message.reply_text(f"❌ Draft #{draft_id} rejected.")


async def cmd_rewrite(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    if len(ctx.args) < 2 or not ctx.args[0].isdigit():
        return await update.message.reply_text("Usage: /rewrite <id> <feedback>")
    draft_id = int(ctx.args[0])
    feedback = " ".join(ctx.args[1:])
    draft = await repo.get_draft(draft_id)
    if not draft:
        return await update.message.reply_text("Draft not found.")
    await update.message.reply_text("✏️ Rewriting…")
    result = await approvals.request_rewrite(draft_id, draft.current_version,
                                             update.effective_user.id, feedback)
    await update.message.reply_text(
        f"New v{result['version']} (needs approval):\n\n{result['content']}"
    )


async def cmd_schedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    if len(ctx.args) < 2 or not ctx.args[0].isdigit():
        return await update.message.reply_text("Usage: /schedule <id> <ISO8601 UTC>")
    from datetime import datetime
    draft_id = int(ctx.args[0])
    try:
        when = datetime.fromisoformat(ctx.args[1])
    except ValueError:
        return await update.message.reply_text("Invalid time. Use e.g. 2026-01-01T09:00:00")
    draft = await repo.get_draft(draft_id)
    if not draft:
        return await update.message.reply_text("Draft not found.")
    try:
        await approvals.schedule_draft(draft_id, draft.current_version, when,
                                       update.effective_user.id)
        await update.message.reply_text(f"📅 Draft #{draft_id} scheduled for {when}.")
    except Exception as exc:
        await update.message.reply_text(f"Could not schedule: {exc}")


async def cmd_publish(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    draft_id = await _id_arg(update, ctx)
    if draft_id is None:
        return
    draft = await repo.get_draft(draft_id)
    if not draft:
        return await update.message.reply_text("Draft not found.")
    settings = get_settings()
    mock = not settings.feature_enabled(draft.platform.value)
    try:
        result = await publishing.publish_draft(draft_id, draft.current_version,
                                                update.effective_user.id, mock=mock)
        suffix = " (mock)" if mock else ""
        await update.message.reply_text(f"🚀 {result['status']}{suffix} for #{draft_id}.")
    except Exception as exc:
        await update.message.reply_text(f"Publish blocked: {exc}")


async def cmd_queue(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    drafts = await repo.list_drafts(status=DraftStatus.SCHEDULED, limit=10)
    if not drafts:
        return await update.message.reply_text("Nothing scheduled.")
    await update.message.reply_text(
        "Scheduled:\n" + "\n".join(f"#{d.id} [{d.platform.value}]" for d in drafts))


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    s = await analytics.overview_stats()
    await update.message.reply_text(
        f"Articles(24h): {s['articles_today']}\nDrafts: {s['total_drafts']}\n"
        f"Pending: {s['pending_approvals']}\nPublished: {s['published_posts']}\n"
        f"Failed: {s['failed_publications']}")


async def cmd_pause(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    await repo.record_audit(str(update.effective_user.id), "pause", "system")
    await update.message.reply_text("⏸ Auto-publishing paused (set AUTO_PUBLISH=false).")


async def cmd_resume(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    await repo.record_audit(str(update.effective_user.id), "resume", "system")
    await update.message.reply_text("▶️ Resumed.")


async def cmd_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    s = get_settings()
    await update.message.reply_text(
        f"Provider: {s.llm_provider.value}\nWindow: {s.research_window_hours}h\n"
        f"Max X/day: {s.max_x_posts_per_day}\nMax LinkedIn/week: {s.max_linkedin_posts_per_week}\n"
        f"Approval required: {s.require_human_approval}\nAuto-publish: {s.auto_publish}")


async def cmd_health(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _deny(update)
    from app.agents.provider import health_check
    rep = await health_check()
    await update.message.reply_text(
        f"LLM: {rep.provider} configured={rep.configured} reachable={rep.reachable}\n"
        f"{rep.detail}")


async def cmd_pending(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Send every draft awaiting review as a card with inline buttons."""
    if not _authorized(update):
        return await _deny(update)
    from app.services.notifications import notify_pending_drafts
    count = await notify_pending_drafts()
    if count == 0:
        await update.message.reply_text("No drafts awaiting review. Run /research.")


async def cmd_connect_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Show which social accounts are connected."""
    if not _authorized(update):
        return await _deny(update)
    from app.database.models import Platform
    from app.services import social_store
    x_conn = await social_store.get_active_connection(Platform.X)
    li_conn = await social_store.get_active_connection(Platform.LINKEDIN)
    settings = get_settings()
    lines = ["🔌 Connection status:"]
    lines.append(f"📱 X: {'✅ ' + x_conn.account_name if x_conn else '❌ not connected'}")
    lines.append(f"💼 LinkedIn: {'✅ ' + li_conn.account_name if li_conn else '❌ not connected'}")
    if not x_conn and settings.feature_enabled("x"):
        lines.append("\nConnect X: http://localhost:8000/auth/x/connect")
    if not li_conn and settings.feature_enabled("linkedin"):
        lines.append("Connect LinkedIn: http://localhost:8000/auth/linkedin/connect")
    await update.message.reply_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Inline button callbacks + rewrite feedback text
# ---------------------------------------------------------------------------
async def _require_approved(draft_id: int):
    """Return the draft if it is APPROVED/SCHEDULED, else None."""
    draft = await repo.get_draft(draft_id)
    if draft and draft.status in (DraftStatus.APPROVED, DraftStatus.SCHEDULED):
        return draft
    return None


async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    from app.services import notifications as notif

    query = update.callback_query
    if not _authorized(update):
        return await _deny(update)
    await query.answer()
    parsed = verify_callback_token(query.data or "")
    if not parsed:
        return await query.answer("Invalid or stale button.", show_alert=True)
    draft_id, version, action = parsed
    user_id = update.effective_user.id
    try:
        if action == "approve":
            # Approve → re-render the SAME card with the publish/schedule menu.
            await approvals.approve_draft(draft_id, version, user_id)
            draft = await repo.get_draft(draft_id)
            await query.edit_message_text(
                notif.draft_preview_html(draft), parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=notif.kb_approved(draft_id, version))
        elif action == "reject":
            # Reject → nothing shown (remove all buttons).
            await approvals.reject_draft(draft_id, version, user_id)
            await query.edit_message_text(f"❌ Draft #{draft_id} rejected.")
        elif action == "sources":
            draft = await repo.get_draft(draft_id)
            srcs = "\n".join(draft.sources or []) or "(none)"
            await query.message.reply_text(f"Sources for #{draft_id}:\n{srcs}")
        elif action == "rewrite":
            _PENDING_REWRITE[user_id] = (draft_id, version)
            await query.message.reply_text(
                f"Reply with rewrite feedback for #{draft_id} "
                f"(e.g. 'make this more technical').")
        elif action == "schedule":
            # Must be approved first; otherwise ask for approval.
            if not await _require_approved(draft_id):
                return await query.answer(
                    "Please approve this draft first.", show_alert=True)
            markup, n = notif.kb_schedule_slots(draft_id, version)
            if n == 0:
                return await query.answer(
                    "No time slots left for today.", show_alert=True)
            await query.edit_message_reply_markup(reply_markup=markup)
        elif action.startswith("sch"):
            # A specific IST slot was tapped, e.g. 'sch14' = 2 PM IST today.
            if not await _require_approved(draft_id):
                return await query.answer(
                    "Please approve this draft first.", show_alert=True)
            hour = int(action[3:])
            when = notif.slot_to_utc(hour)
            await approvals.schedule_draft(draft_id, version, when, user_id)
            await query.edit_message_text(
                f"📅 Draft #{draft_id} scheduled for "
                f"{notif._slot_label(hour)} IST today.")
        elif action == "back":
            # Return from the slot view to the approved menu.
            await query.edit_message_reply_markup(
                reply_markup=notif.kb_approved(draft_id, version))
        elif action == "publish":
            # Must be approved first; otherwise ask for approval.
            if not await _require_approved(draft_id):
                return await query.answer(
                    "Please approve this draft first.", show_alert=True)
            settings = get_settings()
            draft = await repo.get_draft(draft_id)
            mock = not settings.feature_enabled(draft.platform.value)
            result = await publishing.publish_draft(draft_id, version, user_id, mock=mock)
            status = result.get("status")
            if status == "FAILED":
                # Live publish failed (e.g. permission/plan) -> offer manual fallback.
                manual = result.get("manual", {})
                compose = manual.get("compose_url", "")
                await query.message.reply_text(
                    f"⚠️ Live publish failed for #{draft_id}: {result.get('error','')}\n\n"
                    f"You can post it manually:\n{compose}\n\n"
                    f"Then tap '📝 Mark Posted Manually'."
                )
            else:
                suffix = " (mock)" if mock else ""
                await query.edit_message_text(f"🚀 {status}{suffix} for #{draft_id}.")
        elif action == "manual":
            result = await publishing.mark_manually_published(draft_id, version, user_id)
            await query.edit_message_text(
                f"📝 Draft #{draft_id} marked as manually published.")
    except Exception as exc:
        await query.message.reply_text(f"Action failed: {exc}")


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Capture rewrite feedback replies."""
    if not _authorized(update):
        return
    user_id = update.effective_user.id
    if user_id not in _PENDING_REWRITE:
        return
    draft_id, version = _PENDING_REWRITE.pop(user_id)
    feedback = update.message.text
    await update.message.reply_text("✏️ Rewriting…")
    result = await approvals.request_rewrite(draft_id, version, user_id, feedback)
    await update.message.reply_text(
        f"New v{result['version']} (needs approval):\n\n{result['content']}")


def build_application() -> Application:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set.")
    app = ApplicationBuilder().token(settings.telegram_bot_token).build()
    handlers = {
        "start": cmd_start, "help": cmd_help, "status": cmd_status, "news": cmd_news,
        "research": cmd_research, "drafts": cmd_drafts, "today": cmd_today,
        "approve": cmd_approve, "reject": cmd_reject, "rewrite": cmd_rewrite,
        "schedule": cmd_schedule, "publish": cmd_publish, "queue": cmd_queue,
        "stats": cmd_stats, "pause": cmd_pause, "resume": cmd_resume,
        "settings": cmd_settings, "health": cmd_health,
        "pending": cmd_pending, "connect_status": cmd_connect_status,
    }
    for name, fn in handlers.items():
        app.add_handler(CommandHandler(name, fn))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return app


async def _on_startup(app: Application) -> None:
    """On bot startup, send a ONE-LINE reminder of pending drafts (not full cards).

    A deploy/restart no longer re-posts every draft card; the owner taps
    /pending to see them. This avoids spamming the same drafts on each deploy.
    """
    try:
        from app.services.notifications import summarize_pending_drafts
        count = await summarize_pending_drafts()
        if count:
            logger.info("Reminded owner of %d pending draft(s) on startup.", count)
    except Exception as exc:  # never block startup on a notification failure
        logger.warning("Startup pending-draft reminder failed: %s", exc)


def run_polling() -> None:
    """Run the bot with long polling (local development)."""
    app = build_application()
    app.post_init = _on_startup
    logger.info("Starting Telegram bot (long polling)…")
    app.run_polling()
