# Architecture

## Overview
A single Python repository with clear layers. No microservices, no Docker, no
Azure-specific services. SQLite is the single store; LangGraph orchestrates the
research→draft pipeline; FastAPI and Streamlit are the interfaces; APScheduler
runs recurring jobs; Telegram is the mobile approval channel.

```
            ┌──────────────┐     ┌───────────────┐    ┌──────────────┐
            │  Streamlit   │     │    FastAPI    │    │   Telegram   │
            │  dashboard   │     │  (REST+OAuth) │    │     bot      │
            └──────┬───────┘     └───────┬───────┘    └──────┬───────┘
                   │                     │                   │
                   └───────────┬─────────┴─────────┬─────────┘
                               ▼                   ▼
                     ┌───────────────────┐  ┌─────────────────┐
                     │  services/        │  │  agents/ (LangGraph)
                     │  approvals,       │  │  provider, graph, nodes
                     │  publishing,      │  └──────┬──────────┘
                     │  scheduling,      │         │
                     │  notifications    │         ▼
                     └─────────┬─────────┘   skills/ (SKILL.md + tools)
                               │                   │
                               ▼                   ▼
                     ┌───────────────────────────────────┐
                     │  database/ (SQLModel) + SQLite     │
                     └───────────────────────────────────┘
                               ▲
                     research/ (RSS, search, parser, dedup, ranking)
```

## Layers
- **app/config.py** — Pydantic Settings; every integration is optional.
- **app/agents/** — `provider.py` (portable LLM adapter), `state.py`, `nodes.py`
  (15 pipeline nodes), `graph.py` (typed StateGraph + SQLite checkpointer).
- **app/research/** — RSS/Atom + optional search discovery, canonicalization,
  deterministic deduplication and weighted ranking.
- **skills/** — 11 reusable instruction+tool packages. Only the relevant
  SKILL.md is loaded into a given node's prompt.
- **app/integrations/** — Telegram, X (OAuth2 PKCE), LinkedIn (OAuth2).
- **app/services/** — approvals state machine, publishing (idempotent, manual
  fallback), scheduling, analytics, notifications, encrypted social store.
- **app/database/** — 18 SQLModel tables, async session, migrations/seed, repos.
- **app/api/** — FastAPI routes (health, research, articles, drafts, OAuth,
  Telegram webhook, settings) with API-key auth.
- **app/dashboard/** — 11-page Streamlit admin UI.

## Pipeline (LangGraph)
`discover_news → deduplicate → filter_freshness → research → verify → rank →
technical_analysis → select → generate_x → generate_linkedin → quality_check →
persist → send_telegram_review`, with conditional short-circuits (no articles /
no fresh / nothing selected) and per-node error capture.

Approval + publishing is a **separate** authorization-controlled workflow so a
long graph is never suspended for hours waiting on a human.

## Portability
The LangGraph workflow, prompts, skills and DB schema are provider-independent.
Switching providers is a single `.env` change (`LLM_PROVIDER`). No critical
state is stored in Foundry.

## Upgrade path
SQLite is correct for a single-instance personal deployment. If concurrency or
scale grows, move `DATABASE_URL` to PostgreSQL and swap the LangGraph
checkpointer; node/service code is unchanged.
