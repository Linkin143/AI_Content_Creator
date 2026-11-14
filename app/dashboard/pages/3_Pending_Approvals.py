import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.dashboard.common import header, require_login, run_async  # noqa: E402
from app.database import repositories as repo  # noqa: E402
from app.database.models import DraftStatus  # noqa: E402
from app.services import approvals  # noqa: E402

st.set_page_config(page_title="Pending Approvals", page_icon="✅", layout="wide")
if not require_login():
    st.stop()
header("Pending Approvals", "Drafts awaiting your decision")

pending = run_async(repo.list_drafts(status=DraftStatus.PENDING_REVIEW, limit=50))
revision = run_async(repo.list_drafts(status=DraftStatus.NEEDS_REVISION, limit=50))
queue = pending + revision

if not queue:
    st.success("Nothing pending. 🎉")
    st.stop()

for d in queue:
    with st.container(border=True):
        st.markdown(f"**#{d.id} [{d.platform.value}] v{d.current_version}** — {d.status.value}")
        st.write(d.content)
        st.caption("Sources: " + (", ".join(d.sources) if d.sources else "—"))
        a, b = st.columns(2)
        if a.button("✅ Approve", key=f"ap{d.id}"):
            try:
                run_async(approvals.approve_draft(d.id, d.current_version, None))
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        if b.button("❌ Reject", key=f"rj{d.id}"):
            run_async(approvals.reject_draft(d.id, d.current_version, None))
            st.rerun()
