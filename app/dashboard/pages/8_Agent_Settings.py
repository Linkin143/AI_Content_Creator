import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.dashboard.common import header, require_login, run_async  # noqa: E402
from app.database import repositories as repo  # noqa: E402

st.set_page_config(page_title="Agent Settings", page_icon="⚙️", layout="wide")
if not require_login():
    st.stop()
header("Agent Settings", "Configuration (edit .env to change; shown read-only here)")

s = get_settings()
st.subheader("Model & research")
st.write({
    "LLM provider": s.llm_provider.value,
    "Model": s.resolved_model or "(default)",
    "Research window (h)": s.research_window_hours,
    "Max articles/run": s.max_articles_per_run,
    "Max LLM calls/run": s.max_llm_calls_per_run,
})

st.subheader("Posting limits & approval")
st.write({
    "Max X posts/day": s.max_x_posts_per_day,
    "Max LinkedIn posts/week": s.max_linkedin_posts_per_week,
    "Require human approval": s.require_human_approval,
    "Auto publish": s.auto_publish,
})

st.divider()
st.subheader("Source registry")
sources = run_async(repo.list_active_sources())
st.caption(f"{len(sources)} active sources")
st.dataframe(
    [{"Name": x["name"], "Category": x["category"], "Region": x["region"],
      "Type": x["source_type"], "Tier": x["reliability_tier"]} for x in sources],
    use_container_width=True, hide_index=True,
)

st.divider()
st.subheader("Brand profile")
brand = run_async(repo.get_brand_profile())
if brand:
    st.write({"Name": brand.name, "Bio": brand.biography,
              "Expertise": brand.technical_expertise,
              "Restricted topics": brand.restricted_topics})
st.caption("Settings are environment-driven for safety. Edit .env and restart "
           "to change provider, limits and credentials.")
