"""Storage of social OAuth connections with encrypted tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.database.models import Platform, SocialConnection
from app.database.session import async_session_factory
from app.security.encryption import encrypt


async def save_connection(platform: Platform, account_name: str, account_id: str,
                          access_token: str, refresh_token: str = "",
                          expires_in: int = 0, scopes: str = "") -> int:
    """Persist (or replace) a social connection with encrypted tokens."""
    expires_at = (datetime.now(UTC) + timedelta(seconds=expires_in)
                  if expires_in else None)
    async with async_session_factory() as session:
        # Deactivate prior connections for this platform.
        existing = (await session.execute(
            select(SocialConnection).where(SocialConnection.platform == platform)
        )).scalars().all()
        for conn in existing:
            conn.active = False
            session.add(conn)

        new_conn = SocialConnection(
            platform=platform,
            account_name=account_name,
            account_id=account_id,
            access_token_enc=encrypt(access_token),
            refresh_token_enc=encrypt(refresh_token) if refresh_token else "",
            expires_at=expires_at,
            scopes=scopes,
            active=True,
        )
        session.add(new_conn)
        await session.commit()
        await session.refresh(new_conn)
        return new_conn.id


async def get_active_connection(platform: Platform) -> SocialConnection | None:
    async with async_session_factory() as session:
        stmt = select(SocialConnection).where(
            SocialConnection.platform == platform, SocialConnection.active)
        return (await session.execute(stmt)).scalars().first()


async def disconnect(platform: Platform) -> bool:
    async with async_session_factory() as session:
        stmt = select(SocialConnection).where(
            SocialConnection.platform == platform, SocialConnection.active)
        conns = (await session.execute(stmt)).scalars().all()
        for conn in conns:
            conn.active = False
            session.add(conn)
        await session.commit()
        return bool(conns)
