"""Tests for naturo config command (setup/show/clear).

Covers credential storage, retrieval, redaction, and CLI output formats.
All tests use tmp_path to avoid touching real ~/.config/naturo/.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from naturo.cli import main


@pytest.fixture
def creds_path(tmp_path: Path) -> Path:
    """Override the credentials path to a temp directory."""
    return tmp_path / "credentials.json"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _patch_creds_path(creds_path: Path):
    """Redirect all credential I/O to temp path for every test."""
    with patch("naturo.cli.config_cmd._CREDENTIALS_PATH", creds_path):
        yield


# ── _load_credentials / _save_credentials ────────────────────────────────────


class TestCredentialIO:
    """Test low-level credential file operations."""

    def test_load_empty(self, creds_path: Path):
        from naturo.cli.config_cmd import _load_credentials

        assert _load_credentials() == {}

    def test_save_and_load(self, creds_path: Path):
        from naturo.cli.config_cmd import _load_credentials, _save_credentials

        data = {"anthropic": {"auth_mode": "api_key", "token": "sk-ant-test123"}}
        _save_credentials(data)
        assert creds_path.exists()
        loaded = _load_credentials()
        assert loaded == data

    def test_load_corrupt_json(self, creds_path: Path):
        from naturo.cli.config_cmd import _load_credentials

        creds_path.parent.mkdir(parents=True, exist_ok=True)
        creds_path.write_text("not valid json{{{", encoding="utf-8")
        assert _load_credentials() == {}

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        from naturo.cli.config_cmd import _save_credentials

        deep_path = tmp_path / "a" / "b" / "c" / "credentials.json"
        with patch("naturo.cli.config_cmd._CREDENTIALS_PATH", deep_path):
            _save_credentials({"test": True})
        assert deep_path.exists()


# ── config show ──────────────────────────────────────────────────────────────


class TestConfigShow:
    """Test 'naturo config show' command."""

    def test_show_empty(self, runner: CliRunner):
        result = runner.invoke(main, ["config", "show"])
        assert result.exit_code == 0
        assert "No credentials stored" in result.output

    def test_show_with_credentials(self, runner: CliRunner, creds_path: Path):
        from naturo.cli.config_cmd import _save_credentials

        _save_credentials({"anthropic": {"auth_mode": "api_key", "token": "sk-ant-abcdef123456"}})
        result = runner.invoke(main, ["config", "show"])
        assert result.exit_code == 0
        assert "anthropic" in result.output
        assert "api_key" in result.output
        # Token should be redacted
        assert "sk-ant-abcdef123456" not in result.output
        assert "sk-ant" in result.output  # prefix shown
        assert "3456" in result.output  # suffix shown

    def test_show_json(self, runner: CliRunner, creds_path: Path):
        from naturo.cli.config_cmd import _save_credentials

        _save_credentials({"anthropic": {"auth_mode": "oauth", "token": "session-token-abcdefghij"}})
        result = runner.invoke(main, ["config", "show", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "anthropic" in data["providers"]
        assert data["providers"]["anthropic"]["auth_mode"] == "oauth"
        # Token must be redacted in JSON too
        assert "session-token-abcdefghij" not in result.output

    def test_show_json_empty(self, runner: CliRunner):
        result = runner.invoke(main, ["config", "show", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["providers"] == {}

    def test_show_env_vars(self, runner: CliRunner):
        """Environment variable status is shown."""
        result = runner.invoke(main, ["config", "show"])
        assert result.exit_code == 0
        assert "ANTHROPIC_API_KEY" in result.output
        assert "ANTHROPIC_AUTH_TOKEN" in result.output


# ── config clear ─────────────────────────────────────────────────────────────


class TestConfigClear:
    """Test 'naturo config clear' command."""

    def test_clear_nonexistent_provider(self, runner: CliRunner):
        result = runner.invoke(main, ["config", "clear", "nonexistent"])
        assert result.exit_code == 0
        assert "No stored credentials" in result.output

    def test_clear_specific_provider(self, runner: CliRunner, creds_path: Path):
        from naturo.cli.config_cmd import _load_credentials, _save_credentials

        _save_credentials({
            "anthropic": {"auth_mode": "api_key", "token": "sk-test"},
            "openai": {"auth_mode": "api_key", "token": "sk-openai"},
        })
        result = runner.invoke(main, ["config", "clear", "anthropic", "--yes"])
        assert result.exit_code == 0
        assert "anthropic" in result.output
        remaining = _load_credentials()
        assert "anthropic" not in remaining
        assert "openai" in remaining

    def test_clear_all(self, runner: CliRunner, creds_path: Path):
        from naturo.cli.config_cmd import _load_credentials, _save_credentials

        _save_credentials({"anthropic": {"token": "a"}, "openai": {"token": "b"}})
        result = runner.invoke(main, ["config", "clear", "all", "--yes"])
        assert result.exit_code == 0
        assert _load_credentials() == {}

    def test_clear_json(self, runner: CliRunner, creds_path: Path):
        from naturo.cli.config_cmd import _save_credentials

        _save_credentials({"anthropic": {"auth_mode": "api_key", "token": "sk-test"}})
        result = runner.invoke(main, ["config", "clear", "anthropic", "--yes", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "anthropic" in data["cleared"]

    def test_clear_json_nonexistent(self, runner: CliRunner):
        result = runner.invoke(main, ["config", "clear", "ghost", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["cleared"] == []

    def test_clear_abort_without_yes(self, runner: CliRunner, creds_path: Path):
        from naturo.cli.config_cmd import _load_credentials, _save_credentials

        _save_credentials({"anthropic": {"token": "sk-test"}})
        result = runner.invoke(main, ["config", "clear", "anthropic"], input="n\n")
        assert "Aborted" in result.output
        assert _load_credentials() != {}


# ── config setup anthropic ───────────────────────────────────────────────────


class TestConfigSetupAnthropic:
    """Test 'naturo config setup anthropic' command."""

    def test_setup_api_key_noninteractive(self, runner: CliRunner, creds_path: Path):
        from naturo.cli.config_cmd import _load_credentials

        result = runner.invoke(main, [
            "config", "setup", "anthropic",
            "--mode", "api_key",
            "--token", "sk-ant-testkey123456",
            "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["auth_mode"] == "api_key"
        creds = _load_credentials()
        assert creds["anthropic"]["token"] == "sk-ant-testkey123456"
        assert creds["anthropic"]["auth_mode"] == "api_key"

    def test_setup_oauth_noninteractive(self, runner: CliRunner, creds_path: Path):
        from naturo.cli.config_cmd import _load_credentials

        result = runner.invoke(main, [
            "config", "setup", "anthropic",
            "--mode", "oauth",
            "--token", "session-token-xyz",
            "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["auth_mode"] == "oauth"
        creds = _load_credentials()
        assert creds["anthropic"]["auth_mode"] == "oauth"

    def test_setup_empty_token_fails(self, runner: CliRunner):
        result = runner.invoke(main, [
            "config", "setup", "anthropic",
            "--mode", "api_key",
            "--token", "   ",
            "--json",
        ])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "empty" in data["error"]["message"].lower()

    def test_setup_json_requires_token(self, runner: CliRunner):
        result = runner.invoke(main, [
            "config", "setup", "anthropic",
            "--mode", "api_key",
            "--json",
        ])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "token" in data["error"]["message"].lower()

    def test_setup_overwrites_existing(self, runner: CliRunner, creds_path: Path):
        from naturo.cli.config_cmd import _load_credentials, _save_credentials

        _save_credentials({"anthropic": {"auth_mode": "api_key", "token": "old-key"}})
        runner.invoke(main, [
            "config", "setup", "anthropic",
            "--mode", "oauth",
            "--token", "new-session-token",
            "--json",
        ])
        creds = _load_credentials()
        assert creds["anthropic"]["auth_mode"] == "oauth"
        assert creds["anthropic"]["token"] == "new-session-token"


# ── Redaction ────────────────────────────────────────────────────────────────


class TestRedaction:
    """Test token redaction logic."""

    def test_redact_long_token(self):
        from naturo.cli.config_cmd import config_show

        # Access the inner _redact function via the show command's closure
        # Instead, test via CLI output
        pass

    def test_redact_via_show_output(self, runner: CliRunner, creds_path: Path):
        from naturo.cli.config_cmd import _save_credentials

        token = "sk-ant-api03-verylongtokenvalue123456789"
        _save_credentials({"anthropic": {"auth_mode": "api_key", "token": token}})
        result = runner.invoke(main, ["config", "show", "--json"])
        data = json.loads(result.output)
        redacted = data["providers"]["anthropic"]["token"]
        # Full token must NOT appear
        assert token not in redacted
        # Prefix (6 chars) and suffix (4 chars) should be visible
        assert redacted.startswith(token[:6])
        assert redacted.endswith(token[-4:])
        assert "..." in redacted

    def test_redact_short_token(self, runner: CliRunner, creds_path: Path):
        from naturo.cli.config_cmd import _save_credentials

        _save_credentials({"anthropic": {"auth_mode": "api_key", "token": "short"}})
        result = runner.invoke(main, ["config", "show", "--json"])
        data = json.loads(result.output)
        redacted = data["providers"]["anthropic"]["token"]
        assert redacted == "***"


# ── Help text ────────────────────────────────────────────────────────────────


class TestConfigHelp:
    """Test config help output."""

    def test_config_help(self, runner: CliRunner):
        result = runner.invoke(main, ["config", "--help"])
        assert result.exit_code == 0
        assert "setup" in result.output
        assert "show" in result.output
        assert "clear" in result.output

    def test_config_setup_help(self, runner: CliRunner):
        result = runner.invoke(main, ["config", "setup", "--help"])
        assert result.exit_code == 0
        assert "anthropic" in result.output
