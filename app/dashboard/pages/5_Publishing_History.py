import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.dashboard.common import header, require_login, run_async  # noqa: E402
from app.database import repositories as repo  # noqa: E402

st.set_page_config(page_title="Publishing History", page_icon="🗂️", layout="wide")
if not require_login():
    st.stop()
header("Publishing History", "Published and manually-published posts")

posts = run_async(repo.list_published(limit=200))
if not posts:
    st.info("Nothing published yet.")
    st.stop()

rows = [{"ID": p.id, "Draft": p.draft_id, "Platform": p.platform.value,
         "Status": p.status, "Manual": p.manual, "Post ID": p.platform_post_id,
         "Published": p.published_at.strftime("%Y-%m-%d %H:%M")} for p in posts]
st.dataframe(rows, use_container_width=True, hide_index=True)
