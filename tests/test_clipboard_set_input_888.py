"""Tests for 'naturo clipboard set' file/stdin input sources (issue #888).

`naturo type` accepts ``--file PATH`` for large/multi-line payloads; `clipboard
set` historically only took a positional ``TEXT`` argument bounded by the shell
ARG_MAX limit. These tests pin the symmetric input paths added in #888:

* ``--file PATH`` reads the clipboard payload from a file (mirrors ``type --file``)
* ``-`` reads the payload from stdin (jq/sed convention)
* mutually-exclusive sources and a missing file fail with a clean error envelope
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.system import clipboard


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    return MagicMock()


class TestClipboardSetFromFile:
    """'naturo clipboard set --file PATH' reads the payload from a file."""

    def test_set_from_file(self, runner, mock_backend, tmp_path):
        payload = "line1\nline2\nline3"
        src = tmp_path / "note.txt"
        src.write_text(payload, encoding="utf-8")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["set", "--file", str(src)])
        assert result.exit_code == 0
        mock_backend.clipboard_set.assert_called_once_with(payload)

    def test_set_from_file_json_length(self, runner, mock_backend, tmp_path):
        payload = "x" * 51200  # exceeds the shell ARG_MAX positional cap
        src = tmp_path / "big.txt"
        src.write_text(payload, encoding="utf-8")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["set", "--file", str(src), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["length"] == 51200
        mock_backend.clipboard_set.assert_called_once_with(payload)

    def test_set_from_file_preserves_real_newlines(self, runner, mock_backend, tmp_path):
        # A real newline in the file must reach the backend as a real newline,
        # not a literal backslash-n (the misleading-help case from #888).
        src = tmp_path / "multi.txt"
        src.write_text("a\nb", encoding="utf-8")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["set", "--file", str(src)])
        assert result.exit_code == 0
        (stored,), _ = mock_backend.clipboard_set.call_args
        assert stored == "a\nb"
        assert "\\n" not in stored

    def test_set_missing_file(self, runner, mock_backend, tmp_path):
        missing = tmp_path / "does_not_exist.txt"
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["set", "--file", str(missing), "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        mock_backend.clipboard_set.assert_not_called()


class TestClipboardSetFromStdin:
    """'naturo clipboard set -' reads the payload from stdin."""

    def test_set_from_stdin(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["set", "-"], input="piped text")
        assert result.exit_code == 0
        mock_backend.clipboard_set.assert_called_once_with("piped text")

    def test_set_from_stdin_json(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["set", "-", "--json"], input="hello\nworld")
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["length"] == len("hello\nworld")
        mock_backend.clipboard_set.assert_called_once_with("hello\nworld")


class TestClipboardSetSourceValidation:
    """Source selection is mutually exclusive and at least one is required."""

    def test_text_and_file_conflict(self, runner, mock_backend, tmp_path):
        src = tmp_path / "note.txt"
        src.write_text("from file", encoding="utf-8")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(
                clipboard, ["set", "literal", "--file", str(src), "--json"]
            )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        mock_backend.clipboard_set.assert_not_called()

    def test_no_source(self, runner, mock_backend):
        # No positional TEXT, no --file, no stdin marker -> clean error.
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["set", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        mock_backend.clipboard_set.assert_not_called()

    def test_literal_text_still_works(self, runner, mock_backend):
        # Regression: the plain positional path is unchanged.
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(clipboard, ["set", "hello world"])
        assert result.exit_code == 0
        mock_backend.clipboard_set.assert_called_once_with("hello world")


class TestClipboardSetHelp:
    """Help text documents the new sources and drops the misleading example."""

    def test_help_mentions_file_and_stdin(self, runner):
        result = runner.invoke(clipboard, ["set", "--help"])
        assert result.exit_code == 0
        assert "--file" in result.output
        # The old example implied naturo interprets a literal '\n' as a newline,
        # which it never did (#888). It must be gone.
        assert "line1\\nline2" not in result.output
