"""Tests for UI hierarchy filling and keyboard shortcut discovery."""

import pytest

from naturo.bridge import ElementInfo, populate_hierarchy


@pytest.fixture
def tree_no_ids():
    """Element tree with empty IDs (simulates DLL output)."""
    child1 = ElementInfo(
        id="", role="Button", name="OK", value=None,
        x=100, y=200, width=80, height=30,
    )
    child2 = ElementInfo(
        id="", role="Button", name="Cancel", value=None,
        x=200, y=200, width=80, height=30,
    )
    grandchild = ElementInfo(
        id="", role="Text", name="Label", value=None,
        x=50, y=50, width=100, height=20,
    )
    child1.children = [grandchild]
    root = ElementInfo(
        id="", role="Window", name="Dialog", value=None,
        x=0, y=0, width=400, height=300,
        children=[child1, child2],
    )
    return root


@pytest.fixture
def tree_with_ids():
    """Element tree with existing IDs."""
    child1 = ElementInfo(
        id="btn1", role="Button", name="OK", value=None,
        x=100, y=200, width=80, height=30,
    )
    child2 = ElementInfo(
        id="btn2", role="Button", name="Cancel", value=None,
        x=200, y=200, width=80, height=30,
    )
    root = ElementInfo(
        id="root", role="Window", name="Dialog", value=None,
        x=0, y=0, width=400, height=300,
        children=[child1, child2],
    )
    return root


class TestPopulateHierarchy:
    """Tests for populate_hierarchy function."""

    def test_fills_parent_id(self, tree_with_ids):
        """Parent IDs are set correctly."""
        populate_hierarchy(tree_with_ids)
        assert tree_with_ids.parent_id is None
        assert tree_with_ids.children[0].parent_id == "root"
        assert tree_with_ids.children[1].parent_id == "root"

    def test_assigns_sequential_ids(self, tree_no_ids):
        """Empty IDs are filled with sequential e1, e2, etc. (1-based)."""
        populate_hierarchy(tree_no_ids)
        assert tree_no_ids.id == "e1"
        assert tree_no_ids.children[0].id == "e2"
        # grandchild of children[0]
        assert tree_no_ids.children[0].children[0].id == "e3"
        assert tree_no_ids.children[1].id == "e4"

    def test_fills_parent_id_with_generated_ids(self, tree_no_ids):
        """Parent IDs reference the generated sequential IDs."""
        populate_hierarchy(tree_no_ids)
        root = tree_no_ids
        assert root.parent_id is None
        assert root.children[0].parent_id == "e1"
        assert root.children[0].children[0].parent_id == "e2"
        assert root.children[1].parent_id == "e1"

    def test_preserves_existing_ids(self, tree_with_ids):
        """Existing non-empty IDs are preserved."""
        populate_hierarchy(tree_with_ids)
        assert tree_with_ids.id == "root"
        assert tree_with_ids.children[0].id == "btn1"
        assert tree_with_ids.children[1].id == "btn2"

    def test_empty_tree(self):
        """Single node tree works."""
        root = ElementInfo(
            id="", role="Window", name="Single", value=None,
            x=0, y=0, width=100, height=100,
        )
        populate_hierarchy(root)
        assert root.id == "e1"
        assert root.parent_id is None


class TestElementInfoFields:
    """Tests for extended ElementInfo fields."""

    def test_parent_id_default(self):
        """parent_id defaults to None."""
        el = ElementInfo(
            id="x", role="Button", name="Test", value=None,
            x=0, y=0, width=10, height=10,
        )
        assert el.parent_id is None

    def test_keyboard_shortcut_default(self):
        """keyboard_shortcut defaults to None."""
        el = ElementInfo(
            id="x", role="Button", name="Test", value=None,
            x=0, y=0, width=10, height=10,
        )
        assert el.keyboard_shortcut is None

    def test_keyboard_shortcut_set(self):
        """keyboard_shortcut can be set."""
        el = ElementInfo(
            id="x", role="Button", name="Save", value=None,
            x=0, y=0, width=10, height=10,
            keyboard_shortcut="Ctrl+S",
        )
        assert el.keyboard_shortcut == "Ctrl+S"

    def test_parent_id_set(self):
        """parent_id can be set."""
        el = ElementInfo(
            id="child", role="Button", name="OK", value=None,
            x=0, y=0, width=10, height=10,
            parent_id="parent",
        )
        assert el.parent_id == "parent"
