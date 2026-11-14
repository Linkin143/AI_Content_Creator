"""AEVRIX dashboard — Overview (Home) page.

Run with:  streamlit run app/dashboard/Home.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is importable when Streamlit runs this file directly.
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.agents.provider import health_check  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.dashboard.common import header, require_login, run_async  # noqa: E402
from app.services import analytics  # noqa: E402

st.set_page_config(page_title="AEVRIX Content Engine", page_icon="🟢", layout="wide")

if not require_login():
    st.stop()

header("AEVRIX Content Intelligence Engine", "Overview")

settings = get_settings()
stats = run_async(analytics.overview_stats())
rep = run_async(health_check())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Articles (24h)", stats["articles_today"])
c2.metric("Drafts", stats["total_drafts"])
c3.metric("Pending approvals", stats["pending_approvals"])
c4.metric("Scheduled", stats["scheduled_posts"])

c5, c6, c7, c8 = st.columns(4)
c5.metric("Published", stats["published_posts"])
c6.metric("Failed", stats["failed_publications"])
c7.metric("AI provider", rep.provider)
c8.metric("AI reachable", "yes" if rep.reachable else "no")

st.divider()
st.subheader("Run research now")
col_a, col_b = st.columns([1, 3])
with col_a:
    if st.button("🔍 Run pipeline", type="primary"):
        from app.agents.graph import run_pipeline
        with st.spinner("Researching…"):
            state = run_async(run_pipeline())
        st.success(
            f"Articles: {len(state.get('raw_articles', []))} · "
            f"Drafts: {len(state.get('persisted_draft_ids', []))} · "
            f"LLM calls: {state.get('llm_calls', 0)}"
        )
        for err in state.get("errors", []):
            st.warning(f"{err['node']}: {err['error']}")
with col_b:
    st.caption(
        f"Provider: **{rep.provider}** ({rep.model or 'default'}) — "
        f"configured={rep.configured}, reachable={rep.reachable}. "
        "Without an AI provider, research still fetches and stores articles; "
        "AI drafting is disabled with a clear notice."
    )

st.divider()
st.caption("Use the pages in the sidebar: News Explorer, Content Studio, "
           "Pending Approvals, Calendar, History, Analytics, Integrations, "
           "Settings and Logs & Health.")
