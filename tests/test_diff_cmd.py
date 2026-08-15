"""Tests for naturo.cli.diff_cmd — UI tree diff command."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.diff_cmd import diff


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    return MagicMock()


def _make_diff_result(has_changes=True, added=None, removed=None, modified=None, summary="1 change"):
    result = MagicMock()
    result.has_changes = has_changes
    result.added = added or []
    result.removed = removed or []
    result.modified = modified or []
    result.summary = summary
    result.to_dict.return_value = {
        "has_changes": has_changes,
        "added": [{"role": c.element_role, "name": c.element_name} for c in (added or [])],
        "removed": [{"role": c.element_role, "name": c.element_name} for c in (removed or [])],
        "modified": [],
    }
    return result


def _make_change(role="Button", name="Save", path="root/panel", old_value=None, new_value=None):
    c = MagicMock()
    c.element_role = role
    c.element_name = name
    c.path = path
    c.old_value = old_value
    c.new_value = new_value
    return c


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class TestDiffValidation:
    def test_no_args(self, runner):
        result = runner.invoke(diff, [])
        assert result.exit_code != 0
        assert "Specify" in result.output or "Error" in result.output

    def test_no_args_json(self, runner):
        result = runner.invoke(diff, ["--json"])
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output

    def test_one_snapshot(self, runner):
        result = runner.invoke(diff, ["--snapshot", "snap1"])
        assert result.exit_code != 0
        assert "two" in result.output.lower() or "Error" in result.output

    def test_one_snapshot_json(self, runner):
        result = runner.invoke(diff, ["--snapshot", "snap1", "--json"])
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output

    def test_negative_interval(self, runner):
        result = runner.invoke(diff, ["--window", "Notepad", "--interval", "0"])
        assert result.exit_code != 0
        assert "interval" in result.output.lower() or "Error" in result.output

    def test_negative_interval_json(self, runner):
        result = runner.invoke(diff, ["--window", "Notepad", "--interval", "-1", "--json"])
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output


# ---------------------------------------------------------------------------
# Window-based diff
# ---------------------------------------------------------------------------

class TestDiffWindow:
    @patch("naturo.cli.diff_cmd.time.sleep")
    @patch("naturo.diff.diff_trees")
    def test_window_no_changes(self, mock_diff, mock_sleep, runner, mock_backend):
        mock_backend.get_element_tree.return_value = {"root": {}}
        mock_diff.return_value = _make_diff_result(has_changes=False)
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(diff, ["--window", "Notepad", "--interval", "0.01"])
        assert result.exit_code == 0
        assert "No changes" in result.output
        assert mock_backend.get_element_tree.call_count == 2

    @patch("naturo.cli.diff_cmd.time.sleep")
    @patch("naturo.diff.diff_trees")
    def test_window_with_added(self, mock_diff, mock_sleep, runner, mock_backend):
        mock_backend.get_element_tree.return_value = {"root": {}}
        added = [_make_change(role="Button", name="New")]
        mock_diff.return_value = _make_diff_result(added=added, summary="1 added")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(diff, ["--window", "Notepad", "--interval", "0.01"])
        assert result.exit_code == 0
        assert "Added" in result.output
        assert "Button" in result.output

    @patch("naturo.cli.diff_cmd.time.sleep")
    @patch("naturo.diff.diff_trees")
    def test_window_with_removed(self, mock_diff, mock_sleep, runner, mock_backend):
        mock_backend.get_element_tree.return_value = {"root": {}}
        removed = [_make_change(role="MenuItem", name="File")]
        mock_diff.return_value = _make_diff_result(removed=removed, summary="1 removed")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(diff, ["--window", "Notepad", "--interval", "0.01"])
        assert result.exit_code == 0
        assert "Removed" in result.output

    @patch("naturo.cli.diff_cmd.time.sleep")
    @patch("naturo.diff.diff_trees")
    def test_window_with_modified(self, mock_diff, mock_sleep, runner, mock_backend):
        mock_backend.get_element_tree.return_value = {"root": {}}
        modified = [_make_change(role="Edit", name="Input", old_value="old", new_value="new")]
        diff_result = _make_diff_result(modified=modified, summary="1 modified")
        mock_diff.return_value = diff_result
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(diff, ["--window", "Notepad", "--interval", "0.01"])
        assert result.exit_code == 0
        assert "Modified" in result.output

    @patch("naturo.cli.diff_cmd.time.sleep")
    @patch("naturo.diff.diff_trees")
    def test_window_json(self, mock_diff, mock_sleep, runner, mock_backend):
        mock_backend.get_element_tree.return_value = {"root": {}}
        mock_diff.return_value = _make_diff_result(has_changes=False)
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(diff, ["--window", "Notepad", "--interval", "0.01", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True

    @patch("naturo.cli.diff_cmd.time.sleep")
    def test_window_not_found_first(self, mock_sleep, runner, mock_backend):
        mock_backend.get_element_tree.return_value = None
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(diff, ["--window", "Missing"])
        assert result.exit_code != 0
        assert "Error" in result.output

    @patch("naturo.cli.diff_cmd.time.sleep")
    def test_window_not_found_second(self, mock_sleep, runner, mock_backend):
        mock_backend.get_element_tree.side_effect = [{"root": {}}, None]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(diff, ["--window", "Closing", "--interval", "0.01"])
        assert result.exit_code != 0

    @patch("naturo.cli.diff_cmd.time.sleep")
    @patch("naturo.diff.diff_trees")
    def test_app_resolves_by_name(self, mock_diff, mock_sleep, runner, mock_backend):
        """(#1121) --app resolves by application NAME, not window title.

        The old code aliased ``window_title = app`` and matched a title
        substring, so it failed on apps whose title differs from their name
        (e.g. the localized "计算器" for Calculator). It must now pass ``app``
        straight to ``get_element_tree(app=...)``.
        """
        mock_backend.get_element_tree.return_value = {"root": {}}
        mock_diff.return_value = _make_diff_result(has_changes=False)
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(diff, ["--app", "notepad", "--interval", "0.01"])
        assert result.exit_code == 0
        mock_backend.get_element_tree.assert_any_call(app="notepad")
        # And it must NOT have degraded --app into a window-title match.
        for call in mock_backend.get_element_tree.call_args_list:
            assert call.kwargs.get("window_title") != "notepad"

    @patch("naturo.cli.diff_cmd.time.sleep")
    @patch("naturo.diff.diff_trees")
    def test_hwnd_mode(self, mock_diff, mock_sleep, runner, mock_backend):
        mock_backend.get_element_tree.return_value = {"root": {}}
        mock_diff.return_value = _make_diff_result(has_changes=False)
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(diff, ["--hwnd", "12345", "--interval", "0.01"])
        assert result.exit_code == 0
        mock_backend.get_element_tree.assert_any_call(hwnd=12345)


# ---------------------------------------------------------------------------
# Snapshot-based diff (#1121 — now implemented against stored ui_map trees)
# ---------------------------------------------------------------------------

def _ui_element(cls, ref, role, title, *, value=None, parent=None, children=None, frame=(0, 0, 10, 10)):
    return cls(
        id=ref,
        element_id=f"element_{ref}",
        role=role,
        title=title,
        label=title,
        value=value,
        frame=frame,
        parent_id=parent,
        children=list(children or []),
    )


class TestDiffSnapshot:
    """The documented ``diff --snapshot A --snapshot B`` example must work.

    Snapshots are written to a real (temp) store via ``get_snapshot_manager``
    with ``Path.home()`` pointed at ``tmp_path``, exactly as ``see`` would
    persist them — proving the command reconstructs both trees from ``ui_map``
    and runs them through ``diff_trees``.
    """

    def _store(self, monkeypatch, tmp_path, ui_map, app_name="Calculator"):
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        from naturo.snapshot import get_snapshot_manager
        mgr = get_snapshot_manager()
        sid = mgr.create_snapshot()
        mgr.store_detection_result(sid, ui_map)
        snap = mgr.get_snapshot(sid)
        snap.application_name = app_name
        mgr._write_json_atomic(mgr._snap_dir(sid) / "snapshot.json", snap.to_dict())
        return mgr, sid

    def test_snapshot_diff_detects_added_element(self, runner, monkeypatch, tmp_path):
        from naturo.models.snapshot import UIElement

        before = {
            "e1": _ui_element(UIElement, "e1", "Window", "Calc", children=["e2"]),
            "e2": _ui_element(UIElement, "e2", "Button", "Seven", parent="e1"),
        }
        after = {
            "e1": _ui_element(UIElement, "e1", "Window", "Calc", children=["e2", "e3"]),
            "e2": _ui_element(UIElement, "e2", "Button", "Seven", parent="e1"),
            "e3": _ui_element(UIElement, "e3", "Button", "Eight", parent="e1"),
        }
        mgr, sid_before = self._store(monkeypatch, tmp_path, before)
        sid_after = mgr.create_snapshot()
        mgr.store_detection_result(sid_after, after)

        result = runner.invoke(diff, ["--snapshot", sid_before, "--snapshot", sid_after, "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert "diff" in data
        added_names = [c["element_name"] for c in data["diff"]["added"]]
        assert "Eight" in added_names

    def test_snapshot_diff_detects_modified_value(self, runner, monkeypatch, tmp_path):
        from naturo.models.snapshot import UIElement

        before = {
            "e1": _ui_element(UIElement, "e1", "Window", "Calc", children=["e2"]),
            "e2": _ui_element(UIElement, "e2", "Edit", "Display", value="0", parent="e1"),
        }
        after = {
            "e1": _ui_element(UIElement, "e1", "Window", "Calc", children=["e2"]),
            "e2": _ui_element(UIElement, "e2", "Edit", "Display", value="42", parent="e1"),
        }
        mgr, sid_before = self._store(monkeypatch, tmp_path, before)
        sid_after = mgr.create_snapshot()
        mgr.store_detection_result(sid_after, after)

        result = runner.invoke(diff, ["--snapshot", sid_before, "--snapshot", sid_after, "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        modified = data["diff"]["modified"]
        assert any(c.get("new_value") == "42" for c in modified)

    def test_snapshot_diff_no_changes(self, runner, monkeypatch, tmp_path):
        from naturo.models.snapshot import UIElement

        ui_map = {
            "e1": _ui_element(UIElement, "e1", "Window", "Calc", children=["e2"]),
            "e2": _ui_element(UIElement, "e2", "Button", "Seven", parent="e1"),
        }
        mgr, sid_before = self._store(monkeypatch, tmp_path, ui_map)
        sid_after = mgr.create_snapshot()
        mgr.store_detection_result(sid_after, dict(ui_map))

        result = runner.invoke(diff, ["--snapshot", sid_before, "--snapshot", sid_after])
        assert result.exit_code == 0, result.output
        assert "No changes" in result.output

    def test_snapshot_not_found(self, runner, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        result = runner.invoke(diff, ["--snapshot", "missing1", "--snapshot", "missing2"])
        assert result.exit_code != 0
        assert "Error" in result.output or "SNAPSHOT_NOT_FOUND" in result.output


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestDiffErrors:
    @patch("naturo.cli.diff_cmd.time.sleep")
    def test_naturo_error(self, mock_sleep, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.get_element_tree.side_effect = NaturoError("BACKEND_ERROR", "fail")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(diff, ["--window", "Notepad"])
        assert result.exit_code != 0

    @patch("naturo.cli.diff_cmd.time.sleep")
    def test_generic_error(self, mock_sleep, runner, mock_backend):
        mock_backend.get_element_tree.side_effect = RuntimeError("unexpected")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(diff, ["--window", "Notepad"])
        assert result.exit_code != 0

    @patch("naturo.cli.diff_cmd.time.sleep")
    def test_naturo_error_json(self, mock_sleep, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.get_element_tree.side_effect = NaturoError("BACKEND_ERROR", "fail")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(diff, ["--window", "Notepad", "--json"])
        data = json.loads(result.output)
        assert data.get("success") is False or "BACKEND_ERROR" in result.output


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

class TestDiffHelp:
    def test_help(self, runner):
        result = runner.invoke(diff, ["--help"])
        assert result.exit_code == 0
        assert "--snapshot" in result.output
        assert "--window" in result.output
        assert "--interval" in result.output
