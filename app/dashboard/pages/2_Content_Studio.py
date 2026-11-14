import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.dashboard.common import header, require_login, run_async  # noqa: E402
from app.database import repositories as repo  # noqa: E402
from app.services import approvals, publishing  # noqa: E402

st.set_page_config(page_title="Content Studio", page_icon="✍️", layout="wide")
if not require_login():
    st.stop()
header("Content Studio", "View, edit, regenerate, approve and schedule drafts")

drafts = run_async(repo.list_drafts(limit=100))
if not drafts:
    st.info("No drafts yet. Run research to generate drafts (requires an AI provider).")
    st.stop()

labels = {f"#{d.id} [{d.platform.value}] v{d.current_version} — {d.status.value}": d.id
          for d in drafts}
choice = st.selectbox("Draft", list(labels.keys()))
draft = run_async(repo.get_draft(labels[choice]))

st.caption(f"Status: **{draft.status.value}** · Quality: {draft.quality_score:.0f}/100")
new_text = st.text_area("Content", value=draft.content, height=200)
st.caption("Sources: " + (", ".join(draft.sources) if draft.sources else "—"))

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    if st.button("💾 Save (new version)"):
        run_async(repo.add_draft_version(draft.id, new_text, "dashboard edit"))
        st.success("Saved as new version — needs re-approval.")
        st.rerun()
with col2:
    if st.button("✅ Approve"):
        try:
            run_async(approvals.approve_draft(draft.id, draft.current_version, None))
            st.success("Approved.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
with col3:
    if st.button("❌ Reject"):
        run_async(approvals.reject_draft(draft.id, draft.current_version, None))
        st.rerun()
with col4:
    if st.button("🔁 Regenerate"):
        fb = st.session_state.get("fb", "make it sharper")
        res = run_async(approvals.request_rewrite(draft.id, draft.current_version, None, fb))
        st.info(f"New v{res['version']} created.")
        st.rerun()
with col5:
    if st.button("🚀 Publish (mock)"):
        try:
            res = run_async(publishing.publish_draft(draft.id, draft.current_version,
                                                     None, mock=True))
            st.success(res["status"])
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

st.text_input("Regenerate feedback", key="fb",
              placeholder="e.g. make this more technical")
