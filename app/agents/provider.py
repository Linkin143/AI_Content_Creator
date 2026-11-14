"""Portable LLM provider adapter.

Switching providers requires only changing LLM_PROVIDER (and the matching
credentials) in the environment - no agent/graph code changes. Provider client
libraries are imported lazily so the app installs and runs even when a given
provider's optional package is absent.

If no provider is available, get_llm() raises NoProviderError and the rest of
the system (research, storage, manual drafting, approvals, export) keeps
working with AI generation disabled.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import LLMProvider, Settings, get_settings


class NoProviderError(RuntimeError):
    """Raised when no usable LLM provider is configured/available."""


class ProviderImportError(RuntimeError):
    """Raised when the optional client package for a provider is missing."""


@dataclass
class HealthReport:
    provider: str
    model: str
    configured: bool
    reachable: bool
    supports_tools: bool
    supports_structured_output: bool
    detail: str = ""


# Capability matrix - conservative defaults. Never assume parity across models.
CAPABILITIES: dict[LLMProvider, dict[str, bool]] = {
    LLMProvider.FOUNDRY: {"tools": True, "structured_output": True},
    LLMProvider.OLLAMA: {"tools": True, "structured_output": False},
    LLMProvider.OPENAI_COMPATIBLE: {"tools": True, "structured_output": True},
    LLMProvider.GEMINI: {"tools": True, "structured_output": True},
    LLMProvider.GROQ: {"tools": True, "structured_output": True},
}


def _build_foundry(settings: Settings):
    """Build a chat model for Azure Foundry / Azure OpenAI.

    Supports BOTH endpoint styles:
      * New v1 / OpenAI-compatible surface - endpoint ends in '/openai/v1'
        (e.g. https://<res>.openai.azure.com/openai/v1). Uses ChatOpenAI with
        base_url, which speaks the standard OpenAI protocol and avoids classic
        Azure deployment-path construction.
      * Classic Azure endpoint (e.g. https://<res>.openai.azure.com/) - uses
        AzureChatOpenAI with api_version + azure_deployment.
    """
    endpoint = (settings.foundry_project_endpoint or "").rstrip("/")
    is_v1 = endpoint.endswith("/openai/v1") or endpoint.endswith("/v1")

    # GPT-5.x / reasoning models reject a custom temperature (only the default is
    # allowed). Omit temperature for those to avoid a 400 error.
    model_name = (settings.resolved_model or "").lower()
    omit_temperature = model_name.startswith(("gpt-5", "o1", "o3", "o4"))
    extra = {} if omit_temperature else {"temperature": 0.4}

    if is_v1:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:  # pragma: no cover
            raise ProviderImportError(
                "Install provider extras: pip install langchain-openai"
            ) from exc
        # Azure's v1 surface accepts the resource key via the 'api-key' header.
        return ChatOpenAI(
            base_url=endpoint + "/",
            api_key=settings.foundry_api_key,
            model=settings.resolved_model,
            default_headers={"api-key": settings.foundry_api_key},
            **extra,
        )

    try:
        from langchain_openai import AzureChatOpenAI
    except ImportError as exc:  # pragma: no cover
        raise ProviderImportError(
            "Install provider extras: pip install langchain-openai"
        ) from exc
    return AzureChatOpenAI(
        azure_endpoint=endpoint,
        api_key=settings.foundry_api_key,
        azure_deployment=settings.resolved_model,
        api_version=settings.foundry_api_version,
        **extra,
    )


def _build_ollama(settings: Settings):
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:  # pragma: no cover
        raise ProviderImportError(
            "Install provider extras: pip install -e '.[providers]' (langchain-ollama)"
        ) from exc
    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.resolved_model or "llama3.1",
        temperature=0.4,
    )


def _build_openai_compatible(settings: Settings):
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover
        raise ProviderImportError(
            "Install provider extras: pip install -e '.[providers]' (langchain-openai)"
        ) from exc
    return ChatOpenAI(
        base_url=settings.openai_compatible_base_url,
        api_key=settings.openai_compatible_api_key or "not-needed",
        model=settings.resolved_model,
        temperature=0.4,
    )


def _build_gemini(settings: Settings):
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:  # pragma: no cover
        raise ProviderImportError(
            "Install provider extras: pip install -e '.[providers]' (langchain-google-genai)"
        ) from exc
    return ChatGoogleGenerativeAI(
        google_api_key=settings.gemini_api_key,
        model=settings.resolved_model or "gemini-1.5-flash",
        temperature=0.4,
    )


def _build_groq(settings: Settings):
    try:
        from langchain_groq import ChatGroq
    except ImportError as exc:  # pragma: no cover
        raise ProviderImportError(
            "Install provider extras: pip install -e '.[providers]' (langchain-groq)"
        ) from exc
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.resolved_model or "llama-3.1-8b-instant",
        temperature=0.4,
    )


_BUILDERS = {
    LLMProvider.FOUNDRY: _build_foundry,
    LLMProvider.OLLAMA: _build_ollama,
    LLMProvider.OPENAI_COMPATIBLE: _build_openai_compatible,
    LLMProvider.GEMINI: _build_gemini,
    LLMProvider.GROQ: _build_groq,
}

# Order in which to attempt fallback providers.
FALLBACK_ORDER = [
    LLMProvider.FOUNDRY,
    LLMProvider.GROQ,
    LLMProvider.GEMINI,
    LLMProvider.OPENAI_COMPATIBLE,
    LLMProvider.OLLAMA,
]


def build_llm(provider: LLMProvider, settings: Settings | None = None):
    """Build a chat model for a specific provider."""
    settings = settings or get_settings()
    builder = _BUILDERS.get(provider)
    if builder is None:
        raise NoProviderError(f"Unknown provider: {provider}")
    return builder(settings)


def get_llm(settings: Settings | None = None, allow_fallback: bool = True):
    """Return a chat model for the configured provider, with optional fallback.

    Raises NoProviderError if nothing is configured.
    """
    settings = settings or get_settings()
    primary = settings.llm_provider

    candidates = [primary]
    if allow_fallback:
        candidates += [p for p in FALLBACK_ORDER if p != primary]

    errors: list[str] = []
    for provider in candidates:
        if not settings.provider_configured(provider):
            continue
        try:
            return build_llm(provider, settings)
        except ProviderImportError as exc:
            errors.append(f"{provider.value}: {exc}")
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"{provider.value}: {exc}")

    detail = "; ".join(errors) if errors else "no provider has required configuration"
    raise NoProviderError(
        f"No usable LLM provider available ({detail}). "
        "Research, storage, manual drafting and approvals remain available."
    )


async def health_check(settings: Settings | None = None) -> HealthReport:
    """Check whether the active provider is configured and reachable."""
    settings = settings or get_settings()
    provider = settings.llm_provider
    caps = CAPABILITIES.get(provider, {"tools": False, "structured_output": False})
    configured = settings.provider_configured(provider)
    report = HealthReport(
        provider=provider.value,
        model=settings.resolved_model,
        configured=configured,
        reachable=False,
        supports_tools=caps["tools"],
        supports_structured_output=caps["structured_output"],
    )
    if not configured:
        report.detail = "provider not configured (missing credentials/endpoint)"
        return report
    try:
        llm = build_llm(provider, settings)
        resp = await llm.ainvoke("Reply with the single word: OK")
        text = getattr(resp, "content", str(resp))
        report.reachable = True
        report.detail = f"response: {str(text)[:60]}"
    except ProviderImportError as exc:
        report.detail = str(exc)
    except Exception as exc:
        report.detail = f"unreachable: {type(exc).__name__}: {exc}"
    return report
