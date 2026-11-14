# AEVRIX Content Intelligence Engine

A portable, lightweight AI content intelligence system for **Prince Kumar / AEVRIX**
(<https://aevrix.in/>). It researches global and Indian technology developments,
evaluates and verifies stories, generates platform-specific X and LinkedIn drafts,
requests approval via Telegram or a Streamlit dashboard, and publishes approved
posts through official APIs.

> **Design goal:** remain fully functional after temporary Microsoft Foundry access
> expires. The LLM provider is a single configuration switch
> (`foundry → ollama → gemini → groq → openai_compatible`). No Azure-specific
> service, Docker, Kubernetes, or microservices are required.

## Key properties

- **Portable LLM adapter** — Foundry, Ollama, OpenAI-compatible, Gemini, Groq.
- **Runs without AI** — research, storage, manual drafting, approvals and export
  keep working even when no model provider is available.
- **Single Python repo** — FastAPI + Streamlit + SQLite + LangGraph + APScheduler.
- **Human-in-the-loop** — nothing publishes without explicit owner approval.
- **Safe by default** — encrypted OAuth tokens, Telegram allowlist, prompt-injection
  defenses, audit trail, mock publishing in tests.

## Quick start (Windows)

```powershell
# 1. Create & activate venv, install deps
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

# 2. Configure
copy .env.example .env
# edit .env (at minimum set APP_ENCRYPTION_KEY and an LLM provider)

# 3. Initialize the database + seed sources
python -m app.cli init-db

# 4. Check your LLM provider
python -m app.cli test-provider

# 5. Run the vertical slice
python -m app.cli research      # fetch + rank real news
python -m app.cli generate      # generate drafts from top stories

# 6. Interfaces
uvicorn app.api.main:app --reload          # API at http://localhost:8000
streamlit run app/dashboard/Home.py        # dashboard
python -m app.cli run-bot                   # Telegram bot (if configured)
python -m app.cli run-scheduler             # scheduled research/publishing
```

## Documentation

See the [`docs/`](docs/) folder: installation, architecture, provider setup
(Foundry/Ollama), Telegram/X/LinkedIn setup, scheduling, security, migration off
Foundry, costs & limits, deployment and troubleshooting.

## Status / honesty notes

- Live publishing to X / LinkedIn requires your own developer credentials and the
  appropriate API access tier. Until those are supplied and authorized, the system
  uses **mock publishing** plus a **manual publishing fallback** (copyable text +
  official compose link). It never claims a post succeeded unless the API confirmed it.
- Hosted models, web-search APIs and X posting access are **not always free**. The
  app degrades gracefully around quotas and restricted access.

## License

MIT © Prince Kumar / AEVRIX
