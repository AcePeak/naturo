"""Tests for naturo.providers.ollama_provider — Ollama local vision provider.

Covers: construction, connectivity check, describe_screenshot, identify_element,
HTTP errors, token counting.
"""
from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from naturo.errors import AIAnalysisFailedError, AIProviderUnavailableError
from naturo.providers.ollama_provider import OllamaVisionProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NATURO_OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)


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


def _mock_ollama_http_response(
    response_text: str = "A screenshot description",
    eval_count: int = 30,
    prompt_eval_count: int = 200,
) -> MagicMock:
    """Build a mock urllib response for Ollama API."""
    data = json.dumps({
        "response": response_text,
        "eval_count": eval_count,
        "prompt_eval_count": prompt_eval_count,
    }).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = data
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ---------------------------------------------------------------------------
# Construction & properties
# ---------------------------------------------------------------------------

class TestOllamaProviderInit:
    def test_defaults(self) -> None:
        p = OllamaVisionProvider()
        assert p.name == "ollama"
        assert p._model == "llava"
        assert p._base_url == "http://localhost:11434"

    def test_custom_model(self) -> None:
        p = OllamaVisionProvider(model="bakllava")
        assert p._model == "bakllava"

    def test_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NATURO_OLLAMA_MODEL", "llava:13b")
        p = OllamaVisionProvider()
        assert p._model == "llava:13b"

    def test_custom_base_url(self) -> None:
        p = OllamaVisionProvider(base_url="http://gpu-server:11434/")
        assert p._base_url == "http://gpu-server:11434"  # trailing slash stripped

    def test_base_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OLLAMA_HOST", "http://remote:11434")
        p = OllamaVisionProvider()
        assert p._base_url == "http://remote:11434"


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------

class TestOllamaIsAvailable:
    @patch("urllib.request.urlopen")
    def test_available(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        p = OllamaVisionProvider()
        assert p.is_available is True

    @patch("urllib.request.urlopen")
    def test_unavailable_connection_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = ConnectionRefusedError("refused")
        p = OllamaVisionProvider()
        assert p.is_available is False

    @patch("urllib.request.urlopen")
    def test_unavailable_timeout(self, mock_urlopen: MagicMock) -> None:
        import socket
        mock_urlopen.side_effect = socket.timeout("timed out")
        p = OllamaVisionProvider()
        assert p.is_available is False


# ---------------------------------------------------------------------------
# describe_screenshot
# ---------------------------------------------------------------------------

class TestOllamaDescribeScreenshot:
    @patch("urllib.request.urlopen")
    def test_basic_describe(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        mock_urlopen.return_value = _mock_ollama_http_response("Notepad window with text")
        p = OllamaVisionProvider()
        result = p.describe_screenshot(fake_image)

        assert result.description == "Notepad window with text"
        assert result.model == "llava"
        assert result.tokens_used == 230  # 30 + 200

    @patch("urllib.request.urlopen")
    def test_custom_prompt(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        mock_urlopen.return_value = _mock_ollama_http_response("buttons only")
        p = OllamaVisionProvider()
        p.describe_screenshot(fake_image, prompt="List all buttons")

        # Verify the request payload
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        assert "List all buttons" in payload["prompt"]

    @patch("urllib.request.urlopen")
    def test_context_prepended(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        mock_urlopen.return_value = _mock_ollama_http_response("result")
        p = OllamaVisionProvider()
        p.describe_screenshot(fake_image, context="Excel spreadsheet")

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["prompt"].startswith("Context: Excel spreadsheet")

    @patch("urllib.request.urlopen")
    def test_url_error(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        p = OllamaVisionProvider()
        with pytest.raises(AIProviderUnavailableError):
            p.describe_screenshot(fake_image)

    @patch("urllib.request.urlopen")
    def test_generic_error(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        mock_urlopen.side_effect = ValueError("bad JSON")
        p = OllamaVisionProvider()
        with pytest.raises(AIAnalysisFailedError):
            p.describe_screenshot(fake_image)

    @patch("urllib.request.urlopen")
    def test_request_payload_structure(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        mock_urlopen.return_value = _mock_ollama_http_response()
        p = OllamaVisionProvider(model="bakllava")
        p.describe_screenshot(fake_image)

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["model"] == "bakllava"
        assert payload["stream"] is False
        assert len(payload["images"]) == 1  # base64 image
        assert isinstance(payload["images"][0], str)

    @patch("urllib.request.urlopen")
    def test_missing_token_counts(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        data = json.dumps({"response": "desc"}).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.return_value = data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        p = OllamaVisionProvider()
        result = p.describe_screenshot(fake_image)
        assert result.tokens_used == 0


# ---------------------------------------------------------------------------
# identify_element
# ---------------------------------------------------------------------------

class TestOllamaIdentifyElement:
    @patch("urllib.request.urlopen")
    def test_basic_identify(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        json_text = json.dumps({"found": True, "bounds": {"x": 10, "y": 20}})
        mock_urlopen.return_value = _mock_ollama_http_response(json_text)

        p = OllamaVisionProvider()
        result = p.identify_element(fake_image, "Save button")
        assert len(result.elements) >= 1

    @patch("urllib.request.urlopen")
    def test_identify_no_json(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        mock_urlopen.return_value = _mock_ollama_http_response("Cannot find that element")
        p = OllamaVisionProvider()
        result = p.identify_element(fake_image, "nonexistent")
        assert result.elements == []

    @patch("urllib.request.urlopen")
    def test_identify_url_error(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("refused")
        p = OllamaVisionProvider()
        with pytest.raises(AIProviderUnavailableError):
            p.identify_element(fake_image, "button")

    @patch("urllib.request.urlopen")
    def test_identify_prompt_format(self, mock_urlopen: MagicMock, fake_image: str) -> None:
        mock_urlopen.return_value = _mock_ollama_http_response("{}")
        p = OllamaVisionProvider()
        p.identify_element(fake_image, "OK button")

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        assert "OK button" in payload["prompt"]
