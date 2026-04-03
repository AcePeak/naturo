"""Tests for naturo record CLI commands and recording engine."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.cli import recording_cmd
from naturo import recording as rec_mod
from naturo.recording import (
    ActionStep,
    Recording,
    generate_recording_id,
    save_recording,
    load_recording,
    list_recordings,
    delete_recording,
    append_step_to_active,
    get_active_recording,
    set_active_recording,
)


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def tmp_recordings(tmp_path):
    """Patch RECORDINGS_DIR so tests use a temp directory."""
    with patch.object(rec_mod, "RECORDINGS_DIR", tmp_path):
        yield tmp_path


def _make_recording(
    name: str = "Test Recording",
    rec_id: str = "rec_20260401_120000",
    steps: list | None = None,
) -> Recording:
    """Helper to create a Recording with optional steps."""
    rec = Recording(
        name=name,
        recording_id=rec_id,
        created_at="2026-04-01T12:00:00",
    )
    if steps:
        rec.steps = steps
    return rec


# ── ActionStep dataclass ────────────────────────────────────────────────────


class TestActionStep:
    def test_to_dict_roundtrip(self):
        step = ActionStep(command="click", args={"x": 100, "y": 200}, timestamp=1000.0)
        d = step.to_dict()
        restored = ActionStep.from_dict(d)
        assert restored.command == "click"
        assert restored.args == {"x": 100, "y": 200}
        assert restored.timestamp == 1000.0
        assert restored.duration_ms == 0.0

    def test_from_dict_with_duration(self):
        step = ActionStep.from_dict({
            "command": "type",
            "args": {"text": "hello"},
            "timestamp": 500.0,
            "duration_ms": 42.5,
        })
        assert step.duration_ms == 42.5

    def test_from_dict_missing_duration_defaults_zero(self):
        step = ActionStep.from_dict({
            "command": "press",
            "args": {"key": "enter"},
            "timestamp": 100.0,
        })
        assert step.duration_ms == 0.0


# ── Recording dataclass ────────────────────────────────────────────────────


class TestRecording:
    def test_add_step(self):
        rec = _make_recording()
        rec.add_step("click", {"x": 10, "y": 20}, duration_ms=5.0)
        assert len(rec.steps) == 1
        assert rec.steps[0].command == "click"

    def test_to_dict_roundtrip(self):
        rec = _make_recording()
        rec.add_step("click", {"x": 10}, duration_ms=1.0)
        d = rec.to_dict()
        restored = Recording.from_dict(d)
        assert restored.name == rec.name
        assert restored.recording_id == rec.recording_id
        assert len(restored.steps) == 1

    def test_total_duration_empty(self):
        rec = _make_recording()
        assert rec.total_duration_ms() == 0.0

    def test_total_duration_single_step(self):
        rec = _make_recording()
        rec.steps = [ActionStep("click", {}, 100.0, duration_ms=50.0)]
        assert rec.total_duration_ms() == 50.0

    def test_total_duration_multiple_steps(self):
        rec = _make_recording()
        rec.steps = [
            ActionStep("click", {}, 100.0, duration_ms=10.0),
            ActionStep("type", {}, 101.0, duration_ms=20.0),
        ]
        # elapsed = (101 - 100) * 1000 = 1000ms, + last duration 20 = 1020
        assert rec.total_duration_ms() == 1020.0


# ── Recording persistence ──────────────────────────────────────────────────


class TestRecordingPersistence:
    def test_save_and_load(self, tmp_recordings):
        rec = _make_recording()
        rec.add_step("click", {"x": 5, "y": 10})
        path = save_recording(rec)
        assert path.exists()
        loaded = load_recording(rec.recording_id)
        assert loaded.name == rec.name
        assert len(loaded.steps) == 1

    def test_load_not_found_raises(self, tmp_recordings):
        with pytest.raises(FileNotFoundError, match="not_real"):
            load_recording("not_real")

    def test_list_recordings_empty(self, tmp_recordings):
        assert list_recordings() == []

    def test_list_recordings_returns_summaries(self, tmp_recordings):
        save_recording(_make_recording("A", "rec_20260401_100000"))
        save_recording(_make_recording("B", "rec_20260401_110000"))
        recs = list_recordings()
        assert len(recs) == 2
        ids = [r["recording_id"] for r in recs]
        assert "rec_20260401_100000" in ids
        assert "rec_20260401_110000" in ids

    def test_delete_recording(self, tmp_recordings):
        save_recording(_make_recording())
        assert delete_recording("rec_20260401_120000") is True
        assert delete_recording("rec_20260401_120000") is False

    def test_delete_not_found(self, tmp_recordings):
        assert delete_recording("nonexistent") is False


# ── Active recording state ──────────────────────────────────────────────────


class TestActiveRecording:
    def test_get_active_none_by_default(self, tmp_recordings):
        assert get_active_recording() is None

    def test_set_and_get_active(self, tmp_recordings):
        rec = _make_recording()
        set_active_recording(rec)
        active = get_active_recording()
        assert active is not None
        assert active.recording_id == rec.recording_id

    def test_clear_active(self, tmp_recordings):
        set_active_recording(_make_recording())
        set_active_recording(None)
        assert get_active_recording() is None

    def test_append_step_to_active(self, tmp_recordings):
        set_active_recording(_make_recording())
        result = append_step_to_active("click", {"x": 1, "y": 2})
        assert result is True
        active = get_active_recording()
        assert len(active.steps) == 1

    def test_append_step_no_active(self, tmp_recordings):
        assert append_step_to_active("click", {"x": 1}) is False


# ── generate_recording_id ──────────────────────────────────────────────────


class TestGenerateRecordingId:
    def test_format(self):
        rid = generate_recording_id()
        assert rid.startswith("rec_")
        assert len(rid) == 19  # rec_YYYYMMDD_HHMMSS


# ── CLI: record start ──────────────────────────────────────────────────────


class TestRecordStart:
    def test_start_creates_active_recording(self, runner, tmp_recordings):
        result = runner.invoke(main, ["record", "start", "My Flow"])
        assert result.exit_code == 0
        assert "Recording started" in result.output
        assert "My Flow" in result.output

    def test_start_auto_names_when_no_name(self, runner, tmp_recordings):
        result = runner.invoke(main, ["record", "start"])
        assert result.exit_code == 0
        assert "Recording started" in result.output

    def test_start_json(self, runner, tmp_recordings):
        result = runner.invoke(main, ["record", "start", "Test", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["name"] == "Test"
        assert "recording_id" in data

    def test_start_fails_if_already_recording(self, runner, tmp_recordings):
        runner.invoke(main, ["record", "start", "First"])
        result = runner.invoke(main, ["record", "start", "Second"])
        assert result.exit_code != 0

    def test_start_fails_if_already_recording_json(self, runner, tmp_recordings):
        runner.invoke(main, ["record", "start", "First", "--json"])
        result = runner.invoke(main, ["record", "start", "Second", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False


# ── CLI: record stop ───────────────────────────────────────────────────────


class TestRecordStop:
    def test_stop_saves_recording(self, runner, tmp_recordings):
        runner.invoke(main, ["record", "start", "StopTest"])
        result = runner.invoke(main, ["record", "stop"])
        assert result.exit_code == 0
        assert "Recording stopped" in result.output
        assert "StopTest" in result.output

    def test_stop_json(self, runner, tmp_recordings):
        runner.invoke(main, ["record", "start", "StopJSON", "--json"])
        result = runner.invoke(main, ["record", "stop", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["name"] == "StopJSON"

    def test_stop_no_active_fails(self, runner, tmp_recordings):
        result = runner.invoke(main, ["record", "stop"])
        assert result.exit_code != 0

    def test_stop_no_active_json(self, runner, tmp_recordings):
        result = runner.invoke(main, ["record", "stop", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False


# ── CLI: record list ───────────────────────────────────────────────────────


class TestRecordList:
    def test_list_empty(self, runner, tmp_recordings):
        result = runner.invoke(main, ["record", "list"])
        assert result.exit_code == 0
        assert "No saved recordings" in result.output

    def test_list_with_recordings(self, runner, tmp_recordings):
        save_recording(_make_recording("Flow A", "rec_20260401_100000"))
        result = runner.invoke(main, ["record", "list"])
        assert result.exit_code == 0
        assert "rec_20260401_100000" in result.output
        assert "Flow A" in result.output

    def test_list_json(self, runner, tmp_recordings):
        save_recording(_make_recording("Flow B", "rec_20260401_110000"))
        result = runner.invoke(main, ["record", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["recordings"]) == 1

    def test_list_shows_active(self, runner, tmp_recordings):
        set_active_recording(_make_recording("Active", "rec_active"))
        result = runner.invoke(main, ["record", "list"])
        assert result.exit_code == 0
        assert "RECORDING" in result.output

    def test_list_json_includes_active(self, runner, tmp_recordings):
        set_active_recording(_make_recording("Active", "rec_active"))
        result = runner.invoke(main, ["record", "list", "--json"])
        data = json.loads(result.output)
        assert "active" in data


# ── CLI: record show ───────────────────────────────────────────────────────


class TestRecordShow:
    def test_show_displays_details(self, runner, tmp_recordings):
        rec = _make_recording()
        rec.add_step("click", {"x": 10, "y": 20})
        save_recording(rec)
        result = runner.invoke(main, ["record", "show", "rec_20260401_120000"])
        assert result.exit_code == 0
        assert "Test Recording" in result.output
        assert "Steps:" in result.output

    def test_show_json(self, runner, tmp_recordings):
        save_recording(_make_recording())
        result = runner.invoke(main, ["record", "show", "rec_20260401_120000", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["name"] == "Test Recording"

    def test_show_not_found(self, runner, tmp_recordings):
        result = runner.invoke(main, ["record", "show", "nonexistent"])
        assert result.exit_code != 0

    def test_show_not_found_json(self, runner, tmp_recordings):
        result = runner.invoke(main, ["record", "show", "nope", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False


# ── CLI: record delete ─────────────────────────────────────────────────────


class TestRecordDelete:
    def test_delete_with_force(self, runner, tmp_recordings):
        save_recording(_make_recording())
        result = runner.invoke(main, [
            "record", "delete", "rec_20260401_120000", "--force",
        ])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_json(self, runner, tmp_recordings):
        save_recording(_make_recording())
        result = runner.invoke(main, [
            "record", "delete", "rec_20260401_120000", "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True

    def test_delete_not_found(self, runner, tmp_recordings):
        result = runner.invoke(main, ["record", "delete", "nope", "--force"])
        assert result.exit_code != 0

    def test_delete_not_found_json(self, runner, tmp_recordings):
        result = runner.invoke(main, ["record", "delete", "nope", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False


# ── CLI: record export ─────────────────────────────────────────────────────


class TestRecordExport:
    @pytest.fixture()
    def saved_rec(self, tmp_recordings):
        rec = _make_recording()
        rec.steps = [
            ActionStep("click", {"x": 100, "y": 200}, 1000.0),
            ActionStep("type", {"text": "hello"}, 1001.0),
            ActionStep("press", {"key": "enter"}, 1002.0),
        ]
        save_recording(rec)
        return rec

    def test_export_json_format(self, runner, tmp_recordings, saved_rec):
        result = runner.invoke(main, [
            "record", "export", "rec_20260401_120000", "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["name"] == "Test Recording"
        assert len(data["steps"]) == 3

    def test_export_python_format(self, runner, tmp_recordings, saved_rec):
        result = runner.invoke(main, [
            "record", "export", "rec_20260401_120000", "--format", "python",
        ])
        assert result.exit_code == 0
        assert "#!/usr/bin/env python3" in result.output
        assert "naturo click" in result.output
        assert "naturo type" in result.output
        assert "naturo press" in result.output

    def test_export_bash_format(self, runner, tmp_recordings, saved_rec):
        result = runner.invoke(main, [
            "record", "export", "rec_20260401_120000", "--format", "bash",
        ])
        assert result.exit_code == 0
        assert "#!/bin/bash" in result.output
        assert "set -e" in result.output
        assert "naturo click" in result.output

    def test_export_to_file(self, runner, tmp_recordings, saved_rec, tmp_path):
        outfile = str(tmp_path / "out.json")
        result = runner.invoke(main, [
            "record", "export", "rec_20260401_120000",
            "--format", "json", "-o", outfile,
        ])
        assert result.exit_code == 0
        assert Path(outfile).exists()

    def test_export_json_output_flag(self, runner, tmp_recordings, saved_rec):
        result = runner.invoke(main, [
            "record", "export", "rec_20260401_120000",
            "--format", "python", "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["format"] == "python"
        assert "content" in data

    def test_export_not_found(self, runner, tmp_recordings):
        result = runner.invoke(main, [
            "record", "export", "nope", "--format", "json",
        ])
        assert result.exit_code != 0

    def test_export_not_found_json(self, runner, tmp_recordings):
        result = runner.invoke(main, [
            "record", "export", "nope", "--format", "json", "--json",
        ])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False


# ── CLI: record play ───────────────────────────────────────────────────────


class TestRecordPlay:
    @pytest.fixture()
    def saved_rec(self, tmp_recordings):
        rec = _make_recording()
        rec.steps = [
            ActionStep("click", {"x": 100, "y": 200}, 1000.0),
            ActionStep("type", {"text": "hello"}, 1000.1),
        ]
        save_recording(rec)
        return rec

    def test_play_dry_run(self, runner, tmp_recordings, saved_rec):
        result = runner.invoke(main, [
            "record", "play", "rec_20260401_120000", "--dry-run",
        ])
        assert result.exit_code == 0
        assert "Replay complete" in result.output
        assert "skipped" in result.output

    def test_play_dry_run_json(self, runner, tmp_recordings, saved_rec):
        result = runner.invoke(main, [
            "record", "play", "rec_20260401_120000", "--dry-run", "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_steps"] == 2
        assert data["skipped"] == 2

    def test_play_not_found(self, runner, tmp_recordings):
        result = runner.invoke(main, ["record", "play", "nope"])
        assert result.exit_code != 0

    def test_play_not_found_json(self, runner, tmp_recordings):
        result = runner.invoke(main, ["record", "play", "nope", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False


# ── _step_to_naturo_cmd ────────────────────────────────────────────────────


class TestStepToNaturoCmd:
    def test_click_with_coords(self):
        step = ActionStep("click", {"x": 100, "y": 200}, 0.0)
        cmd = recording_cmd._step_to_naturo_cmd(step)
        assert cmd == "naturo click 100 200"

    def test_click_with_button(self):
        step = ActionStep("click", {"x": 10, "y": 20, "button": "right"}, 0.0)
        cmd = recording_cmd._step_to_naturo_cmd(step)
        assert "--button right" in cmd

    def test_click_double(self):
        step = ActionStep("click", {"x": 1, "y": 2, "double_click": True}, 0.0)
        cmd = recording_cmd._step_to_naturo_cmd(step)
        assert "--double" in cmd

    def test_type_cmd(self):
        step = ActionStep("type", {"text": "hello world"}, 0.0)
        cmd = recording_cmd._step_to_naturo_cmd(step)
        assert cmd == 'naturo type "hello world"'

    def test_press_cmd(self):
        step = ActionStep("press", {"key": "enter"}, 0.0)
        cmd = recording_cmd._step_to_naturo_cmd(step)
        assert cmd == "naturo press enter"

    def test_hotkey_cmd(self):
        step = ActionStep("hotkey", {"keys": ["ctrl", "c"]}, 0.0)
        cmd = recording_cmd._step_to_naturo_cmd(step)
        assert cmd == "naturo hotkey ctrl+c"

    def test_scroll_cmd(self):
        step = ActionStep("scroll", {"direction": "up", "amount": 5}, 0.0)
        cmd = recording_cmd._step_to_naturo_cmd(step)
        assert "naturo scroll up" in cmd
        assert "--amount 5" in cmd

    def test_drag_cmd(self):
        step = ActionStep("drag", {
            "from_x": 0, "from_y": 0, "to_x": 100, "to_y": 100,
        }, 0.0)
        cmd = recording_cmd._step_to_naturo_cmd(step)
        assert "naturo drag" in cmd
        assert "--from 0 0" in cmd
        assert "--to 100 100" in cmd

    def test_move_cmd(self):
        step = ActionStep("move", {"x": 50, "y": 60}, 0.0)
        cmd = recording_cmd._step_to_naturo_cmd(step)
        assert cmd == "naturo move 50 60"

    def test_wait_cmd(self):
        step = ActionStep("wait", {"seconds": 2}, 0.0)
        cmd = recording_cmd._step_to_naturo_cmd(step)
        assert "naturo wait" in cmd
        assert "--duration 2" in cmd

    def test_unknown_cmd(self):
        step = ActionStep("custom_thing", {"a": 1}, 0.0)
        cmd = recording_cmd._step_to_naturo_cmd(step)
        assert "Unknown" in cmd


# ── _export_recording ──────────────────────────────────────────────────────


class TestExportRecording:
    def test_export_python_includes_sleep(self):
        rec = _make_recording()
        rec.steps = [
            ActionStep("click", {"x": 1, "y": 2}, 100.0),
            ActionStep("press", {"key": "a"}, 101.0),  # 1s gap
        ]
        content = recording_cmd._export_recording(rec, "python")
        assert "time.sleep" in content

    def test_export_bash_includes_sleep(self):
        rec = _make_recording()
        rec.steps = [
            ActionStep("click", {"x": 1, "y": 2}, 100.0),
            ActionStep("press", {"key": "a"}, 101.0),
        ]
        content = recording_cmd._export_recording(rec, "bash")
        assert "sleep" in content

    def test_export_unknown_format_returns_empty(self):
        rec = _make_recording()
        assert recording_cmd._export_recording(rec, "unknown_fmt") == ""


# ── help ────────────────────────────────────────────────────────────────────


class TestRecordHelp:
    def test_record_group_help(self, runner):
        result = runner.invoke(main, ["record", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output
        assert "stop" in result.output
        assert "play" in result.output
        assert "list" in result.output
        assert "show" in result.output
        assert "delete" in result.output
        assert "export" in result.output

    def test_record_start_help(self, runner):
        result = runner.invoke(main, ["record", "start", "--help"])
        assert result.exit_code == 0

    def test_record_stop_help(self, runner):
        result = runner.invoke(main, ["record", "stop", "--help"])
        assert result.exit_code == 0

    def test_record_play_help(self, runner):
        result = runner.invoke(main, ["record", "play", "--help"])
        assert result.exit_code == 0

    def test_record_list_help(self, runner):
        result = runner.invoke(main, ["record", "list", "--help"])
        assert result.exit_code == 0

    def test_record_show_help(self, runner):
        result = runner.invoke(main, ["record", "show", "--help"])
        assert result.exit_code == 0

    def test_record_delete_help(self, runner):
        result = runner.invoke(main, ["record", "delete", "--help"])
        assert result.exit_code == 0

    def test_record_export_help(self, runner):
        result = runner.invoke(main, ["record", "export", "--help"])
        assert result.exit_code == 0
