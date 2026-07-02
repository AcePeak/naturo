"""Regression tests for #1173 — ``naturo find --limit`` must reject < 1.

Before this fix, ``--limit 0`` / ``--limit -3`` were accepted silently and
collapsed the result set to an empty (or, on the selector path, a *negatively
sliced* and silently-wrong) set while still reporting ``success: true`` — a
silent-misleading-result. Its sibling numeric options ``--depth`` and
``--threshold`` already rejected out-of-range input with a clean
``INVALID_INPUT`` envelope; ``--limit`` now matches them.

The validation is centralised *before any strategy dispatch* (tree / selector /
image / ai) and *before* the platform/GUI gate, so:

* every find strategy rejects a non-positive ``--limit`` identically, and
* the bad-input → error-code contract is platform-invariant — these tests run
  the real validation path with no platform mock, so they behave the same on a
  headless Linux/macOS CI runner as on a Windows desktop.
"""
from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from naturo.cli.core import find_cmd


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _error(result) -> dict:
    """Parse the JSON error envelope emitted on stdout."""
    return json.loads(result.output)["error"]


@pytest.mark.parametrize("bad_limit", ["0", "-1", "-3", "-100"])
def test_tree_path_rejects_non_positive_limit(runner, bad_limit) -> None:
    """Default tree-search path: ``--limit < 1`` is INVALID_INPUT, not empty success."""
    result = runner.invoke(
        find_cmd, ["--all", "--app", "notepad", "--limit", bad_limit, "--json"]
    )
    assert result.exit_code == 1
    err = _error(result)
    assert err["code"] == "INVALID_INPUT"
    # Assert the derived taxonomy (category + recoverable), not just the envelope
    # shape — these come from INVALID_INPUT being a registered ErrorCode, so a
    # bare-string code would silently degrade them (EVOLUTION error-code class).
    assert err["category"] == "validation"
    assert err["recoverable"] is False
    assert bad_limit in err["message"]
    assert "--limit" in err["message"]


@pytest.mark.parametrize("bad_limit", ["0", "-3"])
def test_selector_path_rejects_non_positive_limit(runner, bad_limit) -> None:
    """Selector path uses a literal ``[:limit]`` slice — a negative limit would
    slice from the end and return a *non-empty but silently-wrong* set. The
    up-front guard must fire before that path is ever reached."""
    result = runner.invoke(
        find_cmd, ["--selector", "//Button", "--limit", bad_limit, "--json"]
    )
    assert result.exit_code == 1
    assert _error(result)["code"] == "INVALID_INPUT"


@pytest.mark.parametrize("bad_limit", ["0", "-3"])
def test_image_path_rejects_non_positive_limit(runner, bad_limit) -> None:
    """Image-template path: validation fires before the template is even loaded,
    so no real image file (and no temp dir) is needed."""
    result = runner.invoke(
        find_cmd,
        ["--image", "anything.png", "--limit", bad_limit, "--json"],
    )
    assert result.exit_code == 1
    assert _error(result)["code"] == "INVALID_INPUT"


@pytest.mark.parametrize("good_limit", ["1", "100"])
def test_positive_limit_is_not_rejected_by_validation(runner, good_limit) -> None:
    """A valid ``--limit`` (including the inclusive lower bound ``1``) must not be
    turned away by the new guard. We assert the failure (if any) is *not* the
    limit-validation error — the command may still fail later for environment
    reasons, but never with the --limit message."""
    result = runner.invoke(
        find_cmd, ["--all", "--app", "does-not-exist", "--limit", good_limit, "--json"]
    )
    if result.exit_code != 0 and result.output.strip():
        message = json.loads(result.output).get("error", {}).get("message", "")
        assert "--limit must be a positive integer" not in message
