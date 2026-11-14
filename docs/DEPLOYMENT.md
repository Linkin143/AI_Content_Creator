# Deployment

The application is designed to run locally or on a small, personally controlled
host with persistent storage. No Docker or Kubernetes in v1.

## Recommended: reliable local machine / mini-PC
Run these processes (each in its own terminal or as a service):
```
uvicorn app.api.main:app --host 0.0.0.0 --port 8000   # API + OAuth callbacks
streamlit run app/dashboard/Home.py                   # dashboard (port 8501)
python -m app.cli run-bot                              # Telegram bot
python -m app.cli run-scheduler                        # recurring jobs
```

## Persistent storage
- Keep `data/aevrix.db` on durable local disk or a persistent host volume.
- Do NOT rely on ephemeral free hosts or CI runners to preserve SQLite between
  executions.
- Back up `data/aevrix.db` regularly (simple file copy; stop writers first or copy
  the WAL files too).

## Optional free-tier hosting
Only use a free host if its real limits fit: persistent disk, always-on process,
and outbound HTTPS. A host that sleeps or wipes storage will lose state — a
reliable local deployment is preferable.

## Keeping processes alive (Windows)
Use Task Scheduler to start the scheduler/bot at login, or run them under a
process supervisor. On Linux, use `systemd` units.

## Scaling up
If you outgrow a single instance, set `DATABASE_URL` to PostgreSQL and switch the
LangGraph checkpointer accordingly. Application logic is unchanged.

## Health checks
- `GET /health` reports DB/LLM/integration status.
- `python -m app.cli test-provider` checks the LLM provider.
- Dashboard → Logs & Health shows provider health and recent logs.
