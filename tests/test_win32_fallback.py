"""Tests for Win32 HWND enumeration fallback (Issue #308).

Tests the VB6/ActiveX control fallback that uses EnumChildWindows
when UIA/MSAA return opaque Pane containers.
"""
import pytest
from naturo.bridge import _WIN32_CLASS_ROLE_MAP


def test_win32_class_role_mapping():
    """Test that common Win32 class names map to UIA-style roles."""
    # Standard Win32 controls
    assert _WIN32_CLASS_ROLE_MAP["Static"] == "Text"
    assert _WIN32_CLASS_ROLE_MAP["Edit"] == "Edit"
    assert _WIN32_CLASS_ROLE_MAP["Button"] == "Button"
    assert _WIN32_CLASS_ROLE_MAP["ComboBox"] == "ComboBox"
    assert _WIN32_CLASS_ROLE_MAP["ListBox"] == "List"
    
    # Common controls
    assert _WIN32_CLASS_ROLE_MAP["SysListView32"] == "DataGrid"
    assert _WIN32_CLASS_ROLE_MAP["SysTreeView32"] == "Tree"
    assert _WIN32_CLASS_ROLE_MAP["msctls_statusbar32"] == "StatusBar"
    
    # VB6/Thunder controls (用友U8 ERP)
    assert _WIN32_CLASS_ROLE_MAP["ThunderRT6FormDC"] == "Window"
    assert _WIN32_CLASS_ROLE_MAP["ThunderRT6UserControlDC"] == "Pane"
    assert _WIN32_CLASS_ROLE_MAP["ThunderRT6PictureBoxDC"] == "Pane"
    assert _WIN32_CLASS_ROLE_MAP["ThunderRT6TextBox"] == "Edit"
    assert _WIN32_CLASS_ROLE_MAP["ThunderRT6CommandButton"] == "Button"
    assert _WIN32_CLASS_ROLE_MAP["ThunderRT6ComboBox"] == "ComboBox"
    assert _WIN32_CLASS_ROLE_MAP["ThunderRT6ListBox"] == "List"
    assert _WIN32_CLASS_ROLE_MAP["ThunderRT6Frame"] == "Group"
    assert _WIN32_CLASS_ROLE_MAP["ThunderRT6OptionButton"] == "RadioButton"
    assert _WIN32_CLASS_ROLE_MAP["ThunderRT6CheckBox"] == "CheckBox"


def test_win32_class_role_default():
    """Test that unknown Win32 class names don't break the mapping."""
    # Unknown class should not be in the map
    assert "SomeWeirdCustomControl" not in _WIN32_CLASS_ROLE_MAP
    # Code should use .get() with a fallback, so test that pattern
    role = _WIN32_CLASS_ROLE_MAP.get("UnknownClass", "Pane")
    assert role == "Pane"


@pytest.mark.skip(reason="Requires Windows and a VB6 app to test live")
def test_enumerate_child_windows_live():
    """Live test of Win32 HWND enumeration (requires VB6 app).
    
    This test is skipped by default. To run it:
    1. Open a VB6/ActiveX application (e.g., 用友U8 ERP)
    2. Get the HWND (e.g., via spy++ or naturo list windows)
    3. Un-skip this test and set the hwnd below
    4. Run: pytest tests/test_win32_fallback.py::test_enumerate_child_windows_live -v
    """
    from naturo.bridge import enumerate_child_windows
    
    # Replace with actual HWND of a VB6 form
    hwnd = 0x12345  # Example HWND (replace with real one)
    
    result = enumerate_child_windows(hwnd=hwnd, depth=3)
    assert result is not None
    assert result.role in ("Window", "Pane")
    assert len(result.children) > 0, "VB6 form should have child controls"
    
    # Check that we got some actionable controls (not just Panes)
    actionable_roles = {"Button", "Edit", "Text", "ComboBox", "CheckBox", "RadioButton"}
    found_actionable = any(
        child.role in actionable_roles
        for child in result.children
    )
    assert found_actionable, "Should find at least one actionable control"


def test_shallow_tree_detection():
    """Test the heuristic for detecting shallow trees that need Win32 fallback."""
    from naturo.backends.windows import WindowsBackend
    from naturo.backends.base import ElementInfo as BaseElementInfo
    
    # Case 1: Empty tree (no children)
    empty_tree = BaseElementInfo(
        id="e0", role="Window", name="Test", value=None,
        x=0, y=0, width=100, height=100, children=[], properties={}
    )
    assert WindowsBackend._is_shallow_tree(empty_tree) is True
    
    # Case 2: Only Pane containers (no actionable elements)
    pane_tree = BaseElementInfo(
        id="e0", role="Window", name="Test", value=None,
        x=0, y=0, width=100, height=100,
        children=[
            BaseElementInfo(
                id="e1", role="Pane", name="", value=None,
                x=0, y=0, width=50, height=50, children=[], properties={}
            ),
            BaseElementInfo(
                id="e2", role="Pane", name="", value=None,
                x=50, y=0, width=50, height=50, children=[], properties={}
            ),
        ],
        properties={}
    )
    assert WindowsBackend._is_shallow_tree(pane_tree) is True
    
    # Case 3: Deep tree with many actionable elements (healthy tree)
    healthy_tree = BaseElementInfo(
        id="e0", role="Window", name="Test", value=None,
        x=0, y=0, width=100, height=100,
        children=[
            BaseElementInfo(
                id="e1", role="Button", name="OK", value=None,
                x=0, y=0, width=50, height=20, children=[], properties={}
            ),
            BaseElementInfo(
                id="e2", role="Edit", name="", value="text", 
                x=0, y=20, width=50, height=20, children=[], properties={}
            ),
            BaseElementInfo(
                id="e3", role="Text", name="Label", value=None,
                x=0, y=40, width=50, height=20, children=[], properties={}
            ),
            BaseElementInfo(
                id="e4", role="ComboBox", name="", value=None,
                x=0, y=60, width=50, height=20, children=[], properties={}
            ),
            BaseElementInfo(
                id="e5", role="CheckBox", name="Check me", value=None,
                x=0, y=80, width=50, height=20, children=[], properties={}
            ),
        ],
        properties={}
    )
    assert WindowsBackend._is_shallow_tree(healthy_tree) is False
    
    # Case 4: 4 actionable elements (below threshold of 5)
    borderline_tree = BaseElementInfo(
        id="e0", role="Window", name="Test", value=None,
        x=0, y=0, width=100, height=100,
        children=[
            BaseElementInfo(
                id="e1", role="Button", name="OK", value=None,
                x=0, y=0, width=50, height=20, children=[], properties={}
            ),
            BaseElementInfo(
                id="e2", role="Edit", name="", value="text",
                x=0, y=20, width=50, height=20, children=[], properties={}
            ),
            BaseElementInfo(
                id="e3", role="Text", name="Label", value=None,
                x=0, y=40, width=50, height=20, children=[], properties={}
            ),
            BaseElementInfo(
                id="e4", role="ComboBox", name="", value=None,
                x=0, y=60, width=50, height=20, children=[], properties={}
            ),
        ],
        properties={}
    )
    assert WindowsBackend._is_shallow_tree(borderline_tree) is True
