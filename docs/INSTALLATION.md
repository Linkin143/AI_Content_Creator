# Installation

## Prerequisites
- Python 3.11+ (tested on 3.13)
- Windows, macOS or Linux
- Optional: [`uv`](https://docs.astral.sh/uv/) for fast installs
- Optional: [Ollama](https://ollama.com/) for a free local LLM

## Windows (recommended)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```
This creates `.venv`, installs dependencies, generates `APP_ENCRYPTION_KEY`,
copies `.env.example` to `.env`, and runs `init-db`.

## Manual (any OS)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |  macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # copy on Windows: copy .env.example .env
python -m app.cli gen-key       # paste into APP_ENCRYPTION_KEY in .env
python -m app.cli init-db
```

## Optional provider clients
Install only the providers you use:
```bash
pip install langchain-ollama          # local Ollama
pip install langchain-openai          # OpenAI-compatible + Azure/Foundry
pip install langchain-google-genai    # Gemini
pip install langchain-groq            # Groq
```

## Verify
```bash
python -m app.cli test-provider
python -m app.cli research
python -m pytest -q
```

## What works without any credentials
- News discovery from 20+ RSS/arXiv sources
- Deduplication, freshness filtering, deterministic ranking
- Article storage and browsing (CLI, API, dashboard)
- Approvals, scheduling state, mock publishing, export
AI drafting is disabled with a clear message until an LLM provider is configured.
