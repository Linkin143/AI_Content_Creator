import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from app.dashboard.common import header, require_login, run_async  # noqa: E402
from app.services import analytics  # noqa: E402

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
if not require_login():
    st.stop()
header("Analytics", "Activity overview")

stats = run_async(analytics.overview_stats())

labels = ["Articles(24h)", "Drafts", "Pending", "Scheduled", "Published", "Failed"]
values = [stats["articles_today"], stats["total_drafts"], stats["pending_approvals"],
          stats["scheduled_posts"], stats["published_posts"], stats["failed_publications"]]

fig = go.Figure(go.Bar(x=labels, y=values, marker_color="#00C853"))
fig.update_layout(paper_bgcolor="#0A0A0A", plot_bgcolor="#0A0A0A",
                  font_color="#F5F5F5", height=400)
st.plotly_chart(fig, use_container_width=True)

st.caption("Engagement metrics (likes/impressions) appear here only when a "
           "connected platform API actually returns them. They are never fabricated.")
