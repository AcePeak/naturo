"""``find --ai`` error JSON must carry the full six-key #884 envelope (#1179).

The ``_find_with_ai`` exception handler (``naturo/cli/core/_find.py``) used to
hand-roll its ``-j`` error as a two-key ``{"code", "message"}`` object, dropping
the four other canonical keys (``category``, ``context``, ``suggested_action``,
``recoverable``) that every other command's error path carries via
:func:`naturo.cli.error_helpers.json_error`. As a side effect the actionable
guidance registered for ``AI_PROVIDER_UNAVAILABLE`` ("set an API key …") never
reached the user. It also emitted an off-taxonomy, unregistered ``AI_FIND_FAILED``
code for the generic-failure branch, which would resolve to category ``unknown``
with no recovery hint.

These tests pin the contract for all three codes the handler assigns
(``AI_ANALYSIS_FAILED`` generic / ``AI_PROVIDER_UNAVAILABLE`` / ``CAPTURE_FAILED``):
the emitted JSON is the canonical six-key envelope, ``error.code`` resolves to a
registered code with the matching category, and ``suggested_action`` is non-empty.
They assert BEHAVIOR (the populated keys), so they fail on the old two-key shape.
"""
from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from naturo.cli.core._find import find_cmd

# The exact six keys the #884 error envelope must carry, in any order.
_SIX_KEYS = {"code", "message", "category", "context", "suggested_action", "recoverable"}


@pytest.fixture
def runner():
    return CliRunner()


def _invoke_ai_failure(runner, exc):
    """Drive ``find --ai --json`` with ``ai_find_element`` raising ``exc``."""
    with pytest.MonkeyPatch().context() as mp:
        def _boom(*args, **kwargs):
            raise exc

        mp.setattr("naturo.ai_find.ai_find_element", _boom)
        result = runner.invoke(find_cmd, ["the save button", "--ai", "--json"])
    return result


def _parse_error(result):
    """Assert non-zero exit and a well-formed error envelope, return the error obj."""
    assert result.exit_code != 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is False
    error = payload["error"]
    assert set(error.keys()) == _SIX_KEYS, (
        f"error envelope must carry exactly the six #884 keys, got {sorted(error)}"
    )
    return error


class TestFindAiErrorEnvelopeContract1179:
    """Every ``find --ai`` failure code emits the full six-key envelope."""

    def test_generic_failure_uses_registered_ai_analysis_failed(self, runner):
        """A generic detector crash yields the registered ``AI_ANALYSIS_FAILED``.

        The old code emitted an unregistered ``AI_FIND_FAILED`` string that would
        degrade to category ``unknown`` with no hint; the fix uses the canonical
        registered code so category resolves to ``ai`` and a recovery hint is set.
        """
        result = _invoke_ai_failure(runner, RuntimeError("detector crashed"))
        error = _parse_error(result)
        assert error["code"] == "AI_ANALYSIS_FAILED"
        assert error["category"] == "ai"
        assert error["suggested_action"]  # non-empty actionable guidance
        assert isinstance(error["recoverable"], bool)
        assert "detector crashed" in error["message"]

    def test_provider_unavailable_carries_set_api_key_guidance(self, runner):
        """``AI_PROVIDER_UNAVAILABLE`` must reach the user with its API-key hint."""
        result = _invoke_ai_failure(
            runner, RuntimeError("AI provider unavailable: auto")
        )
        error = _parse_error(result)
        assert error["code"] == "AI_PROVIDER_UNAVAILABLE"
        assert error["category"] == "ai"
        # The registered guidance (error_helpers.py) tells the user to set a key.
        assert "API key" in error["suggested_action"]
        assert error["recoverable"] is False

    def test_capture_failure_uses_registered_capture_failed(self, runner):
        """A capture-related message maps to the registered ``CAPTURE_FAILED``."""
        result = _invoke_ai_failure(
            runner, RuntimeError("screen capture failed: no display")
        )
        error = _parse_error(result)
        assert error["code"] == "CAPTURE_FAILED"
        assert error["category"] == "automation"
        assert error["suggested_action"]
        assert isinstance(error["recoverable"], bool)
