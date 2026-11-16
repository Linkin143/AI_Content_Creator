# LinkedIn API setup

> Use current official LinkedIn APIs and verify your approved permissions.
> Personal-profile posting requires the `w_member_social` product to be approved
> for your developer app. Do not assume unrestricted analytics access.

## 1. Create a developer app
1. Create an app in the LinkedIn Developer Portal, associated with a Company Page.
2. Add the **Sign In with LinkedIn using OpenID Connect** product (for `openid`,
   `profile`) and request **Share on LinkedIn** / `w_member_social`.
3. Set the redirect URL to match `LINKEDIN_REDIRECT_URI`
   (default `http://localhost:8000/auth/linkedin/callback`).

## 2. Configure `.env`
```
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
LINKEDIN_REDIRECT_URI=http://localhost:8000/auth/linkedin/callback
LINKEDIN_SCOPES=openid profile w_member_social
LINKEDIN_API_VERSION=202610
```
The API version is configurable (sent via the `LinkedIn-Version` header) — no
obsolete version is hardcoded. LinkedIn retires each `YYYYMM` version after
~2 years; a stale value returns HTTP 426 "version not active". Bump this to a
current month if that happens.

## 3. Connect your account
1. Start the API and visit `http://localhost:8000/auth/linkedin/connect`.
2. After authorizing, the callback fetches your member `sub` (author URN) via the
   OpenID Connect `userinfo` endpoint and stores **encrypted** tokens.

## 4. Publishing
- Uses the current **Posts API** (`POST /rest/posts`) with
  `author = urn:li:person:{sub}`, `lifecycleState = PUBLISHED`,
  `visibility = PUBLIC`, and the required headers.

## Access limitations & manual fallback
If LinkedIn rejects publishing (permission not granted), the app:
- preserves the approved draft,
- notifies you on Telegram,
- offers a manual posting workflow with copyable text,
- records manual publication.
It never claims the post succeeded if the API returned an error. No scraping or
unauthorized browser automation is used.
