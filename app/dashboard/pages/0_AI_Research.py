import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.dashboard.common import header, require_login, run_async  # noqa: E402
from app.database import repositories as repo  # noqa: E402

st.set_page_config(page_title="AI Research", page_icon="🔬", layout="wide")
if not require_login():
    st.stop()
header("AI Research", "Research sources & recent articles by category")

articles = run_async(repo.list_recent_articles(limit=300))
research_articles = [a for a in articles if a.category in ("research", "ai_engineering")]

st.subheader("Research & AI-engineering articles")
if not research_articles:
    st.info("No research articles yet. Run research from the Overview page.")
else:
    rows = [{"Title": a.title, "Publisher": a.publisher, "Category": a.category,
             "URL": a.url} for a in research_articles]
    st.dataframe(rows, use_container_width=True, hide_index=True,
                 column_config={"URL": st.column_config.LinkColumn("URL")})

st.divider()
st.subheader("Source health")
sources = run_async(repo.list_active_sources())
st.caption(f"{len(sources)} active sources configured")
