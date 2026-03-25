"""Tests for ElementInfo hwnd field (Issue #316)."""
import pytest
from naturo.bridge import ElementInfo


class TestElementInfoHwnd:
    """Verify ElementInfo stores hwnd for Win32 hybrid mode."""

    def test_hwnd_field_exists(self):
        """ElementInfo should have optional hwnd attribute."""
        elem = ElementInfo(
            id="e0",
            role="Button",
            name="OK",
            value=None,
            x=10,
            y=20,
            width=80,
            height=30,
            hwnd=12345,
        )
        assert elem.hwnd == 12345

    def test_hwnd_optional(self):
        """hwnd should be optional (None for non-Win32 backends)."""
        elem = ElementInfo(
            id="e1",
            role="Edit",
            name="Input",
            value="text",
            x=0,
            y=0,
            width=100,
            height=20,
        )
        assert elem.hwnd is None

    def test_hwnd_serializes_to_dict(self):
        """When converting to dict, hwnd should be included."""
        from dataclasses import asdict
        elem = ElementInfo(
            id="e2",
            role="Window",
            name="Main",
            value=None,
            x=0,
            y=0,
            width=800,
            height=600,
            hwnd=0x1234ABCD,
        )
        d = asdict(elem)
        assert "hwnd" in d
        assert d["hwnd"] == 0x1234ABCD

    def test_hwnd_none_serializes_as_none(self):
        """hwnd=None should serialize as null in JSON."""
        from dataclasses import asdict
        elem = ElementInfo(
            id="e3",
            role="Text",
            name="Label",
            value="Hello",
            x=10,
            y=10,
            width=50,
            height=15,
        )
        d = asdict(elem)
        assert d["hwnd"] is None
