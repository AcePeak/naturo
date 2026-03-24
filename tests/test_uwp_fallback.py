"""Tests for UWP/WinUI ApplicationFrameHost child window element tree fallback.

These tests use mocking and run on all platforms to verify the fallback
logic in WindowsBackend.get_element_tree for UWP and WinUI 3 apps.

The fallback enumerates child HWNDs of the ApplicationFrameHost window
and tries each one until a non-empty UIA element tree is found.  This
handles both classic UWP (CoreWindow) and WinUI 3 (DesktopWindowXamlSource).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def backend():
    """Create a WindowsBackend with mocked core initialization."""
    with patch("naturo.backends.windows.WindowsBackend._ensure_core"):
        from naturo.backends.windows import WindowsBackend

        b = WindowsBackend()
        b._core = MagicMock()
        return b


def _make_element(role="Pane", name="", children=None):
    """Create a mock ElementInfo-like object."""
    el = SimpleNamespace(
        id="e0",
        role=role,
        name=name,
        value=None,
        x=0, y=0, width=100, height=100,
        children=children or [],
        parent_id=None,
        keyboard_shortcut=None,
    )
    return el


def _make_window(handle, title, process_name, pid=100):
    """Create a mock WindowInfo."""
    return SimpleNamespace(
        handle=handle,
        title=title,
        process_name=process_name,
        pid=pid,
        x=0, y=0, width=800, height=600,
        is_visible=True,
        is_minimized=False,
    )


class TestIsAfhWindow:
    """Tests for _is_afh_window helper."""

    def test_detects_afh_window(self, backend):
        """Should return True for ApplicationFrameHost.exe windows."""
        backend.list_windows = MagicMock(return_value=[
            _make_window(123, "Calculator", "ApplicationFrameHost.exe"),
        ])
        assert backend._is_afh_window(123) is True

    def test_rejects_non_afh_window(self, backend):
        """Should return False for regular windows."""
        backend.list_windows = MagicMock(return_value=[
            _make_window(456, "Notepad", "notepad.exe"),
        ])
        assert backend._is_afh_window(456) is False

    def test_unknown_handle(self, backend):
        """Should return False for unknown handles."""
        backend.list_windows = MagicMock(return_value=[])
        assert backend._is_afh_window(999) is False


class TestFindUwpContentHwnd:
    """Tests for _find_uwp_content_hwnd static method."""

    def test_returns_empty_on_non_windows(self):
        """Should return empty list on non-Windows platforms."""
        from naturo.backends.windows import WindowsBackend

        import sys
        if sys.platform == "win32":
            pytest.skip("Test only applicable on non-Windows")

        assert WindowsBackend._find_uwp_content_hwnd(12345) == []


class TestUwpElementTreeFallback:
    """Tests for UWP/WinUI child window fallback in get_element_tree."""

    def test_uwp_fallback_retries_with_child_hwnds(self, backend):
        """When AFH returns empty tree, should try child HWNDs."""
        empty_root = _make_element(role="Pane", name="", children=[])
        rich_root = _make_element(
            role="Window", name="Calculator",
            children=[_make_element(role="Button", name="1")],
        )

        # First call returns empty tree, second with child HWND returns rich
        backend._core.get_element_tree = MagicMock(
            side_effect=[empty_root, rich_root],
        )
        backend._resolve_hwnd = MagicMock(return_value=100)
        backend._is_afh_window = MagicMock(return_value=True)

        with patch.object(type(backend), "_find_uwp_content_hwnd",
                          return_value=[200]):
            with patch("naturo.backends.windows.populate_hierarchy"):
                result = backend.get_element_tree(app="calc", backend="uia")

        assert result is not None
        assert result.role == "Window"
        assert len(result.children) == 1
        assert result.children[0].role == "Button"

    def test_uwp_fallback_tries_multiple_children(self, backend):
        """Should try multiple child HWNDs until one has content."""
        empty_root = _make_element(role="Pane", name="", children=[])
        also_empty = _make_element(role="Pane", name="", children=[])
        rich_root = _make_element(
            role="Window", name="Settings",
            children=[_make_element(role="List", name="Categories")],
        )

        # First call: AFH empty; child 200: empty; child 300: rich
        backend._core.get_element_tree = MagicMock(
            side_effect=[empty_root, also_empty, rich_root],
        )
        backend._resolve_hwnd = MagicMock(return_value=100)
        backend._is_afh_window = MagicMock(return_value=True)

        with patch.object(type(backend), "_find_uwp_content_hwnd",
                          return_value=[200, 300]):
            with patch("naturo.backends.windows.populate_hierarchy"):
                result = backend.get_element_tree(app="settings", backend="uia")

        assert result is not None
        assert result.role == "Window"
        assert len(result.children) == 1
        # Should have tried 3 times: AFH + child 200 + child 300
        assert backend._core.get_element_tree.call_count == 3

    def test_no_fallback_when_tree_has_children(self, backend):
        """Should not attempt fallback when tree already has children."""
        rich_root = _make_element(
            role="Pane", name="Notepad",
            children=[_make_element(role="Edit", name="Text")],
        )

        backend._core.get_element_tree = MagicMock(return_value=rich_root)
        backend._resolve_hwnd = MagicMock(return_value=100)
        backend._is_afh_window = MagicMock()

        with patch("naturo.backends.windows.populate_hierarchy"):
            result = backend.get_element_tree(app="notepad", backend="uia")

        # _is_afh_window should not be called since tree has children
        backend._is_afh_window.assert_not_called()
        assert len(result.children) == 1

    def test_fallback_skipped_for_non_afh(self, backend):
        """Should not retry for non-AFH windows even with empty tree."""
        empty_root = _make_element(role="Pane", name="", children=[])

        backend._core.get_element_tree = MagicMock(return_value=empty_root)
        backend._resolve_hwnd = MagicMock(return_value=100)
        backend._is_afh_window = MagicMock(return_value=False)

        with patch("naturo.backends.windows.populate_hierarchy"):
            result = backend.get_element_tree(app="notepad", backend="uia")

        # Only one call — no retry
        assert backend._core.get_element_tree.call_count == 1

    def test_auto_backend_uses_uwp_fallback(self, backend):
        """UWP fallback should also work with backend='auto'."""
        empty_root = _make_element(role="Pane", name="", children=[])
        rich_root = _make_element(
            role="Window", name="Settings",
            children=[_make_element(role="List", name="Categories")],
        )

        backend._core.get_element_tree = MagicMock(
            side_effect=[empty_root, rich_root],
        )
        backend._resolve_hwnd = MagicMock(return_value=100)
        backend._is_afh_window = MagicMock(return_value=True)

        with patch.object(type(backend), "_find_uwp_content_hwnd",
                          return_value=[300]):
            with patch("naturo.backends.windows.populate_hierarchy"):
                result = backend.get_element_tree(app="settings",
                                                  backend="auto")

        assert result is not None
        assert result.role == "Window"
        assert len(result.children) == 1

    def test_fallback_returns_original_when_no_children_found(self, backend):
        """When all child HWNDs also return empty, keep original result."""
        empty_root = _make_element(role="Pane", name="", children=[])
        child_empty = _make_element(role="Pane", name="", children=[])

        backend._core.get_element_tree = MagicMock(
            side_effect=[empty_root, child_empty],
        )
        backend._resolve_hwnd = MagicMock(return_value=100)
        backend._is_afh_window = MagicMock(return_value=True)

        with patch.object(type(backend), "_find_uwp_content_hwnd",
                          return_value=[200]):
            with patch("naturo.backends.windows.populate_hierarchy"):
                result = backend.get_element_tree(app="calc", backend="uia")

        # Should return original empty result (post-processed)
        assert result is not None
        assert result.children == []

    def test_fallback_with_no_child_windows(self, backend):
        """When AFH has no child windows at all, return original result."""
        empty_root = _make_element(role="Pane", name="", children=[])

        backend._core.get_element_tree = MagicMock(return_value=empty_root)
        backend._resolve_hwnd = MagicMock(return_value=100)
        backend._is_afh_window = MagicMock(return_value=True)

        with patch.object(type(backend), "_find_uwp_content_hwnd",
                          return_value=[]):
            with patch("naturo.backends.windows.populate_hierarchy"):
                result = backend.get_element_tree(app="calc", backend="uia")

        assert result is not None
        assert backend._core.get_element_tree.call_count == 1

class TestClickElementUia:
    """Tests for click_element_uia UWP click fallback (#248)."""

    def test_click_element_uia_returns_false_on_non_windows(self, backend):
        """Should return False gracefully on non-Windows (no comtypes)."""
        import sys
        if sys.platform == "win32":
            pytest.skip("Test only applicable on non-Windows")
        result = backend.click_element_uia(x=100, y=200)
        assert result is False

    def test_click_element_uia_method_exists(self, backend):
        """Backend should have click_element_uia method."""
        assert hasattr(backend, "click_element_uia")

    def test_click_element_uia_handles_import_error(self, backend):
        """Should return False when comtypes is not available."""
        with patch.object(backend, "_init_comtypes_uia", side_effect=ImportError("no comtypes")):
            result = backend.click_element_uia(x=100, y=200)
        assert result is False


class TestWinui3DesktopWindowXamlSource:
    """Tests for WinUI 3 DesktopWindowXamlSource child window support."""

    def test_winui3_desktop_window_xaml_source(self, backend):
        """Should find WinUI 3 apps that use DesktopWindowXamlSource."""
        empty_root = _make_element(role="Pane", name="", children=[])
        # First child (CoreWindow) also empty, second (DesktopWindowXamlSource) has content
        also_empty = _make_element(role="Pane", name="", children=[])
        rich_root = _make_element(
            role="Window", name="Calculator",
            children=[
                _make_element(role="Group", name="Number pad"),
                _make_element(role="Button", name="7"),
            ],
        )

        backend._core.get_element_tree = MagicMock(
            side_effect=[empty_root, also_empty, rich_root],
        )
        backend._resolve_hwnd = MagicMock(return_value=100)
        backend._is_afh_window = MagicMock(return_value=True)

        # Simulate: CoreWindow(200) → empty, DesktopWindowXamlSource(300) → rich
        with patch.object(type(backend), "_find_uwp_content_hwnd",
                          return_value=[200, 300]):
            with patch("naturo.backends.windows.populate_hierarchy"):
                result = backend.get_element_tree(app="calc", backend="uia")

        assert result is not None
        assert result.role == "Window"
        assert len(result.children) == 2
