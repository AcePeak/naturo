"""Tests for naturo.search — element search and query."""

import pytest

from naturo.bridge import ElementInfo
from naturo.search import search_elements, SearchResult, _parse_query


@pytest.fixture
def sample_tree():
    """Build a sample element tree for search tests."""
    save_btn = ElementInfo(
        id="e3", role="Button", name="Save", value=None,
        x=100, y=200, width=80, height=30,
    )
    cancel_btn = ElementInfo(
        id="e4", role="Button", name="Cancel", value=None,
        x=200, y=200, width=80, height=30,
    )
    save_as_btn = ElementInfo(
        id="e5", role="Button", name="Save As...", value=None,
        x=100, y=250, width=80, height=30,
    )
    name_edit = ElementInfo(
        id="e2", role="Edit", name="File Name", value="doc.txt",
        x=100, y=100, width=200, height=25,
    )
    toolbar = ElementInfo(
        id="e1", role="ToolBar", name="Main Toolbar", value=None,
        x=0, y=0, width=400, height=40,
        children=[save_btn, cancel_btn, save_as_btn],
    )
    root = ElementInfo(
        id="e0", role="Window", name="Notepad", value=None,
        x=0, y=0, width=800, height=600,
        children=[toolbar, name_edit],
    )
    # Fill parent_id
    from naturo.bridge import populate_hierarchy
    populate_hierarchy(root)
    return root


class TestParseQuery:
    """Tests for query parsing."""

    def test_simple_text(self):
        role, name = _parse_query("Save")
        assert role is None
        assert name == "Save"

    def test_role_name_kv(self):
        role, name = _parse_query("role:Button name:Save")
        assert role == "Button"
        assert name == "Save"

    def test_role_only(self):
        role, name = _parse_query("role:Edit")
        assert role == "Edit"
        assert name is None

    def test_shorthand(self):
        role, name = _parse_query("Button:Save")
        assert role == "Button"
        assert name == "Save"

    def test_wildcard_shorthand(self):
        role, name = _parse_query("Button:*Save*")
        assert role == "Button"
        assert name == "*Save*"

    def test_star(self):
        role, name = _parse_query("*")
        assert role is None
        assert name is None

    def test_empty(self):
        role, name = _parse_query("")
        assert role is None
        assert name is None


class TestSearchElements:
    """Tests for search_elements function."""

    def test_fuzzy_name_match(self, sample_tree):
        """Simple substring match finds both Save and Save As."""
        results = search_elements(sample_tree, "Save")
        names = [r.element.name for r in results]
        assert "Save" in names
        assert "Save As..." in names
        assert len(results) == 2

    def test_exact_name(self, sample_tree):
        """Can search for an exact name."""
        results = search_elements(sample_tree, "Cancel")
        assert len(results) == 1
        assert results[0].element.name == "Cancel"

    def test_role_filter(self, sample_tree):
        """role:Button only returns buttons."""
        results = search_elements(sample_tree, "role:Button")
        assert all(r.element.role == "Button" for r in results)
        assert len(results) == 3

    def test_combined_query(self, sample_tree):
        """Combined role + name filter."""
        results = search_elements(sample_tree, "role:Button name:Save")
        assert len(results) == 2  # Save and Save As...
        assert all(r.element.role == "Button" for r in results)

    def test_shorthand_query(self, sample_tree):
        """Button:Save shorthand."""
        results = search_elements(sample_tree, "Button:Save")
        assert len(results) == 2
        assert all(r.element.role == "Button" for r in results)

    def test_glob_pattern(self, sample_tree):
        """Wildcard name search."""
        results = search_elements(sample_tree, "Button:*As*")
        assert len(results) == 1
        assert results[0].element.name == "Save As..."

    def test_actionable_only(self, sample_tree):
        """Actionable filter limits to clickable elements."""
        results = search_elements(sample_tree, "*", actionable_only=True)
        roles = {r.element.role for r in results}
        assert "Window" not in roles
        assert "ToolBar" not in roles
        assert "Button" in roles

    def test_role_filter_param(self, sample_tree):
        """role_filter parameter overrides query role."""
        results = search_elements(sample_tree, "Save", role_filter="Edit")
        # No Edit elements named "Save"
        assert len(results) == 0

    def test_breadcrumb(self, sample_tree):
        """Search results include breadcrumb path."""
        results = search_elements(sample_tree, "Cancel")
        assert len(results) == 1
        assert "Window:Notepad" in results[0].breadcrumb_str
        assert "ToolBar:Main Toolbar" in results[0].breadcrumb_str
        assert "Button:Cancel" in results[0].breadcrumb_str

    def test_max_results(self, sample_tree):
        """max_results limits output."""
        results = search_elements(sample_tree, "*", max_results=2)
        assert len(results) <= 2

    def test_case_insensitive(self, sample_tree):
        """Name search is case-insensitive."""
        results = search_elements(sample_tree, "save")
        names = [r.element.name for r in results]
        assert "Save" in names

    def test_no_match(self, sample_tree):
        """Returns empty list when nothing matches."""
        results = search_elements(sample_tree, "Nonexistent")
        assert len(results) == 0

    def test_edit_role_search(self, sample_tree):
        """Can find Edit elements."""
        results = search_elements(sample_tree, "Edit:*")
        assert len(results) == 1
        assert results[0].element.role == "Edit"
