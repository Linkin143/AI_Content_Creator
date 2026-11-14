import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.agents.provider import health_check  # noqa: E402
from app.dashboard.common import header, require_login, run_async  # noqa: E402

st.set_page_config(page_title="Logs & Health", page_icon="🩺", layout="wide")
if not require_login():
    st.stop()
header("Logs & Health", "Provider health and recent logs")

rep = run_async(health_check())
st.subheader("LLM provider health")
st.json({
    "provider": rep.provider, "model": rep.model, "configured": rep.configured,
    "reachable": rep.reachable, "supports_tools": rep.supports_tools,
    "supports_structured_output": rep.supports_structured_output,
    "detail": rep.detail,
})

st.subheader("Recent logs")
log_dir = ROOT / "logs"
log_files = sorted(log_dir.glob("*.log")) if log_dir.exists() else []
if not log_files:
    st.caption("No log files yet.")
else:
    chosen = st.selectbox("Log file", [f.name for f in log_files])
    content = (log_dir / chosen).read_text(encoding="utf-8", errors="ignore")
    st.code(content[-5000:] or "(empty)")
