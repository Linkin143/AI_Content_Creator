"""Shared helpers for the Streamlit dashboard.

Provides login gating and a small async bridge so pages can call the app's async
repositories/services. Dashboard login is SEPARATE from authorization to publish
to X/LinkedIn (which is gated by approval state in the services layer).
"""

from __future__ import annotations

import asyncio
from typing import Any

import streamlit as st

from app.config import get_settings


def run_async(coro) -> Any:
    """Run an async coroutine from Streamlit's sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():  # pragma: no cover - defensive
            return asyncio.run_coroutine_threadsafe(coro, loop).result()
    except RuntimeError:
        pass
    return asyncio.run(coro)


def require_login() -> bool:
    """Render a login gate. Returns True when authenticated."""
    settings = get_settings()
    if st.session_state.get("authenticated"):
        return True

    st.markdown("### 🔒 AEVRIX — Admin Login")
    pwd = st.text_input("Password", type="password")
    if st.button("Sign in"):
        if pwd and pwd == settings.dashboard_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.caption(
        "Dashboard login is separate from X/LinkedIn authorization. "
        "Publishing still requires an approved draft and a connected account."
    )
    return False


def header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"<h1 style='color:#F5F5F5;margin-bottom:0'>{title}</h1>",
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(
            f"<p style='color:#00C853;margin-top:4px'>{subtitle}</p>",
            unsafe_allow_html=True,
        )
    st.divider()
