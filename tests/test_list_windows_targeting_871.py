"""#871: window-targeting flag harmonization for ``list windows``.

``list windows`` historically accepted only ``--app`` (title *or* process-name
substring) and ``--pid``, while the "gold standard" commands
(``see``/``capture``/``click``/...) accept the full window-targeting set
(``--app``, ``--window``, ``--hwnd``, ``--pid``, ``--app-id``).  A scripter who
typed ``naturo list windows --window <title>`` — the natural muscle-memory from
every other command — hit ``No such option: --window. Did you mean --pid?``.

This change closes the ``list windows`` row of #871's matrix by adding three
filters, purely additively (no existing flag changes behaviour):

* ``--window`` — window-title substring filter (title only, distinct from
  ``--app`` which also matches the process name);
* ``--hwnd`` — exact window-handle filter;
* ``--app-id`` — resolve the session app ID (``a1`` …) to its window handle and
  filter to it, mirroring the ``--app-id`` targeting in ``see``/``capture``.

A supplied-but-unresolvable ``--app-id`` fails loudly (``INVALID_INPUT``,
exit 1) rather than silently listing every window.

All mock-based, CI-safe (no real desktop / DLL).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.app_ids import AppIdEntry
from naturo.backends.base import WindowInfo
from naturo.cli.core._list import list_cmd

runner = CliRunner()

_NEW_FLAGS = ["--window", "--hwnd", "--app-id"]


def _make_window(**overrides):
    """Create a real WindowInfo (avoids MagicMock attribute pitfalls)."""
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


def _invoke(args, windows, *, app_id_entry="__unset__"):
    """Invoke ``list windows`` with a mocked backend and (optionally) app-id map.

    Returns the Click result. ``os.getpid``/``getppid`` are mocked away from the
    fixture pids so the self/parent exclusion (#358) never drops the test windows.
    """
    backend = MagicMock()
    backend.list_windows.return_value = windows
    ctx = [
        patch("naturo.cli.core._common._platform_supports_gui", return_value=True),
        patch("naturo.cli.core._common._get_backend", return_value=backend),
        patch("os.getpid", return_value=99999),
        patch("os.getppid", return_value=99998),
    ]
    if app_id_entry != "__unset__":
        mock_map = MagicMock()
        mock_map.resolve.return_value = app_id_entry
        ctx.append(patch("naturo.app_ids.get_app_id_map", return_value=mock_map))
    else:
        ctx.append(patch("naturo.app_ids.get_app_id_map", return_value=MagicMock()))

    with ctx[0], ctx[1], ctx[2], ctx[3], ctx[4]:
        return runner.invoke(list_cmd, ["windows", *args], catch_exceptions=False)


def _titles(result):
    payload = json.loads(result.output)
    return [w["title"] for w in payload["windows"]]


# --- flag surface -----------------------------------------------------------

@pytest.mark.parametrize("flag", _NEW_FLAGS)
def test_new_flag_in_help(flag):
    """``list windows --help`` must advertise the harmonized flag set."""
    result = runner.invoke(list_cmd, ["windows", "--help"])
    assert result.exit_code == 0, result.output
    assert flag in result.output, f"--help missing {flag}:\n{result.output}"


@pytest.mark.parametrize(
    "flag_with_value",
    [["--window", "Notepad"], ["--hwnd", "12345"], ["--app-id", "a1"]],
)
def test_new_flag_accepted(flag_with_value):
    """The flag must reach the handler, not abort at the Click layer."""
    result = _invoke(flag_with_value, [_make_window()], app_id_entry=None)
    assert "No such option" not in result.output, result.output


# --- filtering behaviour ----------------------------------------------------

def test_window_filters_by_title_substring():
    """``--window`` keeps only title-substring matches (case-insensitive)."""
    wins = [
        _make_window(title="Untitled - Notepad", handle=1, pid=10),
        _make_window(title="Document - WordPad", handle=2, pid=20),
        _make_window(title="calc", handle=3, pid=30),
    ]
    result = _invoke(["--window", "pad", "--json"], wins)
    assert result.exit_code == 0, result.output
    assert _titles(result) == ["Untitled - Notepad", "Document - WordPad"]


def test_window_does_not_match_process_name():
    """``--window`` is title-only — unlike ``--app`` it must not match process_name."""
    wins = [
        _make_window(title="My Editor", process_name="notepad.exe", handle=1, pid=10),
    ]
    result = _invoke(["--window", "notepad", "--json"], wins)
    assert result.exit_code == 0, result.output
    assert _titles(result) == []  # title "My Editor" has no "notepad"


def test_hwnd_filters_to_exact_handle():
    """``--hwnd`` keeps only the window with the matching handle."""
    wins = [
        _make_window(title="A", handle=111, pid=10),
        _make_window(title="B", handle=222, pid=20),
    ]
    result = _invoke(["--hwnd", "222", "--json"], wins)
    assert result.exit_code == 0, result.output
    assert _titles(result) == ["B"]


def test_app_id_resolves_to_window_handle():
    """``--app-id`` resolves to a handle and filters to that window."""
    wins = [
        _make_window(title="A", handle=111, pid=10),
        _make_window(title="B", handle=222, pid=20),
    ]
    entry = AppIdEntry(
        app_id="a2", pid=20, handle=222, process_name="b.exe", title="B", timestamp=0.0,
    )
    result = _invoke(["--app-id", "a2", "--json"], wins, app_id_entry=entry)
    assert result.exit_code == 0, result.output
    assert _titles(result) == ["B"]


def test_unresolvable_app_id_fails_loudly():
    """A supplied-but-unresolvable ``--app-id`` must error, not list everything."""
    wins = [_make_window(title="A", handle=111, pid=10)]
    result = _invoke(["--app-id", "a9", "--json"], wins, app_id_entry=None)
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_INPUT"
