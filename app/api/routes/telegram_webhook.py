"""Optional Telegram webhook endpoint.

Only used in webhook mode. Validates the Telegram secret header. Do NOT run
polling and webhook simultaneously.
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import TelegramMode, get_settings

router = APIRouter()


@router.post("/telegram/webhook", tags=["telegram"])
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    settings = get_settings()
    if settings.telegram_mode != TelegramMode.WEBHOOK:
        raise HTTPException(400, "Webhook mode is disabled (TELEGRAM_MODE=polling).")
    if not settings.telegram_webhook_secret:
        raise HTTPException(500, "TELEGRAM_WEBHOOK_SECRET not configured.")
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(401, "Invalid Telegram secret token.")

    from telegram import Update

    from app.integrations.telegram import build_application

    application = build_application()
    await application.initialize()
    update = Update.de_json(await request.json(), application.bot)
    await application.process_update(update)
    await application.shutdown()
    return {"ok": True}
