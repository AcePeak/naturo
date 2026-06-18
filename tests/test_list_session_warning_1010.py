"""Regression tests for #1010 — `list windows` false "no interactive desktop
session" warning.

`naturo list windows --app <nonmatching>` used to print a misleading
"no interactive desktop session detected" warning whenever the
``--app``/``--pid`` filter matched zero windows, even on a fully interactive
desktop with many windows enumerated.  The session diagnostic must key on the
*raw* (pre-filter) enumeration and reuse the canonical WTS-based session check,
not the post-filter list and an ad-hoc ``SESSIONNAME`` heuristic.

All tests mock the backend and ``platform.system`` so they run on any CI host.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.core._list import list_cmd

_SESSION_PHRASE = "no interactive desktop session"


def _make_window(**overrides):
    w = MagicMock()
    w.handle = overrides.get("handle", 12345)
    w.title = overrides.get("title", "Untitled - Notepad")
    w.process_name = overrides.get("process_name", "notepad.exe")
    w.pid = overrides.get("pid", 5678)
    w.x = overrides.get("x", 100)
    w.y = overrides.get("y", 100)
    w.width = overrides.get("width", 800)
    w.height = overrides.get("height", 600)
    w.is_visible = overrides.get("is_visible", True)
    w.is_minimized = overrides.get("is_minimized", False)
    return w


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def populated_backend():
    """A backend whose raw enumeration returns several real windows."""
    backend = MagicMock()
    backend.list_windows.return_value = [
        _make_window(handle=1001, title="claude", process_name="WindowsTerminal.exe", pid=100),
        _make_window(handle=1002, title="Calculator", process_name="calc.exe", pid=200),
    ]
    return backend


def _patches(backend):
    """Common patches: GUI-capable platform reported as Windows, mocked backend,
    and own/parent PIDs that never collide with the mock windows."""
    return [
        patch("naturo.cli.core._common._platform_supports_gui", return_value=True),
        patch("naturo.cli.core._common._get_backend", return_value=backend),
        patch("naturo.cli.core._list.platform.system", return_value="Windows"),
        patch("os.getpid", return_value=99999),
        patch("os.getppid", return_value=99998),
    ]


def _run(runner, backend, args):
    ctx = _patches(backend)
    for p in ctx:
        p.start()
    try:
        return runner.invoke(list_cmd, args, catch_exceptions=False)
    finally:
        for p in reversed(ctx):
            p.stop()


def test_filter_no_match_does_not_warn_about_session(runner, populated_backend):
    """A --app filter that matches none of the enumerated windows must NOT
    claim the desktop has no interactive session."""
    result = _run(runner, populated_backend, ["windows", "--app", "ZZ_NoSuchApp_QA"])
    assert result.exit_code == 0
    assert _SESSION_PHRASE not in result.output


def test_filter_no_match_json_returns_empty_success(runner, populated_backend):
    """-j with a non-matching filter returns an empty success envelope and no
    session warning."""
    result = _run(runner, populated_backend, ["windows", "--app", "ZZ_NoSuchApp_QA", "-j"])
    assert result.exit_code == 0
    assert _SESSION_PHRASE not in result.output
    data = json.loads(result.output)
    assert data == {"success": True, "windows": [], "count": 0}


def test_pid_filter_no_match_does_not_warn(runner, populated_backend):
    """A --pid filter matching no window behaves like --app (no session warning)."""
    result = _run(runner, populated_backend, ["windows", "--pid", "424242"])
    assert result.exit_code == 0
    assert _SESSION_PHRASE not in result.output


def test_genuinely_no_session_still_warns(runner):
    """When the raw enumeration is empty AND the session is not interactive,
    the (single, un-doubled) session warning is still emitted."""
    empty_backend = MagicMock()
    empty_backend.list_windows.return_value = []
    with patch(
        "naturo.cli.interaction._common._is_current_session_interactive",
        return_value=False,
    ):
        result = _run(runner, empty_backend, ["windows"])
    assert result.exit_code == 0
    assert _SESSION_PHRASE in result.output
    # The old message doubled the "Warning:" prefix — guard against regression.
    assert "(Warning:" not in result.output


def test_empty_but_interactive_desktop_does_not_warn(runner):
    """An interactive desktop that simply has no open windows (raw enumeration
    empty, session interactive) must not claim there is no session."""
    empty_backend = MagicMock()
    empty_backend.list_windows.return_value = []
    with patch(
        "naturo.cli.interaction._common._is_current_session_interactive",
        return_value=True,
    ):
        result = _run(runner, empty_backend, ["windows"])
    assert result.exit_code == 0
    assert _SESSION_PHRASE not in result.output
    assert "No windows found" in result.output
