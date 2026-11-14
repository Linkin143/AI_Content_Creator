"""HMAC signing for Telegram callback tokens and OAuth state.

Callback tokens reference a real draft id + version and are signed so that
stale or forged inline buttons cannot trigger publishing of old drafts.
"""

from __future__ import annotations

import hashlib
import hmac
import time

from app.config import get_settings


def _secret() -> bytes:
    return get_settings().app_session_secret.encode()


def sign(payload: str) -> str:
    """Return a hex HMAC-SHA256 signature for the payload."""
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def make_callback_token(draft_id: int, version: int, action: str) -> str:
    """Build a signed callback token: draftid:version:action:sig."""
    payload = f"{draft_id}:{version}:{action}"
    return f"{payload}:{sign(payload)}"


def verify_callback_token(token: str) -> tuple[int, int, str] | None:
    """Validate a callback token. Returns (draft_id, version, action) or None."""
    parts = token.split(":")
    if len(parts) != 4:
        return None
    draft_id_s, version_s, action, sig = parts
    payload = f"{draft_id_s}:{version_s}:{action}"
    if not hmac.compare_digest(sig, sign(payload)):
        return None
    if not (draft_id_s.isdigit() and version_s.isdigit()):
        return None
    return int(draft_id_s), int(version_s), action


def make_oauth_state(provider: str) -> str:
    """Create a signed OAuth state value with a timestamp."""
    payload = f"{provider}:{int(time.time())}"
    return f"{payload}:{sign(payload)}"


def verify_oauth_state(state: str, max_age_seconds: int = 600) -> str | None:
    """Validate OAuth state and age. Returns provider name or None."""
    parts = state.split(":")
    if len(parts) != 3:
        return None
    provider, ts_s, sig = parts
    payload = f"{provider}:{ts_s}"
    if not hmac.compare_digest(sig, sign(payload)):
        return None
    if not ts_s.isdigit() or (time.time() - int(ts_s)) > max_age_seconds:
        return None
    return provider
