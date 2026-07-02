"""Tests for naturo.providers.anthropic_provider — Anthropic/Claude vision provider.

Covers: auth resolution, OAuth token exchange/cache, model aliases,
describe_screenshot, identify_element, error paths.
"""
from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from naturo.errors import AIAnalysisFailedError, AIProviderUnavailableError
from naturo.providers.anthropic_provider import (
    AnthropicVisionProvider,
    _OAuthCache,
    _exchange_refresh_token,
    _get_oauth_access_token,
    _is_oauth_refresh_token,
    _load_credentials,
    _persist_refresh_token,
    _resolve_auth,
    _resolve_model,
    _save_credentials,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove auth env vars so tests start clean."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("NATURO_AI_MODEL", raising=False)
    # Clear OAuth cache between tests
    _OAuthCache.clear()
    _OAuthCache._refresh_token = ""


@pytest.fixture()
def fake_image(tmp_path: Path) -> str:
    """Create a minimal 1x1 red PNG for image-based tests."""
    import struct
    import zlib

    def _chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"\x00\xff\x00\x00"  # filter byte + RGB
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw)) + _chunk(b"IEND", b"")
    p = tmp_path / "test.png"
    p.write_bytes(png)
    return str(p)


def _mock_anthropic_response(text: str = "A description", input_tokens: int = 100, output_tokens: int = 50) -> MagicMock:
    """Build a mock Anthropic messages.create response."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    resp.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    return resp


# ---------------------------------------------------------------------------
# Helper / utility tests
# ---------------------------------------------------------------------------

class TestIsOAuthRefreshToken:
    def test_refresh_token(self) -> None:
        assert _is_oauth_refresh_token("sk-ant-oat01-abc123") is True

    def test_api_key(self) -> None:
        assert _is_oauth_refresh_token("sk-ant-api03-abc123") is False

    def test_empty(self) -> None:
        assert _is_oauth_refresh_token("") is False


class TestResolveModel:
    def test_alias_opus_4_6(self) -> None:
        assert _resolve_model("opus-4-6") == "claude-opus-4-6"

    def test_alias_sonnet(self) -> None:
        assert _resolve_model("sonnet") == "claude-sonnet-4-20250514"

    def test_alias_haiku(self) -> None:
        assert _resolve_model("haiku") == "claude-haiku-4-5-20251001"

    def test_alias_opus(self) -> None:
        assert _resolve_model("opus") == "claude-opus-4-6"

    def test_passthrough(self) -> None:
        assert _resolve_model("claude-sonnet-4-20250514") == "claude-sonnet-4-20250514"


class TestResolveAuth:
    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-xyz")
        mode, token = _resolve_auth()
        assert mode == "api_key"
        assert token == "sk-ant-api03-xyz"

    def test_oauth_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-oat01-xyz")
        mode, token = _resolve_auth()
        assert mode == "oauth"
        assert token == "sk-ant-oat01-xyz"

    def test_auth_token_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "session-token-abc")
        mode, token = _resolve_auth()
        assert mode == "oauth"
        assert token == "session-token-abc"

    def test_auth_token_env_refresh(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-ant-oat01-refresh")
        mode, token = _resolve_auth()
        assert mode == "oauth"

    @patch("naturo.providers.anthropic_provider._load_credentials")
    def test_credentials_file(self, mock_load: MagicMock) -> None:
        mock_load.return_value = {"anthropic": {"token": "sk-ant-api03-file", "auth_mode": "api_key"}}
        mode, token = _resolve_auth()
        assert mode == "api_key"
        assert token == "sk-ant-api03-file"

    @patch("naturo.providers.anthropic_provider._load_credentials")
    def test_credentials_file_oauth(self, mock_load: MagicMock) -> None:
        mock_load.return_value = {"anthropic": {"token": "sk-ant-oat01-file"}}
        mode, token = _resolve_auth()
        assert mode == "oauth"

    @patch("naturo.providers.anthropic_provider._load_credentials")
    def test_no_credentials(self, mock_load: MagicMock) -> None:
        mock_load.return_value = {}
        mode, token = _resolve_auth()
        assert mode == "api_key"
        assert token == ""


# ---------------------------------------------------------------------------
# Credentials file I/O
# ---------------------------------------------------------------------------

class TestCredentialsIO:
    @patch("naturo.config.CREDENTIALS_PATH")
    def test_load_missing_file(self, mock_path: MagicMock) -> None:
        mock_path.exists.return_value = False
        assert _load_credentials() == {}

    @patch("naturo.config.CREDENTIALS_PATH")
    def test_load_valid_json(self, mock_path: MagicMock) -> None:
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = '{"anthropic": {"token": "abc"}}'
        result = _load_credentials()
        assert result == {"anthropic": {"token": "abc"}}

    @patch("naturo.config.CREDENTIALS_PATH")
    def test_load_invalid_json(self, mock_path: MagicMock) -> None:
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "not-json"
        assert _load_credentials() == {}

    def test_save_and_load(self, tmp_path: Path) -> None:
        creds_path = tmp_path / "credentials.json"
        with patch("naturo.config.CREDENTIALS_PATH", creds_path):
            _save_credentials({"anthropic": {"token": "test"}})
            result = _load_credentials()
            assert result["anthropic"]["token"] == "test"


# ---------------------------------------------------------------------------
# OAuth cache
# ---------------------------------------------------------------------------

class TestOAuthCache:
    def test_initially_invalid(self) -> None:
        assert _OAuthCache.is_valid() is False

    def test_set_and_valid(self) -> None:
        _OAuthCache.set("access-token", 3600, "refresh-token")
        assert _OAuthCache.is_valid() is True
        assert _OAuthCache._access_token == "access-token"

    def test_clear(self) -> None:
        _OAuthCache.set("token", 3600)
        _OAuthCache.clear()
        assert _OAuthCache.is_valid() is False

    def test_expired_token(self) -> None:
        # Set with negative expires_in (already expired after buffer subtraction)
        _OAuthCache.set("token", 0)
        assert _OAuthCache.is_valid() is False

    def test_refresh_token_stored(self) -> None:
        _OAuthCache.set("access", 3600, "new-refresh")
        assert _OAuthCache._refresh_token == "new-refresh"


# ---------------------------------------------------------------------------
# OAuth token exchange
# ---------------------------------------------------------------------------

class TestExchangeRefreshToken:
    @patch("urllib.request.urlopen")
    def test_success(self, mock_urlopen: MagicMock) -> None:
        resp_data = json.dumps({
            "access_token": "at-123",
            "expires_in": 3600,
            "refresh_token": "",
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        token = _exchange_refresh_token("sk-ant-oat01-old")
        assert token == "at-123"
        assert _OAuthCache.is_valid()

    @patch("urllib.request.urlopen")
    def test_rotated_refresh_token(self, mock_urlopen: MagicMock) -> None:
        resp_data = json.dumps({
            "access_token": "at-new",
            "expires_in": 3600,
            "refresh_token": "sk-ant-oat01-rotated",
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        with patch("naturo.providers.anthropic_provider._persist_refresh_token") as mock_persist:
            token = _exchange_refresh_token("sk-ant-oat01-old")
            mock_persist.assert_called_once_with("sk-ant-oat01-rotated")
        assert token == "at-new"

    @patch("urllib.request.urlopen")
    def test_http_error(self, mock_urlopen: MagicMock) -> None:
        import urllib.error
        err = urllib.error.HTTPError("url", 401, "Unauthorized", {}, MagicMock(read=lambda: b"error"))
        mock_urlopen.side_effect = err
        with pytest.raises(AIProviderUnavailableError):
            _exchange_refresh_token("sk-ant-oat01-bad")

    @patch("urllib.request.urlopen")
    def test_no_access_token_in_response(self, mock_urlopen: MagicMock) -> None:
        resp_data = json.dumps({"expires_in": 3600}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        with pytest.raises(AIProviderUnavailableError):
            _exchange_refresh_token("sk-ant-oat01-bad")

    @patch("urllib.request.urlopen")
    def test_network_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = ConnectionError("offline")
        with pytest.raises(AIProviderUnavailableError):
            _exchange_refresh_token("sk-ant-oat01-bad")


class TestGetOAuthAccessToken:
    def test_returns_cached(self) -> None:
        _OAuthCache.set("cached-token", 3600, "refresh")
        assert _get_oauth_access_token("refresh") == "cached-token"

    @patch("naturo.providers.anthropic_provider._exchange_refresh_token", return_value="new-token")
    def test_exchanges_when_expired(self, mock_exchange: MagicMock) -> None:
        token = _get_oauth_access_token("sk-ant-oat01-xyz")
        assert token == "new-token"
        mock_exchange.assert_called_once()


class TestPersistRefreshToken:
    def test_persist(self, tmp_path: Path) -> None:
        creds_path = tmp_path / "credentials.json"
        with patch("naturo.config.CREDENTIALS_PATH", creds_path):
            _persist_refresh_token("sk-ant-oat01-new")
            data = json.loads(creds_path.read_text())
            assert data["anthropic"]["token"] == "sk-ant-oat01-new"
            assert data["anthropic"]["auth_mode"] == "oauth"

    @patch("naturo.providers.anthropic_provider._save_credentials", side_effect=OSError("disk full"))
    @patch("naturo.providers.anthropic_provider._load_credentials", return_value={})
    def test_persist_failure_logs_warning(self, mock_load: MagicMock, mock_save: MagicMock) -> None:
        # Should not raise — just logs warning
        _persist_refresh_token("sk-ant-oat01-new")


# ---------------------------------------------------------------------------
# AnthropicVisionProvider — construction & properties
# ---------------------------------------------------------------------------

class TestAnthropicVisionProviderInit:
    def test_explicit_api_key(self) -> None:
        p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
        assert p.name == "anthropic"
        assert p.auth_mode == "api_key"
        assert p.is_available is True

    def test_explicit_oauth_token(self) -> None:
        p = AnthropicVisionProvider(api_key="sk-ant-oat01-test")
        assert p.auth_mode == "oauth"
        assert p.is_available is True

    def test_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-env")
        p = AnthropicVisionProvider()
        assert p.is_available is True

    @patch("naturo.providers.anthropic_provider._resolve_auth", return_value=("api_key", ""))
    def test_no_credentials(self, mock_auth: MagicMock) -> None:
        p = AnthropicVisionProvider()
        assert p.is_available is False

    def test_model_alias(self) -> None:
        p = AnthropicVisionProvider(api_key="sk-ant-api03-test", model="haiku")
        assert p._model == "claude-haiku-4-5-20251001"

    def test_model_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NATURO_AI_MODEL", "claude-3-opus-20240229")
        p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
        assert p._model == "claude-3-opus-20240229"

    def test_explicit_model_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NATURO_AI_MODEL", "something-else")
        p = AnthropicVisionProvider(api_key="sk-ant-api03-test", model="sonnet")
        assert p._model == "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# _get_client
# ---------------------------------------------------------------------------

class TestAnthropicGetClient:
    def test_api_key_client(self) -> None:
        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
            p._get_client()
            mock_anthropic.Anthropic.assert_called_once_with(api_key="sk-ant-api03-test")

    @patch("naturo.providers.anthropic_provider._get_oauth_access_token", return_value="access-123")
    def test_oauth_refresh_client(self, mock_get_token: MagicMock) -> None:
        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            p = AnthropicVisionProvider(api_key="sk-ant-oat01-refresh")
            p._get_client()
            mock_anthropic.Anthropic.assert_called_once()
            call_kwargs = mock_anthropic.Anthropic.call_args[1]
            assert call_kwargs["api_key"] == "access-123"
            assert "anthropic-beta" in call_kwargs["default_headers"]

    def test_missing_package(self) -> None:
        p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(AIProviderUnavailableError):
                p._get_client()

    @patch("naturo.providers.anthropic_provider._resolve_auth", return_value=("api_key", ""))
    def test_no_token(self, mock_auth: MagicMock) -> None:
        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            p = AnthropicVisionProvider()
            with pytest.raises(AIProviderUnavailableError):
                p._get_client()

    def test_oauth_legacy_session_token(self) -> None:
        """OAuth mode with a non-refresh token (legacy session)."""
        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            p = AnthropicVisionProvider.__new__(AnthropicVisionProvider)
            p._auth_mode = "oauth"
            p._token = "session-token-123"
            p._model = "claude-sonnet-4-20250514"
            p._get_client()
            mock_anthropic.Anthropic.assert_called()


# ---------------------------------------------------------------------------
# describe_screenshot
# ---------------------------------------------------------------------------

class TestAnthropicDescribeScreenshot:
    @patch("naturo.providers.anthropic_provider.AnthropicVisionProvider._get_client")
    def test_basic_describe(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response("Notepad window")
        mock_get_client.return_value = mock_client

        p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
        result = p.describe_screenshot(fake_image)

        assert result.description == "Notepad window"
        assert result.model == "claude-opus-4-6"
        assert result.tokens_used == 150

    @patch("naturo.providers.anthropic_provider.AnthropicVisionProvider._get_client")
    def test_custom_prompt(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response("Custom result")
        mock_get_client.return_value = mock_client

        p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
        result = p.describe_screenshot(fake_image, prompt="List all buttons")

        call_args = mock_client.messages.create.call_args
        user_msg = call_args[1]["messages"][0]
        text_block = [c for c in user_msg["content"] if c["type"] == "text"][0]
        assert "List all buttons" in text_block["text"]

    @patch("naturo.providers.anthropic_provider.AnthropicVisionProvider._get_client")
    def test_context_prepended(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response("result")
        mock_get_client.return_value = mock_client

        p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
        p.describe_screenshot(fake_image, context="This is Notepad")

        call_args = mock_client.messages.create.call_args
        text_block = [c for c in call_args[1]["messages"][0]["content"] if c["type"] == "text"][0]
        assert text_block["text"].startswith("Context: This is Notepad")

    @patch("naturo.providers.anthropic_provider.AnthropicVisionProvider._get_client")
    def test_api_error(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("rate limited")
        mock_get_client.return_value = mock_client

        p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
        with pytest.raises(AIAnalysisFailedError):
            p.describe_screenshot(fake_image)

    @patch("naturo.providers.anthropic_provider._resolve_auth", return_value=("api_key", ""))
    def test_unavailable(self, mock_auth: MagicMock, fake_image: str) -> None:
        p = AnthropicVisionProvider()
        with pytest.raises(AIProviderUnavailableError):
            p.describe_screenshot(fake_image)

    @patch("naturo.providers.anthropic_provider.AnthropicVisionProvider._get_client")
    def test_multi_block_response(self, mock_get_client: MagicMock, fake_image: str) -> None:
        block1 = MagicMock(type="text", text="First part. ")
        block2 = MagicMock(type="text", text="Second part.")
        resp = MagicMock()
        resp.content = [block1, block2]
        resp.usage = MagicMock(input_tokens=200, output_tokens=100)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = resp
        mock_get_client.return_value = mock_client

        p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
        result = p.describe_screenshot(fake_image)
        assert result.description == "First part. Second part."
        assert result.tokens_used == 300

    @patch("naturo.providers.anthropic_provider.AnthropicVisionProvider._get_client")
    def test_no_usage_attribute(self, mock_get_client: MagicMock, fake_image: str) -> None:
        block = MagicMock(type="text", text="desc")
        resp = MagicMock(spec=[])  # no usage attribute
        resp.content = [block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = resp
        mock_get_client.return_value = mock_client

        p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
        result = p.describe_screenshot(fake_image)
        assert result.tokens_used == 0

    @patch("naturo.providers.anthropic_provider.AnthropicVisionProvider._get_client")
    def test_max_tokens_passed(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response()
        mock_get_client.return_value = mock_client

        p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
        p.describe_screenshot(fake_image, max_tokens=2048)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 2048


# ---------------------------------------------------------------------------
# identify_element
# ---------------------------------------------------------------------------

class TestAnthropicIdentifyElement:
    @patch("naturo.providers.anthropic_provider.AnthropicVisionProvider._get_client")
    def test_basic_identify(self, mock_get_client: MagicMock, fake_image: str) -> None:
        json_response = json.dumps({"found": True, "bounds": {"x": 100, "y": 200}})
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(json_response)
        mock_get_client.return_value = mock_client

        p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
        result = p.identify_element(fake_image, "Save button")

        assert len(result.elements) >= 1
        assert result.description == json_response

    @patch("naturo.providers.anthropic_provider.AnthropicVisionProvider._get_client")
    def test_identify_not_found(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response("no JSON here")
        mock_get_client.return_value = mock_client

        p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
        result = p.identify_element(fake_image, "nonexistent button")
        assert result.elements == []

    @patch("naturo.providers.anthropic_provider._resolve_auth", return_value=("api_key", ""))
    def test_unavailable(self, mock_auth: MagicMock, fake_image: str) -> None:
        p = AnthropicVisionProvider()
        with pytest.raises(AIProviderUnavailableError):
            p.identify_element(fake_image, "button")

    @patch("naturo.providers.anthropic_provider.AnthropicVisionProvider._get_client")
    def test_api_error(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("timeout")
        mock_get_client.return_value = mock_client

        p = AnthropicVisionProvider(api_key="sk-ant-api03-test")
        with pytest.raises(AIAnalysisFailedError):
            p.identify_element(fake_image, "button")
