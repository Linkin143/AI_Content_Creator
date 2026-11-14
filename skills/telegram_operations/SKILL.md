# Skill: telegram_operations

## Purpose
Operate the Telegram command/approval interface: send draft previews and digests,
and handle approve/reject/rewrite/schedule/publish actions.

## Required inputs
- Draft IDs + versions, target chat (authorized owner only).
- Callback tokens (HMAC-signed) referencing a specific draft id + version.

## Available tools
- `send_draft_preview(draft)` - preview text + sources + inline buttons.
- `send_digest(stories)` - daily/weekly summaries.
- `handle_callback(token, user_id)` - validate and route a button press.

## Operational constraints
- Enforce the Telegram user-ID allowlist on EVERY command and callback.
- Validate the HMAC callback token; reject stale/forged tokens so old buttons
  cannot publish old drafts.
- A revised draft invalidates prior approval and needs new approval.
- Never display social access tokens in any message.
- Do not run polling and webhook simultaneously.

## Error conditions
- Unauthorized user: refuse and log. Unknown/stale token: refuse with a note.
- Telegram unavailable: preserve the draft; retry/notify later.

## When to run
- After drafts are persisted (previews) and whenever the owner issues a command.

## When NOT to run
- Never auto-approve or auto-publish on behalf of the human.

## Rules preventing unsupported claims
- Previews must show the real stored draft and its real sources, unedited.
