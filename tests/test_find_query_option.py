"""Tests for find command --query option (fixes #112).

The --query/-q named option is an alternative to the positional QUERY
argument, specifically to avoid shell glob expansion of wildcards like ``*``.
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
    with patch("naturo.cli.core._platform_supports_gui", return_value=True), \
         patch("naturo.cli.core._get_backend", return_value=mock_be):
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

    def test_query_option_overrides_positional(self, runner, mock_backend):
        """When both provided, --query takes precedence over positional."""
        result = runner.invoke(find_cmd, ["positional", "--query", "named", "--json"])
        assert "Missing argument" not in (result.output or "")

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
