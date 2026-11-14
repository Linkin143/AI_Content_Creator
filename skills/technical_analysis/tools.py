"""Tools for technical_analysis."""
from app.agents.llm_helpers import call_structured
from app.schemas.content import TechnicalAnalysis


async def analyze(system_prompt: str, content: str):
    return await call_structured(system_prompt, content, TechnicalAnalysis)
