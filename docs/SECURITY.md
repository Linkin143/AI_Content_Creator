# Security

## Secrets
- No hardcoded credentials; everything comes from environment variables / `.env`.
- `.env` and the database are gitignored; never commit them.
- OAuth tokens are encrypted at rest with Fernet (`APP_ENCRYPTION_KEY`), managed
  separately from the database. Rotate the key by re-connecting accounts.
- Secret-looking values are redacted in logs (`redact_secrets`).

## Authentication & authorization
- Telegram: numeric user-ID allowlist enforced on every command and callback.
- Dashboard: password gate (separate from publishing authorization).
- API: admin/publishing routes require `X-API-Key` (the dashboard password).
- Publishing authorization is additionally gated by approval state — dashboard
  login alone does not authorize posting to X/LinkedIn.

## Callback / OAuth integrity
- Telegram callback tokens are HMAC-signed and bound to draft id + version,
  preventing stale/forged buttons from publishing old drafts.
- OAuth `state` is signed and time-bound (CSRF protection); X uses PKCE.

## Untrusted content & prompt injection
- Every article, RSS item and webpage is treated as untrusted.
- HTML is stripped of scripts/styles; obvious injection phrases are defanged.
- Untrusted text is wrapped in explicit delimiters before reaching an LLM, so it
  cannot override system instructions.
- An AI model can never publish without human authorization.

## Network safety
- SSRF protection rejects private/loopback/link-local hosts and non-HTTP schemes.
- Outgoing requests use timeouts; research tools have no access to secret files.
- No arbitrary shell execution; skills are local files only — untrusted pages
  cannot install or modify skills.

## Auditing
- Approvals, rejections, rewrites, schedules and publishes are written to the
  `audit_events` table with actor, action, entity and timestamp.
