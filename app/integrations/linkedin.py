"""LinkedIn API integration: OAuth 2.0 + Posts API for a personal profile.

Live posting requires your own LinkedIn developer app with the `w_member_social`
product approved. When unavailable, callers use the manual fallback in
app.services.publishing. No scraping or browser automation is used.

Endpoints (confirm current versions in docs/LINKEDIN_API_SETUP.md):
  - Authorize: https://www.linkedin.com/oauth/v2/authorization
  - Token:     https://www.linkedin.com/oauth/v2/accessToken
  - Userinfo:  https://api.linkedin.com/v2/userinfo   (OpenID Connect)
  - Posts:     https://api.linkedin.com/rest/posts    (POST)
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.config import get_settings

AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
POSTS_URL = "https://api.linkedin.com/rest/posts"


class LinkedInAPIError(RuntimeError):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"LinkedIn API {status}: {message}")


@dataclass
class TokenResponse:
    access_token: str
    refresh_token: str
    expires_in: int
    scope: str


def build_authorize_url(state: str) -> str:
    settings = get_settings()
    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": settings.linkedin_redirect_uri,
        "scope": settings.linkedin_scopes,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> TokenResponse:
    settings = get_settings()
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.linkedin_redirect_uri,
        "client_id": settings.linkedin_client_id,
        "client_secret": settings.linkedin_client_secret,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(TOKEN_URL, data=data, headers=headers)
    if resp.status_code != 200:
        raise LinkedInAPIError(resp.status_code, resp.text)
    body = resp.json()
    return TokenResponse(
        access_token=body.get("access_token", ""),
        refresh_token=body.get("refresh_token", ""),
        expires_in=body.get("expires_in", 3600),
        scope=body.get("scope", ""),
    )


async def get_member_info(access_token: str) -> dict:
    """OpenID Connect userinfo - returns the member's 'sub' used as author URN."""
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(USERINFO_URL, headers=headers)
    if resp.status_code != 200:
        raise LinkedInAPIError(resp.status_code, resp.text)
    return resp.json()


async def create_post(access_token: str, author_sub: str, text: str) -> dict:
    """Publish a text post to the member's feed using the Posts API."""
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": settings.linkedin_api_version,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    payload = {
        "author": f"urn:li:person:{author_sub}",
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(POSTS_URL, json=payload, headers=headers)
    if resp.status_code in (200, 201):
        # LinkedIn returns the post id in the x-restli-id header.
        post_id = resp.headers.get("x-restli-id", "")
        return {"id": post_id, "status": resp.status_code}
    raise LinkedInAPIError(resp.status_code, resp.text)


def manual_compose_url(text: str) -> str:
    """Official share link for manual posting fallback."""
    return "https://www.linkedin.com/feed/?" + urlencode({"shareActive": "true"})
