"""Tests for naturo.providers.openai_provider — OpenAI/GPT-4 vision provider.

Covers: construction, base_url, describe_screenshot, identify_element, error paths.
"""
from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from naturo.errors import AIAnalysisFailedError, AIProviderUnavailableError
from naturo.providers.openai_provider import OpenAIVisionProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("NATURO_AI_MODEL", raising=False)


@pytest.fixture()
def fake_image(tmp_path: Path) -> str:
    def _chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"\x00\xff\x00\x00"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw)) + _chunk(b"IEND", b"")
    p = tmp_path / "test.png"
    p.write_bytes(png)
    return str(p)


def _mock_openai_response(text: str = "A description", prompt_tokens: int = 100, completion_tokens: int = 50) -> MagicMock:
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = MagicMock(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return resp


# ---------------------------------------------------------------------------
# Construction & properties
# ---------------------------------------------------------------------------

class TestOpenAIProviderInit:
    def test_explicit_api_key(self) -> None:
        p = OpenAIVisionProvider(api_key="sk-test")
        assert p.name == "openai"
        assert p.is_available is True

    def test_env_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
        p = OpenAIVisionProvider()
        assert p.is_available is True

    def test_no_api_key(self) -> None:
        p = OpenAIVisionProvider()
        assert p.is_available is False

    def test_default_model(self) -> None:
        p = OpenAIVisionProvider(api_key="sk-test")
        assert p._model == "gpt-4o"

    def test_custom_model(self) -> None:
        p = OpenAIVisionProvider(api_key="sk-test", model="gpt-4-turbo")
        assert p._model == "gpt-4-turbo"

    def test_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NATURO_AI_MODEL", "gpt-4o-mini")
        p = OpenAIVisionProvider(api_key="sk-test")
        assert p._model == "gpt-4o-mini"

    def test_base_url_explicit(self) -> None:
        p = OpenAIVisionProvider(api_key="sk-test", base_url="http://localhost:8080")
        assert p._base_url == "http://localhost:8080"

    def test_base_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_BASE_URL", "http://azure.example.com")
        p = OpenAIVisionProvider(api_key="sk-test")
        assert p._base_url == "http://azure.example.com"


# ---------------------------------------------------------------------------
# _get_client
# ---------------------------------------------------------------------------

class TestOpenAIGetClient:
    def test_basic_client(self) -> None:
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            p = OpenAIVisionProvider(api_key="sk-test")
            p._get_client()
            mock_openai.OpenAI.assert_called_once_with(api_key="sk-test")

    def test_client_with_base_url(self) -> None:
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            p = OpenAIVisionProvider(api_key="sk-test", base_url="http://custom")
            p._get_client()
            call_kwargs = mock_openai.OpenAI.call_args[1]
            assert call_kwargs["base_url"] == "http://custom"

    def test_missing_package(self) -> None:
        p = OpenAIVisionProvider(api_key="sk-test")
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(AIProviderUnavailableError):
                p._get_client()


# ---------------------------------------------------------------------------
# describe_screenshot
# ---------------------------------------------------------------------------

class TestOpenAIDescribeScreenshot:
    @patch("naturo.providers.openai_provider.OpenAIVisionProvider._get_client")
    def test_basic_describe(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_response("Notepad")
        mock_get_client.return_value = mock_client

        p = OpenAIVisionProvider(api_key="sk-test")
        result = p.describe_screenshot(fake_image)
        assert result.description == "Notepad"
        assert result.model == "gpt-4o"
        assert result.tokens_used == 150

    @patch("naturo.providers.openai_provider.OpenAIVisionProvider._get_client")
    def test_custom_prompt(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_response("buttons")
        mock_get_client.return_value = mock_client

        p = OpenAIVisionProvider(api_key="sk-test")
        p.describe_screenshot(fake_image, prompt="List buttons")

        call_args = mock_client.chat.completions.create.call_args[1]
        user_msg = call_args["messages"][0]
        text_block = [c for c in user_msg["content"] if c["type"] == "text"][0]
        assert "List buttons" in text_block["text"]

    @patch("naturo.providers.openai_provider.OpenAIVisionProvider._get_client")
    def test_context_prepended(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_response("r")
        mock_get_client.return_value = mock_client

        p = OpenAIVisionProvider(api_key="sk-test")
        p.describe_screenshot(fake_image, context="Calculator app")

        call_args = mock_client.chat.completions.create.call_args[1]
        text_block = [c for c in call_args["messages"][0]["content"] if c["type"] == "text"][0]
        assert text_block["text"].startswith("Context: Calculator app")

    @patch("naturo.providers.openai_provider.OpenAIVisionProvider._get_client")
    def test_api_error(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("rate limit")
        mock_get_client.return_value = mock_client

        p = OpenAIVisionProvider(api_key="sk-test")
        with pytest.raises(AIAnalysisFailedError):
            p.describe_screenshot(fake_image)

    def test_unavailable(self, fake_image: str) -> None:
        p = OpenAIVisionProvider()
        with pytest.raises(AIProviderUnavailableError):
            p.describe_screenshot(fake_image)

    @patch("naturo.providers.openai_provider.OpenAIVisionProvider._get_client")
    def test_no_usage(self, mock_get_client: MagicMock, fake_image: str) -> None:
        msg = MagicMock(content="desc")
        choice = MagicMock(message=msg)
        resp = MagicMock(choices=[choice], usage=None)

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = resp
        mock_get_client.return_value = mock_client

        p = OpenAIVisionProvider(api_key="sk-test")
        result = p.describe_screenshot(fake_image)
        assert result.tokens_used == 0

    @patch("naturo.providers.openai_provider.OpenAIVisionProvider._get_client")
    def test_max_tokens_passed(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_response()
        mock_get_client.return_value = mock_client

        p = OpenAIVisionProvider(api_key="sk-test")
        p.describe_screenshot(fake_image, max_tokens=4096)

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["max_tokens"] == 4096

    @patch("naturo.providers.openai_provider.OpenAIVisionProvider._get_client")
    def test_image_url_format(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_response()
        mock_get_client.return_value = mock_client

        p = OpenAIVisionProvider(api_key="sk-test")
        p.describe_screenshot(fake_image)

        call_args = mock_client.chat.completions.create.call_args[1]
        img_block = [c for c in call_args["messages"][0]["content"] if c["type"] == "image_url"][0]
        assert img_block["image_url"]["url"].startswith("data:image/png;base64,")


# ---------------------------------------------------------------------------
# identify_element
# ---------------------------------------------------------------------------

class TestOpenAIIdentifyElement:
    @patch("naturo.providers.openai_provider.OpenAIVisionProvider._get_client")
    def test_basic_identify(self, mock_get_client: MagicMock, fake_image: str) -> None:
        json_text = json.dumps({"found": True, "bounds": {"x": 50, "y": 75}})
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_response(json_text)
        mock_get_client.return_value = mock_client

        p = OpenAIVisionProvider(api_key="sk-test")
        result = p.identify_element(fake_image, "OK button")
        assert len(result.elements) >= 1

    @patch("naturo.providers.openai_provider.OpenAIVisionProvider._get_client")
    def test_identify_no_json(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_response("I cannot find it")
        mock_get_client.return_value = mock_client

        p = OpenAIVisionProvider(api_key="sk-test")
        result = p.identify_element(fake_image, "missing")
        assert result.elements == []

    def test_unavailable(self, fake_image: str) -> None:
        p = OpenAIVisionProvider()
        with pytest.raises(AIProviderUnavailableError):
            p.identify_element(fake_image, "button")

    @patch("naturo.providers.openai_provider.OpenAIVisionProvider._get_client")
    def test_api_error(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("server error")
        mock_get_client.return_value = mock_client

        p = OpenAIVisionProvider(api_key="sk-test")
        with pytest.raises(AIAnalysisFailedError):
            p.identify_element(fake_image, "button")
