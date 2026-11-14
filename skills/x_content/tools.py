"""Tools for x_content."""
from app.agents.llm_helpers import call_structured
from app.schemas.content import XPostOutput


async def generate_x_post(system_prompt: str, content: str):
    return await call_structured(system_prompt, content, XPostOutput)


def check_post_length(text: str, limit: int = 280) -> bool:
    return len(text) <= limit
