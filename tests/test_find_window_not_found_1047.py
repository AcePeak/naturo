"""Tests for find's window/app-not-found error classification (fixes #1047).

When the backend cannot locate the target window/app, ``naturo find`` used to
report the condition as a generic, *unrecoverable* ``UNKNOWN_ERROR`` with no
remediation hint — diverging from its sibling element-targeting commands
(``see``/``menu-inspect``/``highlight``), which return a recoverable
``WINDOW_NOT_FOUND`` envelope with a ``suggested_action``.

The backend's ``get_element_tree`` *raises* a :class:`WindowNotFoundError`
(message ``"Window not found: <target>"``) rather than returning ``None``, so
the dedicated ``WINDOW_NOT_FOUND`` branch (which only fires when ``tree is
None``) was dead for the raise path, and the broad ``except Exception``
flattened the structured error into ``UNKNOWN_ERROR``.

These tests pin the corrected contract: a not-found target yields a recoverable
``WINDOW_NOT_FOUND`` envelope, identical in shape to what ``see`` emits.
"""

import json

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from naturo.cli.core import find_cmd
from naturo.errors import WindowNotFoundError


@pytest.fixture
def runner():
    return CliRunner()


def _backend_raising(exc):
    """Build a mocked backend whose get_element_tree raises ``exc``."""
    mock_be = MagicMock()
    mock_be.get_element_tree.side_effect = exc
    return mock_be


class TestFindWindowNotFound:
    """find must classify a missing window/app as recoverable WINDOW_NOT_FOUND."""

    def test_window_not_found_emits_recoverable_envelope(self, runner):
        """A raised WindowNotFoundError → WINDOW_NOT_FOUND, recoverable, with a hint."""
        mock_be = _backend_raising(WindowNotFoundError("NaturoNoSuchApp_QA_PROBE"))
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=mock_be):
            result = runner.invoke(find_cmd, ["button", "--app", "NaturoNoSuchApp_QA_PROBE", "--json"])

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["success"] is False
        error = payload["error"]
        # The defining regression: no longer an unknown/unrecoverable failure.
        assert error["code"] == "WINDOW_NOT_FOUND"
        assert error["code"] != "UNKNOWN_ERROR"
        assert error["category"] == "automation"
        assert error["recoverable"] is True
        assert error["suggested_action"]  # non-null, non-empty guidance
        assert "NaturoNoSuchApp_QA_PROBE" in error["message"]

    def test_window_not_found_matches_see_envelope(self, runner):
        """find's not-found envelope is identical in shape to see's (#1047 sibling parity)."""
        from naturo.cli.core import see

        exc = WindowNotFoundError("BogusWindowTitle")

        def _run(cmd, args):
            mock_be = _backend_raising(exc)
            with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
                 patch("naturo.cli.core._common._get_backend", return_value=mock_be):
                return runner.invoke(cmd, args)

        find_err = json.loads(_run(find_cmd, ["x", "--window", "BogusWindowTitle", "--json"]).output)["error"]
        see_err = json.loads(_run(see, ["--window", "BogusWindowTitle", "--json"]).output)["error"]

        # Same keys, same code/category/recoverable classification across siblings.
        assert set(find_err) == set(see_err)
        assert find_err["code"] == see_err["code"] == "WINDOW_NOT_FOUND"
        assert find_err["category"] == see_err["category"]
        assert find_err["recoverable"] == see_err["recoverable"] is True

    def test_window_not_found_text_mode(self, runner):
        """Without --json, the not-found path stays a clean 'Error:' line, exit 1."""
        mock_be = _backend_raising(WindowNotFoundError("BogusWindowTitle"))
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=mock_be):
            result = runner.invoke(find_cmd, ["x", "--window", "BogusWindowTitle"])

        assert result.exit_code == 1
        assert "Window not found: BogusWindowTitle" in result.output
        assert "UNKNOWN_ERROR" not in result.output

    def test_unexpected_error_still_unknown(self, runner):
        """A genuinely unexpected backend failure is still reported as UNKNOWN_ERROR."""
        mock_be = _backend_raising(RuntimeError("disk on fire"))
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=mock_be):
            result = runner.invoke(find_cmd, ["x", "--app", "Whatever", "--json"])

        assert result.exit_code == 1
        error = json.loads(result.output)["error"]
        assert error["code"] == "UNKNOWN_ERROR"
        assert error["recoverable"] is False
