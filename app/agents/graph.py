"""LangGraph StateGraph assembly for the content pipeline.

The graph is linear with conditional short-circuits:
  - no raw articles      -> END
  - no fresh stories     -> END
  - no selected stories  -> END
  - no drafts generated  -> still persists/ends cleanly

A separate short publishing workflow (app.services.publishing) handles
approve -> schedule -> publish, so we never keep a long graph suspended for
hours waiting on human approval.

Checkpointing uses a persistent local SQLite database.
"""

from __future__ import annotations

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph

from app.agents import nodes
from app.agents.state import ContentPipelineState
from app.config import get_settings


def _has(key: str):
    def router(state: ContentPipelineState) -> str:
        return "continue" if state.get(key) else "stop"
    return router


def build_graph():
    """Construct and compile the content pipeline graph (no checkpointer)."""
    g = StateGraph(ContentPipelineState)

    g.add_node("discover_news", nodes.discover_news)
    g.add_node("deduplicate_stories", nodes.deduplicate_stories)
    g.add_node("filter_freshness", nodes.filter_freshness)
    g.add_node("research_stories", nodes.research_stories)
    g.add_node("verify_claims", nodes.verify_claims)
    g.add_node("rank_stories", nodes.rank_stories_node)
    g.add_node("technical_analysis", nodes.technical_analysis)
    g.add_node("select_content", nodes.select_content)
    g.add_node("generate_x_posts", nodes.generate_x_posts)
    g.add_node("generate_linkedin_posts", nodes.generate_linkedin_posts)
    g.add_node("editorial_quality_check", nodes.editorial_quality_check)
    g.add_node("persist_drafts", nodes.persist_drafts)
    g.add_node("send_telegram_review", nodes.send_telegram_review)

    g.add_edge(START, "discover_news")

    # Short-circuit if no articles were found.
    g.add_conditional_edges(
        "discover_news", _has("raw_articles"),
        {"continue": "deduplicate_stories", "stop": END},
    )
    g.add_edge("deduplicate_stories", "filter_freshness")

    # Short-circuit if nothing is fresh.
    g.add_conditional_edges(
        "filter_freshness", _has("fresh"),
        {"continue": "research_stories", "stop": END},
    )
    g.add_edge("research_stories", "verify_claims")
    g.add_edge("verify_claims", "rank_stories")
    g.add_edge("rank_stories", "technical_analysis")
    g.add_edge("technical_analysis", "select_content")

    # Short-circuit if nothing selected (e.g. all contradicted).
    g.add_conditional_edges(
        "select_content", _has("selected"),
        {"continue": "generate_x_posts", "stop": END},
    )
    g.add_edge("generate_x_posts", "generate_linkedin_posts")
    g.add_edge("generate_linkedin_posts", "editorial_quality_check")
    g.add_edge("editorial_quality_check", "persist_drafts")
    g.add_edge("persist_drafts", "send_telegram_review")
    g.add_edge("send_telegram_review", END)

    return g


async def run_pipeline(
    window_hours: int | None = None,
    max_posts: int | None = None,
    run_id: str | None = None,
) -> ContentPipelineState:
    """Execute the full pipeline with a persistent SQLite checkpointer."""
    import uuid

    settings = get_settings()
    run_id = run_id or uuid.uuid4().hex
    initial: ContentPipelineState = {
        "run_id": run_id,
        "research_window_hours": window_hours or settings.research_window_hours,
        "max_articles": settings.max_articles_per_run,
        "max_posts": max_posts if max_posts is not None else settings.max_x_posts_per_day,
        "llm_calls": 0,
        "llm_available": False,
        "errors": [],
        "metadata": {},
    }

    graph_def = build_graph()
    async with AsyncSqliteSaver.from_conn_string(settings.sqlite_path) as saver:
        compiled = graph_def.compile(checkpointer=saver)
        config = {"configurable": {"thread_id": run_id}}
        final_state = await compiled.ainvoke(initial, config=config)
    return final_state
