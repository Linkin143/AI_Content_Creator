import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.dashboard.common import header, require_login, run_async  # noqa: E402
from app.database import repositories as repo  # noqa: E402
from app.database.models import DraftStatus  # noqa: E402

st.set_page_config(page_title="Content Calendar", page_icon="📅", layout="wide")
if not require_login():
    st.stop()
header("Content Calendar", "Scheduled posts (times stored in UTC)")

scheduled = run_async(repo.list_drafts(status=DraftStatus.SCHEDULED, limit=100))
if not scheduled:
    st.info("No scheduled posts. Approve a draft, then schedule it.")
    st.stop()

rows = [{"Draft": f"#{d.id}", "Platform": d.platform.value,
         "Version": d.current_version, "Content": d.content[:80]} for d in scheduled]
st.dataframe(rows, use_container_width=True, hide_index=True)
