"""Tools for editorial_review."""
from app.agents.llm_helpers import call_structured
from app.schemas.content import QualityReview


async def review(system_prompt: str, content: str):
    return await call_structured(system_prompt, content, QualityReview)
