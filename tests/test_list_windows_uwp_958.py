"""Regression tests for #958 — ``list_windows`` must resolve UWP host PIDs.

For a UWP/packaged app hosted by ``ApplicationFrameHost.exe``, the core
bridge reports the *host* process PID/executable. ``list_apps`` already
resolves this to the real child process (#267/#276), but ``list_windows``
historically returned the unresolved host PID, so the two listing commands
disagreed on ``pid``/``process_name`` for the same window handle (#958).

These tests are desktop-independent: the core bridge and the UWP child
resolver are mocked, so they run on any platform (including CI Linux).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from naturo.backends.base import WindowInfo as BaseWindowInfo
from naturo.backends.windows._shell._app import AppMixin
from naturo.backends.windows._window import WindowMixin

# Bare exe name (no directory): the production basename check runs under
# Windows ``os.path`` (ntpath) at runtime, but these tests also run on CI
# Linux/macOS where ``os.path.basename`` would NOT split a Windows path. Using
# a bare name keeps the host-process detection portable, matching the existing
# convention in test_app_control.py / test_shell_mixin.py.
_AFH = "ApplicationFrameHost.exe"


def _bridge_window(*, hwnd, title, process_name, pid):
    """Build a fake core-bridge window (uses ``.hwnd`` like the real bridge)."""
    return SimpleNamespace(
        hwnd=hwnd, title=title, process_name=process_name, pid=pid,
        x=0, y=0, width=400, height=500, is_visible=True, is_minimized=False,
    )


class _FakeBackend(WindowMixin, AppMixin):
    """Minimal backend mixing window + app listing with mocked native calls."""

    _SYSTEM_PROCESS_NAMES: set[str] = {"dwm.exe", "runtimebroker.exe"}
    _UWP_HOST_PROCESS: str = "applicationframehost.exe"

    def __init__(self, bridge_windows, resolver):
        self._bridge_windows = bridge_windows
        self._resolver = resolver

    def _ensure_core(self):
        core = MagicMock()
        core.list_windows.return_value = self._bridge_windows
        return core

    def _resolve_uwp_child_pid(self, hwnd):
        return self._resolver(hwnd)


def test_list_windows_resolves_uwp_host_pid():
    """A UWP window reports the real child PID/exe, not ApplicationFrameHost."""
    backend = _FakeBackend(
        [_bridge_window(hwnd=2428040, title="Calculator",
                        process_name=_AFH, pid=3844)],
        resolver=lambda hwnd: (55388, "C:\\Program Files\\WindowsApps\\CalculatorApp.exe"),
    )
    [win] = backend.list_windows()
    assert win.pid == 55388
    assert win.process_name.endswith("CalculatorApp.exe")
    assert "applicationframehost" not in win.process_name.lower()


def test_list_windows_leaves_plain_windows_unchanged():
    """Non-UWP windows pass through untouched (no resolver call)."""
    resolver = MagicMock()
    backend = _FakeBackend(
        [_bridge_window(hwnd=1001, title="Notepad",
                        process_name="C:\\Windows\\notepad.exe", pid=100)],
        resolver=resolver,
    )
    [win] = backend.list_windows()
    assert win.pid == 100
    assert win.process_name.endswith("notepad.exe")
    resolver.assert_not_called()


def test_list_windows_falls_back_when_resolution_fails():
    """When the child PID cannot be resolved, keep the host window as-is."""
    for failed in [(0, ""), (None, None)]:
        backend = _FakeBackend(
            [_bridge_window(hwnd=2428040, title="Calculator",
                            process_name=_AFH, pid=3844)],
            resolver=lambda hwnd, failed=failed: failed,
        )
        [win] = backend.list_windows()
        assert win.pid == 3844
        assert win.process_name == _AFH


def test_list_windows_and_list_apps_agree_for_same_uwp_handle():
    """#958 core assertion: both surfaces report the same real PID/process
    for the same UWP window handle, and neither reports the host process."""
    backend = _FakeBackend(
        [_bridge_window(hwnd=2428040, title="Calculator",
                        process_name=_AFH, pid=3844)],
        resolver=lambda hwnd: (55388, "C:\\Program Files\\WindowsApps\\CalculatorApp.exe"),
    )
    [win] = backend.list_windows()
    apps = backend.list_apps()
    matching = [a for a in apps if a["pid"] == win.pid]
    assert matching, "list_apps and list_windows disagree on the UWP PID"
    assert win.pid == 55388
    assert "applicationframehost" not in win.process_name.lower()
    assert all("applicationframehost" not in a["process"].lower() for a in apps)


def test_list_windows_unresolved_keeps_raw_host_pid():
    """The raw helper that ``list_apps`` consumes must NOT pre-resolve UWP,
    so ``list_apps`` can run its own detection on the host basename."""
    backend = _FakeBackend(
        [_bridge_window(hwnd=2428040, title="Calculator",
                        process_name=_AFH, pid=3844)],
        resolver=lambda hwnd: (55388, "CalculatorApp.exe"),
    )
    [raw] = backend._list_windows_unresolved()
    assert isinstance(raw, BaseWindowInfo)
    assert raw.pid == 3844
    assert raw.process_name == _AFH
