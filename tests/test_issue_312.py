"""Tests for issue #312: Win32+UIA hybrid mode for VB6/ActiveX apps.

All tests use mocks — no real Windows environment is needed.
The hybrid mode builds a Win32 HWND skeleton, then probes known complex
controls (VSFlexGrid, SysListView32, etc.) with UIA to fill in virtual
items (rows, cells) that have no HWND of their own.
"""
from __future__ import annotations

import platform
import types
from unittest.mock import MagicMock, patch, call

import pytest

from naturo.backends.base import ElementInfo as BaseElementInfo
from naturo.bridge import ElementInfo as BridgeElementInfo


# ── Helper factories ───────────────────────────────────────────────────────


def _bridge_elem(
    id: str = "e0",
    role: str = "Window",
    name: str = "Test",
    hwnd: int | None = None,
    children: list | None = None,
) -> BridgeElementInfo:
    """Create a BridgeElementInfo for mocking Win32/UIA results."""
    return BridgeElementInfo(
        id=id,
        role=role,
        name=name,
        value=None,
        x=0,
        y=0,
        width=100,
        height=100,
        children=children or [],
        hwnd=hwnd,
    )


def _make_backend():
    """Create a WindowsBackend instance with mocked core, bypassing DPI init."""
    from naturo.backends.windows import WindowsBackend
    backend = WindowsBackend.__new__(WindowsBackend)
    backend._core = MagicMock()
    backend._initialized = True
    backend._dpi_aware = True
    return backend


def _make_vsflexgrid_tree() -> BridgeElementInfo:
    """Win32 tree with a VSFlexGrid leaf node (no sub-HWNDs)."""
    grid_node = _bridge_elem(
        id="e2",
        role="Custom",
        name="[VSFlexGrid8N]",
        hwnd=2001,
        children=[],  # leaf — no child HWNDs
    )
    root = _bridge_elem(
        id="e0",
        role="Window",
        name="U8 ERP [ThunderRT6Main]",
        hwnd=1000,
        children=[
            _bridge_elem(id="e1", role="Pane", name="[ThunderRT6Frame]", hwnd=1001, children=[
                grid_node,
            ]),
        ],
    )
    return root


def _make_uia_grid_subtree() -> BridgeElementInfo:
    """UIA sub-tree returned when probing the VSFlexGrid HWND."""
    rows = [
        _bridge_elem(id=f"row{i}", role="DataItem", name=f"Row {i}", hwnd=None)
        for i in range(3)
    ]
    grid_root = _bridge_elem(
        id="grid_root",
        role="Custom",
        name="VSFlexGrid",
        hwnd=2001,
        children=rows,
    )
    return grid_root


# ── Test 1: Basic hybrid merging ───────────────────────────────────────────


class TestHybridBasic:
    def test_hybrid_basic(self):
        """Win32 skeleton + UIA row/cell merge for VSFlexGrid."""
        backend = _make_backend()
        win32_tree = _make_vsflexgrid_tree()
        uia_subtree = _make_uia_grid_subtree()

        with patch("naturo.backends.windows.HYBRID_UIA_PROBE_CLASSES", {"VSFlexGrid8N"}):
            with patch("naturo.bridge.enumerate_child_windows", return_value=win32_tree):
                with patch("platform.system", return_value="Windows"):
                    # core.get_element_tree returns UIA sub-tree when probing the grid
                    def _get_tree(hwnd, depth):
                        if hwnd == 2001:
                            return uia_subtree
                        return None
                    backend._core.get_element_tree.side_effect = _get_tree

                    result = backend._hybrid_get_element_tree(handle=1000, depth=5)

        assert result is not None
        # Navigate to grid node: root → e1 → e2
        pane = result.children[0]
        grid = pane.children[0]
        # Grid should now have UIA children (3 rows)
        assert len(grid.children) == 3
        assert grid.children[0].role == "DataItem"


# ── Test 2: Leaf node UIA probing ─────────────────────────────────────────


class TestHybridLeafUIAProbe:
    def test_hybrid_leaf_uia_probe(self):
        """Any leaf node (no child HWNDs) triggers UIA probe."""
        backend = _make_backend()

        # A plain Edit control — not in HYBRID_UIA_PROBE_CLASSES, but a leaf
        edit_leaf = _bridge_elem(id="e1", role="Edit", name="Quantity", hwnd=3001, children=[])
        root = _bridge_elem(id="e0", role="Window", name="Dialog", hwnd=9000, children=[edit_leaf])

        uia_edit_sub = _bridge_elem(
            id="edit_root", role="Edit", name="Quantity", hwnd=3001,
            children=[_bridge_elem(id="inner", role="Text", name="value", hwnd=None)],
        )

        with patch("platform.system", return_value="Windows"):
            with patch("naturo.bridge.enumerate_child_windows", return_value=root):
                def _get_tree(hwnd, depth):
                    if hwnd == 3001:
                        return uia_edit_sub
                    return None
                backend._core.get_element_tree.side_effect = _get_tree

                result = backend._hybrid_get_element_tree(handle=9000, depth=5)

        assert result is not None
        edit_node = result.children[0]
        # Leaf was probed; UIA returned 1 child
        assert len(edit_node.children) == 1
        assert edit_node.children[0].role == "Text"


# ── Test 3: Source tagging ─────────────────────────────────────────────────


class TestHybridSourceTagging:
    def test_hybrid_source_tagging(self):
        """Win32 nodes get _hybrid_source='win32', UIA-filled children get 'uia'."""
        backend = _make_backend()
        win32_tree = _make_vsflexgrid_tree()
        uia_subtree = _make_uia_grid_subtree()

        with patch("naturo.backends.windows.HYBRID_UIA_PROBE_CLASSES", {"VSFlexGrid8N"}):
            with patch("naturo.bridge.enumerate_child_windows", return_value=win32_tree):
                with patch("platform.system", return_value="Windows"):
                    def _get_tree(hwnd, depth):
                        if hwnd == 2001:
                            return uia_subtree
                        return None
                    backend._core.get_element_tree.side_effect = _get_tree

                    result_bridge = backend._hybrid_get_element_tree(handle=1000, depth=5)

        # Check raw bridge tags before convert()
        assert result_bridge is not None
        assert result_bridge._hybrid_source == "win32"
        pane = result_bridge.children[0]
        assert pane._hybrid_source == "win32"
        grid = pane.children[0]
        # Grid itself is Win32 node; its children are UIA-sourced
        assert grid._hybrid_source == "win32"
        for row in grid.children:
            assert row._hybrid_source == "uia"

    def test_source_preserved_in_get_element_tree(self):
        """After full get_element_tree(), properties['source'] is present."""
        backend = _make_backend()
        win32_tree = _make_vsflexgrid_tree()
        uia_subtree = _make_uia_grid_subtree()

        with patch("naturo.backends.windows.HYBRID_UIA_PROBE_CLASSES", {"VSFlexGrid8N"}):
            with patch("naturo.backends.windows.WindowsBackend._resolve_hwnd", return_value=1000):
                with patch("naturo.bridge.enumerate_child_windows", return_value=win32_tree):
                    with patch("naturo.bridge.populate_hierarchy"):
                        with patch("platform.system", return_value="Windows"):
                            def _get_tree(hwnd, depth):
                                if hwnd == 2001:
                                    return uia_subtree
                                return None
                            backend._core.get_element_tree.side_effect = _get_tree

                            result = backend.get_element_tree(hwnd=1000, backend="hybrid")

        assert result is not None
        pane = result.children[0]
        grid = pane.children[0]
        # Grid node itself is win32
        assert grid.properties.get("source") == "win32"
        # Grid's children are uia-sourced
        for row in grid.children:
            assert row.properties.get("source") == "uia"


# ── Test 4: UIA failure graceful handling ─────────────────────────────────


class TestHybridUIAFailureGraceful:
    def test_hybrid_uia_failure_graceful(self):
        """When UIA probe raises an exception, the node is skipped gracefully."""
        backend = _make_backend()
        win32_tree = _make_vsflexgrid_tree()

        with patch("naturo.backends.windows.HYBRID_UIA_PROBE_CLASSES", {"VSFlexGrid8N"}):
            with patch("naturo.bridge.enumerate_child_windows", return_value=win32_tree):
                with patch("platform.system", return_value="Windows"):
                    # UIA always raises an exception
                    backend._core.get_element_tree.side_effect = RuntimeError("COM error")

                    result = backend._hybrid_get_element_tree(handle=1000, depth=5)

        # Should not raise; grid node just has no children
        assert result is not None
        pane = result.children[0]
        grid = pane.children[0]
        assert len(grid.children) == 0  # UIA failed, no children added


# ── Test 5: Non-Windows platform returns None ──────────────────────────────


class TestHybridNoWin32Support:
    def test_hybrid_no_win32_support(self):
        """On non-Windows platforms, _hybrid_get_element_tree returns None."""
        backend = _make_backend()

        with patch("platform.system", return_value="Darwin"):
            result = backend._hybrid_get_element_tree(handle=12345, depth=5)

        assert result is None


# ── Test 6: Auto mode upgrades to hybrid ──────────────────────────────────


class TestAutoModeUpgradesToHybrid:
    def test_auto_mode_upgrades_to_hybrid(self):
        """In auto mode, shallow UIA tree triggers hybrid upgrade."""
        backend = _make_backend()

        # Shallow UIA tree: 1 Pane child only
        shallow_pane = _bridge_elem(id="e1", role="Pane", name="Container", hwnd=None)
        shallow_root = _bridge_elem(
            id="e0", role="Window", name="U8 ERP", hwnd=1000,
            children=[shallow_pane],
        )

        # Hybrid produces a richer tree: 10 children
        rich_children = [_bridge_elem(id=f"e{i}", role="Edit", name=f"Field{i}", hwnd=2000 + i)
                         for i in range(10)]
        rich_root = _bridge_elem(
            id="e0", role="Window", name="U8 ERP", hwnd=1000,
            children=rich_children,
        )

        with patch("naturo.backends.windows.WindowsBackend._resolve_hwnd", return_value=1000):
            with patch("naturo.backends.windows.WindowsBackend._is_afh_window", return_value=False):
                with patch("naturo.bridge.populate_hierarchy"):
                    # core.get_element_tree returns shallow result initially
                    backend._core.get_element_tree.return_value = shallow_root
                    # Hybrid method returns rich tree
                    with patch.object(backend, "_hybrid_get_element_tree", return_value=rich_root):
                        result = backend.get_element_tree(hwnd=1000, backend="auto")

        assert result is not None
        # Should have used hybrid (10 children) not shallow UIA (1 child)
        assert len(result.children) == 10


# ── Test 7: CLI accepts --backend hybrid ─────────────────────────────────


class TestHybridCLIOption:
    def test_hybrid_cli_see_option(self):
        """'see' command --backend choice list includes 'hybrid'."""
        from naturo.cli.core import see

        backend_param = None
        for param in see.params:
            if param.name == "backend":
                backend_param = param
                break

        assert backend_param is not None, "--backend parameter not found on 'see' command"
        choices = backend_param.type.choices
        assert "hybrid" in choices, f"'hybrid' not in backend choices: {choices}"

    def test_hybrid_find_cmd_option(self):
        """find_cmd command --backend choice list also includes 'hybrid'."""
        from naturo.cli.core import find_cmd

        backend_param = None
        for param in find_cmd.params:
            if param.name == "backend":
                backend_param = param
                break

        assert backend_param is not None, "--backend parameter not found on 'find_cmd' command"
        choices = backend_param.type.choices
        assert "hybrid" in choices, f"'hybrid' not in find_cmd backend choices: {choices}"


# ── Test 8: Empty Win32 tree falls back to UIA ────────────────────────────


class TestHybridEmptyWin32Tree:
    def test_hybrid_empty_win32_tree(self):
        """When Win32 enumeration returns None, fall back to UIA."""
        backend = _make_backend()

        uia_fallback = _bridge_elem(
            id="e0", role="Window", name="App", hwnd=1000,
            children=[_bridge_elem(id="e1", role="Edit", name="Field", hwnd=None)],
        )

        with patch("platform.system", return_value="Windows"):
            with patch("naturo.bridge.enumerate_child_windows", return_value=None):
                backend._core.get_element_tree.return_value = uia_fallback

                result = backend._hybrid_get_element_tree(handle=1000, depth=5)

        # Should return UIA result (fallback)
        assert result is not None
        assert len(result.children) == 1
        assert result.children[0].role == "Edit"


# ── Test 9: UIA probe depth is limited ────────────────────────────────────


class TestHybridDepthLimit:
    def test_hybrid_depth_limit_known_class(self):
        """Known complex controls get UIA depth=3."""
        backend = _make_backend()

        grid_node = _bridge_elem(id="e1", role="Custom", name="[VSFlexGrid8N]", hwnd=2001, children=[])
        root = _bridge_elem(id="e0", role="Window", name="App", hwnd=1000, children=[grid_node])

        probed_depths = []

        def _get_tree(hwnd, depth):
            probed_depths.append((hwnd, depth))
            return None

        with patch("naturo.backends.windows.HYBRID_UIA_PROBE_CLASSES", {"VSFlexGrid8N"}):
            with patch("platform.system", return_value="Windows"):
                with patch("naturo.bridge.enumerate_child_windows", return_value=root):
                    backend._core.get_element_tree.side_effect = _get_tree
                    backend._hybrid_get_element_tree(handle=1000, depth=5)

        # The grid node (hwnd=2001) should be probed with depth=3
        grid_calls = [(h, d) for h, d in probed_depths if h == 2001]
        assert len(grid_calls) == 1
        assert grid_calls[0][1] == 3, f"Expected depth=3 for VSFlexGrid, got {grid_calls[0][1]}"

    def test_hybrid_depth_limit_leaf_node(self):
        """Leaf nodes (not in known classes) get UIA depth=2."""
        backend = _make_backend()

        # A plain Edit leaf — not in HYBRID_UIA_PROBE_CLASSES
        edit_node = _bridge_elem(id="e1", role="Edit", name="Amount", hwnd=5001, children=[])
        root = _bridge_elem(id="e0", role="Window", name="App", hwnd=1000, children=[edit_node])

        probed_depths = []

        def _get_tree(hwnd, depth):
            probed_depths.append((hwnd, depth))
            return None

        with patch("naturo.backends.windows.HYBRID_UIA_PROBE_CLASSES", {"VSFlexGrid8N"}):
            with patch("platform.system", return_value="Windows"):
                with patch("naturo.bridge.enumerate_child_windows", return_value=root):
                    backend._core.get_element_tree.side_effect = _get_tree
                    backend._hybrid_get_element_tree(handle=1000, depth=5)

        # The edit node (hwnd=5001) should be probed with depth=2
        edit_calls = [(h, d) for h, d in probed_depths if h == 5001]
        assert len(edit_calls) == 1
        assert edit_calls[0][1] == 2, f"Expected depth=2 for leaf, got {edit_calls[0][1]}"


# ── Test 10: HWND preserved after merge ────────────────────────────────────


class TestHybridPreservesHwnd:
    def test_hybrid_preserves_hwnd(self):
        """Win32 node HWND is preserved in properties after convert()."""
        backend = _make_backend()

        edit_node = _bridge_elem(id="e1", role="Edit", name="Field", hwnd=9999, children=[])
        root = _bridge_elem(id="e0", role="Window", name="App", hwnd=1000, children=[edit_node])

        with patch("naturo.backends.windows.WindowsBackend._resolve_hwnd", return_value=1000):
            with patch("platform.system", return_value="Windows"):
                with patch("naturo.bridge.enumerate_child_windows", return_value=root):
                    with patch("naturo.bridge.populate_hierarchy"):
                        # UIA probe returns nothing for the leaf
                        backend._core.get_element_tree.return_value = None

                        result = backend.get_element_tree(hwnd=1000, backend="hybrid")

        assert result is not None
        edit_base = result.children[0]
        assert edit_base.properties.get("hwnd") == 9999, (
            f"Expected hwnd=9999 in properties, got {edit_base.properties}"
        )
