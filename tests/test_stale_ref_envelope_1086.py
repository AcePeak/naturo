"""Contract test for the stale ``eN`` snapshot-ref error envelope (#1086).

Every command that accepts an ``eN`` element ref resolves it against the most
recent ``see`` snapshot *before* doing any work. When that ref is missing or
stale the failure is **recoverable** — the agent just needs to run ``naturo
see`` and retry — and it is the semantically identical condition that ``get`` /
``set`` already surface as the registered :class:`~naturo.errors.ErrorCode`
``STALE_SNAPSHOT_CACHE`` (``category:"session"``, ``recoverable:true``, with a
recovery hint and ``context={"ref": ...}``).

Before #1086 the interaction commands (``click``/``type``/``press``/``move``/
``drag``/``scroll``) and ``capture --element`` instead emitted a *bare string*
``code:"REF_NOT_FOUND"`` — absent from the ``ErrorCode`` enum and the recovery
registry — which silently degraded to ``category:"unknown"``,
``recoverable:false`` and ``suggested_action:null``. An AI agent dispatching on
those fields to self-correct hit a dead end on the single most-used command
(``click``).

This test pins the corrected contract — *category and recoverable*, not just the
envelope shape — across every command that accepts an ``eN`` ref, so the
semantic leg cannot drift again (the shape-only contract test in #1001 passed
while these values were wrong).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli import main

#: ``(command-id, argv)`` for every command that resolves an ``eN`` ref. The ref
#: ``e999`` is never in the (mocked-empty) snapshot cache, so each invocation
#: takes the stale-ref leg.
STALE_REF_INVOCATIONS = [
    ("click", ["click", "--id", "e999", "-j"]),
    ("type", ["type", "hello", "--on", "e999", "-j"]),
    ("press", ["press", "enter", "--on", "e999", "-j"]),
    ("move", ["move", "--to", "e999", "-j"]),
    ("drag", ["drag", "--from", "e999", "--to", "e1", "-j"]),
    ("scroll", ["scroll", "down", "--on", "e999", "-j"]),
    ("capture", ["capture", "--element", "e999", "-j"]),
]


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _invoke_with_empty_snapshot(runner: CliRunner, argv: list[str]):
    """Run ``argv`` with a snapshot manager that resolves every ref to ``None``.

    Neutralises the snapshot cache and the live backend / auto-router so the
    forced path reflects the code, not the host's desktop state (hermetic on
    headless CI and a real desktop alike).
    """
    mock_mgr = MagicMock()
    mock_mgr.resolve_ref.return_value = None
    mock_mgr.resolve_ref_element.return_value = None
    with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr), \
         patch("naturo.cli.interaction._common._get_backend",
               return_value=MagicMock()), \
         patch("naturo.cli.interaction._common._auto_route", return_value={}):
        return runner.invoke(main, argv)


@pytest.mark.parametrize(
    "command,argv", STALE_REF_INVOCATIONS, ids=[c for c, _ in STALE_REF_INVOCATIONS]
)
def test_stale_ref_emits_recoverable_session_envelope(runner, command, argv):
    """An unknown ``eN`` ref yields the registered ``STALE_SNAPSHOT_CACHE`` envelope.

    Pins the agent-self-correction contract: a non-``unknown`` category, a
    recovery hint, ``recoverable:true`` and a ``{"ref": ...}`` context — matching
    ``get``/``set`` — for every command that accepts an ``eN`` ref.
    """
    result = _invoke_with_empty_snapshot(runner, argv)
    assert result.exit_code != 0, f"{command}: expected a non-zero exit, got 0"

    error = json.loads(result.output)["error"]
    assert error["code"] == "STALE_SNAPSHOT_CACHE", (
        f"{command}: code {error['code']!r} is not the registered ErrorCode"
    )
    assert error["category"] == "session", (
        f"{command}: category {error['category']!r} degraded (expected 'session')"
    )
    assert error["recoverable"] is True, (
        f"{command}: a stale ref is recoverable by running 'naturo see'"
    )
    assert error["suggested_action"], (
        f"{command}: missing the recovery hint that lets an agent self-correct"
    )
    assert error["context"] == {"ref": "e999"}, (
        f"{command}: context {error['context']!r} should carry the offending ref"
    )
