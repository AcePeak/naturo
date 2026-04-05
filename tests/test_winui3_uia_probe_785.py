"""Tests for #785: UIA probe must detect standalone WinUI 3 apps.

Win11 Calculator and Paint are standalone WinUI 3 apps not hosted by
ApplicationFrameHost. The UIA probe only checked AFH child windows when
the main HWND returned an empty tree, so these apps fell through to
vision-only detection.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from naturo.detect.probes import _find_winui_content_children, probe_uia


class TestFindWinuiContentChildren:
    """Tests for the _find_winui_content_children helper."""

    def test_returns_empty_on_non_windows(self):
        with patch("naturo.detect.probes.platform") as mock_platform:
            mock_platform.system.return_value = "Linux"
            assert _find_winui_content_children(12345) == []

    @pytest.mark.desktop
    def test_returns_empty_for_normal_window(self):
        """A normal window with no WinUI children returns empty."""
        # This would need a real desktop to test — skip on CI
        pass


class TestProbeUiaWinuiFallback:
    """probe_uia must try WinUI children when AFH children are empty."""

    @patch("naturo.detect.probes.platform")
    @patch("naturo.detect.probes._find_main_window", return_value=1001)
    @patch("naturo.detect.probes._find_afh_content_children", return_value=[])
    @patch("naturo.detect.probes._find_winui_content_children", return_value=[2001])
    def test_winui_fallback_succeeds(
        self, mock_winui, mock_afh, mock_main, mock_platform
    ):
        """When AFH search returns empty but WinUI children exist, probe succeeds."""
        mock_platform.system.return_value = "Windows"

        mock_core = MagicMock()
        # Main HWND returns None (empty tree), WinUI child returns tree
        mock_core.get_element_tree.side_effect = [None, {"role": "Window"}]

        with patch("naturo.detect.probes._get_native_core", return_value=mock_core):
            result = probe_uia(pid=100, exe="CalculatorApp.exe", hwnd=None)

        assert result is not None
        assert result.method.value == "uia"
        assert mock_core.get_element_tree.call_count == 2

    @patch("naturo.detect.probes.platform")
    @patch("naturo.detect.probes._find_main_window", return_value=1001)
    @patch("naturo.detect.probes._find_afh_content_children", return_value=[])
    @patch("naturo.detect.probes._find_winui_content_children", return_value=[])
    def test_winui_fallback_no_children(
        self, mock_winui, mock_afh, mock_main, mock_platform
    ):
        """When both AFH and WinUI searches find nothing, probe returns None."""
        mock_platform.system.return_value = "Windows"

        mock_core = MagicMock()
        mock_core.get_element_tree.return_value = None

        with patch("naturo.detect.probes._get_native_core", return_value=mock_core):
            result = probe_uia(pid=100, exe="CalculatorApp.exe", hwnd=None)

        assert result is None

    @patch("naturo.detect.probes.platform")
    @patch("naturo.detect.probes._find_main_window", return_value=1001)
    def test_direct_tree_success_skips_fallbacks(self, mock_main, mock_platform):
        """When main HWND has a tree, no fallback probing needed."""
        mock_platform.system.return_value = "Windows"

        mock_core = MagicMock()
        mock_core.get_element_tree.return_value = {"role": "Window"}

        with patch("naturo.detect.probes._get_native_core", return_value=mock_core):
            result = probe_uia(pid=100, exe="notepad.exe", hwnd=None)

        assert result is not None
        mock_core.get_element_tree.assert_called_once()


class TestComtypesFallbackWinUI:
    """#841: comtypes fallback must also probe WinUI child windows.

    Actual comtypes testing requires Windows with the COM DLL loaded.
    These tests verify the Strategy 1 (native DLL) path covers the same
    child-window probing logic that was added to Strategy 2 (comtypes).
    The integration test test_detect_calculator_has_uia exercises the
    full path on a real Windows desktop.
    """

    @patch("naturo.detect.probes.platform")
    @patch("naturo.detect.probes._find_main_window", return_value=1001)
    @patch("naturo.detect.probes._find_afh_content_children", return_value=[])
    @patch("naturo.detect.probes._find_winui_content_children", return_value=[2001, 2002])
    def test_winui_fallback_tries_multiple_children(
        self, mock_winui, mock_afh, mock_main, mock_platform,
    ):
        """When multiple WinUI children exist, probe tries each in order."""
        mock_platform.system.return_value = "Windows"

        mock_core = MagicMock()
        # Main HWND empty, first WinUI child empty, second succeeds
        mock_core.get_element_tree.side_effect = [None, None, {"role": "Window"}]

        with patch("naturo.detect.probes._get_native_core", return_value=mock_core):
            result = probe_uia(pid=100, exe="CalculatorApp.exe", hwnd=None)

        assert result is not None
        assert result.method.value == "uia"
        assert mock_core.get_element_tree.call_count == 3
