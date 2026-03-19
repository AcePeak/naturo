"""Tests for naturo.models.menu — MenuItem data model."""

import pytest

from naturo.models.menu import MenuItem


class TestMenuItem:
    """Tests for MenuItem dataclass."""

    def test_basic_creation(self):
        """Create a simple menu item."""
        item = MenuItem(name="File")
        assert item.name == "File"
        assert item.shortcut is None
        assert item.submenu is None
        assert item.enabled is True
        assert item.checked is False

    def test_with_shortcut(self):
        """Menu item with keyboard shortcut."""
        item = MenuItem(name="Save", shortcut="Ctrl+S")
        assert item.shortcut == "Ctrl+S"

    def test_with_submenu(self):
        """Nested menu structure."""
        sub_items = [
            MenuItem(name="New", shortcut="Ctrl+N"),
            MenuItem(name="Open", shortcut="Ctrl+O"),
            MenuItem(name="Save", shortcut="Ctrl+S"),
        ]
        file_menu = MenuItem(name="File", submenu=sub_items)
        assert len(file_menu.submenu) == 3
        assert file_menu.submenu[0].name == "New"
        assert file_menu.submenu[2].shortcut == "Ctrl+S"

    def test_disabled_item(self):
        """Disabled menu item."""
        item = MenuItem(name="Paste", enabled=False)
        assert item.enabled is False

    def test_checked_item(self):
        """Checked/toggled menu item."""
        item = MenuItem(name="Word Wrap", checked=True)
        assert item.checked is True

    def test_to_dict(self):
        """Serialise to dictionary."""
        item = MenuItem(name="Save", shortcut="Ctrl+S")
        d = item.to_dict()
        assert d["name"] == "Save"
        assert d["shortcut"] == "Ctrl+S"
        assert "enabled" not in d  # True is default, omitted
        assert "checked" not in d  # False is default, omitted

    def test_to_dict_disabled(self):
        """Disabled state appears in dict."""
        item = MenuItem(name="Paste", enabled=False)
        d = item.to_dict()
        assert d["enabled"] is False

    def test_to_dict_checked(self):
        """Checked state appears in dict."""
        item = MenuItem(name="Wrap", checked=True)
        d = item.to_dict()
        assert d["checked"] is True

    def test_to_dict_nested(self):
        """Nested submenu serialises correctly."""
        item = MenuItem(
            name="File",
            submenu=[MenuItem(name="New", shortcut="Ctrl+N")],
        )
        d = item.to_dict()
        assert "submenu" in d
        assert len(d["submenu"]) == 1
        assert d["submenu"][0]["name"] == "New"

    def test_from_dict(self):
        """Deserialise from dictionary."""
        d = {"name": "Save", "shortcut": "Ctrl+S", "enabled": True, "checked": False}
        item = MenuItem.from_dict(d)
        assert item.name == "Save"
        assert item.shortcut == "Ctrl+S"

    def test_from_dict_nested(self):
        """Deserialise nested structure."""
        d = {
            "name": "File",
            "submenu": [
                {"name": "New", "shortcut": "Ctrl+N"},
                {"name": "Open"},
            ],
        }
        item = MenuItem.from_dict(d)
        assert item.submenu is not None
        assert len(item.submenu) == 2
        assert item.submenu[0].shortcut == "Ctrl+N"

    def test_roundtrip(self):
        """to_dict -> from_dict preserves data."""
        original = MenuItem(
            name="File",
            submenu=[
                MenuItem(name="New", shortcut="Ctrl+N"),
                MenuItem(name="Save", shortcut="Ctrl+S", enabled=False),
            ],
        )
        restored = MenuItem.from_dict(original.to_dict())
        assert restored.name == original.name
        assert len(restored.submenu) == 2
        assert restored.submenu[1].enabled is False

    def test_flatten(self):
        """Flatten produces path-based list."""
        item = MenuItem(
            name="File",
            submenu=[
                MenuItem(name="New", shortcut="Ctrl+N"),
                MenuItem(
                    name="Recent",
                    submenu=[MenuItem(name="doc.txt")],
                ),
            ],
        )
        flat = item.flatten()
        paths = [f["path"] for f in flat]
        assert "File" in paths
        assert "File > New" in paths
        assert "File > Recent" in paths
        assert "File > Recent > doc.txt" in paths

    def test_flatten_shortcuts(self):
        """Flattened items include shortcuts."""
        item = MenuItem(
            name="Edit",
            submenu=[MenuItem(name="Copy", shortcut="Ctrl+C")],
        )
        flat = item.flatten()
        copy_entry = [f for f in flat if f["path"] == "Edit > Copy"][0]
        assert copy_entry["shortcut"] == "Ctrl+C"
