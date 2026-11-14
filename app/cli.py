"""AEVRIX Content Intelligence Engine - command line interface.

Commands:
  init-db         Create schema + seed default sources and brand profile.
  test-provider   Health-check the configured LLM provider.
  research        Run the full research -> draft pipeline once.
  generate        Alias for research (kept for the documented workflow).
  run-bot         Start the Telegram bot (long polling).
  run-scheduler   Start APScheduler for recurring jobs.
  list-drafts     Print recent drafts.
  gen-key         Print a fresh encryption key for APP_ENCRYPTION_KEY.
"""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="AEVRIX Content Intelligence Engine CLI", no_args_is_help=True)
console = Console()


@app.command("init-db")
def init_db() -> None:
    """Create the database schema and seed default data."""
    from app.database.migrations import create_db_and_tables, seed_initial_data

    async def _run() -> None:
        await create_db_and_tables()
        result = await seed_initial_data()
        console.print(f"[green]Database initialized.[/green] Seeded "
                      f"{result['sources_added']} new sources.")

    asyncio.run(_run())


@app.command("test-provider")
def test_provider() -> None:
    """Check whether the configured LLM provider is reachable."""
    from app.agents.provider import health_check

    async def _run() -> None:
        rep = await health_check()
        table = Table(title="LLM Provider Health")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Provider", rep.provider)
        table.add_row("Model", rep.model or "(default)")
        table.add_row("Configured", str(rep.configured))
        table.add_row("Reachable", str(rep.reachable))
        table.add_row("Tools", str(rep.supports_tools))
        table.add_row("Structured output", str(rep.supports_structured_output))
        table.add_row("Detail", rep.detail)
        console.print(table)
        if not rep.configured:
            console.print("[yellow]Provider not configured. The app still runs in "
                          "research-only mode (AI generation disabled).[/yellow]")

    asyncio.run(_run())


@app.command("research")
def research(
    window: int = typer.Option(None, help="Research window in hours."),
    max_posts: int = typer.Option(None, help="Max posts to draft."),
) -> None:
    """Run the full pipeline once: discover -> verify -> rank -> draft -> notify."""
    from app.agents.graph import run_pipeline

    async def _run() -> None:
        console.print("[cyan]Running research pipeline…[/cyan]")
        state = await run_pipeline(window_hours=window, max_posts=max_posts)
        console.print(
            f"[green]Done.[/green] articles={len(state.get('raw_articles', []))} "
            f"fresh={len(state.get('fresh', []))} "
            f"drafts={len(state.get('persisted_draft_ids', []))} "
            f"llm_calls={state.get('llm_calls', 0)}"
        )
        for err in state.get("errors", []):
            console.print(f"[yellow]warn[/yellow] {err['node']}: {err['error']}")
        if not state.get("persisted_draft_ids") and not state.get("llm_available"):
            console.print("[yellow]No AI provider available -> no drafts generated. "
                          "Articles were still fetched and stored.[/yellow]")

    asyncio.run(_run())


@app.command("generate")
def generate() -> None:
    """Alias for `research` (documented workflow name)."""
    research(window=None, max_posts=None)


@app.command("list-drafts")
def list_drafts_cmd() -> None:
    """Print recent drafts."""
    from app.database import repositories as repo

    async def _run() -> None:
        drafts = await repo.list_drafts(limit=20)
        if not drafts:
            console.print("No drafts.")
            return
        table = Table(title="Drafts")
        for col in ("ID", "Platform", "Status", "v", "Quality", "Content"):
            table.add_column(col)
        for d in drafts:
            table.add_row(str(d.id), d.platform.value, d.status.value,
                          str(d.current_version), f"{d.quality_score:.0f}",
                          (d.content[:60] + "…") if len(d.content) > 60 else d.content)
        console.print(table)

    asyncio.run(_run())


@app.command("run-bot")
def run_bot() -> None:
    """Start the Telegram bot (long polling)."""
    from app.config import get_settings
    settings = get_settings()
    if not settings.feature_enabled("telegram"):
        console.print("[red]Telegram not configured.[/red] Set TELEGRAM_BOT_TOKEN and "
                      "TELEGRAM_ALLOWED_USER_IDS in .env.")
        raise typer.Exit(code=1)
    from app.integrations.telegram import run_polling
    run_polling()


@app.command("run-scheduler")
def run_scheduler() -> None:
    """Start APScheduler (research at 08:00 IST + due publications)."""
    from app.services.scheduling import build_scheduler

    async def _run() -> None:
        scheduler = build_scheduler()
        scheduler.start()
        console.print("[green]Scheduler started.[/green] Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()

    asyncio.run(_run())


@app.command("gen-key")
def gen_key() -> None:
    """Generate a Fernet encryption key for APP_ENCRYPTION_KEY."""
    from app.security.encryption import generate_key
    console.print(generate_key())


if __name__ == "__main__":
    app()
