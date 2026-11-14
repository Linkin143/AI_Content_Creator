"""Typed LangGraph state for the content pipeline.

The state carries plain dicts (JSON-serializable) so it works cleanly with the
LangGraph SQLite checkpointer's strict serialization.
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph.message import add_messages  # noqa: F401 (available if needed)


class PipelineError(TypedDict):
    node: str
    error: str


class ContentPipelineState(TypedDict, total=False):
    run_id: str
    research_window_hours: int
    max_articles: int
    max_posts: int

    # Each stage stores JSON-serializable article/story dicts.
    raw_articles: list[dict]
    deduplicated: list[dict]
    fresh: list[dict]
    researched: list[dict]
    verified: list[dict]
    ranked: list[dict]
    analyzed: list[dict]
    selected: list[dict]

    x_drafts: list[dict]
    linkedin_drafts: list[dict]
    reviewed_drafts: list[dict]
    persisted_draft_ids: list[int]

    telegram_sent: bool
    llm_available: bool
    llm_calls: int
    errors: list[PipelineError]
    metadata: dict
