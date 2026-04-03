"""Tests for naturo record CLI commands."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.recording import (
    Recording,
    ActionStep,
    save_recording,
    set_active_recording,
    get_active_recording,
    RECORDINGS_DIR,
)


@pytest.fixture()
def tmp_recordings(tmp_path):
    """Patch RECORDINGS_DIR to use a temp directory."""
    with patch("naturo.recording.RECORDINGS_DIR", tmp_path):
        with patch("naturo.cli.recording_cmd.get_active_recording",
                    side_effect=lambda: get_active_recording(tmp_path)):
            yield tmp_path


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def sample_recording(tmp_path) -> Recording:
    """Create and save a sample recording."""
    rec = Recording(
        name="Test Recording",
        recording_id="rec_20260401_120000",
        created_at="2026-04-01T12:00:00",
        steps=[
            ActionStep(command="click", args={"x": 100, "y": 200}, timestamp=1000.0),
            ActionStep(command="type", args={"text": "hello"}, timestamp=1001.0),
            ActionStep(command="press", args={"key": "enter"}, timestamp=1002.0),
        ],
    )
    with patch("naturo.recording.RECORDINGS_DIR", tmp_path):
        save_recording(rec, tmp_path)
    return rec


# ── record start ─────────────────────────────────────────────────────────────


class TestRecordStart:
    def test_start_creates_active_recording(self, runner, tmp_path):
        with patch("naturo.recording.RECORDINGS_DIR", tmp_path), \
             patch("naturo.cli.recording_cmd.get_active_recording", return_value=None), \
             patch("naturo.cli.recording_cmd.set_active_recording") as mock_set:
            result = runner.invoke(main, ["record", "start", "My Flow"])
            assert result.exit_code == 0
            assert "Recording started" in result.output
            assert "My Flow" in result.output
            mock_set.assert_called_once()
            rec = mock_set.call_args[0][0]
            assert rec.name == "My Flow"
            assert rec.recording_id.startswith("rec_")

    def test_start_json_output(self, runner, tmp_path):
        with patch("naturo.recording.RECORDINGS_DIR", tmp_path), \
             patch("naturo.cli.recording_cmd.get_active_recording", return_value=None), \
             patch("naturo.cli.recording_cmd.set_active_recording"):
            result = runner.invoke(main, ["record", "start", "My Flow", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["success"] is True
            assert data["name"] == "My Flow"

    def test_start_fails_if_already_recording(self, runner):
        active = Recording(name="existing", recording_id="rec_old",
                           created_at="2026-01-01T00:00:00")
        with patch("naturo.cli.recording_cmd.get_active_recording", return_value=active):
            result = runner.invoke(main, ["record", "start", "New"])
            assert result.exit_code != 0
            assert "already in progress" in result.output


# ── record stop ──────────────────────────────────────────────────────────────


class TestRecordStop:
    def test_stop_saves_and_clears_active(self, runner, tmp_path):
        active = Recording(name="Test", recording_id="rec_test",
                           created_at="2026-01-01T00:00:00",
                           steps=[ActionStep("click", {"x": 1, "y": 2}, 1000.0)])
        with patch("naturo.cli.recording_cmd.get_active_recording", return_value=active), \
             patch("naturo.cli.recording_cmd.save_recording", return_value=tmp_path / "rec_test.json") as mock_save, \
             patch("naturo.cli.recording_cmd.set_active_recording") as mock_clear:
            result = runner.invoke(main, ["record", "stop"])
            assert result.exit_code == 0
            assert "rec_test" in result.output
            assert "1" in result.output  # step count
            mock_save.assert_called_once_with(active)
            mock_clear.assert_called_once_with(None)

    def test_stop_fails_if_not_recording(self, runner):
        with patch("naturo.cli.recording_cmd.get_active_recording", return_value=None):
            result = runner.invoke(main, ["record", "stop"])
            assert result.exit_code != 0
            assert "No active recording" in result.output


# ── record list ──────────────────────────────────────────────────────────────


class TestRecordList:
    def test_list_empty(self, runner):
        with patch("naturo.cli.recording_cmd.list_recordings", return_value=[]), \
             patch("naturo.cli.recording_cmd.get_active_recording", return_value=None):
            result = runner.invoke(main, ["record", "list"])
            assert result.exit_code == 0
            assert "No saved recordings" in result.output

    def test_list_shows_recordings(self, runner):
        recs = [
            {"recording_id": "rec_001", "name": "Flow A", "created_at": "2026-04-01T12:00:00", "step_count": 5},
            {"recording_id": "rec_002", "name": "Flow B", "created_at": "2026-04-01T13:00:00", "step_count": 3},
        ]
        with patch("naturo.cli.recording_cmd.list_recordings", return_value=recs), \
             patch("naturo.cli.recording_cmd.get_active_recording", return_value=None):
            result = runner.invoke(main, ["record", "list"])
            assert result.exit_code == 0
            assert "rec_001" in result.output
            assert "Flow A" in result.output
            assert "rec_002" in result.output

    def test_list_json(self, runner):
        recs = [{"recording_id": "rec_001", "name": "Flow A", "created_at": "2026-04-01", "step_count": 5}]
        with patch("naturo.cli.recording_cmd.list_recordings", return_value=recs), \
             patch("naturo.cli.recording_cmd.get_active_recording", return_value=None):
            result = runner.invoke(main, ["record", "list", "--json"])
            data = json.loads(result.output)
            assert len(data["recordings"]) == 1

    def test_list_shows_active_recording(self, runner):
        active = Recording(name="In progress", recording_id="rec_active",
                           created_at="2026-04-01T00:00:00",
                           steps=[ActionStep("click", {"x": 1, "y": 2}, 1000.0)])
        with patch("naturo.cli.recording_cmd.list_recordings", return_value=[]), \
             patch("naturo.cli.recording_cmd.get_active_recording", return_value=active):
            result = runner.invoke(main, ["record", "list"])
            assert "RECORDING" in result.output
            assert "rec_active" in result.output


# ── record show ──────────────────────────────────────────────────────────────


class TestRecordShow:
    def test_show_recording(self, runner):
        rec = Recording(
            name="Test", recording_id="rec_test", created_at="2026-04-01T12:00:00",
            steps=[
                ActionStep("click", {"x": 100, "y": 200}, 1000.0),
                ActionStep("type", {"text": "hello"}, 1001.0),
            ],
        )
        with patch("naturo.cli.recording_cmd.load_recording", return_value=rec):
            result = runner.invoke(main, ["record", "show", "rec_test"])
            assert result.exit_code == 0
            assert "rec_test" in result.output
            assert "click" in result.output
            assert "type" in result.output

    def test_show_not_found(self, runner):
        with patch("naturo.cli.recording_cmd.load_recording",
                    side_effect=FileNotFoundError("not found")):
            result = runner.invoke(main, ["record", "show", "rec_nope"])
            assert result.exit_code != 0


# ── record play ──────────────────────────────────────────────────────────────


class TestRecordPlay:
    def test_play_dry_run(self, runner):
        rec = Recording(
            name="Test", recording_id="rec_test", created_at="2026-04-01T12:00:00",
            steps=[ActionStep("click", {"x": 100, "y": 200}, 1000.0)],
        )
        with patch("naturo.cli.recording_cmd.load_recording", return_value=rec), \
             patch("naturo.cli.recording_cmd.replay_recording") as mock_replay:
            mock_replay.return_value = [{"step": 1, "command": "click", "args": {}, "status": "skipped"}]
            result = runner.invoke(main, ["record", "play", "rec_test", "--dry-run"])
            assert result.exit_code == 0
            mock_replay.assert_called_once()
            assert mock_replay.call_args[1]["dry_run"] is True

    def test_play_not_found(self, runner):
        with patch("naturo.cli.recording_cmd.load_recording",
                    side_effect=FileNotFoundError("not found")):
            result = runner.invoke(main, ["record", "play", "rec_nope"])
            assert result.exit_code != 0


# ── record delete ────────────────────────────────────────────────────────────


class TestRecordDelete:
    def test_delete_with_force(self, runner):
        rec = Recording(name="Test", recording_id="rec_test",
                        created_at="2026-04-01T12:00:00")
        with patch("naturo.cli.recording_cmd.load_recording", return_value=rec), \
             patch("naturo.cli.recording_cmd.delete_recording", return_value=True):
            result = runner.invoke(main, ["record", "delete", "rec_test", "--force"])
            assert result.exit_code == 0
            assert "Deleted" in result.output


# ── record export ────────────────────────────────────────────────────────────


class TestRecordExport:
    def test_export_json(self, runner):
        rec = Recording(
            name="Test", recording_id="rec_test", created_at="2026-04-01T12:00:00",
            steps=[ActionStep("click", {"x": 100, "y": 200}, 1000.0)],
        )
        with patch("naturo.cli.recording_cmd.load_recording", return_value=rec):
            result = runner.invoke(main, ["record", "export", "rec_test"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["recording_id"] == "rec_test"

    def test_export_python(self, runner):
        rec = Recording(
            name="Test", recording_id="rec_test", created_at="2026-04-01T12:00:00",
            steps=[
                ActionStep("click", {"x": 100, "y": 200}, 1000.0),
                ActionStep("type", {"text": "hello"}, 1001.5),
            ],
        )
        with patch("naturo.cli.recording_cmd.load_recording", return_value=rec):
            result = runner.invoke(main, ["record", "export", "rec_test", "--format", "python"])
            assert result.exit_code == 0
            assert "#!/usr/bin/env python3" in result.output
            assert 'naturo click 100 200' in result.output
            assert 'naturo type "hello"' in result.output
            assert "time.sleep" in result.output

    def test_export_bash(self, runner):
        rec = Recording(
            name="Test", recording_id="rec_test", created_at="2026-04-01T12:00:00",
            steps=[ActionStep("press", {"key": "enter"}, 1000.0)],
        )
        with patch("naturo.cli.recording_cmd.load_recording", return_value=rec):
            result = runner.invoke(main, ["record", "export", "rec_test", "--format", "bash"])
            assert result.exit_code == 0
            assert "#!/bin/bash" in result.output
            assert "naturo press enter" in result.output

    def test_export_to_file(self, runner, tmp_path):
        rec = Recording(
            name="Test", recording_id="rec_test", created_at="2026-04-01T12:00:00",
            steps=[ActionStep("click", {"x": 1, "y": 2}, 1000.0)],
        )
        out = str(tmp_path / "export.json")
        with patch("naturo.cli.recording_cmd.load_recording", return_value=rec):
            result = runner.invoke(main, ["record", "export", "rec_test", "-o", out])
            assert result.exit_code == 0
            assert Path(out).exists()


# ── record_action hook ───────────────────────────────────────────────────────


class TestRecordActionHook:
    def test_record_action_appends_to_active(self, tmp_path):
        """Verify _record_action hooks into the recording engine."""
        from naturo.cli.interaction._common import _record_action

        rec = Recording(name="Hook test", recording_id="rec_hook",
                        created_at="2026-04-01T12:00:00")
        with patch("naturo.recording.RECORDINGS_DIR", tmp_path):
            set_active_recording(rec, tmp_path)
            _record_action("click", {"x": 50, "y": 60})
            active = get_active_recording(tmp_path)
            assert active is not None
            assert len(active.steps) == 1
            assert active.steps[0].command == "click"

    def test_record_action_noop_without_active(self, tmp_path):
        """Verify _record_action is silent when no recording is active."""
        from naturo.cli.interaction._common import _record_action

        with patch("naturo.recording.RECORDINGS_DIR", tmp_path):
            set_active_recording(None, tmp_path)
            _record_action("click", {"x": 50, "y": 60})  # should not raise


# ── help text ────────────────────────────────────────────────────────────────


class TestRecordHelp:
    def test_record_help(self, runner):
        result = runner.invoke(main, ["record", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output
        assert "stop" in result.output
        assert "play" in result.output
        assert "list" in result.output
        assert "export" in result.output

    def test_record_start_help(self, runner):
        result = runner.invoke(main, ["record", "start", "--help"])
        assert result.exit_code == 0

    def test_record_play_help(self, runner):
        result = runner.invoke(main, ["record", "play", "--help"])
        assert result.exit_code == 0

    def test_record_export_help(self, runner):
        result = runner.invoke(main, ["record", "export", "--help"])
        assert result.exit_code == 0
