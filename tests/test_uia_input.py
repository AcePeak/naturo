"""Tests for UIA-based input methods (#226).

Tests the set_element_value, focus_element_uia, and _init_comtypes_uia
methods added to WindowsBackend to fix silent input failures in schtasks
context.
"""
import platform
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# Skip entire module on non-Windows
pytestmark = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="UIA input methods are Windows-only",
)

# Check if comtypes is available (not installed in CI)
try:
    import comtypes  # noqa: F401
    _has_comtypes = True
except ImportError:
    _has_comtypes = False


@pytest.fixture
def windows_backend():
    """Create a WindowsBackend instance with mocked core."""
    from naturo.backends.windows import WindowsBackend
    backend = WindowsBackend()
    return backend


class TestInitComtypesUia:
    """Tests for _init_comtypes_uia helper."""

    @pytest.mark.skipif(not _has_comtypes, reason="comtypes not installed")
    def test_returns_uia_and_module(self, windows_backend):
        """_init_comtypes_uia returns (uia, module) tuple."""
        mock_mod = MagicMock()
        mock_mod.IUIAutomation = MagicMock()
        mock_uia = MagicMock()

        with patch("comtypes.client.CreateObject", return_value=mock_uia), \
             patch.dict("sys.modules", {"comtypes.gen.UIAutomationClient": mock_mod}):
            uia, mod = windows_backend._init_comtypes_uia()
            assert mod is mock_mod

    def test_raises_on_no_comtypes(self, windows_backend):
        """_init_comtypes_uia raises ImportError without comtypes."""
        import sys
        # Temporarily hide comtypes
        saved = {}
        for key in list(sys.modules.keys()):
            if key == "comtypes" or key.startswith("comtypes."):
                saved[key] = sys.modules.pop(key)
        try:
            with patch.dict("sys.modules", {"comtypes": None, "comtypes.client": None}):
                with pytest.raises((ImportError, ModuleNotFoundError)):
                    windows_backend._init_comtypes_uia()
        finally:
            sys.modules.update(saved)


class TestSetElementValue:
    """Tests for set_element_value method."""

    def test_returns_false_without_comtypes(self, windows_backend):
        """set_element_value returns False when comtypes unavailable."""
        with patch.object(windows_backend, "_init_comtypes_uia",
                          side_effect=ImportError("no comtypes")):
            result = windows_backend.set_element_value("hello", hwnd=12345)
            assert result is False

    def test_returns_true_on_success(self, windows_backend):
        """set_element_value returns True after successful SetValue."""
        mock_mod = MagicMock()
        mock_mod.UIA_ValuePatternId = 10002
        mock_uia = MagicMock()
        mock_elem = MagicMock()
        mock_vp = MagicMock()
        mock_vp.CurrentIsReadOnly = False

        mock_pat_unk = MagicMock()
        mock_pat_unk.QueryInterface.return_value = mock_vp
        mock_elem.GetCurrentPattern.return_value = mock_pat_unk

        with patch.object(windows_backend, "_init_comtypes_uia",
                          return_value=(mock_uia, mock_mod)), \
             patch.object(windows_backend, "_find_uia_element",
                          return_value=mock_elem):
            result = windows_backend.set_element_value(
                "Hello World", hwnd=12345, role="Edit"
            )
            assert result is True
            mock_vp.SetValue.assert_called_once_with("Hello World")

    def test_returns_false_when_element_not_found(self, windows_backend):
        """set_element_value returns False when target element not found."""
        mock_mod = MagicMock()
        mock_mod.UIA_ControlTypePropertyId = 30003
        mock_uia = MagicMock()
        # Make FindFirst also return None for the fallback path
        mock_root = MagicMock()
        mock_root.FindFirst.return_value = None
        mock_uia.ElementFromHandle.return_value = mock_root

        with patch.object(windows_backend, "_init_comtypes_uia",
                          return_value=(mock_uia, mock_mod)), \
             patch.object(windows_backend, "_find_uia_element",
                          return_value=None):
            result = windows_backend.set_element_value(
                "text", hwnd=12345, name="nonexistent"
            )
            assert result is False

    def test_returns_false_when_readonly(self, windows_backend):
        """set_element_value returns False for read-only elements."""
        mock_mod = MagicMock()
        mock_mod.UIA_ValuePatternId = 10002
        mock_uia = MagicMock()
        mock_elem = MagicMock()
        mock_vp = MagicMock()
        mock_vp.CurrentIsReadOnly = True

        mock_pat_unk = MagicMock()
        mock_pat_unk.QueryInterface.return_value = mock_vp
        mock_elem.GetCurrentPattern.return_value = mock_pat_unk

        with patch.object(windows_backend, "_init_comtypes_uia",
                          return_value=(mock_uia, mock_mod)), \
             patch.object(windows_backend, "_find_uia_element",
                          return_value=mock_elem):
            result = windows_backend.set_element_value(
                "text", hwnd=12345, role="Edit"
            )
            assert result is False

    def test_returns_false_when_no_value_pattern(self, windows_backend):
        """set_element_value returns False when element lacks ValuePattern."""
        mock_mod = MagicMock()
        mock_mod.UIA_ValuePatternId = 10002
        mock_uia = MagicMock()
        mock_elem = MagicMock()
        mock_elem.GetCurrentPattern.return_value = None

        with patch.object(windows_backend, "_init_comtypes_uia",
                          return_value=(mock_uia, mock_mod)), \
             patch.object(windows_backend, "_find_uia_element",
                          return_value=mock_elem):
            result = windows_backend.set_element_value(
                "text", hwnd=12345, role="Edit"
            )
            assert result is False


class TestFocusElementUia:
    """Tests for focus_element_uia method."""

    def test_returns_true_on_success(self, windows_backend):
        """focus_element_uia returns True after successful SetFocus."""
        mock_mod = MagicMock()
        mock_uia = MagicMock()
        mock_elem = MagicMock()

        with patch.object(windows_backend, "_init_comtypes_uia",
                          return_value=(mock_uia, mock_mod)), \
             patch.object(windows_backend, "_find_uia_element",
                          return_value=mock_elem):
            result = windows_backend.focus_element_uia(
                hwnd=12345, name="Edit1"
            )
            assert result is True
            mock_elem.SetFocus.assert_called_once()

    def test_returns_false_without_comtypes(self, windows_backend):
        """focus_element_uia returns False without comtypes."""
        with patch.object(windows_backend, "_init_comtypes_uia",
                          side_effect=ImportError("no comtypes")):
            result = windows_backend.focus_element_uia(hwnd=12345, name="Edit1")
            assert result is False

    def test_returns_false_when_element_not_found(self, windows_backend):
        """focus_element_uia returns False when element not found."""
        mock_mod = MagicMock()
        mock_uia = MagicMock()

        with patch.object(windows_backend, "_init_comtypes_uia",
                          return_value=(mock_uia, mock_mod)), \
             patch.object(windows_backend, "_find_uia_element",
                          return_value=None):
            result = windows_backend.focus_element_uia(
                hwnd=12345, name="nonexistent"
            )
            assert result is False


class TestFindUiaElement:
    """Tests for _find_uia_element helper."""

    def test_searches_by_name(self, windows_backend):
        """_find_uia_element creates name condition and searches."""
        mock_mod = MagicMock()
        mock_mod.UIA_NamePropertyId = 30005
        mock_mod.TreeScope_Descendants = 4
        mock_uia = MagicMock()
        mock_element = MagicMock()
        mock_uia.GetRootElement.return_value.FindFirst.return_value = mock_element

        result = windows_backend._find_uia_element(
            mock_uia, mock_mod, hwnd=0, name="Test"
        )
        assert result is mock_element
        mock_uia.CreatePropertyCondition.assert_called_with(30005, "Test")

    def test_searches_by_automation_id(self, windows_backend):
        """_find_uia_element creates AutomationId condition."""
        mock_mod = MagicMock()
        mock_mod.UIA_AutomationIdPropertyId = 30011
        mock_mod.TreeScope_Descendants = 4
        mock_uia = MagicMock()

        windows_backend._find_uia_element(
            mock_uia, mock_mod, hwnd=0, automation_id="txtContent"
        )
        mock_uia.CreatePropertyCondition.assert_called_with(30011, "txtContent")

    def test_returns_none_without_criteria(self, windows_backend):
        """_find_uia_element returns None when no name/aid given."""
        mock_mod = MagicMock()
        mock_uia = MagicMock()

        result = windows_backend._find_uia_element(mock_uia, mock_mod, hwnd=0)
        assert result is None

    def test_scopes_to_hwnd(self, windows_backend):
        """_find_uia_element uses ElementFromHandle when hwnd given."""
        mock_mod = MagicMock()
        mock_mod.UIA_NamePropertyId = 30005
        mock_mod.TreeScope_Descendants = 4
        mock_uia = MagicMock()

        windows_backend._find_uia_element(
            mock_uia, mock_mod, hwnd=99999, name="Test"
        )
        mock_uia.ElementFromHandle.assert_called_with(99999)
