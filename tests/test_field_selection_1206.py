"""#1206 — scriptable ``--field`` selection for list-style commands.

Common scripting lookups ("get the HWND of the SolidWorks main window") used to
force a pipe into ``jq``/Python. ``--field NAME[,NAME...]`` projects the row down
to the requested columns so the value comes straight out of naturo:

* text mode prints one row per line, tab-separated in the requested order — a
  single field of a single row is a bare, ``$(...)``-capturable value;
* ``-j`` returns the canonical success envelope with each item projected;
* an unknown field name fails loudly (``INVALID_INPUT``) listing the valid
  fields, rather than silently emitting blanks;
* default (no ``--field``) output is unchanged.

All mock-based, CI-safe (no real desktop / DLL).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.backends.base import WindowInfo
from naturo.cli._app.lifecycle import app_find, app_list
from naturo.cli._app.window_ops import app_windows
from naturo.cli.core._list import list_cmd


@pytest.fixture
def runner():
    return CliRunner()


def _make_window(**overrides):
    return WindowInfo(
        handle=overrides.get("handle", 1182906),
        title=overrides.get("title", "Untitled - Notepad"),
        process_name=overrides.get("process_name", "notepad.exe"),
        pid=overrides.get("pid", 31912),
        x=overrides.get("x", 100),
        y=overrides.get("y", 100),
        width=overrides.get("width", 800),
        height=overrides.get("height", 600),
        is_visible=overrides.get("is_visible", True),
        is_minimized=overrides.get("is_minimized", False),
    )


def _invoke_list_windows(runner, args, windows):
    backend = MagicMock()
    backend.list_windows.return_value = windows
    with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
         patch("naturo.cli.core._common._get_backend", return_value=backend), \
         patch("naturo.app_ids.get_app_id_map", return_value=MagicMock()), \
         patch("os.getpid", return_value=99999), patch("os.getppid", return_value=99998):
        return runner.invoke(list_cmd, ["windows", *args], catch_exceptions=False)


def _invoke_app_list(runner, args, windows):
    backend = MagicMock()
    backend.list_windows.return_value = windows
    backend._SYSTEM_PROCESS_NAMES = set()
    backend._UWP_HOST_PROCESS = "applicationframehost.exe"
    with patch("naturo.backends.base.get_backend", return_value=backend), \
         patch("naturo.cli.interaction._check_desktop_session"), \
         patch("naturo.app_ids.get_app_id_map", return_value=MagicMock()):
        return runner.invoke(app_list, args, obj={}, catch_exceptions=False)


def _invoke_app_windows(runner, args, windows):
    backend = MagicMock()
    backend.list_windows.return_value = windows
    with patch("naturo.backends.base.get_backend", return_value=backend), \
         patch("naturo.cli.core._common._enforce_desktop_session"), \
         patch("naturo.cli._app.window_ops._enforce_desktop_session"):
        return runner.invoke(app_windows, args, obj={}, catch_exceptions=False)


# ── list windows ────────────────────────────────────────────────────────────

class TestListWindowsField:

    def test_single_field_text_is_bare_value(self, runner):
        """One field + one row prints the bare value (no header) for $(...)."""
        result = _invoke_list_windows(runner, ["--field", "hwnd"], [_make_window(handle=70354)])
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "70354"

    def test_single_field_multiple_rows_one_per_line(self, runner):
        wins = [_make_window(handle=1, pid=10, title="A"),
                _make_window(handle=2, pid=20, title="B")]
        result = _invoke_list_windows(runner, ["--field", "hwnd"], wins)
        assert result.exit_code == 0, result.output
        assert result.output.strip().splitlines() == ["1", "2"]

    def test_multi_field_tab_separated_in_order(self, runner):
        wins = [_make_window(handle=70354, pid=29388, title="SOLIDWORKS")]
        result = _invoke_list_windows(runner, ["--field", "hwnd,pid,title"], wins)
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "70354\t29388\tSOLIDWORKS"

    def test_field_json_projects_envelope(self, runner):
        wins = [_make_window(handle=1, pid=10, title="A"),
                _make_window(handle=2, pid=20, title="B")]
        result = _invoke_list_windows(runner, ["--field", "hwnd,title", "--json"], wins)
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is True
        assert payload["count"] == 2
        assert payload["windows"] == [
            {"hwnd": 1, "title": "A"},
            {"hwnd": 2, "title": "B"},
        ]

    def test_unknown_field_errors_text(self, runner):
        result = _invoke_list_windows(runner, ["--field", "bogus"], [_make_window()])
        assert result.exit_code == 1, result.output
        assert "bogus" in result.output
        # Lists the valid fields to guide recovery.
        assert "title" in result.output

    def test_unknown_field_errors_json(self, runner):
        result = _invoke_list_windows(runner, ["--field", "hwnd,bogus", "--json"], [_make_window()])
        assert result.exit_code == 1, result.output
        payload = json.loads(result.output)
        assert payload["success"] is False
        assert payload["error"]["code"] == "INVALID_INPUT"
        assert "bogus" in payload["error"]["message"]

    def test_default_output_unchanged(self, runner):
        """No --field: the human table is untouched."""
        result = _invoke_list_windows(runner, [], [_make_window(handle=70354, title="Untitled - Notepad")])
        assert result.exit_code == 0, result.output
        assert "HWND" in result.output
        assert "70354" in result.output
        assert "1 windows found" in result.output

    def test_default_json_unchanged(self, runner):
        result = _invoke_list_windows(runner, ["--json"], [_make_window(handle=70354)])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        w = payload["windows"][0]
        # Full schema still present when no projection requested.
        assert {"id", "handle", "hwnd", "title", "process_name", "pid",
                "x", "y", "width", "height", "is_visible", "is_minimized"} <= set(w)


# ── list apps / app list ────────────────────────────────────────────────────

class TestAppListField:

    def test_single_field_text(self, runner):
        result = _invoke_app_list(runner, ["--field", "pid"], [_make_window(pid=4242)])
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "4242"

    def test_field_json_projects(self, runner):
        result = _invoke_app_list(runner, ["--field", "pid,title", "--json"],
                                  [_make_window(pid=4242, title="Doc")])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["windows"] == [{"pid": 4242, "title": "Doc"}]

    def test_unknown_field_errors(self, runner):
        result = _invoke_app_list(runner, ["--field", "nope", "--json"], [_make_window()])
        assert result.exit_code == 1, result.output
        payload = json.loads(result.output)
        assert payload["error"]["code"] == "INVALID_INPUT"

    def test_default_unchanged(self, runner):
        result = _invoke_app_list(runner, ["--json"], [_make_window(pid=4242)])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["windows"][0]["pid"] == 4242
        assert "process_name" in payload["windows"][0]


# ── app windows ─────────────────────────────────────────────────────────────

class TestAppWindowsField:

    def test_single_field_text(self, runner):
        result = _invoke_app_windows(runner, ["--field", "handle"], [_make_window(handle=555)])
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "555"

    def test_multi_field_json(self, runner):
        result = _invoke_app_windows(runner, ["--field", "handle,pid", "--json"],
                                     [_make_window(handle=555, pid=77)])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["windows"] == [{"handle": 555, "pid": 77}]

    def test_unknown_field_errors(self, runner):
        result = _invoke_app_windows(runner, ["--field", "hwnd"], [_make_window()])
        # `app windows` schema exposes `handle`, not the `hwnd` alias.
        assert result.exit_code == 1, result.output
        assert "hwnd" in result.output


# ── app find (singular) ─────────────────────────────────────────────────────

class TestAppFindField:

    def _proc(self, **kw):
        from types import SimpleNamespace
        return SimpleNamespace(
            pid=kw.get("pid", 1234), name=kw.get("name", "notepad.exe"),
            path=kw.get("path", "C:\\notepad.exe"),
            is_running=kw.get("is_running", True),
            window_count=kw.get("window_count", 1),
        )

    def test_single_field_text_bare(self, runner):
        with patch("naturo.process.find_process", return_value=self._proc(pid=999)):
            result = runner.invoke(app_find, ["notepad", "--field", "pid"], obj={})
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "999"

    def test_multi_field_json(self, runner):
        with patch("naturo.process.find_process", return_value=self._proc(pid=999, name="notepad.exe")):
            result = runner.invoke(app_find, ["notepad", "--field", "pid,name", "--json"], obj={})
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["process"] == {"pid": 999, "name": "notepad.exe"}

    def test_unknown_field_errors(self, runner):
        with patch("naturo.process.find_process", return_value=self._proc()):
            result = runner.invoke(app_find, ["notepad", "--field", "hwnd", "--json"], obj={})
        assert result.exit_code == 1, result.output
        payload = json.loads(result.output)
        assert payload["error"]["code"] == "INVALID_INPUT"


# ── shared helper unit coverage ─────────────────────────────────────────────

class TestFieldHelpers:

    def test_parse_fields_none(self):
        from naturo.cli._field import parse_fields
        assert parse_fields(None) is None

    def test_parse_fields_splits_and_strips(self):
        from naturo.cli._field import parse_fields
        assert parse_fields(" hwnd , pid ,title") == ["hwnd", "pid", "title"]

    def test_parse_fields_all_empty_is_empty_list(self):
        from naturo.cli._field import parse_fields
        assert parse_fields(" , ") == []

    def test_empty_field_spec_rejected(self, runner):
        """--field "" (parses to no names) is INVALID_INPUT, not blank output."""
        result = _invoke_list_windows(runner, ["--field", ",", "--json"], [_make_window()])
        assert result.exit_code == 1, result.output
        payload = json.loads(result.output)
        assert payload["error"]["code"] == "INVALID_INPUT"
