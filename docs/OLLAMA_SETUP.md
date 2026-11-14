# Ollama setup (recommended free, local, long-term provider)

Ollama runs open-weight models locally — a strong long-term option after Foundry
access ends, with no per-call cost.

## Install
1. Download Ollama from <https://ollama.com/> and install.
2. Pull a model, for example:
   ```
   ollama pull llama3.1
   ```
3. Ensure the server is running (Ollama runs a local service on port 11434).

## Configure
In `.env`:
```
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```
Install the client: `pip install langchain-ollama`.

## Verify
```
python -m app.cli test-provider
```

## Capability note
Smaller local models may not reliably produce structured JSON. The app:
- tries native structured output,
- falls back to JSON parsing from text,
- validates against Pydantic schemas,
- applies bounded retries,
- and marks a story for manual review if output stays invalid —
it never accepts malformed content silently.

For better structured-output reliability, prefer instruct models and, if needed,
a larger variant (e.g. `llama3.1:8b-instruct` or similar available on your host).
