"""Store manually-generated X OAuth 2.0 tokens and verify them.

Use this to connect X WITHOUT the browser flow, once your app is attached to a
Project in the X developer portal (generate tokens from the project-app's
"Keys and tokens" tab).

Usage:
    python scripts/inject_x_tokens.py <ACCESS_TOKEN> <REFRESH_TOKEN>
"""

import asyncio
import sys

from app.database.models import Platform
from app.integrations import x_api
from app.services import social_store


async def main(access_token: str, refresh_token: str) -> None:
    print("Verifying against GET /2/users/me ...")
    try:
        account = await x_api.verify_connection(access_token)
    except x_api.XAPIError as exc:
        print(f"FAILED: {exc}")
        if exc.status == 403 and "client-not-enrolled" in str(exc):
            print("\n-> The app is still NOT attached to a Project. Create/attach "
                  "the app to a Project in the X developer portal first.")
        return

    username = account.get("username", "")
    account_id = account.get("id", "")
    print(f"OK: @{username} (id={account_id})")
    await social_store.save_connection(
        Platform.X, username, account_id,
        access_token, refresh_token,
        expires_in=7200, scopes="tweet.read tweet.write users.read offline.access",
    )
    print(f"Stored encrypted X connection for @{username}.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/inject_x_tokens.py <ACCESS_TOKEN> <REFRESH_TOKEN>")
        raise SystemExit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
