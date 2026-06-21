"""Tests for #1084: the full-path ``process_name`` the list family emits must
round-trip back into ``--app`` everywhere.

``list windows``/``list apps``/``app list`` expose each window's executable as
``process_name`` set to a full absolute path (e.g.
``C:\\Program Files\\WindowsApps\\...\\WindowsTerminal.exe``). An agent that
discovers a window and feeds that exact value back into ``--app`` must select
the same window — both via ``list windows --app`` (covered in
``test_cli_list.py``) and via the shared resolver used by
``see``/``capture``/``click``/``find``/``highlight``/``menu`` (covered here).

The resolver previously normalized only the *stored* ``process_name`` to a
basename (#789) while comparing it against the *raw* query, so a full-path or
``.exe``-suffixed query matched nothing — the discover→act round-trip was broken
and ``list windows --app`` would have diverged from the action commands.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from naturo.backends.base import WindowInfo

_ELEMENT_MOD = "naturo.backends.windows._element._app_discovery"

# A realistic full-path process_name as emitted by `list windows -j` for a
# packaged (MSIX) app — the exact value from the #1084 repro.
_TERMINAL_PATH = (
    r"C:\Program Files\WindowsApps"
    r"\Microsoft.WindowsTerminal_1.24.11321.0_x64__8wekyb3d8bbwe"
    r"\WindowsTerminal.exe"
)


def _backend_class():
    try:
        from naturo.backends.windows import WindowsBackend
        return WindowsBackend
    except Exception:
        pytest.skip("WindowsBackend not available on this platform")


def _windows():
    """Two windows whose process_name fields contain full executable paths."""
    return [
        WindowInfo(
            handle=2001, title="claude",
            process_name=_TERMINAL_PATH, pid=300,
            x=0, y=0, width=1200, height=800,
            is_visible=True, is_minimized=False,
        ),
        WindowInfo(
            handle=2002, title="Untitled - Notepad",
            process_name=r"C:\Windows\System32\notepad.exe", pid=100,
            x=0, y=0, width=800, height=600,
            is_visible=True, is_minimized=False,
        ),
    ]


def _resolve_hwnd(app):
    BackendClass = _backend_class()
    backend = MagicMock(spec=BackendClass)
    backend.list_windows = MagicMock(return_value=_windows())
    backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
    backend._APP_ALIASES = BackendClass._APP_ALIASES
    backend._DESKTOP_SHELL_CLASSES = BackendClass._DESKTOP_SHELL_CLASSES
    backend._get_window_class_name = MagicMock(return_value="")
    backend._get_foreground_hwnd = MagicMock(return_value=0)
    backend._uwp_afh_fallback = MagicMock(return_value=None)
    with patch(f"{_ELEMENT_MOD}._get_console_session_id", return_value=-1), \
         patch(f"{_ELEMENT_MOD}._get_process_session_id", return_value=1):
        return backend._resolve_hwnd(app=app)


def _resolve_hwnds(app):
    BackendClass = _backend_class()
    backend = MagicMock(spec=BackendClass)
    backend.list_windows = MagicMock(return_value=_windows())
    backend._resolve_hwnds = BackendClass._resolve_hwnds.__get__(backend)
    backend._APP_ALIASES = BackendClass._APP_ALIASES
    backend._uwp_afh_fallback = MagicMock(return_value=None)
    with patch(f"{_ELEMENT_MOD}._get_console_session_id", return_value=-1), \
         patch(f"{_ELEMENT_MOD}._get_process_session_id", return_value=1):
        return backend._resolve_hwnds(app=app)


class TestResolveHwndPathRoundTrip:
    """_resolve_hwnd must accept the full-path value list output emits."""

    def test_full_path_round_trips(self):
        # The exact emitted process_name selects the same window.
        assert _resolve_hwnd(_TERMINAL_PATH) == 2001

    def test_basename_with_exe_round_trips(self):
        assert _resolve_hwnd("WindowsTerminal.exe") == 2001

    def test_plain_basename_still_matches(self):
        assert _resolve_hwnd("WindowsTerminal") == 2001

    def test_partial_name_still_matches(self):
        assert _resolve_hwnd("terminal") == 2001

    def test_shared_directory_does_not_overmatch(self):
        # Basenaming the query must NOT broaden to full-path substring matching:
        # a shared directory component must not pull in unrelated windows (#789).
        from naturo.errors import WindowNotFoundError
        with pytest.raises(WindowNotFoundError):
            _resolve_hwnd(r"C:\Program Files\WindowsApps")


class TestResolveHwndsPathRoundTrip:
    """_resolve_hwnds must round-trip the full path the same way (#304 see --app)."""

    def test_full_path_round_trips(self):
        assert 2001 in _resolve_hwnds(_TERMINAL_PATH)

    def test_basename_with_exe_round_trips(self):
        assert 2001 in _resolve_hwnds("WindowsTerminal.exe")

    def test_plain_basename_still_matches(self):
        assert 2001 in _resolve_hwnds("WindowsTerminal")

    def test_shared_directory_does_not_overmatch(self):
        assert _resolve_hwnds(r"C:\Program Files\WindowsApps") == []
