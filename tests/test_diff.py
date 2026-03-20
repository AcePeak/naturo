"""Tests for naturo.diff — tree comparison, added/removed/modified detection."""
import pytest
from naturo.diff import diff_trees, TreeDiff, ElementChange, _element_key, _flatten_tree
from naturo.backends.base import ElementInfo


def _el(role="Button", name="Save", value=None, children=None, el_id=""):
    return ElementInfo(
        id=el_id, role=role, name=name, value=value,
        x=0, y=0, width=100, height=30,
        children=children or [], properties={},
    )


class TestElementChange:
    def test_creation(self):
        c = ElementChange(
            type="added", element_id="e1", element_role="Button",
            element_name="Save", path="Window > Button:Save",
        )
        assert c.type == "added"
        assert c.element_name == "Save"

    def test_modified_with_values(self):
        c = ElementChange(
            type="modified", element_id="e1", element_role="Edit",
            element_name="Name", old_value="Alice", new_value="Bob",
            path="Window > Edit:Name",
        )
        assert c.old_value == "Alice"
        assert c.new_value == "Bob"


class TestTreeDiff:
    def test_empty_diff(self):
        d = TreeDiff()
        assert d.total_changes == 0
        assert d.has_changes is False
        assert d.summary == ""

    def test_to_dict(self):
        d = TreeDiff(
            added=[ElementChange("added", "e1", "Button", "Save", path="x")],
            summary="1 added",
        )
        result = d.to_dict()
        assert result["total_changes"] == 1
        assert len(result["added"]) == 1
        assert result["added"][0]["element_name"] == "Save"


class TestDiffTrees:
    def test_identical_trees(self):
        tree = _el("Window", "Root", children=[
            _el("Button", "Save"),
            _el("Edit", "Name", value="Alice"),
        ])
        # Deep copy by recreating
        tree2 = _el("Window", "Root", children=[
            _el("Button", "Save"),
            _el("Edit", "Name", value="Alice"),
        ])
        result = diff_trees(tree, tree2)
        assert result.has_changes is False
        assert result.total_changes == 0
        assert "No changes" in result.summary

    def test_added_element(self):
        before = _el("Window", "Root", children=[
            _el("Button", "Save"),
        ])
        after = _el("Window", "Root", children=[
            _el("Button", "Save"),
            _el("Button", "Cancel"),
        ])
        result = diff_trees(before, after)
        assert len(result.added) == 1
        assert result.added[0].element_name == "Cancel"
        assert result.added[0].type == "added"

    def test_removed_element(self):
        before = _el("Window", "Root", children=[
            _el("Button", "Save"),
            _el("Button", "Cancel"),
        ])
        after = _el("Window", "Root", children=[
            _el("Button", "Save"),
        ])
        result = diff_trees(before, after)
        assert len(result.removed) == 1
        assert result.removed[0].element_name == "Cancel"
        assert result.removed[0].type == "removed"

    def test_modified_value(self):
        before = _el("Window", "Root", children=[
            _el("Edit", "Name", value="Alice"),
        ])
        after = _el("Window", "Root", children=[
            _el("Edit", "Name", value="Bob"),
        ])
        result = diff_trees(before, after)
        assert len(result.modified) == 1
        assert result.modified[0].old_value == "Alice"
        assert result.modified[0].new_value == "Bob"
        assert result.modified[0].type == "modified"

    def test_mixed_changes(self):
        before = _el("Window", "Root", children=[
            _el("Button", "Save"),
            _el("Edit", "Name", value="Old"),
            _el("Button", "Delete"),
        ])
        after = _el("Window", "Root", children=[
            _el("Button", "Save"),
            _el("Edit", "Name", value="New"),
            _el("Button", "Add"),
        ])
        result = diff_trees(before, after)
        assert len(result.added) >= 1  # Add button
        assert len(result.removed) >= 1  # Delete button
        assert len(result.modified) >= 1  # Name edit
        assert result.has_changes is True

    def test_summary_format(self):
        before = _el("Window", "Root", children=[_el("Button", "A")])
        after = _el("Window", "Root", children=[_el("Button", "B")])
        result = diff_trees(before, after)
        assert "added" in result.summary or "removed" in result.summary

    def test_empty_trees(self):
        before = _el("Window", "Root")
        after = _el("Window", "Root")
        result = diff_trees(before, after)
        assert result.has_changes is False

    def test_nested_changes(self):
        before = _el("Window", "Root", children=[
            _el("Panel", "Main", children=[
                _el("Button", "Save"),
            ]),
        ])
        after = _el("Window", "Root", children=[
            _el("Panel", "Main", children=[
                _el("Button", "Save"),
                _el("Button", "Cancel"),
            ]),
        ])
        result = diff_trees(before, after)
        assert len(result.added) == 1
        assert result.added[0].element_name == "Cancel"


class TestHelpers:
    def test_element_key_with_role_name(self):
        el = _el("Button", "Save")
        assert _element_key(el) == "Button:Save"

    def test_element_key_fallback_to_id(self):
        el = _el("", "", el_id="e42")
        assert _element_key(el) == "id:e42"

    def test_flatten_tree(self):
        tree = _el("Window", "Root", children=[
            _el("Button", "Save"),
            _el("Button", "Cancel"),
        ])
        flat = _flatten_tree(tree)
        assert len(flat) >= 3  # Root + 2 buttons
