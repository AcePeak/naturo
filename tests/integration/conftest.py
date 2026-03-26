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
    """Check if a desktop session is available (not headless)."""
    if platform.system() != "Windows":
        return False
    try:
        import ctypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        desktop = user32.GetDesktopWindow()
        return desktop != 0
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


@pytest.fixture(scope="module")
def notepad_app(has_desktop) -> Generator[int, None, None]:
    """Launch Notepad and yield its PID. Clean up on teardown.

    Notepad is a classic Win32 application — the baseline test target.
    """
    proc = _launch_app("notepad.exe", wait_seconds=2.0)
    if proc is None:
        pytest.skip("Could not launch Notepad")

    # Windows 11 UWP Notepad: launcher PID differs from the actual Notepad process.
    # Look up the real process the same way calculator_app handles UWP apps.
    time.sleep(1)
    actual_pid = _find_process_by_name("Notepad.exe")
    if actual_pid is None:
        actual_pid = proc.pid

    yield actual_pid

    # Teardown: kill Notepad (by image name for UWP, fallback to proc handle)
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "Notepad.exe"],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass
    try:
        proc.terminate()
    except Exception:
        pass


@pytest.fixture(scope="module")
def calculator_app(has_desktop) -> Generator[int, None, None]:
    """Launch Calculator and yield its PID. Clean up on teardown.

    Windows Calculator is a UWP/WinUI3 app — tests modern UI framework detection.
    Note: UWP apps launch via a broker, so the PID from Popen may differ
    from the actual Calculator process.
    """
    proc = _launch_app("calc.exe", wait_seconds=3.0)
    if proc is None:
        pytest.skip("Could not launch Calculator")

    # UWP apps: the actual process is CalculatorApp.exe, not calc.exe
    time.sleep(1)
    actual_pid = _find_process_by_name("CalculatorApp.exe")
    if actual_pid is None:
        # Fallback: try the broker PID
        actual_pid = _find_process_by_name("Calculator.exe")
    if actual_pid is None:
        actual_pid = proc.pid

    yield actual_pid

    # Teardown: kill Calculator
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "CalculatorApp.exe"],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass
    try:
        proc.terminate()
    except Exception:
        pass


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
