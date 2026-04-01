"""Tests for Google Gemini vision provider."""
from __future__ import annotations

import json
import os
from unittest import mock

import pytest

from naturo.providers.google_provider import GoogleVisionProvider


class TestGoogleProviderInit:
    """Tests for GoogleVisionProvider constructor."""

    def test_default_model(self) -> None:
        provider = GoogleVisionProvider()
        assert provider._model == "gemini-2.5-flash"

    def test_explicit_api_key(self) -> None:
        provider = GoogleVisionProvider(api_key="test-key-123")
        assert provider._api_key == "test-key-123"
        assert provider.is_available is True

    def test_env_api_key(self) -> None:
        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "env-key-456"}):
            provider = GoogleVisionProvider()
            assert provider._api_key == "env-key-456"
            assert provider.is_available is True

    def test_no_api_key(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            provider = GoogleVisionProvider()
            assert provider.is_available is False

    def test_explicit_model(self) -> None:
        provider = GoogleVisionProvider(model="gemini-2.5-pro")
        assert provider._model == "gemini-2.5-pro"

    def test_env_model(self) -> None:
        with mock.patch.dict(os.environ, {"NATURO_AI_MODEL": "gemini-2.0-flash"}):
            provider = GoogleVisionProvider()
            assert provider._model == "gemini-2.0-flash"

    def test_name(self) -> None:
        provider = GoogleVisionProvider()
        assert provider.name == "google"


class TestGoogleProviderRegistered:
    """Tests that the Google provider registers itself."""

    def test_registered_in_provider_registry(self) -> None:
        from naturo.providers.base import _PROVIDER_CLASSES, _ensure_providers_registered
        _ensure_providers_registered()
        assert "google" in _PROVIDER_CLASSES

    def test_get_vision_provider_recognizes_google(self) -> None:
        """get_vision_provider('google') should return GoogleVisionProvider
        when an API key is available."""
        from naturo.providers.base import get_vision_provider
        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            provider = get_vision_provider("google")
            assert provider.name == "google"


class TestGoogleProviderAutoDetection:
    """Tests that model-based auto-detection works for Google models."""

    def test_auto_detect_from_gemini_model(self) -> None:
        from naturo.providers.base import get_vision_provider
        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            provider = get_vision_provider("auto", model="gemini-2.5-pro")
            assert provider.name == "google"

    def test_auto_detect_from_gemini_alias(self) -> None:
        from naturo.providers.base import get_vision_provider
        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            provider = get_vision_provider("auto", model="gemini-pro")
            # gemini-pro resolves to gemini-2.5-pro, which infers google
            assert provider.name == "google"
