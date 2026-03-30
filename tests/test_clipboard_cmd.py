"""Tests for naturo.cli.clipboard_cmd — clipboard get, set, clear, info."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.clipboard_cmd import clipboard


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    return MagicMock()


# ---------------------------------------------------------------------------
# clipboard get
# ---------------------------------------------------------------------------

class TestClipboardGet:
    """Tests for 'naturo clipboard get' command."""

    def test_get_text(self, runner, mock_backend):
        mock_backend.clipboard_get.return_value = "hello world"
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["get"])
        assert result.exit_code == 0
        assert "hello world" in result.output

    def test_get_empty(self, runner, mock_backend):
        mock_backend.clipboard_get.return_value = ""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["get"])
        assert result.exit_code == 0
        assert "clipboard is empty" in result.output

    def test_get_json(self, runner, mock_backend):
        mock_backend.clipboard_get.return_value = "test data"
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["get", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["text"] == "test data"
        assert data["length"] == 9
        assert data["format"] == "text"

    def test_get_json_empty(self, runner, mock_backend):
        mock_backend.clipboard_get.return_value = ""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["get", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["text"] == ""
        assert data["length"] == 0

    def test_get_error(self, runner, mock_backend):
        mock_backend.clipboard_get.side_effect = RuntimeError("access denied")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["get"])
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_get_error_json(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.clipboard_get.side_effect = NaturoError("CLIPBOARD_ERROR", "locked")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["get", "--json"])
        assert "CLIPBOARD_ERROR" in result.output or "error" in result.output.lower()

    def test_get_multiline_text(self, runner, mock_backend):
        mock_backend.clipboard_get.return_value = "line1\nline2\nline3"
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["get"])
        assert result.exit_code == 0
        assert "line1" in result.output
        assert "line2" in result.output


# ---------------------------------------------------------------------------
# clipboard set
# ---------------------------------------------------------------------------

class TestClipboardSet:
    """Tests for 'naturo clipboard set' command."""

    def test_set_text(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["set", "hello world"])
        assert result.exit_code == 0
        assert "Clipboard set" in result.output
        assert "11 chars" in result.output
        mock_backend.clipboard_set.assert_called_once_with("hello world")

    def test_set_json(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["set", "test", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "clipboard_set"
        assert data["length"] == 4

    def test_set_error(self, runner, mock_backend):
        mock_backend.clipboard_set.side_effect = RuntimeError("write failed")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["set", "data"])
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_set_missing_argument(self, runner):
        result = runner.invoke(clipboard, ["set"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# clipboard clear
# ---------------------------------------------------------------------------

class TestClipboardClear:
    """Tests for 'naturo clipboard clear' command."""

    def test_clear(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["clear"])
        assert result.exit_code == 0
        assert "Clipboard cleared" in result.output
        mock_backend.clipboard_clear.assert_called_once()

    def test_clear_json(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["clear", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "clipboard_clear"

    def test_clear_error(self, runner, mock_backend):
        mock_backend.clipboard_clear.side_effect = RuntimeError("failed")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["clear"])
        assert result.exit_code != 0 or "error" in result.output.lower()


# ---------------------------------------------------------------------------
# clipboard info
# ---------------------------------------------------------------------------

class TestClipboardInfo:
    """Tests for 'naturo clipboard info' command."""

    def test_info_with_text(self, runner, mock_backend):
        mock_backend.clipboard_info.return_value = {
            "format": "text",
            "size": 256,
            "has_text": True,
            "has_image": False,
            "has_files": False,
        }
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["info"])
        assert result.exit_code == 0
        assert "text" in result.output.lower()
        assert "256" in result.output
        assert "Available: text" in result.output

    def test_info_with_all_types(self, runner, mock_backend):
        mock_backend.clipboard_info.return_value = {
            "format": "multiple",
            "size": 1024,
            "has_text": True,
            "has_image": True,
            "has_files": True,
        }
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["info"])
        assert result.exit_code == 0
        assert "text" in result.output
        assert "image" in result.output
        assert "files" in result.output

    def test_info_empty_clipboard(self, runner, mock_backend):
        mock_backend.clipboard_info.return_value = {
            "format": "unknown",
            "size": 0,
            "has_text": False,
            "has_image": False,
            "has_files": False,
        }
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["info"])
        assert result.exit_code == 0
        assert "none" in result.output

    def test_info_json(self, runner, mock_backend):
        info_data = {
            "format": "text",
            "size": 100,
            "has_text": True,
            "has_image": False,
            "has_files": False,
        }
        mock_backend.clipboard_info.return_value = info_data
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["info", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["format"] == "text"
        assert data["size"] == 100

    def test_info_error(self, runner, mock_backend):
        mock_backend.clipboard_info.side_effect = RuntimeError("not available")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["info"])
        assert result.exit_code != 0 or "error" in result.output.lower()


# ---------------------------------------------------------------------------
# Backend unavailable
# ---------------------------------------------------------------------------

class TestClipboardBackendError:
    """Tests for backend unavailability handling."""

    def test_get_backend_error(self, runner):
        with patch("naturo.backends.base.get_backend", side_effect=RuntimeError("no backend")):
            result = runner.invoke(clipboard, ["get"])
        assert result.exit_code != 0

    def test_get_backend_error_json(self, runner):
        with patch("naturo.backends.base.get_backend", side_effect=RuntimeError("no backend")):
            result = runner.invoke(clipboard, ["get", "--json"])
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"] == "BACKEND_ERROR"


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

class TestClipboardHelp:
    """Tests for clipboard command help text."""

    def test_clipboard_help(self, runner):
        result = runner.invoke(clipboard, ["--help"])
        assert result.exit_code == 0
        assert "get" in result.output
        assert "set" in result.output
        assert "clear" in result.output
        assert "info" in result.output

    def test_get_help(self, runner):
        result = runner.invoke(clipboard, ["get", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_set_help(self, runner):
        result = runner.invoke(clipboard, ["set", "--help"])
        assert result.exit_code == 0
        assert "TEXT" in result.output
