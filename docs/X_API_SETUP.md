# X (Twitter) API setup

> Verify current endpoints, product tiers and pricing in the official X developer
> docs before relying on posting. Posting is **not guaranteed free** — your API
> access tier must permit writes.

## 1. Create a developer app
1. Go to the X Developer Portal and create a Project + App.
2. Enable **OAuth 2.0** with the **Authorization Code + PKCE** flow.
3. Set the callback/redirect URL to match `X_REDIRECT_URI`
   (default `http://localhost:8000/auth/x/callback`).
4. Request scopes: `tweet.read tweet.write users.read offline.access`.

## 2. Configure `.env`
```
X_CLIENT_ID=...
X_CLIENT_SECRET=...        # if your app type uses a secret
X_REDIRECT_URI=http://localhost:8000/auth/x/callback
X_SCOPES=tweet.read tweet.write users.read offline.access
```
Install client deps: `pip install langchain-openai` is unrelated here; the X
integration uses `httpx` which is already installed.

## 3. Connect your account
1. Start the API: `uvicorn app.api.main:app --reload`.
2. Visit `http://localhost:8000/auth/x/connect` and authorize.
3. The callback stores **encrypted** tokens in SQLite.

## 4. Publishing
- Uses the official v2 create-post endpoint with a user-context token.
- Threads are posted as a reply chain.
- Handles 401 / 403 / 429 / timeouts / expired credentials explicitly and never
  blindly retries a request whose outcome is unknown.

## Access limitations & manual fallback
If your plan does **not** permit posting, the app does NOT attempt browser
automation or undocumented endpoints. Instead it:
- saves the approved post,
- sends the final text to Telegram,
- provides an official compose link (`twitter.com/intent/tweet`),
- lets you mark the post as manually published.

Live publishing should only be enabled after you confirm it works with your
authorized account. The system never claims success unless the API confirmed it.
