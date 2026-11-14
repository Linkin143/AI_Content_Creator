"""Skill registry and loader.

A skill is a reusable instruction-and-tool package: a SKILL.md with the
operating instructions plus optional tools.py / schemas.py. Only the relevant
skill's instructions are loaded into a given node's prompt - we never dump every
skill document into every prompt.

Security: skills are local, explicitly-shipped files. Untrusted webpages can
never install new skills or modify existing skill files; this loader only reads
from the fixed skills directory and performs no code download or execution of
remote content.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent

VALID_SKILLS = {
    "news_discovery", "article_research", "fact_verification", "news_ranking",
    "technical_analysis", "x_content", "linkedin_content", "editorial_review",
    "telegram_operations", "social_publishing", "performance_analysis",
}


@dataclass
class Skill:
    name: str
    instructions: str
    path: Path


@cache
def load_skill(name: str) -> Skill:
    """Load a skill's SKILL.md instructions. Raises if the skill is unknown."""
    if name not in VALID_SKILLS:
        raise ValueError(f"Unknown skill '{name}'. Valid: {sorted(VALID_SKILLS)}")
    skill_md = SKILLS_DIR / name / "SKILL.md"
    instructions = ""
    if skill_md.exists():
        instructions = skill_md.read_text(encoding="utf-8")
    return Skill(name=name, instructions=instructions, path=SKILLS_DIR / name)


def list_skills() -> list[str]:
    return sorted(VALID_SKILLS)
