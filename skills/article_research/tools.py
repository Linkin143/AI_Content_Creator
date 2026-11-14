"""Tools for article_research."""
from app.agents.llm_helpers import call_structured
from app.schemas.content import ExtractedClaims


async def extract_claims(system_prompt: str, content: str):
    return await call_structured(system_prompt, content, ExtractedClaims)
