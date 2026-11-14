"""OAuth connect/callback routes for X and LinkedIn.

State is signed and time-bound (CSRF protection). PKCE is used for X. Tokens are
stored encrypted. Callbacks are public endpoints but reject invalid state.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import get_settings
from app.database.models import Platform
from app.integrations import linkedin as li
from app.integrations import x_api
from app.security.signing import make_oauth_state, verify_oauth_state
from app.services import social_store

router = APIRouter()

# PKCE verifiers kept in-memory keyed by state (single-instance app).
_PKCE: dict[str, str] = {}


def _success_page(platform: str, account: str) -> HTMLResponse:
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Connected</title><style>
body{{background:#0A0A0A;color:#F5F5F5;font-family:sans-serif;
text-align:center;padding:80px 20px}}
.card{{display:inline-block;background:#161616;border:1px solid #00C853;
border-radius:12px;padding:40px 56px}}
h1{{color:#00C853;margin:0 0 8px}} p{{color:#ccc}}</style></head>
<body><div class="card"><h1>✅ {platform} connected</h1>
<p>Account: <b>{account or '(unknown)'}</b></p>
<p>You can close this tab and return to Telegram / the dashboard.</p>
</div></body></html>"""
    return HTMLResponse(html)


def _error_page(platform: str, status: int, detail: str) -> HTMLResponse:
    """Friendly error page. Detects the common X 'not in a Project' case."""
    hint = ""
    if "client-not-enrolled" in detail or "attached to a Project" in detail:
        hint = (
            "<p style='color:#ffc107'><b>Fix:</b> Your X App is not attached to a "
            "<b>Project</b>. X API v2 only works for apps inside a Project.</p>"
            "<ol style='text-align:left;color:#ccc;max-width:520px;margin:0 auto'>"
            "<li>Open the X Developer Portal dashboard.</li>"
            "<li>Under your <b>Project</b>, click <b>+ Add App</b> (create the app "
            "<i>inside</i> the Project, not as a standalone app).</li>"
            "<li>In that app: Settings → User authentication settings → enable "
            "OAuth 2.0, type <b>Web App / Bot</b>, callback "
            "<code>http://localhost:8000/auth/x/callback</code>, scopes "
            "<code>tweet.read tweet.write users.read offline.access</code>.</li>"
            "<li>Copy the new Client ID + Secret into <code>.env</code> "
            "(X_CLIENT_ID / X_CLIENT_SECRET) and restart the API.</li>"
            "<li>Retry <code>http://localhost:8000/auth/x/connect</code>.</li>"
            "</ol>"
            "<p><a style='color:#00C853' href='https://developer.x.com/en/portal/dashboard'"
            " target='_blank'>Open X Developer Portal →</a></p>"
        )
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Connection failed</title><style>
body{{background:#0A0A0A;color:#F5F5F5;font-family:sans-serif;
text-align:center;padding:60px 20px}}
.card{{display:inline-block;background:#161616;border:1px solid #ff5252;
border-radius:12px;padding:32px 48px;max-width:640px}}
h1{{color:#ff5252;margin:0 0 8px}} code{{color:#00C853}}
pre{{color:#888;white-space:pre-wrap;text-align:left;font-size:12px}}</style></head>
<body><div class="card"><h1>⚠️ {platform} connection failed</h1>
<p>HTTP {status}</p>{hint}
<details><summary style='cursor:pointer;color:#888'>Technical detail</summary>
<pre>{detail}</pre></details>
</div></body></html>"""
    return HTMLResponse(html, status_code=200)


@router.get("/auth/x/connect", tags=["oauth"])
async def x_connect() -> RedirectResponse:
    settings = get_settings()
    if not settings.feature_enabled("x"):
        raise HTTPException(400, "X client credentials not configured.")
    state = make_oauth_state("x")
    verifier, challenge = x_api.generate_pkce()
    _PKCE[state] = verifier
    return RedirectResponse(x_api.build_authorize_url(state, challenge))


@router.get("/auth/x/callback", tags=["oauth"])
async def x_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state", "")
    if verify_oauth_state(state) != "x":
        raise HTTPException(400, "invalid or expired state")
    verifier = _PKCE.pop(state, None)
    if not code or not verifier:
        raise HTTPException(400, "missing code or PKCE verifier")
    try:
        token = await x_api.exchange_code(code, verifier)
        account = await x_api.verify_connection(token.access_token)
    except x_api.XAPIError as exc:
        return _error_page("X (Twitter)", exc.status, str(exc))
    await social_store.save_connection(
        Platform.X, account.get("username", ""), account.get("id", ""),
        token.access_token, token.refresh_token, token.expires_in, token.scope)
    return _success_page("X (Twitter)", "@" + account.get("username", ""))


@router.get("/auth/linkedin/connect", tags=["oauth"])
async def linkedin_connect() -> RedirectResponse:
    settings = get_settings()
    if not settings.feature_enabled("linkedin"):
        raise HTTPException(400, "LinkedIn client credentials not configured.")
    state = make_oauth_state("linkedin")
    return RedirectResponse(li.build_authorize_url(state))


@router.get("/auth/linkedin/callback", tags=["oauth"])
async def linkedin_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state", "")
    if verify_oauth_state(state) != "linkedin":
        raise HTTPException(400, "invalid or expired state")
    if not code:
        raise HTTPException(400, "missing code")
    try:
        token = await li.exchange_code(code)
        info = await li.get_member_info(token.access_token)
    except li.LinkedInAPIError as exc:
        return _error_page("LinkedIn", exc.status, str(exc))
    await social_store.save_connection(
        Platform.LINKEDIN, info.get("name", ""), info.get("sub", ""),
        token.access_token, token.refresh_token, token.expires_in, token.scope)
    return _success_page("LinkedIn", info.get("name", ""))
