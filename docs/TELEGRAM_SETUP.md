# Telegram bot setup

Telegram is the primary mobile command + approval interface.

## 1. Create a bot
1. Open Telegram and message **@BotFather**.
2. Send `/newbot`, follow the prompts, and copy the **bot token**.

## 2. Find your numeric user ID
1. Message **@userinfobot** (or similar) to get your numeric Telegram user ID.
2. Only IDs in the allowlist can command the bot.

## 3. Configure `.env`
```
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_ALLOWED_USER_IDS=11111111,22222222
TELEGRAM_MODE=polling
# TELEGRAM_WEBHOOK_SECRET=...   # only for webhook mode
```

## 4. Run the bot
```
python -m app.cli run-bot
```
Long polling is used for local development. Do not run polling and webhook mode
at the same time.

## Commands
`/start /help /status /news /research /drafts /today /approve /reject /rewrite
/schedule /publish /queue /stats /pause /resume /settings /health`

## Inline buttons
Draft previews include: Approve, Reject, Rewrite, View Sources, Schedule,
Publish Now.

## Security
- Every command and callback is checked against the user-ID allowlist.
- Callback tokens are HMAC-signed and bound to a specific draft id + version, so
  stale or forged buttons cannot publish old drafts.
- A revised draft invalidates prior approval and requires fresh approval.
- Social access tokens are never shown in Telegram.

## Webhook mode (optional, for hosting)
Set `TELEGRAM_MODE=webhook` and `TELEGRAM_WEBHOOK_SECRET`, expose
`POST /telegram/webhook`, and register the webhook with Telegram using the secret
token. The endpoint validates the `X-Telegram-Bot-Api-Secret-Token` header.
