"""Shared fixtures for integration tests.

These tests require a Windows desktop environment with real applications.
They are skipped on non-Windows platforms and in CI environments without
a desktop session.
"""

import os
import platform
import subprocess
import time
from typing import Generator, Optional

import pytest

# Skip entire module on non-Windows
pytestmark = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Integration tests require Windows desktop",
)


def _has_desktop_session() -> bool:
    """Check if an interactive desktop session is available.

    On Windows, queries the WTS (Windows Terminal Services) API to determine
    whether the current process runs in an active Console or RDP session.
    This correctly returns False for non-interactive SSH sessions, unlike the
    old ``GetDesktopWindow()`` approach which returned True for any session type.

    Uses the same detection logic as ``tests/conftest.py::_has_desktop_session()``.
    See GitHub issue #392 for details.

    Returns:
        True if running in an interactive desktop session, False otherwise.
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


def _find_process_by_name(name: str) -> Optional[int]:
    """Find a running process by name in the current desktop session, return PID or None.

    Filters out Session 0 (Services) processes which have no GUI and would cause
    UIA detection to fail. Prefers Session 1+ (Console/RDP) processes.
    See GitHub issue #389 for details.

    Args:
        name: Executable image name (e.g. "Notepad.exe").

    Returns:
        PID of a matching process in an interactive session, or None.
    """
    try:
        # Use SESSION ne 0 to exclude Services session processes (no GUI)
        result = subprocess.run(
            [
                "tasklist", "/FI", f"IMAGENAME eq {name}",
                "/FI", "SESSION ne 0",
                "/FO", "CSV", "/NH",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.strip().splitlines():
            parts = line.strip('"').split('","')
            if len(parts) >= 2 and parts[0].lower() == name.lower():
                return int(parts[1])
    except Exception:
        pass

    # Fallback: try without session filter (older Windows versions may not support it)
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.strip().splitlines():
            parts = line.strip('"').split('","')
            if len(parts) >= 2 and parts[0].lower() == name.lower():
                return int(parts[1])
    except Exception:
        pass
    return None


def _launch_app(exe_path: str, wait_seconds: float = 2.0) -> Optional[subprocess.Popen]:
    """Launch an application and wait for it to initialize.

    Args:
        exe_path: Path or command to launch.
        wait_seconds: Seconds to wait after launch for UI to appear.

    Returns:
        Popen object if launched successfully, None otherwise.
    """
    try:
        proc = subprocess.Popen(
            exe_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(wait_seconds)
        if proc.poll() is not None:
            return None
        return proc
    except Exception:
        return None


@pytest.fixture(scope="session")
def has_desktop():
    """Ensure a desktop session is available."""
    if not _has_desktop_session():
        pytest.skip("No desktop session available")
    return True


def _find_notepad_window_pid() -> Optional[int]:
    """Find the PID of the process owning a visible Notepad window.

    On Windows 11, UWP/WinUI3 Notepad is launched via a broker whose PID
    differs from the window-owning process.  Instead of relying on tasklist
    (which may return the broker PID), enumerate windows and find one whose
    title contains "Notepad" (#534).

    Returns:
        PID of the Notepad window owner, or None.
    """
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        found_pid = ctypes.c_ulong(0)

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_callback(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            title = buf.value
            title_lower = title.lower()
            # (#570) Match by title: English "Notepad" or Chinese "记事本"
            if (("notepad" in title_lower or "\u8bb0\u4e8b\u672c" in title_lower)
                    and title.strip()):
                window_pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
                found_pid.value = window_pid.value
                return False  # stop
            # (#570) Fallback: match by process name for any locale
            window_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            h_proc = kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, window_pid.value,
            )
            if h_proc:
                try:
                    name_buf = ctypes.create_unicode_buffer(260)
                    if psapi.GetProcessImageFileNameW(h_proc, name_buf, 260):
                        import os
                        proc_name = os.path.basename(name_buf.value).lower()
                        if "notepad" in proc_name:
                            found_pid.value = window_pid.value
                            return False
                finally:
                    kernel32.CloseHandle(h_proc)
            return True

        user32.EnumWindows(enum_callback, 0)
        return found_pid.value or None
    except Exception:
        return None


def _app_window_pids(title_substrings, proc_name_substr) -> "set[int]":
    """Set of PIDs owning a visible top-level window matching by title
    (case-insensitive substring) or owning-process image name.

    Enumerating windows works when ``tasklist`` is broken. Returning a SET (not
    the first match) lets a fixture **baseline-diff** its own launch, so it can
    never select — or kill — a window the user already had open (the old
    first-match finder killed a pre-existing user Notepad).
    """
    pids: "set[int]" = set()
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_callback(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            title = buf.value.strip()
            window_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            matched = bool(title) and any(s in title.lower() for s in title_substrings)
            if not matched and proc_name_substr and window_pid.value:
                h_proc = kernel32.OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION, False, window_pid.value,
                )
                if h_proc:
                    try:
                        name_buf = ctypes.create_unicode_buffer(260)
                        if psapi.GetProcessImageFileNameW(h_proc, name_buf, 260):
                            import os
                            if proc_name_substr in os.path.basename(name_buf.value).lower():
                                matched = True
                    finally:
                        kernel32.CloseHandle(h_proc)
            if matched and window_pid.value:
                pids.add(window_pid.value)
            return True

        user32.EnumWindows(enum_callback, 0)
    except Exception:
        pass
    return pids


def _notepad_window_pids() -> "set[int]":
    return _app_window_pids(("notepad", "记事本"), "notepad")


def _calculator_window_pids() -> "set[int]":
    return _app_window_pids(("calculator", "计算器"), "calculator")


def _launch_and_resolve(cmd, window_pids_fn, app_label):
    """Launch *cmd* and resolve the PID of a window that appeared AFTER launch.

    Returns ``(proc, actual_pid, before)`` where ``actual_pid`` is guaranteed not
    to be a pre-existing window (baseline-diff), so a fixture can never touch a
    window the user already had open. Skips loudly if no new window appears.
    """
    before = window_pids_fn()
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    actual_pid = None
    deadline = time.monotonic() + 15.0
    while actual_pid is None and time.monotonic() < deadline:
        new = window_pids_fn() - before
        if new:
            actual_pid = sorted(new)[0]
        else:
            time.sleep(1.0)
    # Classic app whose launcher owns the window — only if that PID is genuinely new.
    if actual_pid is None and proc.poll() is None and proc.pid not in before:
        actual_pid = proc.pid
    if actual_pid is None:
        try:
            proc.terminate()
        except Exception:
            pass
        pytest.skip(f"Could not launch {app_label} (no new window appeared)")
    return proc, actual_pid, before


def _teardown_launched(proc, actual_pid, before) -> None:
    """PID-scoped teardown of only what the fixture launched — the resolved
    window-owner + launcher, each guarded to never be a pre-existing PID. Robust
    to a broken ``taskkill`` (Win32 TerminateProcess); force-kill so a Save dialog
    cannot strand the process.
    """
    from tests._launch import kill_pid

    for pid in {actual_pid, proc.pid}:
        if pid not in before:  # never kill a pre-existing window/process
            kill_pid(pid)
    try:
        proc.terminate()
    except Exception:
        pass


@pytest.fixture(scope="module")
def notepad_app(has_desktop) -> Generator[int, None, None]:
    """Launch Notepad and yield the PID of the window IT launched.

    Resolved by baseline-diff, so a Notepad the user already had open is never
    selected or killed. Handles UWP Notepad where the window owner differs from
    the launcher (#534).
    """
    proc, actual_pid, before = _launch_and_resolve(
        "notepad.exe", _notepad_window_pids, "Notepad",
    )
    yield actual_pid
    _teardown_launched(proc, actual_pid, before)


def _find_calculator_window_pid() -> Optional[int]:
    """PID of the process owning a visible Calculator window (mirrors the Notepad
    finder, #534). ``calc.exe`` is a launcher stub that exits immediately and the
    UWP ``CalculatorApp.exe`` hosts the window via a broker; the ``tasklist``
    IMAGENAME filter is also broken on some hosts — so enumerate windows and match
    the Calculator title/owner instead.
    """
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        found_pid = ctypes.c_ulong(0)

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_callback(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            title = buf.value.strip()
            # English "Calculator" or Chinese "计算器"
            if title and ("calculator" in title.lower() or "计算器" in title):
                window_pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
                h_proc = kernel32.OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION, False, window_pid.value,
                )
                if h_proc:
                    try:
                        name_buf = ctypes.create_unicode_buffer(260)
                        if psapi.GetProcessImageFileNameW(h_proc, name_buf, 260):
                            import os
                            if "calculator" in os.path.basename(name_buf.value).lower():
                                found_pid.value = window_pid.value
                                return False
                    finally:
                        kernel32.CloseHandle(h_proc)
                if not found_pid.value:  # Calculator-titled visible window is enough
                    found_pid.value = window_pid.value
                    return False
            return True

        user32.EnumWindows(enum_callback, 0)
        return found_pid.value or None
    except Exception:
        return None


@pytest.fixture(scope="module")
def calculator_app(has_desktop) -> Generator[int, None, None]:
    """Launch Calculator and yield the PID of the window IT launched.

    ``calc.exe`` is a launcher stub that exits immediately; ``CalculatorApp.exe``
    hosts the UWP window, resolved via ``EnumWindows`` and baseline-diff so a
    Calculator the user already had open is never selected or killed.
    """
    proc, actual_pid, before = _launch_and_resolve(
        "calc.exe", _calculator_window_pids, "Calculator",
    )
    yield actual_pid
    _teardown_launched(proc, actual_pid, before)


@pytest.fixture(scope="module")
def explorer_app(has_desktop) -> Generator[int, None, None]:
    """Open a File Explorer window and yield its PID.

    Explorer is a native Win32 shell application with COM-based automation.
    """
    proc = _launch_app("explorer.exe /e,C:\\", wait_seconds=3.0)

    # Explorer is always running; find the newest explorer process
    pid = _find_process_by_name("explorer.exe")
    if pid is None:
        pytest.skip("Could not find Explorer process")

    yield pid

    # Don't kill explorer — it's the shell


@pytest.fixture(scope="session")
def detect_chain():
    """Provide the detection chain function.

    Returns the detect function from the chain module, or skips
    if the module cannot be imported (e.g., missing native deps).
    """
    try:
        from naturo.detect.chain import detect
        return detect
    except ImportError as exc:
        pytest.skip(f"Detection chain not available: {exc}")
