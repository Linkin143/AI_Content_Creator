# Microsoft Foundry setup (temporary, optional provider)

> **Security boundary:** Do NOT use employer/company-provided Foundry credentials
> or company data for this personal project unless your employer explicitly
> authorizes it. Never copy corporate credentials or internal documents into this
> application or into `.env.example`.

Foundry is treated as a **temporary** inference provider. The application does
not depend on it for orchestration, hosting, scheduling, storage, Telegram,
publishing, auth or research. When Foundry access ends, switch `LLM_PROVIDER`
(see `MIGRATION_FROM_FOUNDRY.md`).

## Configure
In `.env`:
```
LLM_PROVIDER=foundry
FOUNDRY_PROJECT_ENDPOINT=https://<your-resource>.openai.azure.com/
FOUNDRY_MODEL_DEPLOYMENT=<your-deployment-name>
FOUNDRY_API_KEY=<key>
FOUNDRY_API_VERSION=2024-05-01-preview
```

- `FOUNDRY_MODEL_DEPLOYMENT` is your **deployment name**, not the base model name.
  Model names are never hardcoded — selection is config-only.
- You intend to use GPT-5.6 where available; **verify** the exact model is
  actually deployed to your account before relying on it. If not available, point
  the deployment at whatever model your account exposes.

## Verify
```
python -m app.cli test-provider
```
This performs a live health check and reports configured/reachable plus the
model's tool-calling and structured-output capability flags.

## Notes
- The adapter uses `AzureChatOpenAI` (via `langchain-openai`). Install with
  `pip install langchain-openai`.
- Capabilities differ per model; the app validates structured output and applies
  bounded retries, falling back to manual review if a model cannot comply.
