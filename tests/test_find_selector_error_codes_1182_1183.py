"""Find-engine selector error codes carry a complete envelope — #1182 + #1183.

Background
----------
The ``find``/``click``/``type --selector`` resolver (the v0.3.2 recognition-moat
surface) emits three error codes that were **raw string literals**, registered in
neither :data:`naturo.errors._ERROR_CATEGORIES` nor
:data:`naturo.cli.error_helpers._RECOVERY_HINTS`:

- ``SELECTOR_REF_ERROR`` — a saved ``@app/name`` reference that does not resolve
  (#1182). The sibling ``selector load``/``test``/``show`` subcommands use the
  registered ``SELECTOR_NOT_FOUND`` for the identical condition, so the moat path
  gave a *less* actionable error (``category:"unknown"`` + ``suggested_action:null``).
- ``INVALID_SELECTOR`` — a malformed selector string (validation fault, #1183).
- ``TREE_ERROR`` — a UI-tree-fetch failure during selector resolution
  (automation fault, #1183).

Because they bypassed the :class:`~naturo.errors.ErrorCode` enum, the #1101 drift
guard (``test_error_category_completeness_1101.py``) never covered them, so they
silently degraded to ``category:"unknown"`` with no recovery hint — defeating the
six-key #884 envelope contract on the moat surface. The fix promotes all three to
real ``ErrorCode`` members and registers their category + recovery hint, so the
#1101 guard now protects them permanently.

These tests are pure-Python (no DLL, no desktop) and run on every CI lane.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner
from unittest.mock import patch

from naturo.cli.core import find_cmd
from naturo.cli.error_helpers import json_error
from naturo.errors import ErrorCategory, ErrorCode, category_for_code

# The three codes this issue pair registers, with the categories chosen to match
# their already-mapped peers: a saved-selector reference is a named, session-scoped
# artifact like SELECTOR_NOT_FOUND (session); a malformed selector is a validation
# fault like INVALID_INPUT (validation); a tree-fetch fault during resolution is an
# automation operation failure like CAPTURE_FAILED (automation).
_EXPECTED = {
    "SELECTOR_REF_ERROR": (ErrorCategory.SESSION, False),
    "INVALID_SELECTOR": (ErrorCategory.VALIDATION, False),
    "TREE_ERROR": (ErrorCategory.AUTOMATION, True),
}


# ── 1. Each code is a first-class ErrorCode member (so #1101 guard covers it) ──


@pytest.mark.parametrize("code", sorted(_EXPECTED))
def test_code_is_a_registered_error_code(code: str) -> None:
    """The code is promoted out of a bare string into the ``ErrorCode`` enum."""
    assert getattr(ErrorCode, code) == code


# ── 2. category_for_code resolves the finalized, non-unknown category ─────────


@pytest.mark.parametrize("code,expected", sorted(_EXPECTED.items()))
def test_category_is_concrete(code: str, expected: tuple) -> None:
    assert category_for_code(code) == expected[0]
    assert category_for_code(code) != ErrorCategory.UNKNOWN


# ── 3. The full six-key envelope: category + non-null suggested_action ────────


@pytest.mark.parametrize("code", sorted(_EXPECTED))
def test_json_error_envelope_is_complete(code: str) -> None:
    """``json_error`` — the path these callsites use — emits all six keys filled.

    The bug was ``suggested_action:null`` + ``category:"unknown"``; pin that both
    are now populated (behavior, not shape).
    """
    expected_category, expected_recoverable = _EXPECTED[code]
    payload = json.loads(json_error(code, "selector resolution failed"))
    error = payload["error"]
    assert payload["success"] is False
    assert error["code"] == code
    assert error["category"] == expected_category
    assert error["suggested_action"] is not None
    assert error["suggested_action"].strip() != ""
    assert error["recoverable"] is expected_recoverable
    # The canonical six keys are all present (#884 contract).
    assert set(error) >= {
        "code", "message", "category", "context",
        "suggested_action", "recoverable",
    }


def test_selector_ref_error_points_at_selector_list() -> None:
    """#1182: the not-found hint reaches parity with ``SELECTOR_NOT_FOUND``.

    A user hitting "@app/name not found" via the find/click/type moat path now
    gets the same actionable pointer the ``selector`` subcommands already give.
    """
    payload = json.loads(json_error("SELECTOR_REF_ERROR", "Selector not found: @noapp/nobtn"))
    assert "selector list" in payload["error"]["suggested_action"]


# ── 4. End-to-end through the real ``find`` CLI (platform-invariant paths) ────
#
# INVALID_SELECTOR and SELECTOR_REF_ERROR are emitted BEFORE the GUI-platform gate
# and any backend call, so these drive the real command on every OS without a DLL.


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_find_invalid_selector_envelope_end_to_end(runner) -> None:
    result = runner.invoke(find_cmd, ["--selector", "app://", "--json"])
    assert result.exit_code == 1
    error = json.loads(result.output)["error"]
    assert error["code"] == "INVALID_SELECTOR"
    assert error["category"] == ErrorCategory.VALIDATION
    assert error["suggested_action"] is not None


def test_find_selector_ref_error_envelope_end_to_end(runner) -> None:
    with patch(
        "naturo.cli.selector_cmd.resolve_named_selector",
        side_effect=KeyError("Selector not found: @ghost/btn"),
    ):
        result = runner.invoke(find_cmd, ["--selector", "@ghost/btn", "--json"])
    assert result.exit_code == 1
    error = json.loads(result.output)["error"]
    assert error["code"] == "SELECTOR_REF_ERROR"
    assert error["category"] == ErrorCategory.SESSION
    assert error["suggested_action"] is not None
    assert "selector list" in error["suggested_action"]
