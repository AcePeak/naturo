"""Tests for issue #143 — Anthropic subscription/OAuth token support.

Verifies:
- Auth resolution priority (explicit key > ANTHROPIC_API_KEY > ANTHROPIC_AUTH_TOKEN > file)
- AnthropicVisionProvider.auth_mode property
- AnthropicVisionProvider.is_available works for both api_key and oauth modes
- _get_client() uses api_key vs auth_token kwarg appropriately
- credentials.json loading/saving helpers
- ``naturo config setup anthropic`` CLI (non-interactive --token path)
- ``naturo config show`` CLI
- ``naturo config clear`` CLI
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.providers.anthropic_provider import (
    AnthropicVisionProvider,
    _load_credentials,
    _resolve_auth,
    _save_credentials,
    _CREDENTIALS_PATH,
)
from naturo.cli import main


# ── Helpers ───────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Remove Anthropic env vars so tests start from a blank slate."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("NATURO_AI_MODEL", raising=False)


@pytest.fixture()
def tmp_creds_path(tmp_path, monkeypatch):
    """Redirect _CREDENTIALS_PATH to a temporary file."""
    import naturo.providers.anthropic_provider as _ap
    import naturo.cli.config_cmd as _cc

    creds_file = tmp_path / "credentials.json"
    monkeypatch.setattr(_ap, "_CREDENTIALS_PATH", creds_file)
    monkeypatch.setattr(_cc, "_CREDENTIALS_PATH", creds_file)
    return creds_file


# ── _resolve_auth ─────────────────────────────────────────────────────────────


class TestResolveAuth:
    def test_api_key_env_takes_priority(self, monkeypatch, tmp_creds_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-key-111")
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sess-token-222")
        mode, token = _resolve_auth()
        assert mode == "api_key"
        assert token == "sk-ant-key-111"

    def test_auth_token_env_when_no_api_key(self, monkeypatch, tmp_creds_path):
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sess-token-333")
        mode, token = _resolve_auth()
        assert mode == "oauth"
        assert token == "sess-token-333"

    def test_credentials_file_fallback(self, monkeypatch, tmp_creds_path):
        tmp_creds_path.write_text(json.dumps({
            "anthropic": {"auth_mode": "oauth", "token": "sess-file-token"}
        }))
        mode, token = _resolve_auth()
        assert mode == "oauth"
        assert token == "sess-file-token"

    def test_empty_when_nothing_configured(self, tmp_creds_path):
        mode, token = _resolve_auth()
        assert token == ""


# ── AnthropicVisionProvider ───────────────────────────────────────────────────


class TestAnthropicVisionProviderAuth:
    def test_explicit_api_key_overrides_env(self, monkeypatch, tmp_creds_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        p = AnthropicVisionProvider(api_key="explicit-key")
        assert p.auth_mode == "api_key"
        assert p._token == "explicit-key"

    def test_env_api_key(self, monkeypatch, tmp_creds_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-abc")
        p = AnthropicVisionProvider()
        assert p.auth_mode == "api_key"
        assert p._token == "sk-ant-abc"
        assert p.is_available

    def test_env_auth_token(self, monkeypatch, tmp_creds_path):
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sess-xyz")
        p = AnthropicVisionProvider()
        assert p.auth_mode == "oauth"
        assert p._token == "sess-xyz"
        assert p.is_available

    def test_no_credentials(self, tmp_creds_path):
        p = AnthropicVisionProvider()
        assert not p.is_available
        assert p._token == ""

    def test_is_available_with_file_creds(self, tmp_creds_path):
        tmp_creds_path.write_text(json.dumps({
            "anthropic": {"auth_mode": "api_key", "token": "sk-file-token"}
        }))
        p = AnthropicVisionProvider()
        assert p.is_available
        assert p.auth_mode == "api_key"

    def test_get_client_api_key_mode(self, monkeypatch, tmp_creds_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        mock_client = MagicMock()
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        p = AnthropicVisionProvider()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            client = p._get_client()

        mock_anthropic.Anthropic.assert_called_once_with(api_key="sk-ant-test")
        assert client is mock_client

    def test_get_client_oauth_mode_with_auth_token_kwarg(self, monkeypatch, tmp_creds_path):
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sess-abc")

        mock_client = MagicMock()
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        p = AnthropicVisionProvider()
        assert p.auth_mode == "oauth"

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            client = p._get_client()

        # SDK supports auth_token kwarg
        mock_anthropic.Anthropic.assert_called_once_with(auth_token="sess-abc")

    def test_get_client_oauth_falls_back_to_api_key_for_old_sdk(self, monkeypatch, tmp_creds_path):
        """If SDK doesn't accept auth_token, fall back to api_key param."""
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sess-fallback")

        mock_client = MagicMock()
        mock_anthropic = MagicMock()

        def anthropic_constructor(**kwargs):
            if "auth_token" in kwargs:
                raise TypeError("unexpected keyword argument 'auth_token'")
            return mock_client

        mock_anthropic.Anthropic.side_effect = anthropic_constructor

        p = AnthropicVisionProvider()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            client = p._get_client()

        assert client is mock_client
        # Was called twice: first with auth_token (failed), then with api_key
        assert mock_anthropic.Anthropic.call_count == 2

    def test_get_client_raises_when_no_token(self, tmp_creds_path):
        from naturo.errors import AIProviderUnavailableError

        mock_anthropic = MagicMock()

        p = AnthropicVisionProvider()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            with pytest.raises(AIProviderUnavailableError):
                p._get_client()


# ── Credentials helpers ───────────────────────────────────────────────────────


class TestCredentialsHelpers:
    def test_save_and_load_roundtrip(self, tmp_creds_path):
        data = {"anthropic": {"auth_mode": "oauth", "token": "tok-abc"}}
        _save_credentials.__wrapped__ = None  # reset any wrapping
        # Use module-level functions with patched path
        with patch("naturo.providers.anthropic_provider._CREDENTIALS_PATH", tmp_creds_path):
            from naturo.providers import anthropic_provider as ap
            ap._save_credentials(data)
            loaded = ap._load_credentials()
        assert loaded == data

    def test_load_returns_empty_when_missing(self, tmp_creds_path):
        # File doesn't exist yet
        assert not tmp_creds_path.exists()
        with patch("naturo.providers.anthropic_provider._CREDENTIALS_PATH", tmp_creds_path):
            from naturo.providers import anthropic_provider as ap
            result = ap._load_credentials()
        assert result == {}

    def test_load_returns_empty_on_corrupt_json(self, tmp_creds_path):
        tmp_creds_path.write_text("not valid json{{{{")
        with patch("naturo.providers.anthropic_provider._CREDENTIALS_PATH", tmp_creds_path):
            from naturo.providers import anthropic_provider as ap
            result = ap._load_credentials()
        assert result == {}


# ── CLI: naturo config ────────────────────────────────────────────────────────


class TestConfigCLI:
    """Tests for naturo config subcommands."""

    def test_setup_anthropic_api_key_non_interactive(self, tmp_creds_path):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["config", "setup", "anthropic", "--mode", "api_key", "--token", "sk-ant-test-123"],
        )
        assert result.exit_code == 0, result.output
        assert "Saved" in result.output
        assert tmp_creds_path.exists()
        creds = json.loads(tmp_creds_path.read_text())
        assert creds["anthropic"]["auth_mode"] == "api_key"
        assert creds["anthropic"]["token"] == "sk-ant-test-123"

    def test_setup_anthropic_oauth_non_interactive(self, tmp_creds_path):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["config", "setup", "anthropic", "--mode", "oauth", "--token", "sess-token-xyz"],
        )
        assert result.exit_code == 0, result.output
        creds = json.loads(tmp_creds_path.read_text())
        assert creds["anthropic"]["auth_mode"] == "oauth"
        assert creds["anthropic"]["token"] == "sess-token-xyz"

    def test_setup_anthropic_json_output(self, tmp_creds_path):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["config", "setup", "anthropic", "--mode", "api_key", "--token", "sk-abc", "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["provider"] == "anthropic"
        assert data["auth_mode"] == "api_key"

    def test_setup_anthropic_empty_token_fails(self, tmp_creds_path):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["config", "setup", "anthropic", "--mode", "api_key", "--token", "", "--json"],
        )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False

    def test_config_show_no_creds(self, tmp_creds_path):
        runner = CliRunner()
        result = runner.invoke(main, ["config", "show"])
        assert result.exit_code == 0
        assert "No credentials stored" in result.output

    def test_config_show_json(self, tmp_creds_path):
        tmp_creds_path.write_text(json.dumps({
            "anthropic": {"auth_mode": "api_key", "token": "sk-ant-123456789"}
        }))
        runner = CliRunner()
        result = runner.invoke(main, ["config", "show", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        # Token should be redacted
        token_display = data["providers"]["anthropic"]["token"]
        assert "sk-ant" in token_display
        assert "123456789" not in token_display  # last 4: 6789 won't be present in full

    def test_config_clear_provider(self, tmp_creds_path):
        tmp_creds_path.write_text(json.dumps({
            "anthropic": {"auth_mode": "api_key", "token": "sk-ant-xxx"},
            "openai": {"auth_mode": "api_key", "token": "sk-openai-yyy"},
        }))
        runner = CliRunner()
        result = runner.invoke(main, ["config", "clear", "anthropic", "--yes"])
        assert result.exit_code == 0
        creds = json.loads(tmp_creds_path.read_text())
        assert "anthropic" not in creds
        assert "openai" in creds

    def test_config_clear_all(self, tmp_creds_path):
        tmp_creds_path.write_text(json.dumps({
            "anthropic": {"token": "a"},
            "openai": {"token": "b"},
        }))
        runner = CliRunner()
        result = runner.invoke(main, ["config", "clear", "all", "--yes"])
        assert result.exit_code == 0
        creds = json.loads(tmp_creds_path.read_text())
        assert creds == {}

    def test_config_clear_nonexistent_provider(self, tmp_creds_path):
        runner = CliRunner()
        result = runner.invoke(main, ["config", "clear", "nonexistent", "--yes"])
        assert result.exit_code == 0
        assert "No stored credentials" in result.output
