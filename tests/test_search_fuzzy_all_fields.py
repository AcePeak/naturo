"""Tests for fuzzy all-fields search (Issue #281)."""
import pytest
from naturo.search import search_elements
from naturo.bridge import ElementInfo


class TestFuzzyAllFieldsSearch:
    """Verify that simple queries match role, name, and value."""

    def test_simple_query_matches_role(self):
        """Simple query should match elements by role (e.g., 'Button' finds Buttons)."""
        tree = ElementInfo(
            id="root",
            role="Window",
            name="Main",
            value=None,
            x=0, y=0, width=800, height=600,
            children=[
                ElementInfo(
                    id="b1",
                    role="Button",
                    name="OK",
                    value=None,
                    x=10, y=10, width=80, height=30,
                ),
                ElementInfo(
                    id="e1",
                    role="Edit",
                    name="Input",
                    value="",
                    x=10, y=50, width=200, height=25,
                ),
            ],
        )

        results = search_elements(tree, "Button")
        assert len(results) == 1
        assert results[0].element.id == "b1"

    def test_simple_query_matches_name(self):
        """Simple query should match elements by name."""
        tree = ElementInfo(
            id="root",
            role="Window",
            name="Main",
            value=None,
            x=0, y=0, width=800, height=600,
            children=[
                ElementInfo(
                    id="b1",
                    role="Button",
                    name="Save",
                    value=None,
                    x=10, y=10, width=80, height=30,
                ),
                ElementInfo(
                    id="b2",
                    role="Button",
                    name="Cancel",
                    value=None,
                    x=100, y=10, width=80, height=30,
                ),
            ],
        )

        results = search_elements(tree, "Save")
        assert len(results) == 1
        assert results[0].element.id == "b1"

    def test_simple_query_matches_value(self):
        """Simple query should match elements by value."""
        tree = ElementInfo(
            id="root",
            role="Window",
            name="Main",
            value=None,
            x=0, y=0, width=800, height=600,
            children=[
                ElementInfo(
                    id="e1",
                    role="Edit",
                    name="Input",
                    value="Hello World",
                    x=10, y=10, width=200, height=25,
                ),
                ElementInfo(
                    id="e2",
                    role="Edit",
                    name="Other",
                    value="Foo Bar",
                    x=10, y=40, width=200, height=25,
                ),
            ],
        )

        results = search_elements(tree, "Hello")
        assert len(results) == 1
        assert results[0].element.id == "e1"

    def test_simple_query_matches_chinese_name(self):
        """Simple query with Chinese characters should match names."""
        tree = ElementInfo(
            id="root",
            role="Window",
            name="主窗口",
            value=None,
            x=0, y=0, width=800, height=600,
            children=[
                ElementInfo(
                    id="m1",
                    role="MenuItem",
                    name="编辑",
                    value=None,
                    x=10, y=10, width=60, height=20,
                ),
                ElementInfo(
                    id="m2",
                    role="MenuItem",
                    name="文件",
                    value=None,
                    x=80, y=10, width=60, height=20,
                ),
            ],
        )

        results = search_elements(tree, "编辑")
        assert len(results) == 1
        assert results[0].element.id == "m1"

    def test_role_prefix_overrides_fuzzy_search(self):
        """role: prefix should only match role, not name/value."""
        tree = ElementInfo(
            id="root",
            role="Window",
            name="Main",
            value=None,
            x=0, y=0, width=800, height=600,
            children=[
                ElementInfo(
                    id="b1",
                    role="Button",
                    name="Edit",  # "Edit" in name
                    value=None,
                    x=10, y=10, width=80, height=30,
                ),
                ElementInfo(
                    id="e1",
                    role="Edit",  # "Edit" is role
                    name="Input",
                    value="",
                    x=10, y=50, width=200, height=25,
                ),
            ],
        )

        # Simple "Edit" should find both (fuzzy search)
        results = search_elements(tree, "Edit")
        assert len(results) == 2

        # "role:Edit" should only find the Edit role element
        results = search_elements(tree, "role:Edit")
        assert len(results) == 1
        assert results[0].element.id == "e1"
