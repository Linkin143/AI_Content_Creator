# Migration from Foundry

The project is designed to survive the loss of Foundry access. Switching
providers is a single configuration change — the LangGraph workflow, prompts,
skills and database formats are provider-independent.

## Switch provider
Edit `.env` and set `LLM_PROVIDER` to one of:
```
LLM_PROVIDER=ollama              # local, free (recommended long-term)
LLM_PROVIDER=gemini
LLM_PROVIDER=groq
LLM_PROVIDER=openai_compatible   # Together, LM Studio, vLLM, etc.
```
Add the matching credentials/model for that provider (see `.env.example`), then:
```
python -m app.cli test-provider
python -m app.cli research
```
No agent or graph code changes are required.

## Fallback chain
If the primary provider is unconfigured/unavailable, `get_llm()` automatically
tries the other configured providers (order:
foundry → groq → gemini → openai_compatible → ollama).

## Smoke test
`tests/test_e2e_pipeline.py::test_pipeline_without_llm` proves the system keeps
working (fetch, store, dedup, rank) with **no** provider, and
`test_pipeline_with_mock_llm` proves drafting works with any provider.
`tests/test_provider.py::test_foundry_to_ollama_fallback` proves the Foundry→
Ollama switch.

## Export your data (provider-independent)
The database holds all portable state: articles, drafts, publishing history,
brand profile, editorial feedback and settings (secrets excluded). Back up
`data/aevrix.db` to migrate. No critical state is stored inside Foundry.

## After Foundry expires
1. Set `LLM_PROVIDER=ollama` (or another provider).
2. Remove the Foundry credentials from `.env`.
3. Run `test-provider` and a `research` run to confirm.
Nothing else changes.
