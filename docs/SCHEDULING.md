# Scheduling

Uses APScheduler in-process (`AsyncIOScheduler`) for a single-instance local
deployment. Timezone defaults to **Asia/Kolkata**.

## Jobs
- **Daily research** at 08:00 IST → runs the pipeline → generates drafts →
  sends Telegram previews.
- **Due publications** every 5 minutes → publishes scheduled, approved drafts
  (only when `AUTO_PUBLISH=true` and outside quiet hours).

## Run
```
python -m app.cli run-scheduler
```

## Behaviour
- Quiet hours (default 22:00–07:00 IST) suppress auto-publishing.
- Missed jobs have a grace window (`misfire_grace_time`).
- Publishing requires approval; unapproved drafts are never auto-published.
- Manual runs: `python -m app.cli research`.

## Single-instance rule
Do not run multiple schedulers against the same database. For a machine without
continuous uptime, consider the optional GitHub Actions workflow
(`.github/workflows/scheduled-research.yml`) — but note:

- GitHub Actions cron is **best-effort**, not guaranteed to run on time.
- A GitHub runner **cannot** read a SQLite file that lives only on your laptop.
  Use durable external storage (e.g. hosted Postgres) if you rely on it.

A reliable local PC / mini-PC running `run-scheduler` is the recommended setup.
