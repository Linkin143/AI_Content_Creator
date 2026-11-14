"""Tools for fact_verification."""
from app.agents.llm_helpers import call_structured
from app.schemas.content import VerificationOutput


async def verify(system_prompt: str, content: str):
    return await call_structured(system_prompt, content, VerificationOutput)
