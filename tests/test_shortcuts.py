"""Tests for keyboard shortcut discovery on UI elements."""

import pytest

from naturo.bridge import ElementInfo, _parse_element


class TestKeyboardShortcutDiscovery:
    """Tests for keyboard_shortcut field on ElementInfo."""

    def test_shortcut_none_by_default(self):
        """Elements without shortcuts default to None."""
        el = ElementInfo(
            id="e0", role="Text", name="Label", value=None,
            x=0, y=0, width=100, height=20,
        )
        assert el.keyboard_shortcut is None

    def test_shortcut_ctrl_combo(self):
        """Standard Ctrl+key shortcut is stored correctly."""
        el = ElementInfo(
            id="e1", role="Button", name="Save", value=None,
            x=0, y=0, width=80, height=30,
            keyboard_shortcut="Ctrl+S",
        )
        assert el.keyboard_shortcut == "Ctrl+S"

    def test_shortcut_multi_modifier(self):
        """Multi-modifier shortcut (Ctrl+Shift+key) is stored."""
        el = ElementInfo(
            id="e2", role="MenuItem", name="Save As", value=None,
            x=0, y=0, width=120, height=25,
            keyboard_shortcut="Ctrl+Shift+S",
        )
        assert el.keyboard_shortcut == "Ctrl+Shift+S"

    def test_shortcut_alt_combo(self):
        """Alt+key shortcut is stored."""
        el = ElementInfo(
            id="e3", role="MenuItem", name="File", value=None,
            x=0, y=0, width=50, height=25,
            keyboard_shortcut="Alt+F",
        )
        assert el.keyboard_shortcut == "Alt+F"

    def test_shortcut_function_key(self):
        """Function key shortcut is stored."""
        el = ElementInfo(
            id="e4", role="MenuItem", name="Help", value=None,
            x=0, y=0, width=50, height=25,
            keyboard_shortcut="F1",
        )
        assert el.keyboard_shortcut == "F1"

    def test_shortcut_parsed_from_dict(self):
        """keyboard_shortcut is parsed from dict via _parse_element."""
        data = {
            "id": "e5", "role": "Button", "name": "Undo", "value": None,
            "x": 10, "y": 20, "width": 80, "height": 30,
            "keyboard_shortcut": "Ctrl+Z",
        }
        el = _parse_element(data)
        assert el.keyboard_shortcut == "Ctrl+Z"

    def test_shortcut_none_when_missing_in_dict(self):
        """keyboard_shortcut is None when not in parsed dict."""
        data = {
            "id": "e6", "role": "Button", "name": "OK", "value": None,
            "x": 10, "y": 20, "width": 80, "height": 30,
        }
        el = _parse_element(data)
        assert el.keyboard_shortcut is None

    def test_shortcut_roundtrip_parse(self):
        """keyboard_shortcut survives dict → _parse_element."""
        data = {
            "id": "e7", "role": "MenuItem", "name": "Copy", "value": None,
            "x": 0, "y": 0, "width": 60, "height": 25,
            "keyboard_shortcut": "Ctrl+C",
        }
        el = _parse_element(data)
        assert el.keyboard_shortcut == "Ctrl+C"
        assert el.role == "MenuItem"
        assert el.name == "Copy"

    def test_shortcut_empty_string(self):
        """Empty string shortcut is stored as-is (not converted to None)."""
        el = ElementInfo(
            id="e8", role="Button", name="Test", value=None,
            x=0, y=0, width=80, height=30,
            keyboard_shortcut="",
        )
        assert el.keyboard_shortcut == ""

    def test_shortcut_preserved_in_children(self):
        """Shortcuts on nested children are preserved."""
        child = ElementInfo(
            id="c1", role="Button", name="Bold", value=None,
            x=10, y=10, width=30, height=30,
            keyboard_shortcut="Ctrl+B",
        )
        root = ElementInfo(
            id="r0", role="Toolbar", name="Format", value=None,
            x=0, y=0, width=400, height=40,
            children=[child],
        )
        assert root.children[0].keyboard_shortcut == "Ctrl+B"

    def test_shortcut_parsed_in_nested_children(self):
        """Shortcuts on nested children survive _parse_element."""
        data = {
            "id": "r0", "role": "Window", "name": "App", "value": None,
            "x": 0, "y": 0, "width": 800, "height": 600,
            "children": [{
                "id": "c1", "role": "Button", "name": "Save",
                "x": 10, "y": 10, "width": 80, "height": 30,
                "keyboard_shortcut": "Ctrl+S",
            }],
        }
        el = _parse_element(data)
        assert el.children[0].keyboard_shortcut == "Ctrl+S"
