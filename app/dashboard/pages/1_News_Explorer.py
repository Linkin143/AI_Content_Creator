import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.dashboard.common import header, require_login, run_async  # noqa: E402
from app.database import repositories as repo  # noqa: E402

st.set_page_config(page_title="News Explorer", page_icon="📰", layout="wide")
if not require_login():
    st.stop()
header("News Explorer", "Discovered articles")

articles = run_async(repo.list_recent_articles(limit=200))
if not articles:
    st.info("No articles yet. Run research from the Overview page.")
    st.stop()

query = st.text_input("Search title/publisher")
categories = sorted({a.category for a in articles if a.category})
chosen = st.multiselect("Category", categories)

rows = []
for a in articles:
    if query and query.lower() not in (a.title + a.publisher).lower():
        continue
    if chosen and a.category not in chosen:
        continue
    rows.append({
        "Title": a.title,
        "Publisher": a.publisher,
        "Category": a.category,
        "Region": a.region,
        "Published": a.published_at.strftime("%Y-%m-%d %H:%M") if a.published_at else "—",
        "URL": a.url,
    })

st.caption(f"{len(rows)} articles")
st.dataframe(rows, use_container_width=True, hide_index=True,
             column_config={"URL": st.column_config.LinkColumn("URL")})
