"""Tests for MenuItem model and menu traversal logic."""

import pytest

from naturo.models.menu import MenuItem


class TestMenuItemModel:
    """Tests for the MenuItem dataclass."""

    def test_basic_creation(self):
        """MenuItem can be created with just a name."""
        item = MenuItem(name="File")
        assert item.name == "File"
        assert item.shortcut is None
        assert item.submenu is None
        assert item.enabled is True
        assert item.checked is False

    def test_creation_with_all_fields(self):
        """MenuItem with all fields set."""
        item = MenuItem(
            name="Bold",
            shortcut="Ctrl+B",
            submenu=None,
            enabled=True,
            checked=True,
        )
        assert item.name == "Bold"
        assert item.shortcut == "Ctrl+B"
        assert item.checked is True

    def test_disabled_item(self):
        """Disabled menu item."""
        item = MenuItem(name="Paste", enabled=False)
        assert item.enabled is False

    def test_nested_submenu(self):
        """MenuItem with nested submenus."""
        sub = [
            MenuItem(name="New", shortcut="Ctrl+N"),
            MenuItem(name="Open", shortcut="Ctrl+O"),
            MenuItem(name="Save", shortcut="Ctrl+S"),
        ]
        file_menu = MenuItem(name="File", submenu=sub)
        assert len(file_menu.submenu) == 3
        assert file_menu.submenu[0].name == "New"
        assert file_menu.submenu[2].shortcut == "Ctrl+S"

    def test_deep_nesting(self):
        """Deeply nested menu structure."""
        leaf = MenuItem(name="A4")
        sub2 = MenuItem(name="Page Size", submenu=[leaf])
        sub1 = MenuItem(name="Page Setup", submenu=[sub2])
        root = MenuItem(name="File", submenu=[sub1])
        assert root.submenu[0].submenu[0].submenu[0].name == "A4"


class TestMenuItemToDict:
    """Tests for to_dict serialization."""

    def test_minimal_to_dict(self):
        """Minimal item only includes name."""
        item = MenuItem(name="Edit")
        d = item.to_dict()
        assert d["name"] == "Edit"
        assert "shortcut" not in d  # None shortcuts are omitted
        assert "enabled" not in d   # True is default, omitted
        assert "checked" not in d   # False is default, omitted
        assert "submenu" not in d   # None is omitted

    def test_shortcut_included(self):
        """Shortcut is included when present."""
        d = MenuItem(name="Save", shortcut="Ctrl+S").to_dict()
        assert d["shortcut"] == "Ctrl+S"

    def test_disabled_included(self):
        """enabled=False is included."""
        d = MenuItem(name="Paste", enabled=False).to_dict()
        assert d["enabled"] is False

    def test_checked_included(self):
        """checked=True is included."""
        d = MenuItem(name="Word Wrap", checked=True).to_dict()
        assert d["checked"] is True

    def test_submenu_serialized(self):
        """Submenu items are recursively serialized."""
        item = MenuItem(name="File", submenu=[
            MenuItem(name="New", shortcut="Ctrl+N"),
            MenuItem(name="Exit"),
        ])
        d = item.to_dict()
        assert len(d["submenu"]) == 2
        assert d["submenu"][0]["name"] == "New"
        assert d["submenu"][0]["shortcut"] == "Ctrl+N"
        assert d["submenu"][1]["name"] == "Exit"


class TestMenuItemFromDict:
    """Tests for from_dict deserialization."""

    def test_roundtrip(self):
        """to_dict → from_dict roundtrip."""
        original = MenuItem(
            name="Format",
            submenu=[
                MenuItem(name="Bold", shortcut="Ctrl+B", checked=True),
                MenuItem(name="Italic", shortcut="Ctrl+I"),
                MenuItem(name="Strikethrough", enabled=False),
            ],
        )
        restored = MenuItem.from_dict(original.to_dict())
        assert restored.name == "Format"
        assert len(restored.submenu) == 3
        assert restored.submenu[0].checked is True
        assert restored.submenu[2].enabled is False

    def test_from_dict_missing_fields(self):
        """from_dict handles minimal dict."""
        item = MenuItem.from_dict({"name": "Test"})
        assert item.name == "Test"
        assert item.shortcut is None
        assert item.submenu is None
        assert item.enabled is True
        assert item.checked is False

    def test_from_dict_empty_name(self):
        """from_dict handles empty dict (name defaults to '')."""
        item = MenuItem.from_dict({})
        assert item.name == ""


class TestMenuItemFlatten:
    """Tests for the flatten method."""

    def test_flatten_single_item(self):
        """Single item flattens to one entry."""
        item = MenuItem(name="Exit")
        flat = item.flatten()
        assert len(flat) == 1
        assert flat[0]["path"] == "Exit"

    def test_flatten_nested(self):
        """Nested menu flattens with path separators."""
        item = MenuItem(name="File", submenu=[
            MenuItem(name="New", shortcut="Ctrl+N"),
            MenuItem(name="Recent", submenu=[
                MenuItem(name="doc1.txt"),
                MenuItem(name="doc2.txt"),
            ]),
        ])
        flat = item.flatten()
        paths = [f["path"] for f in flat]
        assert "File" in paths
        assert "File > New" in paths
        assert "File > Recent" in paths
        assert "File > Recent > doc1.txt" in paths
        assert "File > Recent > doc2.txt" in paths

    def test_flatten_preserves_shortcut(self):
        """Flatten preserves shortcut info."""
        item = MenuItem(name="Save", shortcut="Ctrl+S")
        flat = item.flatten()
        assert flat[0]["shortcut"] == "Ctrl+S"

    def test_flatten_preserves_enabled(self):
        """Flatten preserves enabled state."""
        item = MenuItem(name="Redo", enabled=False)
        flat = item.flatten()
        assert flat[0]["enabled"] is False

    def test_flatten_preserves_checked(self):
        """Flatten preserves checked state."""
        item = MenuItem(name="Status Bar", checked=True)
        flat = item.flatten()
        assert flat[0]["checked"] is True

    def test_flatten_with_prefix(self):
        """Flatten with a custom prefix."""
        item = MenuItem(name="Bold")
        flat = item.flatten(prefix="Format")
        assert flat[0]["path"] == "Format > Bold"
