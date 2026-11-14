"""On-demand single-draft (re)generation used by rewrite and dashboard actions.

Separate from the batch LangGraph pipeline so a single draft can be regenerated
quickly from Telegram or Streamlit.
"""

from __future__ import annotations

from app.agents.llm_helpers import call_structured, call_text
from app.database import repositories as repo
from app.database.models import Draft, Platform
from app.schemas.content import LinkedInPostOutput, XPostOutput
from app.security.sanitization import wrap_untrusted
from skills import load_skill


async def rewrite_draft_content(draft: Draft, feedback: str) -> str:
    """Regenerate a draft's content applying the human's feedback."""
    brand = await repo.get_brand_profile()
    brand_ctx = (
        f"{brand.name}: {brand.writing_preferences}" if brand
        else "Prince Kumar - senior engineer, AI builder, founder of AEVRIX."
    )
    skill_name = "x_content" if draft.platform == Platform.X else "linkedin_content"
    skill = load_skill(skill_name)

    instruction = (
        f"{skill.instructions}\n\nAUTHOR PROFILE:\n{brand_ctx}\n\n"
        f"Revise the following post according to this feedback: '{feedback}'. "
        f"Keep all factual claims supported by the existing evidence."
    )
    content = wrap_untrusted(
        f"CURRENT POST:\n{draft.content}\n\nEVIDENCE:\n{draft.evidence}", label="DRAFT"
    )

    schema = XPostOutput if draft.platform == Platform.X else LinkedInPostOutput
    result = await call_structured(instruction, content, schema)
    if result is not None and result.content.strip():
        return result.content.strip()

    # Fallback to a plain-text rewrite if structured output failed.
    text = await call_text(instruction, content)
    if text:
        return text.strip()
    # No provider available - keep original content, signal via unchanged text.
    return draft.content
