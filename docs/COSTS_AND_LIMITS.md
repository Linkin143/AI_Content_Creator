# Costs and limits

## Honest cost notes
- Hosted LLMs, web-search APIs, hosting and X posting access are **not always
  free**. This app prioritizes free/open-source options but does not pretend paid
  services are free.
- The app degrades gracefully around quotas, restricted access and unavailable
  services, and warns when limits are exceeded. It never invents billing data.

## Free vs paid at a glance
| Capability | Free option | Paid/limited |
|---|---|---|
| News discovery | RSS/arXiv (20+ sources) | optional search APIs |
| LLM inference | Ollama (local) | Foundry/Gemini/Groq/OpenAI-compat tiers |
| Telegram | free | — |
| X posting | — | requires write-capable API tier |
| LinkedIn posting | — | requires approved `w_member_social` |

## Configurable limits (`.env`)
```
MAX_ARTICLES_PER_RUN=60
MAX_LLM_CALLS_PER_RUN=50
MAX_X_POSTS_PER_DAY=5
MAX_LINKEDIN_POSTS_PER_DAY=4
MAX_LINKEDIN_POSTS_PER_WEEK=4
RESEARCH_WINDOW_HOURS=24
DRAFT_RETENTION_DAYS=7
REQUIRE_HUMAN_APPROVAL=true
AUTO_PUBLISH=false
```

## Cost-control mechanisms
- Deterministic dedup and ranking run **before** any LLM call.
- LLM work is bounded by `MAX_LLM_CALLS_PER_RUN` and applied only to top stories.
- Articles are stored so identical stories are not re-analysed across runs.
- Token usage is tracked when a provider exposes it; unknown costs are never
  fabricated.
