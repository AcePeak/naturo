from __future__ import annotations

import platform
from typing import Optional

import pytest


def pytest_configure(config):
    """Register custom markers."""
    pass  # markers defined in pyproject.toml


def _has_desktop_session() -> bool:
    """Check if an interactive desktop session is available.

    On Windows, calls GetDesktopWindow() via user32. Returns False when
    running headless (e.g. via SSH without an attached console session).
    Always returns False on non-Windows platforms.
    """
    if platform.system() != "Windows":
        return False
    try:
        import ctypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        desktop = user32.GetDesktopWindow()
        return desktop != 0
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
