# Troubleshooting

## `APP_ENCRYPTION_KEY is not set`
Generate one and put it in `.env`:
```
python -m app.cli gen-key
```

## `test-provider` shows reachable=False
- **Ollama**: ensure the Ollama service is running and `pip install langchain-ollama`.
- **Foundry/Gemini/Groq/OpenAI-compatible**: install the matching client
  (`langchain-openai` / `langchain-google-genai` / `langchain-groq`) and verify
  credentials and the exact model/deployment name.
- The app still runs in research-only mode without a provider.

## `research` returns 0 articles
- Check internet connectivity.
- Some feeds may be temporarily down — this is expected and non-fatal; failing
  sources are recorded in `sources.last_error` and skipped.
- Widen the window: `python -m app.cli research --window 72`.

## No drafts generated
- Drafts require a working LLM provider. Run `test-provider`.
- Without AI, articles are still fetched, deduplicated, ranked and stored.

## `database is locked`
- Only run one writer at a time for scheduled jobs. WAL mode is enabled to reduce
  contention. Avoid multiple `run-scheduler` instances on the same DB.

## Telegram bot does nothing
- Confirm `TELEGRAM_BOT_TOKEN` and that your numeric ID is in
  `TELEGRAM_ALLOWED_USER_IDS`.
- Do not run polling and webhook mode simultaneously.

## OAuth callback fails with "invalid or expired state"
- The signed state is valid for 10 minutes; restart the connect flow.
- Ensure the redirect URI in your developer app exactly matches `.env`.

## Publishing says FAILED / permission denied
- Your API tier may not permit posting. Use the manual fallback (copyable text +
  compose link) and mark as manually published. See `X_API_SETUP.md` /
  `LINKEDIN_API_SETUP.md`.

## Tests
```
python -m pytest -q          # all tests, external APIs mocked
ruff check app skills tests  # lint
```
