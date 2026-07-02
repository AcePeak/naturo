"""Tests for Win32+UIA hybrid enumeration (Issue #312).

Tests the hybrid mode that uses Win32 HWND tree as base with UIA
drill-down for complex controls (VSFlexGrid, SysListView32, etc.).
"""
import pytest
from unittest.mock import MagicMock, patch

from naturo.bridge import (
    ElementInfo,
    _HYBRID_UIA_DRILL_CLASSES,
    _needs_uia_drill,
    _tag_uia_source,
    populate_hierarchy,
)


# ── _HYBRID_UIA_DRILL_CLASSES ──────────────────────────────────────────────


def test_hybrid_drill_classes_contains_expected():
    """Known complex controls should be in the drill-down set."""
    assert "VSFlexGrid8N" in _HYBRID_UIA_DRILL_CLASSES
    assert "VSFlexGrid8U" in _HYBRID_UIA_DRILL_CLASSES
    assert "SysListView32" in _HYBRID_UIA_DRILL_CLASSES
    assert "SysTreeView32" in _HYBRID_UIA_DRILL_CLASSES
    assert "AfxOleControl42u" in _HYBRID_UIA_DRILL_CLASSES


def test_hybrid_drill_classes_excludes_simple_controls():
    """Simple Win32 controls should NOT be in the drill-down set."""
    assert "Button" not in _HYBRID_UIA_DRILL_CLASSES
    assert "Edit" not in _HYBRID_UIA_DRILL_CLASSES
    assert "Static" not in _HYBRID_UIA_DRILL_CLASSES
    assert "ComboBox" not in _HYBRID_UIA_DRILL_CLASSES


# ── _needs_uia_drill ──────────────────────────────────────────────────────


def test_needs_uia_drill_known_class():
    """Known complex controls always need UIA drill-down."""
    assert _needs_uia_drill("SysListView32", has_hwnd_children=False) is True
    assert _needs_uia_drill("SysListView32", has_hwnd_children=True) is True
    assert _needs_uia_drill("VSFlexGrid8N", has_hwnd_children=False) is True
    assert _needs_uia_drill("SysTreeView32", has_hwnd_children=True) is True


def test_needs_uia_drill_simple_class():
    """Simple Win32 controls do not need UIA drill-down."""
    assert _needs_uia_drill("Button", has_hwnd_children=False) is False
    assert _needs_uia_drill("Edit", has_hwnd_children=True) is False
    assert _needs_uia_drill("Static", has_hwnd_children=False) is False


def test_needs_uia_drill_unknown_class():
    """Unknown classes should not trigger drill-down."""
    assert _needs_uia_drill("MyCustomControl", has_hwnd_children=False) is False
    assert _needs_uia_drill("SomeGrid123", has_hwnd_children=True) is False


def test_needs_uia_drill_winforms_variant():
    """WindowsForms10.SysListView32.app.0.xxx should trigger drill-down."""
    assert _needs_uia_drill(
        "WindowsForms10.SysListView32.app.0.abc123", has_hwnd_children=False
    ) is True
    assert _needs_uia_drill(
        "WindowsForms10.SysTreeView32.app.0.abc123", has_hwnd_children=False
    ) is True


def test_needs_uia_drill_winforms_simple():
    """WindowsForms10.EDIT should NOT trigger drill-down."""
    assert _needs_uia_drill(
        "WindowsForms10.EDIT.app.0.abc", has_hwnd_children=False
    ) is False


# ── _tag_uia_source ───────────────────────────────────────────────────────


def test_tag_uia_source_tags_name():
    """Tag prepends [uia] to element names."""
    elem = ElementInfo(
        id="e1", role="DataItem", name="Row 1", value=None,
        x=0, y=0, width=100, height=20, children=[],
    )
    _tag_uia_source(elem)
    assert elem.name == "[uia] Row 1"


def test_tag_uia_source_tags_empty_name():
    """Elements with no name get [uia] as name."""
    elem = ElementInfo(
        id="e1", role="DataItem", name="", value=None,
        x=0, y=0, width=100, height=20, children=[],
    )
    _tag_uia_source(elem)
    assert elem.name == "[uia]"


def test_tag_uia_source_no_double_tag():
    """Already-tagged elements should not be tagged again."""
    elem = ElementInfo(
        id="e1", role="DataItem", name="[uia] Row 1", value=None,
        x=0, y=0, width=100, height=20, children=[],
    )
    _tag_uia_source(elem)
    assert elem.name == "[uia] Row 1"


def test_tag_uia_source_recursive():
    """Tag should propagate to all descendants."""
    child = ElementInfo(
        id="e2", role="Text", name="Cell A1", value=None,
        x=0, y=0, width=50, height=20, children=[],
    )
    parent = ElementInfo(
        id="e1", role="DataItem", name="Row 1", value=None,
        x=0, y=0, width=100, height=20, children=[child],
    )
    _tag_uia_source(parent)
    assert parent.name == "[uia] Row 1"
    assert child.name == "[uia] Cell A1"


# ── enumerate_hybrid_tree (platform-forced, host-independent) ─────────────


def test_hybrid_tree_returns_none_on_non_windows():
    """On non-Windows platforms, enumerate_hybrid_tree returns None.

    ``platform.system()`` is forced to a non-Windows value so the non-Windows
    contract is asserted deterministically regardless of the host OS. Without
    this pin the test reddens on a real Windows desktop, where the function
    performs live HWND enumeration and returns a tree (#1133).
    """
    from naturo.bridge import enumerate_hybrid_tree
    with patch("naturo.bridge._tree.platform.system", return_value="Linux"):
        result = enumerate_hybrid_tree(hwnd=12345, depth=3, core=None)
    assert result is None


def test_hybrid_tree_returns_none_on_non_windows_without_core():
    """Without a NaturoCore instance, the non-Windows path still returns None.

    ``platform.system()`` is forced to a non-Windows value so the assertion
    holds on any host; on Windows the function enumerates the real HWND tree
    even with ``core=None`` (pure Win32), so the platform must be pinned (#1133).
    """
    from naturo.bridge import enumerate_hybrid_tree
    with patch("naturo.bridge._tree.platform.system", return_value="Linux"):
        result = enumerate_hybrid_tree(hwnd=0, depth=3, core=None)
    assert result is None


@pytest.mark.skipif(
    __import__("platform").system() != "Windows",
    reason="Win32 HWND enumeration requires Windows",
)
class TestHybridTreeLive:
    """Live tests for hybrid enumeration (Windows-only, skipped in CI)."""

    def test_hybrid_tree_with_foreground(self):
        """Hybrid tree should return something for the foreground window."""
        from naturo.bridge import enumerate_hybrid_tree
        result = enumerate_hybrid_tree(hwnd=0, depth=3, core=None)
        assert result is not None
        assert result.role in ("Window", "Pane")


# ── Integration: WindowsBackend.get_element_tree with win32hybrid ─────────


def test_backend_get_element_tree_dispatches_win32hybrid():
    """Verify get_element_tree dispatches to enumerate_hybrid_tree for win32hybrid."""
    with patch("naturo.backends.windows.WindowsBackend._ensure_core") as mock_core, \
         patch("naturo.backends.windows.WindowsBackend._resolve_hwnd") as mock_resolve, \
         patch("naturo.bridge.enumerate_hybrid_tree") as mock_hybrid:

        mock_core_instance = MagicMock()
        mock_core.return_value = mock_core_instance
        mock_resolve.return_value = 12345

        # Return a minimal tree from hybrid
        mock_result = ElementInfo(
            id="e0", role="Window", name="Test", value=None,
            x=0, y=0, width=800, height=600,
            children=[
                ElementInfo(
                    id="e1", role="Button", name="OK", value=None,
                    x=10, y=10, width=80, height=30, children=[],
                ),
            ],
        )
        mock_hybrid.return_value = mock_result

        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = None
        backend._initialized = False
        backend._dpi_aware = False

        result = backend.get_element_tree(
            hwnd=12345, depth=5, backend="win32hybrid",
        )

        mock_hybrid.assert_called_once_with(
            hwnd=12345, depth=5, core=mock_core_instance,
        )
        assert result is not None
        assert result.role == "Window"


def test_auto_mode_uses_hybrid_for_shallow_tree():
    """Auto mode should use hybrid (not pure win32) when UIA tree is shallow."""
    with patch("naturo.backends.windows.WindowsBackend._ensure_core") as mock_core, \
         patch("naturo.backends.windows.WindowsBackend._resolve_hwnd") as mock_resolve, \
         patch("naturo.bridge.enumerate_hybrid_tree") as mock_hybrid:

        mock_core_instance = MagicMock()
        mock_core.return_value = mock_core_instance
        mock_resolve.return_value = 12345

        # UIA returns shallow tree (only Pane containers)
        from naturo.bridge import ElementInfo as BridgeElementInfo
        shallow_uia = BridgeElementInfo(
            id="e0", role="Window", name="VB6 App", value=None,
            x=0, y=0, width=800, height=600,
            children=[
                BridgeElementInfo(
                    id="e1", role="Pane", name="", value=None,
                    x=0, y=0, width=400, height=300, children=[],
                ),
                BridgeElementInfo(
                    id="e2", role="Pane", name="", value=None,
                    x=400, y=0, width=400, height=300, children=[],
                ),
            ],
        )
        mock_core_instance.get_element_tree.return_value = shallow_uia

        # Hybrid returns richer tree
        hybrid_tree = BridgeElementInfo(
            id="e0", role="Window", name="VB6 App", value=None,
            x=0, y=0, width=800, height=600,
            children=[
                BridgeElementInfo(
                    id="e1", role="Button", name="Save", value=None,
                    x=10, y=10, width=80, height=30, children=[],
                ),
                BridgeElementInfo(
                    id="e2", role="Edit", name="Name", value=None,
                    x=10, y=50, width=200, height=25, children=[],
                ),
                BridgeElementInfo(
                    id="e3", role="DataGrid", name="Grid", value=None,
                    x=10, y=100, width=780, height=400,
                    children=[
                        BridgeElementInfo(
                            id="e4", role="DataItem", name="[uia] Row 1",
                            value=None, x=10, y=120, width=780, height=20,
                            children=[],
                        ),
                    ],
                ),
            ],
        )
        mock_hybrid.return_value = hybrid_tree

        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = None
        backend._initialized = False
        backend._dpi_aware = False

        # Patch _is_afh_window to return False (not UWP)
        with patch.object(backend, "_is_afh_window", return_value=False):
            result = backend.get_element_tree(
                hwnd=12345, depth=5, backend="auto",
            )

        # Should have called hybrid since UIA was shallow
        mock_hybrid.assert_called_once()
        assert result is not None
        # Result should have 3 children (from hybrid), not 2 (from shallow UIA)
        assert len(result.children) == 3
