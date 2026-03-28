"""Tests for click --on with Chinese accessibility names (#525).

Verifies that:
1. find_element passes the target hwnd (not foreground) when provided
2. click passes hwnd through to find_element
3. ElementNotFoundError is raised (not NaturoCoreError -1) on miss
4. The text fallback receives the correct window context
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call
from inspect import signature

from naturo.backends.base import WindowInfo, ElementInfo


def _make_backend():
    """Create a WindowsBackend class for testing."""
    try:
        from naturo.backends.windows import WindowsBackend
        return WindowsBackend
    except Exception:
        pytest.skip("WindowsBackend not available on this platform")


class TestFindElementHwnd:
    """find_element should accept and use hwnd parameter (#525)."""

    def test_find_element_accepts_hwnd(self):
        """find_element signature includes hwnd parameter."""
        BackendClass = _make_backend()
        sig = signature(BackendClass.find_element)
        assert "hwnd" in sig.parameters
        assert sig.parameters["hwnd"].default is None

    def test_find_element_passes_hwnd_to_core(self):
        """find_element forwards hwnd to the C++ core."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend.find_element = BackendClass.find_element.__get__(backend)

        mock_core = MagicMock()
        mock_core.find_element.return_value = None  # not found
        backend._ensure_core = MagicMock(return_value=mock_core)

        result = backend.find_element(selector="七", hwnd=0x12345)

        # Should pass hwnd=0x12345, not hwnd=0
        mock_core.find_element.assert_called_once_with(
            hwnd=0x12345, role=None, name="七",
        )
        assert result is None

    def test_find_element_defaults_to_foreground(self):
        """find_element uses hwnd=0 (foreground) when hwnd not provided."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend.find_element = BackendClass.find_element.__get__(backend)

        mock_core = MagicMock()
        mock_core.find_element.return_value = None
        backend._ensure_core = MagicMock(return_value=mock_core)

        backend.find_element(selector="七")

        mock_core.find_element.assert_called_once_with(
            hwnd=0, role=None, name="七",
        )


class TestClickHwnd:
    """click should pass hwnd to find_element (#525)."""

    def test_click_accepts_hwnd(self):
        """click signature includes hwnd parameter."""
        BackendClass = _make_backend()
        sig = signature(BackendClass.click)
        assert "hwnd" in sig.parameters

    def test_click_passes_hwnd_to_find_element(self):
        """click forwards hwnd to find_element for element search."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend.click = BackendClass.click.__get__(backend)

        mock_element = MagicMock()
        mock_element.x = 100
        mock_element.y = 200
        mock_element.width = 50
        mock_element.height = 30
        backend.find_element = MagicMock(return_value=mock_element)

        mock_core = MagicMock()
        backend._ensure_core = MagicMock(return_value=mock_core)

        backend.click(element_id="七", hwnd=0xABCD)

        backend.find_element.assert_called_once_with(
            selector="七", hwnd=0xABCD,
        )


class TestClickNotFoundError:
    """click should raise ElementNotFoundError, not NaturoCoreError (#525)."""

    def test_raises_element_not_found_error(self):
        """click raises ElementNotFoundError when element is not found."""
        from naturo.errors import ElementNotFoundError

        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend.click = BackendClass.click.__get__(backend)
        backend.find_element = MagicMock(return_value=None)

        mock_core = MagicMock()
        backend._ensure_core = MagicMock(return_value=mock_core)

        with pytest.raises(ElementNotFoundError) as exc_info:
            backend.click(element_id="七")

        # Error message should mention the selector, not "Invalid argument"
        assert "七" in str(exc_info.value)
        assert "Invalid argument" not in str(exc_info.value)

    def test_not_found_error_for_chinese_text(self):
        """Verify the error message is clear for Chinese element names."""
        from naturo.errors import ElementNotFoundError

        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend.click = BackendClass.click.__get__(backend)
        backend.find_element = MagicMock(return_value=None)

        mock_core = MagicMock()
        backend._ensure_core = MagicMock(return_value=mock_core)

        with pytest.raises(ElementNotFoundError):
            backend.click(element_id="清除", hwnd=0x1234)

        # find_element should have been called with the correct hwnd
        backend.find_element.assert_called_once_with(
            selector="清除", hwnd=0x1234,
        )
