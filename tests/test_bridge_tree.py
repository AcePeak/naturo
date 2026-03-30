"""Tests for naturo.bridge._tree — role mapping, UIA drill decisions, UIA tagging.

Only tests pure-logic helpers that don't require Windows/ctypes.
"""

import pytest

from naturo.bridge._models import ElementInfo
from naturo.bridge._tree import (
    _WIN32_CLASS_ROLE_MAP,
    _HYBRID_UIA_DRILL_CLASSES,
    _get_role_from_class_name,
    _needs_uia_drill,
    _tag_uia_source,
)


# ---------------------------------------------------------------------------
# _get_role_from_class_name
# ---------------------------------------------------------------------------

class TestGetRoleFromClassName:
    """Tests for Win32 class name → UIA role mapping."""

    def test_direct_match_button(self):
        assert _get_role_from_class_name("Button") == "Button"

    def test_direct_match_edit(self):
        assert _get_role_from_class_name("Edit") == "Edit"

    def test_direct_match_static(self):
        assert _get_role_from_class_name("Static") == "Text"

    def test_direct_match_combobox(self):
        assert _get_role_from_class_name("ComboBox") == "ComboBox"

    def test_direct_match_syslistview(self):
        assert _get_role_from_class_name("SysListView32") == "DataGrid"

    def test_direct_match_systreeview(self):
        assert _get_role_from_class_name("SysTreeView32") == "Tree"

    def test_direct_match_statusbar(self):
        assert _get_role_from_class_name("msctls_statusbar32") == "StatusBar"

    def test_thunderrt6_button(self):
        assert _get_role_from_class_name("ThunderRT6CommandButton") == "Button"

    def test_thunderrt6_textbox(self):
        assert _get_role_from_class_name("ThunderRT6TextBox") == "Edit"

    def test_thunderrt6_form(self):
        assert _get_role_from_class_name("ThunderRT6FormDC") == "Window"

    def test_unknown_class_default_pane(self):
        assert _get_role_from_class_name("SomeUnknownClass") == "Pane"

    def test_unknown_class_top_level_window(self):
        assert _get_role_from_class_name("SomeUnknownClass", is_top_level=True) == "Window"

    def test_windowsforms_edit(self):
        assert _get_role_from_class_name("WindowsForms10.EDIT.app.0.xxx") == "Edit"

    def test_windowsforms_static(self):
        assert _get_role_from_class_name("WindowsForms10.STATIC.app.0.xxx") == "Text"

    def test_windowsforms_embedded_systreeview(self):
        assert _get_role_from_class_name("WindowsForms10.SysTreeView32.app.0.xxx") == "Tree"

    def test_windowsforms_unknown_inner_type(self):
        """Unknown inner type should fall through to default Pane."""
        assert _get_role_from_class_name("WindowsForms10.CustomCtrl.app.0.xxx") == "Pane"

    def test_windowsforms_short_class(self):
        """WindowsForms class with too few parts should fall through."""
        assert _get_role_from_class_name("WindowsForms10.X") == "Pane"

    def test_all_map_entries_have_string_values(self):
        """Sanity check: all values in the role map should be strings."""
        for cls_name, role in _WIN32_CLASS_ROLE_MAP.items():
            assert isinstance(cls_name, str)
            assert isinstance(role, str)


# ---------------------------------------------------------------------------
# _needs_uia_drill
# ---------------------------------------------------------------------------

class TestNeedsUiaDrill:
    """Tests for _needs_uia_drill decision logic."""

    def test_known_class_vsflexgrid(self):
        assert _needs_uia_drill("VSFlexGrid8N", has_hwnd_children=False) is True
        assert _needs_uia_drill("VSFlexGrid8U", has_hwnd_children=True) is True

    def test_known_class_syslistview(self):
        assert _needs_uia_drill("SysListView32", has_hwnd_children=False) is True

    def test_known_class_systreeview(self):
        assert _needs_uia_drill("SysTreeView32", has_hwnd_children=True) is True

    def test_unknown_class_returns_false(self):
        assert _needs_uia_drill("Button", has_hwnd_children=False) is False
        assert _needs_uia_drill("Edit", has_hwnd_children=True) is False

    def test_windowsforms_variant_of_known_class(self):
        assert _needs_uia_drill("WindowsForms10.SysListView32.app.0.xxx", has_hwnd_children=False) is True

    def test_windowsforms_variant_of_unknown_class(self):
        assert _needs_uia_drill("WindowsForms10.Button.app.0.xxx", has_hwnd_children=False) is False

    def test_windowsforms_short_class(self):
        assert _needs_uia_drill("WindowsForms10.X", has_hwnd_children=False) is False

    def test_all_drill_classes_in_set(self):
        """Sanity check: all entries in the drill set are strings."""
        for cls in _HYBRID_UIA_DRILL_CLASSES:
            assert isinstance(cls, str)
            assert len(cls) > 0


# ---------------------------------------------------------------------------
# _tag_uia_source
# ---------------------------------------------------------------------------

class TestTagUiaSource:
    """Tests for _tag_uia_source UIA subtree tagging."""

    def test_tags_element_name(self):
        elem = ElementInfo(id="e1", role="Button", name="Save", value=None, x=0, y=0, width=0, height=0)
        _tag_uia_source(elem)
        assert elem.name == "[uia] Save"

    def test_tags_empty_name(self):
        elem = ElementInfo(id="e1", role="Button", name="", value=None, x=0, y=0, width=0, height=0)
        _tag_uia_source(elem)
        assert elem.name == "[uia]"

    def test_does_not_double_tag(self):
        elem = ElementInfo(id="e1", role="Button", name="[uia] Save", value=None, x=0, y=0, width=0, height=0)
        _tag_uia_source(elem)
        assert elem.name == "[uia] Save"  # not "[uia] [uia] Save"

    def test_tags_children_recursively(self):
        child1 = ElementInfo(id="c1", role="Text", name="Label", value=None, x=0, y=0, width=0, height=0)
        child2 = ElementInfo(id="c2", role="Button", name="OK", value=None, x=0, y=0, width=0, height=0)
        parent = ElementInfo(
            id="p1", role="Group", name="Panel", value=None,
            x=0, y=0, width=0, height=0,
            children=[child1, child2],
        )
        _tag_uia_source(parent)
        assert parent.name == "[uia] Panel"
        assert child1.name == "[uia] Label"
        assert child2.name == "[uia] OK"

    def test_tags_deeply_nested(self):
        grandchild = ElementInfo(id="gc", role="Text", name="Deep", value=None, x=0, y=0, width=0, height=0)
        child = ElementInfo(id="ch", role="Group", name="Mid", value=None, x=0, y=0, width=0, height=0, children=[grandchild])
        root = ElementInfo(id="rt", role="Window", name="Top", value=None, x=0, y=0, width=0, height=0, children=[child])
        _tag_uia_source(root)
        assert grandchild.name == "[uia] Deep"

    def test_leaf_element_no_children(self):
        elem = ElementInfo(id="e1", role="Edit", name="Input", value=None, x=0, y=0, width=0, height=0)
        _tag_uia_source(elem)
        assert elem.name == "[uia] Input"
        assert elem.children == []
