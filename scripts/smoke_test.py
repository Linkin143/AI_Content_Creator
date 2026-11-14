"""Import smoke test: verifies every project module imports cleanly.

Usage:  python scripts/smoke_test.py
Exits non-zero if any module fails to import.
"""

import importlib

MODULES = [
    "app.config",
    "app.security.encryption",
    "app.security.sanitization",
    "app.security.signing",
    "app.database.models",
    "app.database.session",
    "app.database.repositories",
    "app.database.migrations",
    "app.research.sources_seed",
    "app.research.parser",
    "app.research.rss",
    "app.research.deduplicate",
    "app.research.ranking",
    "app.research.search",
    "app.agents.provider",
    "app.agents.state",
    "app.agents.llm_helpers",
    "app.agents.nodes",
    "app.agents.graph",
    "app.schemas.content",
    "app.integrations.x_api",
    "app.integrations.linkedin",
    "app.services.approvals",
    "app.services.generation",
    "app.services.publishing",
    "app.services.social_store",
    "app.services.analytics",
    "app.services.notifications",
    "app.services.scheduling",
    "skills",
    "skills.x_content.tools",
    "skills.fact_verification.tools",
    "skills.social_publishing.tools",
]

errors = []
for m in MODULES:
    try:
        importlib.import_module(m)
        print(f"ok   {m}")
    except Exception as e:  # noqa: BLE001
        errors.append((m, repr(e)))
        print(f"FAIL {m}: {e!r}")

if errors:
    print(f"\n{len(errors)} module(s) failed to import.")
    raise SystemExit(1)
print("\nALL_MODULES_OK")
