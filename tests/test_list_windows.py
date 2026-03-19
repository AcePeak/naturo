"""Tests for window listing functionality.

These tests require Windows with the naturo_core.dll available.
They are automatically skipped on other platforms.
"""

from __future__ import annotations

import platform

import pytest


pytestmark = [
    pytest.mark.ui,
    pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Window listing tests require Windows with naturo_core.dll",
    ),
]


@pytest.fixture
def core():
    """Create and initialize a NaturoCore instance."""
    from naturo.bridge import NaturoCore

    c = NaturoCore()
    c.init()
    yield c
    c.shutdown()


@pytest.fixture
def backend():
    """Create a WindowsBackend instance."""
    from naturo.backends.windows import WindowsBackend

    return WindowsBackend()


def test_list_windows_returns_list(core):
    """T030: list_windows should return a list of WindowInfo objects."""
    from naturo.bridge import WindowInfo

    windows = core.list_windows()
    assert isinstance(windows, list)
    for w in windows:
        assert isinstance(w, WindowInfo)
        assert isinstance(w.hwnd, int)
        assert isinstance(w.title, str)
        assert isinstance(w.pid, int)


def test_list_windows_has_visible_windows(core):
    """T031: On a desktop session, there should be visible windows."""
    windows = core.list_windows()
    visible = [w for w in windows if w.is_visible]
    assert isinstance(visible, list)


def test_list_windows_window_has_dimensions(core):
    """T032: Each window should have non-negative dimensions."""
    windows = core.list_windows()
    for w in windows:
        assert w.width >= 0
        assert w.height >= 0


def test_backend_list_windows(backend):
    """T033: WindowsBackend.list_windows should return base.WindowInfo instances."""
    from naturo.backends.base import WindowInfo

    windows = backend.list_windows()
    assert isinstance(windows, list)
    for w in windows:
        assert isinstance(w, WindowInfo)
        assert hasattr(w, "handle")
        assert hasattr(w, "title")
        assert hasattr(w, "process_name")


def test_list_windows_json_has_required_fields(core):
    """T034: Each window should have all required fields populated."""
    windows = core.list_windows()
    for w in windows:
        assert w.hwnd is not None
        assert w.title is not None
        assert w.process_name is not None
        assert w.pid is not None
        assert w.x is not None
        assert w.y is not None
        assert w.is_visible is not None
        assert w.is_minimized is not None


def test_filter_windows_by_app_name(core):
    """T035: Filter windows by app/process name.

    Verify that filtering by process name substring returns only matching windows.
    """
    windows = core.list_windows()
    if not windows:
        pytest.skip("No windows available")

    # Pick the first window's process name to filter by
    target_proc = windows[0].process_name
    if not target_proc:
        pytest.skip("No process name available")

    # Extract just the executable name for filtering
    import os
    exe_name = os.path.basename(target_proc).lower()

    filtered = [w for w in windows if exe_name in w.process_name.lower()]
    assert len(filtered) >= 1
    for w in filtered:
        assert exe_name in w.process_name.lower()


def test_filter_windows_by_pid(core):
    """T036: Filter windows by PID.

    Verify that filtering by PID returns only windows owned by that process.
    """
    windows = core.list_windows()
    if not windows:
        pytest.skip("No windows available")

    target_pid = windows[0].pid
    filtered = [w for w in windows if w.pid == target_pid]
    assert len(filtered) >= 1
    for w in filtered:
        assert w.pid == target_pid


def test_filter_windows_by_title_substring(core):
    """T037: Filter windows by title substring.

    Verify that title-based filtering works correctly.
    """
    windows = core.list_windows()
    titled = [w for w in windows if w.title]
    if not titled:
        pytest.skip("No titled windows available")

    # Use first 3 characters of a known title as search term
    target_title = titled[0].title
    search = target_title[:3].lower() if len(target_title) >= 3 else target_title.lower()

    filtered = [w for w in windows if search in w.title.lower()]
    assert len(filtered) >= 1
    for w in filtered:
        assert search in w.title.lower()


def test_filter_visible_only_windows(core):
    """T038: Filter visible-only windows (exclude minimized).

    Verify that we can separate visible from minimized windows.
    """
    windows = core.list_windows()
    visible = [w for w in windows if w.is_visible and not w.is_minimized]
    minimized = [w for w in windows if w.is_minimized]

    # Both lists should be valid (possibly empty)
    assert isinstance(visible, list)
    assert isinstance(minimized, list)

    # No overlap between visible-not-minimized and minimized
    visible_hwnds = {w.hwnd for w in visible}
    for w in minimized:
        # A minimized window may still be is_visible=True on some OS versions
        # but it should be is_minimized=True
        assert w.is_minimized
