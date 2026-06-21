"""Regression tests for #1111: `naturo type` must be captured by `record`.

Before the fix, ``naturo/cli/interaction/_type.py`` never called
``_common._record_action`` on its success path, so a ``type`` performed while
a recording was active was silently dropped (``step_count`` stayed 0) even
though ``recording.py`` already replays a ``"type"`` step. A recorded login
flow's username/password typing was therefore lost on replay.

These tests drive the real recording pipeline (temp recordings dir + an
active recording) with a mocked backend, then assert the ``type`` step — and
its follow-up navigation keys — are captured. They are intentionally not
Windows-only: the typing path is exercised entirely through a mocked backend,
so the recording-capture contract is verified on every CI platform.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo import recording as rec_mod
from naturo.recording import Recording, get_active_recording, set_active_recording


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def active_recording(tmp_path):
    """Point recordings at a temp dir with one active (empty) recording."""
    with patch.object(rec_mod, "RECORDINGS_DIR", tmp_path):
        rec = Recording(
            name="login flow",
            recording_id="rec_20260401_120000",
            created_at="2026-04-01T12:00:00",
        )
        set_active_recording(rec)
        yield


def _invoke_type(runner, args):
    """Invoke the type command with a mocked backend and routing."""
    from naturo.cli.interaction import type_cmd

    mock_backend = MagicMock()
    mock_backend.clipboard_get.return_value = ""
    with patch(
        "naturo.cli.interaction._common._get_backend", return_value=mock_backend
    ), patch("naturo.cli.interaction._common._auto_route", return_value={}):
        return runner.invoke(type_cmd, args)


def test_type_is_recorded(runner, active_recording):
    """A `type` during an active recording yields a `type` step (text + wpm)."""
    result = _invoke_type(runner, ["QA_PROBE", "--wpm", "90", "--json", "--no-verify"])
    assert result.exit_code == 0, result.output

    rec = get_active_recording()
    assert rec is not None
    type_steps = [s for s in rec.steps if s.command == "type"]
    assert len(type_steps) == 1, f"expected one type step, got {rec.to_dict()}"
    assert type_steps[0].args["text"] == "QA_PROBE"
    assert type_steps[0].args["wpm"] == 90


def test_pasted_text_is_recorded_as_type(runner, active_recording):
    """`type "x" --paste` records a replayable `type` step with the text."""
    result = _invoke_type(runner, ["hello", "--paste", "--json", "--no-verify"])
    assert result.exit_code == 0, result.output

    rec = get_active_recording()
    type_steps = [s for s in rec.steps if s.command == "type"]
    assert len(type_steps) == 1
    assert type_steps[0].args["text"] == "hello"


def test_bare_clipboard_paste_is_not_recorded(runner, active_recording):
    """`type --paste` with no text has no capturable content → no step."""
    result = _invoke_type(runner, ["--paste", "--json"])
    assert result.exit_code == 0, result.output

    rec = get_active_recording()
    assert rec.steps == []


def test_followup_keys_are_recorded(runner, active_recording):
    """--return/--tab/--escape are captured as press steps after the type."""
    result = _invoke_type(
        runner,
        ["user", "--return", "--tab", "2", "--escape", "--json", "--no-verify"],
    )
    assert result.exit_code == 0, result.output

    rec = get_active_recording()
    captured = [(s.command, s.args) for s in rec.steps]
    assert captured == [
        ("type", {"text": "user", "wpm": 120}),
        ("press", {"key": "enter", "count": 1}),
        ("press", {"key": "tab", "count": 2}),
        ("press", {"key": "escape", "count": 1}),
    ]


def test_no_recording_active_is_a_noop(runner, tmp_path):
    """With no active recording, typing must not error (record is optional)."""
    with patch.object(rec_mod, "RECORDINGS_DIR", tmp_path):
        set_active_recording(None)  # ensure clean state
        result = _invoke_type(runner, ["hello", "--json", "--no-verify"])
    assert result.exit_code == 0, result.output
    with patch.object(rec_mod, "RECORDINGS_DIR", tmp_path):
        assert get_active_recording() is None
