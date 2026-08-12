"""Tests for find command --query and --all options (fixes #112).

The --query/-q named option is an alternative to the positional QUERY
argument, specifically to avoid shell glob expansion of wildcards like ``*``.

The --all flag sets query to ``*`` internally without any shell-expandable
characters, making it fully safe for SSH and cmd.exe on Windows.
"""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from naturo.cli.core import find_cmd


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    """Mock the backend so find_cmd doesn't need a real GUI session."""
    mock_be = MagicMock()
    mock_be.find_elements.return_value = []
    mock_be.get_element_tree.return_value = None
    with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
         patch("naturo.cli.core._common._get_backend", return_value=mock_be):
        yield mock_be


class TestFindQueryOption:
    """Tests for the --query/-q alternative to positional QUERY."""

    def test_positional_query_accepted(self, runner, mock_backend):
        """Positional QUERY argument continues to be accepted."""
        result = runner.invoke(find_cmd, ["Save", "--json"])
        # Exit 1 is fine (mock returns no tree), but should NOT fail on query parsing
        assert "Missing argument" not in (result.output or "")
        mock_backend.get_element_tree.assert_called()

    def test_query_option_accepted(self, runner, mock_backend):
        """--query option is accepted and reaches backend."""
        result = runner.invoke(find_cmd, ["--query", "Save", "--json"])
        assert "Missing argument" not in (result.output or "")
        mock_backend.get_element_tree.assert_called()

    def test_query_short_option_accepted(self, runner, mock_backend):
        """Short form -q is accepted."""
        result = runner.invoke(find_cmd, ["-q", "Save", "--json"])
        assert "Missing argument" not in (result.output or "")
        mock_backend.get_element_tree.assert_called()

    def test_query_option_with_wildcard(self, runner, mock_backend):
        """--query '*' survives without shell glob expansion."""
        result = runner.invoke(find_cmd, ["--query", "*", "--json"])
        assert "Missing argument" not in (result.output or "")
        mock_backend.get_element_tree.assert_called()

    def test_query_option_conflicts_with_positional(self, runner, mock_backend):
        """Positional QUERY + --query is a conflict, not a silent override (#1201).

        The old behavior silently let -q win and dropped the positional query;
        supplying the text query via two sources now errors INVALID_INPUT rather
        than returning a confidently-wrong result set.
        """
        import json
        result = runner.invoke(find_cmd, ["positional", "--query", "named", "--json"])
        assert result.exit_code != 0, result.output
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT", data
        mock_backend.get_element_tree.assert_not_called()

    def test_no_query_gives_json_error(self, runner):
        """Missing both positional and --query gives a clear JSON error."""
        result = runner.invoke(find_cmd, ["--json"])
        assert result.exit_code != 0
        assert "QUERY" in (result.output or "") or "Missing" in (result.output or "")

    def test_no_query_gives_plain_error(self, runner):
        """Missing query without --json shows plain text error."""
        result = runner.invoke(find_cmd, [])
        assert result.exit_code != 0
        assert "QUERY" in (result.output or "") or "Missing" in (result.output or "")

    def test_actionable_without_query_uses_wildcard(self, runner, mock_backend):
        """--actionable without QUERY should implicitly use '*' wildcard (fixes #124)."""
        result = runner.invoke(find_cmd, ["--actionable", "--json"])
        assert "Missing argument" not in (result.output or "")
        mock_backend.get_element_tree.assert_called()

    def test_role_without_query_uses_wildcard(self, runner, mock_backend):
        """--role without QUERY should implicitly use '*' wildcard (fixes #124)."""
        result = runner.invoke(find_cmd, ["--role", "Button", "--json"])
        assert "Missing argument" not in (result.output or "")
        mock_backend.get_element_tree.assert_called()

    def test_actionable_with_role_without_query(self, runner, mock_backend):
        """--actionable --role without QUERY should work (fixes #124)."""
        result = runner.invoke(find_cmd, ["--actionable", "--role", "Button", "--json"])
        assert "Missing argument" not in (result.output or "")


class TestFindAllFlag:
    """Tests for the --all flag (fixes #112 — shell glob expansion on Windows)."""

    def test_all_flag_sets_wildcard(self, runner, mock_backend):
        """--all flag should work as equivalent to query '*'."""
        result = runner.invoke(find_cmd, ["--all", "--json"])
        assert "Missing argument" not in (result.output or "")
        mock_backend.get_element_tree.assert_called()

    def test_all_with_actionable(self, runner, mock_backend):
        """--all --actionable finds all actionable elements (wildcard)."""
        result = runner.invoke(find_cmd, ["--all", "--actionable", "--json"])
        assert "Missing argument" not in (result.output or "")
        mock_backend.get_element_tree.assert_called()

    def test_all_with_role_filter(self, runner, mock_backend):
        """--all --role Button finds all buttons."""
        result = runner.invoke(find_cmd, ["--all", "--role", "Button", "--json"])
        assert "Missing argument" not in (result.output or "")
        mock_backend.get_element_tree.assert_called()

    def test_all_conflicts_with_positional(self, runner, mock_backend):
        """--all + a positional query is a conflict, not a silent override (#1198).

        Previously --all silently discarded the positional query and matched
        every element as success:true. A positional/-q query combined with --all
        now errors INVALID_INPUT so the caller's real query is never dropped.
        """
        import json
        result = runner.invoke(find_cmd, ["Save", "--all", "--json"])
        assert result.exit_code != 0, result.output
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT", data
        mock_backend.get_element_tree.assert_not_called()
