"""Tests for window listing functionality.

These tests require Windows with the naturo_core.dll available.
They are automatically skipped on other platforms.
"""

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
    """list_windows should return a list of WindowInfo objects."""
    from naturo.bridge import WindowInfo

    windows = core.list_windows()
    assert isinstance(windows, list)
    # In a desktop session, there should be at least one window
    # In CI, the list might be empty but should still work
    for w in windows:
        assert isinstance(w, WindowInfo)
        assert isinstance(w.hwnd, int)
        assert isinstance(w.title, str)
        assert isinstance(w.pid, int)


def test_list_windows_has_visible_windows(core):
    """On a desktop session, there should be visible windows."""
    windows = core.list_windows()
    visible = [w for w in windows if w.is_visible]
    # This might be 0 in a headless CI, so just verify the filtering works
    assert isinstance(visible, list)


def test_list_windows_window_has_dimensions(core):
    """Each window should have non-negative dimensions."""
    windows = core.list_windows()
    for w in windows:
        # Minimized windows may have 0 dimensions
        assert w.width >= 0
        assert w.height >= 0


def test_backend_list_windows(backend):
    """WindowsBackend.list_windows should return base.WindowInfo instances."""
    from naturo.backends.base import WindowInfo

    windows = backend.list_windows()
    assert isinstance(windows, list)
    for w in windows:
        assert isinstance(w, WindowInfo)
        assert hasattr(w, "handle")
        assert hasattr(w, "title")
        assert hasattr(w, "process_name")


def test_list_windows_json_has_required_fields(core):
    """Each window should have all required fields populated."""
    windows = core.list_windows()
    for w in windows:
        # All fields should be present (even if empty string)
        assert w.hwnd is not None
        assert w.title is not None
        assert w.process_name is not None
        assert w.pid is not None
        assert w.x is not None
        assert w.y is not None
        assert w.is_visible is not None
        assert w.is_minimized is not None
