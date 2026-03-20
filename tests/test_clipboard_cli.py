"""Tests for naturo clipboard CLI commands.

Tests clipboard get/set functionality including text mode, file mode,
stdin piping, JSON output consistency, and error handling.
"""
import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli import main


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_backend():
    """Mock backend with clipboard methods."""
    backend = MagicMock()
    backend.clipboard_get.return_value = "Hello World"
    backend.clipboard_set.return_value = None
    return backend


# ── clipboard get ───────────────────────────────


class TestClipboardGet:
    """Tests for 'naturo clipboard get'."""

    def test_get_text(self, runner, mock_backend):
        """clipboard get prints clipboard text to stdout."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get"])
        assert result.exit_code == 0
        assert result.output == "Hello World"
        mock_backend.clipboard_get.assert_called_once()

    def test_get_empty_clipboard(self, runner, mock_backend):
        """clipboard get with empty clipboard prints nothing."""
        mock_backend.clipboard_get.return_value = ""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get"])
        assert result.exit_code == 0
        assert result.output == ""

    def test_get_json(self, runner, mock_backend):
        """clipboard get --json outputs structured JSON."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["text"] == "Hello World"

    def test_get_json_empty(self, runner, mock_backend):
        """clipboard get --json with empty clipboard."""
        mock_backend.clipboard_get.return_value = ""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["text"] == ""

    def test_get_unicode(self, runner, mock_backend):
        """clipboard get handles Unicode content (Chinese characters)."""
        mock_backend.clipboard_get.return_value = "你好世界 🌍"
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get"])
        assert result.exit_code == 0
        assert "你好世界 🌍" in result.output

    def test_get_json_unicode(self, runner, mock_backend):
        """clipboard get --json handles Unicode in JSON output."""
        mock_backend.clipboard_get.return_value = "中文路径测试"
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["text"] == "中文路径测试"

    def test_get_multiline(self, runner, mock_backend):
        """clipboard get preserves multiline content."""
        mock_backend.clipboard_get.return_value = "line1\nline2\nline3"
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get"])
        assert result.exit_code == 0
        assert "line1\nline2\nline3" in result.output

    def test_get_error_json(self, runner, mock_backend):
        """clipboard get --json returns structured error on failure."""
        mock_backend.clipboard_get.side_effect = Exception("Clipboard locked")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "UNKNOWN_ERROR"
        assert "Clipboard locked" in data["error"]["message"]

    def test_get_error_text(self, runner, mock_backend):
        """clipboard get shows user-friendly error on failure."""
        mock_backend.clipboard_get.side_effect = Exception("Clipboard locked")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get"])
        assert result.exit_code != 0


# ── clipboard set ───────────────────────────────


class TestClipboardSet:
    """Tests for 'naturo clipboard set'."""

    def test_set_text(self, runner, mock_backend):
        """clipboard set sets text to clipboard."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "set", "Hello World"])
        assert result.exit_code == 0
        mock_backend.clipboard_set.assert_called_once_with("Hello World")
        assert "11 chars" in result.output

    def test_set_text_json(self, runner, mock_backend):
        """clipboard set --json outputs structured JSON."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "set", "test", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["length"] == 4

    def test_set_unicode(self, runner, mock_backend):
        """clipboard set handles Unicode text."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "set", "你好世界"])
        assert result.exit_code == 0
        mock_backend.clipboard_set.assert_called_once_with("你好世界")

    def test_set_from_file(self, runner, mock_backend):
        """clipboard set --file reads content from file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("file content here")
            f.flush()
            temp_path = f.name

        try:
            with patch("naturo.backends.base.get_backend", return_value=mock_backend):
                result = runner.invoke(main, ["clipboard", "set", "--file", temp_path])
            assert result.exit_code == 0
            mock_backend.clipboard_set.assert_called_once_with("file content here")
        finally:
            os.unlink(temp_path)

    def test_set_from_file_json(self, runner, mock_backend):
        """clipboard set --file --json outputs structured JSON."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("abc")
            f.flush()
            temp_path = f.name

        try:
            with patch("naturo.backends.base.get_backend", return_value=mock_backend):
                result = runner.invoke(
                    main, ["clipboard", "set", "--file", temp_path, "--json"]
                )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["success"] is True
            assert data["length"] == 3
        finally:
            os.unlink(temp_path)

    def test_set_text_and_file_conflict(self, runner, mock_backend):
        """clipboard set rejects both text and --file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write("x")
            temp_path = f.name

        try:
            with patch("naturo.backends.base.get_backend", return_value=mock_backend):
                result = runner.invoke(
                    main, ["clipboard", "set", "text", "--file", temp_path]
                )
            assert result.exit_code != 0
        finally:
            os.unlink(temp_path)

    def test_set_conflict_json(self, runner, mock_backend):
        """clipboard set text+file conflict returns JSON error."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write("x")
            temp_path = f.name

        try:
            with patch("naturo.backends.base.get_backend", return_value=mock_backend):
                result = runner.invoke(
                    main, ["clipboard", "set", "text", "--file", temp_path, "--json"]
                )
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["success"] is False
            assert data["error"]["code"] == "INVALID_INPUT"
        finally:
            os.unlink(temp_path)

    def test_set_no_args_reads_stdin(self, runner, mock_backend):
        """clipboard set with no args reads empty stdin (pipe scenario)."""
        # CliRunner stdin is not a TTY, so it reads from stdin (empty → empty string)
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "set"], input="")
        assert result.exit_code == 0
        mock_backend.clipboard_set.assert_called_once_with("")

    def test_set_from_stdin(self, runner, mock_backend):
        """clipboard set reads from stdin when piped."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "set"], input="piped text")
        assert result.exit_code == 0
        mock_backend.clipboard_set.assert_called_once_with("piped text")

    def test_set_error_json(self, runner, mock_backend):
        """clipboard set --json returns structured error on backend failure."""
        mock_backend.clipboard_set.side_effect = Exception("Access denied")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "set", "test", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert "Access denied" in data["error"]["message"]

    def test_set_error_text(self, runner, mock_backend):
        """clipboard set shows user-friendly error on backend failure."""
        mock_backend.clipboard_set.side_effect = Exception("Access denied")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "set", "test"])
        assert result.exit_code != 0

    def test_set_empty_string(self, runner, mock_backend):
        """clipboard set with empty string clears clipboard."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "set", ""])
        assert result.exit_code == 0
        mock_backend.clipboard_set.assert_called_once_with("")


# ── JSON consistency ────────────────────────────


class TestClipboardJsonConsistency:
    """Verify clipboard JSON output matches project-wide schema."""

    def test_get_success_has_success_field(self, runner, mock_backend):
        """JSON success responses always include 'success': true."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get", "--json"])
        data = json.loads(result.output)
        assert "success" in data
        assert data["success"] is True

    def test_set_success_has_success_field(self, runner, mock_backend):
        """JSON success responses always include 'success': true."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "set", "x", "--json"])
        data = json.loads(result.output)
        assert "success" in data
        assert data["success"] is True

    def test_error_has_standard_structure(self, runner, mock_backend):
        """JSON errors follow {success: false, error: {code, message}} schema."""
        mock_backend.clipboard_get.side_effect = Exception("fail")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get", "--json"])
        data = json.loads(result.output)
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]


# ── Help text ───────────────────────────────────


class TestClipboardHelp:
    """Verify help output is correct and not stub text."""

    def test_clipboard_help(self, runner):
        """clipboard --help shows group help."""
        result = runner.invoke(main, ["clipboard", "--help"])
        assert result.exit_code == 0
        assert "clipboard" in result.output.lower()
        assert "Not implemented" not in result.output

    def test_clipboard_get_help(self, runner):
        """clipboard get --help shows command help."""
        result = runner.invoke(main, ["clipboard", "get", "--help"])
        assert result.exit_code == 0
        assert "Not implemented" not in result.output

    def test_clipboard_set_help(self, runner):
        """clipboard set --help shows command help."""
        result = runner.invoke(main, ["clipboard", "set", "--help"])
        assert result.exit_code == 0
        assert "Not implemented" not in result.output
