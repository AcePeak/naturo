from __future__ import annotations

import platform
from typing import Optional

import pytest


def pytest_configure(config):
    """Register custom markers."""
    pass  # markers defined in pyproject.toml


def _has_desktop_session() -> bool:
    """Check if an interactive desktop session is available.

    On Windows, queries the WTS (Windows Terminal Services) API to determine
    whether the current process runs in an active Console or RDP session.
    This correctly returns False for SSH sessions, unlike the old
    ``GetDesktopWindow()`` approach which returned True for any session type.

    Uses the same detection logic as ``naturo.cli.interaction._is_current_session_interactive()``.

    Always returns False on non-Windows platforms.
    """
    if platform.system() != "Windows":
        return False
    try:
        import ctypes
        import ctypes.wintypes

        # Get the session ID for the current process.
        pid = ctypes.windll.kernel32.GetCurrentProcessId()
        session_id = ctypes.wintypes.DWORD(0)
        ok = ctypes.windll.kernel32.ProcessIdToSessionId(
            pid, ctypes.byref(session_id),
        )
        if not ok:
            return False
        sid = session_id.value

        # Session 0 is always the non-interactive services session.
        if sid == 0:
            return False

        # Query WTS connect state via pure ctypes.
        WTS_CURRENT_SERVER_HANDLE = 0
        WTSConnectState = 8  # WTS_INFO_CLASS enum value
        WTSActive = 0
        WTSConnected = 1

        wtsapi32 = ctypes.windll.wtsapi32
        buf = ctypes.wintypes.LPWSTR()
        bytes_returned = ctypes.wintypes.DWORD(0)

        ok = wtsapi32.WTSQuerySessionInformationW(
            WTS_CURRENT_SERVER_HANDLE,
            sid,
            WTSConnectState,
            ctypes.byref(buf),
            ctypes.byref(bytes_returned),
        )
        if not ok:
            return False

        try:
            state = ctypes.cast(
                buf, ctypes.POINTER(ctypes.wintypes.DWORD),
            ).contents.value
        finally:
            wtsapi32.WTSFreeMemory(buf)

        return state in (WTSActive, WTSConnected)
    except Exception:
        return False


# Cache the result once per session to avoid repeated FFI calls.
_DESKTOP_AVAILABLE: Optional[bool] = None


def _check_desktop() -> bool:
    """Return cached desktop session availability."""
    global _DESKTOP_AVAILABLE
    if _DESKTOP_AVAILABLE is None:
        _DESKTOP_AVAILABLE = _has_desktop_session()
    return _DESKTOP_AVAILABLE


@pytest.fixture(autouse=True)
def _skip_desktop_tests(request: pytest.FixtureRequest):
    """Auto-skip tests marked ``@pytest.mark.desktop`` when no desktop session.

    This covers the gap where tests guard on ``platform.system() == 'Windows'``
    but still fail when run via SSH (Windows, but no interactive desktop).
    """
    if request.node.get_closest_marker("desktop") is not None:
        if not _check_desktop():
            pytest.skip("No interactive desktop session available")


def cli_stdout(result):
    """Extract stdout-only text from a Click CliRunner result.

    Click 8.x's ``result.output`` mixes stderr and stdout. Use
    ``result.stdout`` when available (Click ≥8.0) to avoid stderr
    warnings contaminating JSON output assertions.
    """
    return getattr(result, "stdout", result.output)


@pytest.fixture
def is_windows():
    return platform.system() == "Windows"


@pytest.fixture
def skip_if_not_windows():
    if platform.system() != "Windows":
        pytest.skip("Windows-only test")
