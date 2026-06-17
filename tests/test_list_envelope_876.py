"""Regression tests for #876 — ``selector list -j`` and ``record list -j``
must emit the standard top-level JSON envelope (``success`` + ``count``).

Every other ``-j`` read command (``list apps``, ``app windows``,
``clipboard get`` ...) returns ``{"success": true, "<collection>": ..., "count": N}``
so a scripter can rely on a single ``jq '.success'`` error-check across the
whole CLI surface.  Before this fix, ``selector list -j`` returned a bare
app-keyed dict (``{}`` when empty) and ``record list -j`` returned
``{"recordings": [...]}`` — neither carried ``success`` or ``count``.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.cli import selector_cmd


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def tmp_selectors(tmp_path):
    """Patch the user-selectors directory to a temp location."""
    with patch.object(selector_cmd, "SELECTORS_DIR", tmp_path):
        yield tmp_path


class TestSelectorListEnvelope:
    def test_empty_has_success_and_zero_count(self, runner, tmp_selectors):
        result = runner.invoke(main, ["selector", "list", "-j"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["selectors"] == []
        assert data["count"] == 0

    def test_populated_lists_every_selector_with_count(self, runner, tmp_selectors):
        runner.invoke(main, ["selector", "save", "notepad", "btn1", "sel1"])
        runner.invoke(main, ["selector", "save", "chrome", "addr", "sel2"])
        result = runner.invoke(main, ["selector", "list", "-j"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 2
        assert len(data["selectors"]) == 2
        # Each record carries its owning app, name, and selector value.
        apps = {entry["app"] for entry in data["selectors"]}
        assert apps == {"notepad", "chrome"}
        for entry in data["selectors"]:
            assert set(entry) >= {"app", "name", "selector", "description"}
        notepad = next(e for e in data["selectors"] if e["app"] == "notepad")
        assert notepad["name"] == "btn1"
        assert notepad["selector"] == "sel1"

    def test_filter_by_app_keeps_envelope(self, runner, tmp_selectors):
        runner.invoke(main, ["selector", "save", "notepad", "btn1", "sel1"])
        runner.invoke(main, ["selector", "save", "chrome", "addr", "sel2"])
        result = runner.invoke(main, ["selector", "list", "--app", "notepad", "-j"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 1
        assert [e["app"] for e in data["selectors"]] == ["notepad"]


class TestRecordListEnvelope:
    def test_empty_has_success_and_zero_count(self, runner):
        with patch("naturo.cli.recording_cmd.list_recordings", return_value=[]), \
             patch("naturo.cli.recording_cmd.get_active_recording", return_value=None):
            result = runner.invoke(main, ["record", "list", "-j"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["recordings"] == []
        assert data["count"] == 0

    def test_populated_has_success_and_count(self, runner):
        recs = [
            {"recording_id": "rec_001", "name": "Flow A",
             "created_at": "2026-04-01", "step_count": 5},
            {"recording_id": "rec_002", "name": "Flow B",
             "created_at": "2026-04-02", "step_count": 3},
        ]
        with patch("naturo.cli.recording_cmd.list_recordings", return_value=recs), \
             patch("naturo.cli.recording_cmd.get_active_recording", return_value=None):
            result = runner.invoke(main, ["record", "list", "-j"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 2
        assert len(data["recordings"]) == 2
