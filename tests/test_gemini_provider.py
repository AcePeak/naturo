"""Tests for naturo.providers.gemini_provider — Google Gemini vision provider.

Covers: construction, auth resolution, model aliases, describe_screenshot,
identify_element, enumerate_elements, error paths, response parsing.
"""
from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from naturo.errors import AIAnalysisFailedError, AIProviderUnavailableError
from naturo.providers.gemini_provider import (
    GeminiVisionProvider,
    _MODEL_ALIASES,
    _resolve_api_key,
    _resolve_model,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("NATURO_AI_MODEL", raising=False)


@pytest.fixture()
def fake_image(tmp_path: Path) -> str:
    """Create a minimal valid 1x1 PNG for testing."""
    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )
    raw = b"\x00\xff\x00\x00"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw))
        + _chunk(b"IEND", b"")
    )
    p = tmp_path / "test.png"
    p.write_bytes(png)
    return str(p)


def _gemini_response(
    text: str = "A description",
    prompt_tokens: int = 100,
    candidates_tokens: int = 50,
) -> dict[str, Any]:
    """Build a mock Gemini API JSON response."""
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": text}],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": prompt_tokens,
            "candidatesTokenCount": candidates_tokens,
        },
    }


# ---------------------------------------------------------------------------
# Auth resolution
# ---------------------------------------------------------------------------

class TestResolveApiKey:
    def test_explicit_key_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_API_KEY", "env-key")
        assert _resolve_api_key("explicit-key") == "explicit-key"

    def test_env_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_API_KEY", "env-key")
        assert _resolve_api_key() == "env-key"

    def test_credentials_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with patch(
            "naturo.providers.gemini_provider._load_credentials",
            return_value={"gemini": {"api_key": "cred-key"}},
        ):
            assert _resolve_api_key() == "cred-key"

    def test_no_key_returns_empty(self) -> None:
        with patch(
            "naturo.providers.gemini_provider._load_credentials",
            return_value={},
        ):
            assert _resolve_api_key() == ""


# ---------------------------------------------------------------------------
# Model resolution
# ---------------------------------------------------------------------------

class TestResolveModel:
    def test_explicit_model(self) -> None:
        assert _resolve_model("gemini-2.5-pro") == "gemini-2.5-pro"

    def test_alias_flash(self) -> None:
        assert _resolve_model("flash") == "gemini-2.5-flash"

    def test_alias_pro(self) -> None:
        assert _resolve_model("pro") == "gemini-2.5-pro"

    def test_alias_gemini_flash(self) -> None:
        assert _resolve_model("gemini-flash") == "gemini-2.5-flash"

    def test_alias_gemini_pro(self) -> None:
        assert _resolve_model("gemini-pro") == "gemini-2.5-pro"

    def test_env_var_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NATURO_AI_MODEL", "gemini-custom")
        assert _resolve_model(None) == "gemini-custom"

    def test_default_model(self) -> None:
        assert _resolve_model(None) == "gemini-2.5-flash"

    def test_all_aliases_resolve(self) -> None:
        for alias, canonical in _MODEL_ALIASES.items():
            assert _resolve_model(alias) == canonical


# ---------------------------------------------------------------------------
# Construction & properties
# ---------------------------------------------------------------------------

class TestGeminiProviderInit:
    def test_explicit_api_key(self) -> None:
        p = GeminiVisionProvider(api_key="test-key")
        assert p.name == "gemini"
        assert p.is_available is True

    def test_env_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_API_KEY", "env-key")
        p = GeminiVisionProvider()
        assert p.is_available is True

    def test_no_api_key(self) -> None:
        with patch(
            "naturo.providers.gemini_provider._load_credentials",
            return_value={},
        ):
            p = GeminiVisionProvider()
            assert p.is_available is False

    def test_default_model(self) -> None:
        p = GeminiVisionProvider(api_key="test-key")
        assert p._model == "gemini-2.5-flash"

    def test_custom_model(self) -> None:
        p = GeminiVisionProvider(api_key="test-key", model="gemini-2.5-pro")
        assert p._model == "gemini-2.5-pro"

    def test_model_alias(self) -> None:
        p = GeminiVisionProvider(api_key="test-key", model="pro")
        assert p._model == "gemini-2.5-pro"

    def test_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NATURO_AI_MODEL", "gemini-custom")
        p = GeminiVisionProvider(api_key="test-key")
        assert p._model == "gemini-custom"


# ---------------------------------------------------------------------------
# _parse_response
# ---------------------------------------------------------------------------

class TestParseResponse:
    def test_basic_response(self) -> None:
        p = GeminiVisionProvider(api_key="test-key")
        result = p._parse_response(_gemini_response("Hello world"))
        assert result.description == "Hello world"
        assert result.tokens_used == 150
        assert result.model == "gemini-2.5-flash"

    def test_multi_part_response(self) -> None:
        p = GeminiVisionProvider(api_key="test-key")
        data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Part 1"},
                            {"text": "Part 2"},
                        ],
                    }
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 20,
            },
        }
        result = p._parse_response(data)
        assert "Part 1" in result.description
        assert "Part 2" in result.description
        assert result.tokens_used == 30

    def test_no_candidates_raises(self) -> None:
        p = GeminiVisionProvider(api_key="test-key")
        with pytest.raises(AIAnalysisFailedError, match="no results"):
            p._parse_response({"candidates": []})

    def test_error_in_response(self) -> None:
        p = GeminiVisionProvider(api_key="test-key")
        with pytest.raises(AIAnalysisFailedError, match="quota exceeded"):
            p._parse_response({
                "candidates": [],
                "error": {"message": "quota exceeded"},
            })

    def test_missing_usage_metadata(self) -> None:
        p = GeminiVisionProvider(api_key="test-key")
        data = {
            "candidates": [
                {"content": {"parts": [{"text": "ok"}]}}
            ],
        }
        result = p._parse_response(data)
        assert result.tokens_used == 0


# ---------------------------------------------------------------------------
# describe_screenshot
# ---------------------------------------------------------------------------

class TestGeminiDescribeScreenshot:
    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_basic_describe(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        resp_data = json.dumps(_gemini_response("Notepad window")).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        p = GeminiVisionProvider(api_key="test-key")
        result = p.describe_screenshot(fake_image)

        assert result.description == "Notepad window"
        assert result.model == "gemini-2.5-flash"
        assert result.tokens_used == 150

    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_custom_prompt(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        resp_data = json.dumps(_gemini_response("buttons")).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        p = GeminiVisionProvider(api_key="test-key")
        p.describe_screenshot(fake_image, prompt="List buttons")

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        payload = json.loads(req.data.decode())
        text_part = payload["contents"][0]["parts"][1]["text"]
        assert "List buttons" in text_part

    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_context_prepended(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        resp_data = json.dumps(_gemini_response("r")).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        p = GeminiVisionProvider(api_key="test-key")
        p.describe_screenshot(fake_image, context="Calculator app")

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode())
        text_part = payload["contents"][0]["parts"][1]["text"]
        assert text_part.startswith("Context: Calculator app")

    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_max_tokens_passed(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        resp_data = json.dumps(_gemini_response()).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        p = GeminiVisionProvider(api_key="test-key")
        p.describe_screenshot(fake_image, max_tokens=2048)

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode())
        assert payload["generationConfig"]["maxOutputTokens"] == 2048

    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_image_inline_data(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        resp_data = json.dumps(_gemini_response()).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        p = GeminiVisionProvider(api_key="test-key")
        p.describe_screenshot(fake_image)

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode())
        inline_data = payload["contents"][0]["parts"][0]["inline_data"]
        assert inline_data["mime_type"] == "image/png"
        assert len(inline_data["data"]) > 0

    def test_unavailable_raises(self, fake_image: str) -> None:
        with patch(
            "naturo.providers.gemini_provider._load_credentials",
            return_value={},
        ):
            p = GeminiVisionProvider()
            with pytest.raises(AIProviderUnavailableError):
                p.describe_screenshot(fake_image)

    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_http_error(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        import urllib.error
        error = urllib.error.HTTPError(
            url="http://example.com", code=429,
            msg="Too Many Requests", hdrs=MagicMock(), fp=None,
        )
        mock_urlopen.side_effect = error

        p = GeminiVisionProvider(api_key="test-key")
        with pytest.raises(AIAnalysisFailedError, match="HTTP 429"):
            p.describe_screenshot(fake_image)

    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_url_error(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")

        p = GeminiVisionProvider(api_key="test-key")
        with pytest.raises(AIAnalysisFailedError, match="connection error"):
            p.describe_screenshot(fake_image)

    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_generic_error(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        mock_urlopen.side_effect = RuntimeError("unexpected")

        p = GeminiVisionProvider(api_key="test-key")
        with pytest.raises(AIAnalysisFailedError, match="unexpected"):
            p.describe_screenshot(fake_image)

    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_api_url_contains_model_and_key(
        self, mock_urlopen: MagicMock, fake_image: str
    ) -> None:
        resp_data = json.dumps(_gemini_response()).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        p = GeminiVisionProvider(api_key="my-secret-key", model="gemini-2.5-pro")
        p.describe_screenshot(fake_image)

        req = mock_urlopen.call_args[0][0]
        assert "gemini-2.5-pro" in req.full_url
        assert "key=my-secret-key" in req.full_url


# ---------------------------------------------------------------------------
# identify_element
# ---------------------------------------------------------------------------

class TestGeminiIdentifyElement:
    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_basic_identify(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        element_json = json.dumps({
            "found": True,
            "bounds": {"x": 50, "y": 75, "width": 80, "height": 30},
            "confidence": 0.95,
        })
        resp_data = json.dumps(_gemini_response(element_json)).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        p = GeminiVisionProvider(api_key="test-key")
        result = p.identify_element(fake_image, "OK button")
        assert len(result.elements) >= 1

    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_identify_no_json(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        resp_data = json.dumps(_gemini_response("I cannot find it")).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        p = GeminiVisionProvider(api_key="test-key")
        result = p.identify_element(fake_image, "missing element")
        assert result.elements == []

    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_identify_prompt_contains_description(
        self, mock_urlopen: MagicMock, fake_image: str
    ) -> None:
        resp_data = json.dumps(_gemini_response("{}")).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        p = GeminiVisionProvider(api_key="test-key")
        p.identify_element(fake_image, "Save button")

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode())
        text_part = payload["contents"][0]["parts"][1]["text"]
        assert "Save button" in text_part


# ---------------------------------------------------------------------------
# enumerate_elements
# ---------------------------------------------------------------------------

class TestGeminiEnumerateElements:
    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_enumerate(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        elements = [
            {"role": "Button", "name": "OK", "bounds": [10, 20, 50, 30]},
            {"role": "TextBox", "name": "Input", "bounds": [10, 60, 200, 30]},
        ]
        resp_data = json.dumps(_gemini_response(json.dumps(elements))).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        p = GeminiVisionProvider(api_key="test-key")
        result = p.enumerate_elements(fake_image, "List all UI elements")
        assert len(result.elements) == 2
        assert result.elements[0]["name"] == "OK"

    @patch("naturo.providers.gemini_provider.urllib.request.urlopen")
    def test_enumerate_passes_prompt_directly(
        self, mock_urlopen: MagicMock, fake_image: str
    ) -> None:
        resp_data = json.dumps(_gemini_response("[]")).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        p = GeminiVisionProvider(api_key="test-key")
        p.enumerate_elements(fake_image, "Custom enumeration prompt")

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode())
        text_part = payload["contents"][0]["parts"][1]["text"]
        assert text_part == "Custom enumeration prompt"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestGeminiRegistration:
    def test_registered_in_provider_registry(self) -> None:
        from naturo.providers.base import _PROVIDER_CLASSES, _ensure_providers_registered
        _ensure_providers_registered()
        assert "gemini" in _PROVIDER_CLASSES

    def test_get_vision_provider_gemini(self) -> None:
        from naturo.providers.base import get_vision_provider
        p = GeminiVisionProvider(api_key="test-key")
        with patch(
            "naturo.providers.gemini_provider.GeminiVisionProvider",
            return_value=p,
        ):
            # Direct instantiation test — provider is registered
            result = get_vision_provider("gemini", api_key="test-key")
            assert result.name == "gemini"
