"""Simple API authentication.

Admin/publishing endpoints require an API key (the dashboard password acts as
the shared admin key for this single-user app). OAuth callbacks are public but
validate signed state. This is separate from authorization to publish, which is
additionally gated by approval state in the services layer.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.config import get_settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    settings = get_settings()
    expected = settings.dashboard_password
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-API-Key.",
        )
    return x_api_key
