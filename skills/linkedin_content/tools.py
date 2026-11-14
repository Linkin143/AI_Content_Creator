"""Tools for linkedin_content."""
from app.agents.llm_helpers import call_structured
from app.schemas.content import LinkedInPostOutput


async def generate_linkedin_post(system_prompt: str, content: str):
    return await call_structured(system_prompt, content, LinkedInPostOutput)
