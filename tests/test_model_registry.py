"""Tests for model registry, alias resolution, and provider inference."""
from __future__ import annotations

import pytest

from naturo.config import (
    MODEL_ALIASES,
    MODEL_REGISTRY,
    infer_provider_from_model,
    resolve_model_alias,
)


class TestResolveModelAlias:
    """Tests for resolve_model_alias()."""

    def test_known_alias(self) -> None:
        assert resolve_model_alias("opus") == "claude-opus-4-6"

    def test_known_alias_sonnet(self) -> None:
        assert resolve_model_alias("sonnet") == "claude-sonnet-4-20250514"

    def test_known_alias_haiku(self) -> None:
        assert resolve_model_alias("haiku") == "claude-haiku-4-5-20251001"

    def test_known_alias_gpt4o(self) -> None:
        assert resolve_model_alias("gpt4o") == "gpt-4o"

    def test_known_alias_gemini_pro(self) -> None:
        assert resolve_model_alias("gemini-pro") == "gemini-2.5-pro"

    def test_unknown_model_returned_as_is(self) -> None:
        assert resolve_model_alias("my-custom-model") == "my-custom-model"

    def test_canonical_id_returned_as_is(self) -> None:
        assert resolve_model_alias("claude-opus-4-6") == "claude-opus-4-6"

    def test_all_aliases_resolve_to_registry_entries(self) -> None:
        for alias, canonical in MODEL_ALIASES.items():
            assert canonical in MODEL_REGISTRY, (
                f"Alias '{alias}' resolves to '{canonical}' which is not in MODEL_REGISTRY"
            )


class TestInferProviderFromModel:
    """Tests for infer_provider_from_model()."""

    def test_anthropic_canonical(self) -> None:
        assert infer_provider_from_model("claude-opus-4-6") == "anthropic"

    def test_anthropic_alias(self) -> None:
        assert infer_provider_from_model("opus") == "anthropic"

    def test_openai_canonical(self) -> None:
        assert infer_provider_from_model("gpt-4o") == "openai"

    def test_openai_alias(self) -> None:
        assert infer_provider_from_model("gpt4o") == "openai"

    def test_google_canonical(self) -> None:
        assert infer_provider_from_model("gemini-2.5-pro") == "google"

    def test_google_alias(self) -> None:
        assert infer_provider_from_model("gemini-pro") == "google"

    def test_ollama_canonical(self) -> None:
        assert infer_provider_from_model("llava") == "ollama"

    def test_prefix_fallback_anthropic(self) -> None:
        assert infer_provider_from_model("claude-future-model") == "anthropic"

    def test_prefix_fallback_openai(self) -> None:
        assert infer_provider_from_model("gpt-5-ultra") == "openai"

    def test_prefix_fallback_google(self) -> None:
        assert infer_provider_from_model("gemini-3.0-ultra") == "google"

    def test_prefix_fallback_openai_o_series(self) -> None:
        assert infer_provider_from_model("o4-mini") == "openai"

    def test_unknown_returns_none(self) -> None:
        assert infer_provider_from_model("totally-unknown-model") is None

    def test_all_registry_entries_infer_correctly(self) -> None:
        for model_id, info in MODEL_REGISTRY.items():
            result = infer_provider_from_model(model_id)
            assert result == info["provider"], (
                f"Model '{model_id}' should infer to '{info['provider']}' but got '{result}'"
            )


class TestModelRegistry:
    """Tests for MODEL_REGISTRY structure."""

    def test_registry_not_empty(self) -> None:
        assert len(MODEL_REGISTRY) > 0

    def test_all_entries_have_required_keys(self) -> None:
        for model_id, info in MODEL_REGISTRY.items():
            assert "provider" in info, f"Model '{model_id}' missing 'provider'"
            assert "display" in info, f"Model '{model_id}' missing 'display'"

    def test_providers_are_valid(self) -> None:
        valid_providers = {"anthropic", "openai", "google", "ollama"}
        for model_id, info in MODEL_REGISTRY.items():
            assert info["provider"] in valid_providers, (
                f"Model '{model_id}' has unknown provider '{info['provider']}'"
            )
