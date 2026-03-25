"""Tests for WindowsForms class name role mapping (Issue #314)."""
import pytest
from naturo.bridge import _get_role_from_class_name


class TestWindowsFormsClassMapping:
    """Test WindowsForms10.{TYPE}.app.0.xxx class name parsing."""

    def test_direct_match_takes_priority(self):
        """Standard Win32 class names should match directly."""
        assert _get_role_from_class_name("Button") == "Button"
        assert _get_role_from_class_name("Edit") == "Edit"
        assert _get_role_from_class_name("Static") == "Text"
        assert _get_role_from_class_name("SysTreeView32") == "Tree"

    def test_windowsforms_static(self):
        """WindowsForms10.STATIC.app.0.xxx should map to Text."""
        cls = "WindowsForms10.STATIC.app.0.37504c8_r29_ad1"
        assert _get_role_from_class_name(cls) == "Text"

    def test_windowsforms_edit(self):
        """WindowsForms10.EDIT.app.0.xxx should map to Edit."""
        cls = "WindowsForms10.EDIT.app.0.12345_r7_ae3"
        assert _get_role_from_class_name(cls) == "Edit"

    def test_windowsforms_systreev32(self):
        """WindowsForms10.SysTreeView32.app.0.xxx should map to Tree."""
        cls = "WindowsForms10.SysTreeView32.app.0.abc123"
        assert _get_role_from_class_name(cls) == "Tree"

    def test_windowsforms_window_generic_container(self):
        """WindowsForms10.Window.8.app.0.xxx should map to Pane (generic container)."""
        cls = "WindowsForms10.Window.8.app.0.37504c8_r29_ad1"
        assert _get_role_from_class_name(cls) == "Pane"

    def test_windowsforms_button(self):
        """WindowsForms10.BUTTON.app.0.xxx should map to Button."""
        cls = "WindowsForms10.BUTTON.app.0.xyz789"
        assert _get_role_from_class_name(cls) == "Button"

    def test_unknown_class_defaults_to_pane(self):
        """Unknown class names should default to Pane."""
        assert _get_role_from_class_name("SomeCustomClass") == "Pane"
        assert _get_role_from_class_name("WindowsForms10.UNKNOWN.app.0.xxx") == "Pane"

    def test_top_level_defaults_to_window(self):
        """Top-level unknown classes should default to Window."""
        assert _get_role_from_class_name("CustomMainWindow", is_top_level=True) == "Window"
        assert _get_role_from_class_name("WindowsForms10.UNKNOWN.app.0.xxx", is_top_level=True) == "Window"

    def test_thunderrt6_vb6_classes(self):
        """VB6 ThunderRT6 class names should still work."""
        assert _get_role_from_class_name("ThunderRT6FormDC") == "Window"
        assert _get_role_from_class_name("ThunderRT6CommandButton") == "Button"
        assert _get_role_from_class_name("ThunderRT6TextBox") == "Edit"
        assert _get_role_from_class_name("ThunderRT6CheckBox") == "CheckBox"

    def test_case_sensitivity(self):
        """Uppercase TYPE should be handled (STATIC → Static)."""
        # STATIC (uppercase) should match Static (capitalized) in map
        cls = "WindowsForms10.STATIC.app.0.xxx"
        assert _get_role_from_class_name(cls) == "Text"
        # EDIT → Edit
        cls = "WindowsForms10.EDIT.app.0.yyy"
        assert _get_role_from_class_name(cls) == "Edit"
