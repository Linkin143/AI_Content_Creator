"""X (Twitter) API v2 integration: OAuth 2.0 PKCE + posting.

This implements the complete official-API interface. Live posting requires your
own X developer app and an API access tier that permits writes. When posting is
not permitted (or credentials are absent), callers fall back to the manual
workflow in app.services.publishing - this module never uses browser automation
or undocumented endpoints.

Endpoints used (verify current pricing/availability in docs/X_API_SETUP.md):
  - Authorize:  https://twitter.com/i/oauth2/authorize
  - Token:      https://api.twitter.com/2/oauth2/token
  - Create post https://api.twitter.com/2/tweets   (POST)
"""

from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.config import get_settings

AUTHORIZE_URL = "https://twitter.com/i/oauth2/authorize"
TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
TWEETS_URL = "https://api.twitter.com/2/tweets"
ME_URL = "https://api.twitter.com/2/users/me"

X_POST_LIMIT = 280


class XAPIError(RuntimeError):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"X API {status}: {message}")


@dataclass
class TokenResponse:
    access_token: str
    refresh_token: str
    expires_in: int
    scope: str


def generate_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for OAuth 2.0 PKCE."""
    verifier = base64.urlsafe_b64encode(os.urandom(48)).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def build_authorize_url(state: str, code_challenge: str) -> str:
    settings = get_settings()
    params = {
        "response_type": "code",
        "client_id": settings.x_client_id,
        "redirect_uri": settings.x_redirect_uri,
        "scope": settings.x_scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def _basic_auth_header() -> dict:
    settings = get_settings()
    if settings.x_client_secret:
        raw = f"{settings.x_client_id}:{settings.x_client_secret}".encode()
        return {"Authorization": f"Basic {base64.b64encode(raw).decode()}"}
    return {}


async def exchange_code(code: str, code_verifier: str) -> TokenResponse:
    settings = get_settings()
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.x_redirect_uri,
        "code_verifier": code_verifier,
        "client_id": settings.x_client_id,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded", **_basic_auth_header()}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(TOKEN_URL, data=data, headers=headers)
    if resp.status_code != 200:
        raise XAPIError(resp.status_code, resp.text)
    body = resp.json()
    return TokenResponse(
        access_token=body.get("access_token", ""),
        refresh_token=body.get("refresh_token", ""),
        expires_in=body.get("expires_in", 7200),
        scope=body.get("scope", ""),
    )


async def refresh_token(refresh_tok: str) -> TokenResponse:
    settings = get_settings()
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_tok,
        "client_id": settings.x_client_id,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded", **_basic_auth_header()}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(TOKEN_URL, data=data, headers=headers)
    if resp.status_code != 200:
        raise XAPIError(resp.status_code, resp.text)
    body = resp.json()
    return TokenResponse(
        access_token=body.get("access_token", ""),
        refresh_token=body.get("refresh_token", refresh_tok),
        expires_in=body.get("expires_in", 7200),
        scope=body.get("scope", ""),
    )


async def verify_connection(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(ME_URL, headers=headers)
    if resp.status_code != 200:
        raise XAPIError(resp.status_code, resp.text)
    return resp.json().get("data", {})


async def create_post(access_token: str, text: str, reply_to: str | None = None) -> dict:
    """Create a single post (user-context token). Returns the API 'data' object."""
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload: dict = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(TWEETS_URL, json=payload, headers=headers)
    if resp.status_code in (200, 201):
        return resp.json().get("data", {})
    # Surface specific, actionable errors - never retry an unknown outcome blindly.
    raise XAPIError(resp.status_code, resp.text)


async def create_thread(access_token: str, parts: list[str]) -> list[dict]:
    """Publish a thread as a reply chain. Stops on first failure."""
    results: list[dict] = []
    reply_to: str | None = None
    for part in parts:
        data = await create_post(access_token, part, reply_to=reply_to)
        results.append(data)
        reply_to = data.get("id")
    return results


def manual_compose_url(text: str) -> str:
    """Official intent URL for manual posting fallback."""
    return "https://twitter.com/intent/tweet?" + urlencode({"text": text})
