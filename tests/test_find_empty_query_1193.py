"""Tests for `find` rejecting an empty/whitespace-only query (fixes #1193).

`naturo find ""` and `naturo find "   "` previously normalized to the ``*``
wildcard and matched **every** element with ``success: true`` — identical to
``--all`` — while ``naturo find`` (argument omitted) correctly errored with
``INVALID_INPUT``. An empty string is, from the caller's perspective, the same
"no query given" situation (a typo / an unpopulated ``naturo find "$VAR"``), so
a silent match-all dump masquerading as success is exactly the silent-wrong
class QA guards against. The default text path now agrees with the
selector/image modes (which already reject empty input) and with the
argument-omitted path: empty/whitespace → ``INVALID_INPUT``. Callers that want
every element opt in explicitly via ``--all`` (or narrow with
``--role``/``--actionable``).
"""

import json

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
    mock_be.get_element_tree.return_value = None
    with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
         patch("naturo.cli.core._common._get_backend", return_value=mock_be):
        yield mock_be


class TestFindEmptyQueryRejected:
    """An empty / whitespace-only query must error, never silently match-all."""

    @pytest.mark.parametrize("args", [
        ["", "--json"],
        ["   ", "--json"],
        ["-q", "", "--json"],
        ["-q", "   ", "--json"],
    ])
    def test_empty_query_json_errors_invalid_input(self, runner, args):
        """Empty/whitespace query returns an INVALID_INPUT envelope, not success."""
        result = runner.invoke(find_cmd, args)
        assert result.exit_code != 0, result.output
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        # It must NOT have fallen through to a match-all element dump.
        assert "elements" not in data

    def test_empty_query_does_not_reach_backend(self, runner, mock_backend):
        """The empty-query guard fires before any backend tree fetch."""
        result = runner.invoke(find_cmd, ["", "--json"])
        assert result.exit_code != 0
        mock_backend.get_element_tree.assert_not_called()

    @pytest.mark.parametrize("args", [[""], ["   "]])
    def test_empty_query_plain_text_errors(self, runner, args):
        """Without --json the empty query shows a plain-text error and exits 1."""
        result = runner.invoke(find_cmd, args)
        assert result.exit_code != 0
        assert "Error" in (result.output or "")


class TestFindEmptyQueryWithExplicitMatchAll:
    """--all / --role / --actionable keep the explicit match-all intent."""

    def test_empty_query_with_all_flag_passes_gate(self, runner, mock_backend):
        """`find "" --all` opts into match-all, so it reaches the backend."""
        result = runner.invoke(find_cmd, ["", "--all", "--json"])
        # Mock tree is None → WINDOW_NOT_FOUND, but the empty-query gate is passed.
        assert "INVALID_INPUT" not in (result.output or "")
        mock_backend.get_element_tree.assert_called()

    def test_empty_query_with_actionable_passes_gate(self, runner, mock_backend):
        """`find "" --actionable` keeps the wildcard intent (#124 parity)."""
        result = runner.invoke(find_cmd, ["", "--actionable", "--json"])
        assert "INVALID_INPUT" not in (result.output or "")
        mock_backend.get_element_tree.assert_called()

    def test_empty_query_with_role_passes_gate(self, runner, mock_backend):
        """`find "" --role Button` keeps the wildcard intent (#124 parity)."""
        result = runner.invoke(find_cmd, ["", "--role", "Button", "--json"])
        assert "INVALID_INPUT" not in (result.output or "")
        mock_backend.get_element_tree.assert_called()
