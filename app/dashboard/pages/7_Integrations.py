import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.agents.provider import health_check  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.dashboard.common import header, require_login, run_async  # noqa: E402
from app.database.models import Platform  # noqa: E402
from app.services import social_store  # noqa: E402

st.set_page_config(page_title="Integrations", page_icon="🔌", layout="wide")
if not require_login():
    st.stop()
header("Integrations", "Provider and account connection status")

settings = get_settings()
rep = run_async(health_check())

st.subheader("AI model provider")
st.write(f"Active: **{rep.provider}** ({rep.model or 'default'})")
st.write(f"Configured: {rep.configured} · Reachable: {rep.reachable}")
st.caption(rep.detail)

st.divider()
st.subheader("Social accounts")
x_conn = run_async(social_store.get_active_connection(Platform.X))
li_conn = run_async(social_store.get_active_connection(Platform.LINKEDIN))

c1, c2 = st.columns(2)
with c1:
    st.markdown("**X (Twitter)**")
    st.write("Connected: " + (x_conn.account_name if x_conn else "no"))
    if settings.feature_enabled("x"):
        st.markdown("[Connect X](http://localhost:8000/auth/x/connect)")
    else:
        st.caption("Set X_CLIENT_ID / X_CLIENT_SECRET to enable.")
with c2:
    st.markdown("**LinkedIn**")
    st.write("Connected: " + (li_conn.account_name if li_conn else "no"))
    if settings.feature_enabled("linkedin"):
        st.markdown("[Connect LinkedIn](http://localhost:8000/auth/linkedin/connect)")
    else:
        st.caption("Set LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET to enable.")

st.divider()
st.subheader("Telegram")
st.write("Configured: " + ("yes" if settings.feature_enabled("telegram") else "no"))
st.caption("Start the bot with: python -m app.cli run-bot")
