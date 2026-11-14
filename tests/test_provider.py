"""Tests for the portable LLM provider adapter and Foundry->fallback switching."""

import pytest

from app.agents.provider import (
    CAPABILITIES,
    NoProviderError,
    get_llm,
    health_check,
)
from app.config import LLMProvider, Settings


def _settings(**over) -> Settings:
    base = dict(
        llm_provider=LLMProvider.OLLAMA,
        ollama_base_url="http://localhost:11434",
        app_encryption_key="x",
    )
    base.update(over)
    return Settings(**base)


def test_capability_matrix_present():
    for provider in LLMProvider:
        assert provider in CAPABILITIES


def test_no_provider_raises_when_nothing_configured():
    s = _settings(llm_provider=LLMProvider.FOUNDRY, ollama_base_url="",
                  foundry_project_endpoint="", foundry_api_key="")
    with pytest.raises(NoProviderError):
        get_llm(s, allow_fallback=True)


def test_provider_configured_checks():
    s = _settings(llm_provider=LLMProvider.GEMINI, gemini_api_key="abc")
    assert s.provider_configured(LLMProvider.GEMINI) is True
    assert s.provider_configured(LLMProvider.GROQ) is False


async def test_health_check_unconfigured_foundry():
    s = _settings(llm_provider=LLMProvider.FOUNDRY, foundry_project_endpoint="",
                  foundry_api_key="")
    rep = await health_check(s)
    assert rep.provider == "foundry"
    assert rep.configured is False
    assert rep.reachable is False


async def test_foundry_to_ollama_fallback(monkeypatch):
    """When Foundry is primary but unconfigured, fallback should try others."""
    # Foundry unconfigured, Ollama configured -> get_llm should attempt Ollama.
    s = _settings(llm_provider=LLMProvider.FOUNDRY,
                  foundry_project_endpoint="", foundry_api_key="",
                  ollama_base_url="http://localhost:11434")

    built = {}

    def fake_build(provider, settings):
        built["provider"] = provider
        return object()

    monkeypatch.setattr("app.agents.provider.build_llm", fake_build)
    llm = get_llm(s, allow_fallback=True)
    assert llm is not None
    assert built["provider"] == LLMProvider.OLLAMA


def test_resolved_model_prefers_explicit():
    s = _settings(llm_model="custom-model")
    assert s.resolved_model == "custom-model"
