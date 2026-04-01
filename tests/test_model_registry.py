"""Tests for naturo.providers.model_registry — centralized model definitions."""
from __future__ import annotations

import pytest

from naturo.providers.model_registry import (
    ModelInfo,
    get_default_model,
    get_model_info,
    list_aliases,
    list_models,
    resolve_model,
)


# ---------------------------------------------------------------------------
# resolve_model
# ---------------------------------------------------------------------------

class TestResolveModel:
    """Alias resolution returns canonical API model IDs."""

    # ── Anthropic aliases ──

    def test_opus_4_6(self) -> None:
        assert resolve_model("opus-4.6") == "claude-opus-4-6"

    def test_opus_4_6_alt(self) -> None:
        assert resolve_model("opus-4-6") == "claude-opus-4-6"

    def test_opus_short(self) -> None:
        assert resolve_model("opus") == "claude-opus-4-6"

    def test_sonnet(self) -> None:
        assert resolve_model("sonnet") == "claude-sonnet-4-20250514"

    def test_sonnet_4(self) -> None:
        assert resolve_model("sonnet-4") == "claude-sonnet-4-20250514"

    def test_haiku(self) -> None:
        assert resolve_model("haiku") == "claude-haiku-4-5-20251001"

    def test_haiku_4_5(self) -> None:
        assert resolve_model("haiku-4.5") == "claude-haiku-4-5-20251001"

    # ── OpenAI aliases ──

    def test_4o(self) -> None:
        assert resolve_model("4o") == "gpt-4o"

    def test_4o_mini(self) -> None:
        assert resolve_model("4o-mini") == "gpt-4o-mini"

    def test_4_turbo(self) -> None:
        assert resolve_model("4-turbo") == "gpt-4-turbo"

    # ── Google Gemini aliases ──

    def test_gemini_pro(self) -> None:
        assert resolve_model("gemini-pro") == "gemini-2.5-pro"

    def test_gemini_short(self) -> None:
        assert resolve_model("gemini") == "gemini-2.5-pro"

    def test_gemini_flash(self) -> None:
        assert resolve_model("gemini-flash") == "gemini-2.5-flash"

    # ── Ollama aliases ──

    def test_llava(self) -> None:
        assert resolve_model("llava") == "llava"

    def test_llava_13b(self) -> None:
        assert resolve_model("llava-13b") == "llava:13b"

    # ── Canonical IDs pass through ──

    def test_canonical_passthrough(self) -> None:
        assert resolve_model("claude-opus-4-6") == "claude-opus-4-6"

    def test_canonical_passthrough_openai(self) -> None:
        assert resolve_model("gpt-4o") == "gpt-4o"

    def test_canonical_passthrough_gemini(self) -> None:
        assert resolve_model("gemini-2.5-pro") == "gemini-2.5-pro"

    # ── Unknown models pass through unchanged ──

    def test_unknown_passthrough(self) -> None:
        assert resolve_model("my-custom-finetune-v3") == "my-custom-finetune-v3"

    # ── Case insensitivity ──

    def test_case_insensitive(self) -> None:
        assert resolve_model("Opus-4.6") == "claude-opus-4-6"

    def test_case_insensitive_sonnet(self) -> None:
        assert resolve_model("SONNET") == "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# get_default_model
# ---------------------------------------------------------------------------

class TestGetDefaultModel:
    """Default model selection per provider and use-case."""

    def test_anthropic_vision_default_is_opus(self) -> None:
        assert get_default_model("anthropic", "vision") == "claude-opus-4-6"

    def test_anthropic_agent_default_is_sonnet(self) -> None:
        assert get_default_model("anthropic", "agent") == "claude-sonnet-4-20250514"

    def test_openai_vision(self) -> None:
        assert get_default_model("openai", "vision") == "gpt-4o"

    def test_openai_agent(self) -> None:
        assert get_default_model("openai", "agent") == "gpt-4o"

    def test_google_vision(self) -> None:
        assert get_default_model("google", "vision") == "gemini-2.5-pro"

    def test_ollama_vision(self) -> None:
        assert get_default_model("ollama", "vision") == "llava"

    def test_unknown_provider_returns_empty(self) -> None:
        assert get_default_model("nonexistent", "vision") == ""


# ---------------------------------------------------------------------------
# get_model_info
# ---------------------------------------------------------------------------

class TestGetModelInfo:
    """Metadata lookup by name or alias."""

    def test_by_canonical_id(self) -> None:
        info = get_model_info("claude-opus-4-6")
        assert info is not None
        assert info.provider == "anthropic"
        assert "vision" in info.capabilities
        assert "agent" in info.capabilities

    def test_by_alias(self) -> None:
        info = get_model_info("opus-4.6")
        assert info is not None
        assert info.canonical_id == "claude-opus-4-6"

    def test_unknown_returns_none(self) -> None:
        assert get_model_info("totally-unknown-model") is None

    def test_gemini_info(self) -> None:
        info = get_model_info("gemini-pro")
        assert info is not None
        assert info.provider == "google"
        assert info.canonical_id == "gemini-2.5-pro"


# ---------------------------------------------------------------------------
# list_models
# ---------------------------------------------------------------------------

class TestListModels:
    """Model listing with optional filters."""

    def test_all_models(self) -> None:
        models = list_models()
        assert len(models) >= 10
        providers = {m.provider for m in models}
        assert "anthropic" in providers
        assert "openai" in providers
        assert "google" in providers
        assert "ollama" in providers

    def test_filter_by_provider(self) -> None:
        models = list_models(provider="anthropic")
        assert all(m.provider == "anthropic" for m in models)
        assert len(models) == 3

    def test_filter_by_capability(self) -> None:
        models = list_models(capability="agent")
        assert all("agent" in m.capabilities for m in models)

    def test_filter_both(self) -> None:
        models = list_models(provider="openai", capability="vision")
        assert all(m.provider == "openai" for m in models)
        assert all("vision" in m.capabilities for m in models)

    def test_empty_provider(self) -> None:
        models = list_models(provider="nonexistent")
        assert models == []


# ---------------------------------------------------------------------------
# list_aliases
# ---------------------------------------------------------------------------

class TestListAliases:
    """Alias map includes all registered aliases and canonical IDs."""

    def test_contains_friendly_names(self) -> None:
        aliases = list_aliases()
        assert "opus-4.6" in aliases
        assert "sonnet" in aliases
        assert "haiku" in aliases
        assert "4o" in aliases
        assert "gemini" in aliases

    def test_contains_canonical_ids(self) -> None:
        aliases = list_aliases()
        assert "claude-opus-4-6" in aliases
        assert "gpt-4o" in aliases

    def test_alias_values_are_canonical(self) -> None:
        aliases = list_aliases()
        for alias, canonical in aliases.items():
            info = get_model_info(canonical)
            assert info is not None, f"Alias {alias!r} → {canonical!r} has no model info"
            assert info.canonical_id == canonical


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case handling for empty/None inputs."""

    def test_resolve_model_empty_string(self) -> None:
        assert resolve_model("") == ""

    def test_get_default_model_empty_provider(self) -> None:
        assert get_default_model("") == ""

    def test_get_default_model_unknown_provider(self) -> None:
        assert get_default_model("nonexistent-provider") == ""

    def test_list_models_empty_provider_returns_all(self) -> None:
        # Empty string is falsy, same as None — returns all models
        all_models = list_models()
        result = list_models(provider="")
        assert result == all_models

    def test_list_models_unknown_capability(self) -> None:
        result = list_models(capability="nonexistent")
        assert result == []


# ---------------------------------------------------------------------------
# ModelInfo frozen dataclass
# ---------------------------------------------------------------------------

class TestModelInfo:
    """ModelInfo is immutable."""

    def test_frozen(self) -> None:
        info = get_model_info("opus-4.6")
        assert info is not None
        with pytest.raises(AttributeError):
            info.canonical_id = "something-else"  # type: ignore[misc]
