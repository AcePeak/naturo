"""Tests for naturo.config — credential management and path constants."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from naturo import config


@pytest.fixture()
def tmp_creds(tmp_path: Path):
    """Redirect CREDENTIALS_PATH to a temp directory."""
    creds_path = tmp_path / "credentials.json"
    with patch.object(config, "CREDENTIALS_PATH", creds_path):
        yield creds_path


# ── load_credentials ─────────────────────────────────────────────────────────


class TestLoadCredentials:
    def test_returns_empty_dict_when_file_missing(self, tmp_creds: Path) -> None:
        assert not tmp_creds.exists()
        result = config.load_credentials()
        assert result == {}

    def test_loads_valid_json(self, tmp_creds: Path) -> None:
        data = {"api_key": "sk-test-123", "provider": "openai"}
        tmp_creds.parent.mkdir(parents=True, exist_ok=True)
        tmp_creds.write_text(json.dumps(data), encoding="utf-8")
        result = config.load_credentials()
        assert result == data

    def test_returns_empty_dict_on_invalid_json(self, tmp_creds: Path) -> None:
        tmp_creds.parent.mkdir(parents=True, exist_ok=True)
        tmp_creds.write_text("{invalid json", encoding="utf-8")
        result = config.load_credentials()
        assert result == {}

    def test_returns_empty_dict_on_os_error(self, tmp_creds: Path) -> None:
        with patch.object(config, "CREDENTIALS_PATH") as mock_path:
            mock_path.exists.side_effect = OSError("permission denied")
            result = config.load_credentials()
        assert result == {}

    def test_loads_nested_data(self, tmp_creds: Path) -> None:
        data = {
            "providers": {
                "openai": {"key": "sk-abc"},
                "anthropic": {"key": "sk-ant-xyz"},
            },
            "default": "anthropic",
        }
        tmp_creds.parent.mkdir(parents=True, exist_ok=True)
        tmp_creds.write_text(json.dumps(data), encoding="utf-8")
        result = config.load_credentials()
        assert result["providers"]["anthropic"]["key"] == "sk-ant-xyz"

    def test_loads_empty_object(self, tmp_creds: Path) -> None:
        tmp_creds.parent.mkdir(parents=True, exist_ok=True)
        tmp_creds.write_text("{}", encoding="utf-8")
        result = config.load_credentials()
        assert result == {}


# ── save_credentials ─────────────────────────────────────────────────────────


class TestSaveCredentials:
    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "nested" / "credentials.json"
        with patch.object(config, "CREDENTIALS_PATH", nested):
            config.save_credentials({"key": "value"})
        assert nested.exists()

    def test_writes_valid_json(self, tmp_creds: Path) -> None:
        data = {"api_key": "sk-test-456", "model": "gpt-4"}
        config.save_credentials(data)
        written = json.loads(tmp_creds.read_text(encoding="utf-8"))
        assert written == data

    def test_overwrites_existing_file(self, tmp_creds: Path) -> None:
        tmp_creds.parent.mkdir(parents=True, exist_ok=True)
        tmp_creds.write_text(json.dumps({"old": "data"}), encoding="utf-8")
        config.save_credentials({"new": "data"})
        written = json.loads(tmp_creds.read_text(encoding="utf-8"))
        assert written == {"new": "data"}
        assert "old" not in written

    def test_atomic_write_no_partial_on_error(self, tmp_creds: Path) -> None:
        """If os.replace fails, temp file is cleaned up and original untouched."""
        tmp_creds.parent.mkdir(parents=True, exist_ok=True)
        original = {"original": True}
        tmp_creds.write_text(json.dumps(original), encoding="utf-8")

        with patch("os.replace", side_effect=OSError("disk full")):
            with pytest.raises(OSError, match="disk full"):
                config.save_credentials({"should": "fail"})

        # Original file unchanged
        assert json.loads(tmp_creds.read_text(encoding="utf-8")) == original
        # No temp files left behind
        tmp_files = list(tmp_creds.parent.glob(".tmp_*"))
        assert tmp_files == []

    def test_preserves_unicode(self, tmp_creds: Path) -> None:
        data = {"name": "日本語テスト", "emoji": "🚀"}
        config.save_credentials(data)
        written = json.loads(tmp_creds.read_text(encoding="utf-8"))
        assert written == data

    def test_round_trip(self, tmp_creds: Path) -> None:
        data = {"key": "value", "nested": {"a": 1, "b": [2, 3]}}
        config.save_credentials(data)
        loaded = config.load_credentials()
        assert loaded == data

    def test_formatted_with_indent(self, tmp_creds: Path) -> None:
        config.save_credentials({"a": 1})
        raw = tmp_creds.read_text(encoding="utf-8")
        assert "\n" in raw  # indented, not single-line


# ── Constants ────────────────────────────────────────────────────────────────


class TestConstants:
    def test_credentials_path_is_absolute(self) -> None:
        assert config.CREDENTIALS_PATH.is_absolute()

    def test_snapshots_dir_is_absolute(self) -> None:
        assert config.SNAPSHOTS_DIR.is_absolute()

    def test_env_var_names_defined(self) -> None:
        assert config.ENV_SESSION == "NATURO_SESSION"
        assert config.ENV_SNAPSHOT_TTL == "NATURO_SNAPSHOT_TTL"
        assert config.ENV_AI_MODEL == "NATURO_AI_MODEL"
        assert config.ENV_AI_PROVIDER == "NATURO_AI_PROVIDER"
        assert config.ENV_LOG_LEVEL == "NATURO_LOG_LEVEL"
