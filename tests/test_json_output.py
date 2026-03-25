"""Tests for JSON output format consistency (#295).

Verifies that:
- ``automation_id`` is exposed separately from the naturo ref
- ``parent_ref`` always uses naturo refs (eN), never raw AutomationIds
- ``parent_id`` is kept as backward-compatible alias of ``parent_ref``
- Tree-assigned "eN" ids are filtered from ``automation_id``
"""
from __future__ import annotations

import json
import platform
import re
import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

_win_only = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="see command requires Windows backend",
)


@pytest.fixture
def runner():
    return CliRunner()


def _make_tree():
    """Build a mock element tree with real AutomationIds and one empty-id element."""
    root = MagicMock()
    root.id = "RootWindow"
    root.role = "Window"
    root.name = "Calculator"
    root.value = ""
    root.x, root.y, root.width, root.height = 0, 0, 400, 600
    root.properties = {}
    root.is_actionable = False

    child1 = MagicMock()
    child1.id = "NavView"
    child1.role = "Pane"
    child1.name = "Navigation"
    child1.value = ""
    child1.x, child1.y, child1.width, child1.height = 0, 0, 200, 600
    child1.properties = {}
    child1.children = []
    child1.is_actionable = False

    child2 = MagicMock()
    child2.id = "TogglePaneButton"
    child2.role = "Button"
    child2.name = "Toggle Pane"
    child2.value = ""
    child2.x, child2.y, child2.width, child2.height = 10, 10, 40, 40
    child2.properties = {}
    child2.children = []
    child2.is_actionable = True

    # Element with no AutomationId
    child3 = MagicMock()
    child3.id = ""
    child3.role = "Text"
    child3.name = "Status"
    child3.value = "Ready"
    child3.x, child3.y, child3.width, child3.height = 0, 560, 400, 40
    child3.properties = {}
    child3.children = []
    child3.is_actionable = False

    root.children = [child1, child2, child3]
    return root


@_win_only
class TestJSONOutputFormat:
    """Validate ``see --json`` output fields for #295."""

    def test_automation_id_exposed(self, runner):
        """Elements with real AutomationIds should expose them."""
        tree = _make_tree()
        backend = MagicMock()
        backend.get_element_tree.return_value = tree
        backend.find_window.return_value = 12345
        backend.get_dpi_scale.return_value = 1.0
        backend.list_monitors.return_value = []

        from naturo.cli.core import see

        with patch("naturo.cli.core._get_backend", return_value=backend):
            with patch("naturo.cli.core.platform") as mock_platform:
                mock_platform.system.return_value = "Windows"
                result = runner.invoke(see, ["--json", "--no-snapshot"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)

        # Root: has AutomationId "RootWindow"
        assert data["id"] == "e1"
        assert data["automation_id"] == "RootWindow"

        # Children
        assert len(data["children"]) == 3
        assert data["children"][0]["automation_id"] == "NavView"
        assert data["children"][1]["automation_id"] == "TogglePaneButton"

    def test_empty_id_filtered(self, runner):
        """Elements with no AutomationId should have empty automation_id."""
        tree = _make_tree()
        backend = MagicMock()
        backend.get_element_tree.return_value = tree
        backend.find_window.return_value = 12345
        backend.get_dpi_scale.return_value = 1.0
        backend.list_monitors.return_value = []

        from naturo.cli.core import see

        with patch("naturo.cli.core._get_backend", return_value=backend):
            with patch("naturo.cli.core.platform") as mock_platform:
                mock_platform.system.return_value = "Windows"
                result = runner.invoke(see, ["--json", "--no-snapshot"])

        data = json.loads(result.output)
        txt = data["children"][2]
        assert txt["automation_id"] == ""

    def test_tree_assigned_id_filtered(self, runner):
        """Elements with tree-assigned eN ids should have empty automation_id."""
        tree = _make_tree()
        # Simulate populate_hierarchy assigning "e5" to the empty-id element
        tree.children[2].id = "e5"

        backend = MagicMock()
        backend.get_element_tree.return_value = tree
        backend.find_window.return_value = 12345
        backend.get_dpi_scale.return_value = 1.0
        backend.list_monitors.return_value = []

        from naturo.cli.core import see

        with patch("naturo.cli.core._get_backend", return_value=backend):
            with patch("naturo.cli.core.platform") as mock_platform:
                mock_platform.system.return_value = "Windows"
                result = runner.invoke(see, ["--json", "--no-snapshot"])

        data = json.loads(result.output)
        txt = data["children"][2]
        assert txt["automation_id"] == ""

    def test_parent_ref_uses_naturo_refs(self, runner):
        """parent_ref should always be a naturo ref (eN), never an AutomationId."""
        tree = _make_tree()
        backend = MagicMock()
        backend.get_element_tree.return_value = tree
        backend.find_window.return_value = 12345
        backend.get_dpi_scale.return_value = 1.0
        backend.list_monitors.return_value = []

        from naturo.cli.core import see

        with patch("naturo.cli.core._get_backend", return_value=backend):
            with patch("naturo.cli.core.platform") as mock_platform:
                mock_platform.system.return_value = "Windows"
                result = runner.invoke(see, ["--json", "--no-snapshot"])

        data = json.loads(result.output)

        # Root has no parent
        assert "parent_ref" not in data

        # All children have parent_ref == "e1"
        for child in data["children"]:
            assert child["parent_ref"] == "e1"
            # Backward compat
            assert child["parent_id"] == "e1"

    def test_no_raw_automation_id_in_parent(self, runner):
        """Recursively verify no raw AutomationId leaks into parent_ref."""
        tree = _make_tree()
        backend = MagicMock()
        backend.get_element_tree.return_value = tree
        backend.find_window.return_value = 12345
        backend.get_dpi_scale.return_value = 1.0
        backend.list_monitors.return_value = []

        from naturo.cli.core import see

        with patch("naturo.cli.core._get_backend", return_value=backend):
            with patch("naturo.cli.core.platform") as mock_platform:
                mock_platform.system.return_value = "Windows"
                result = runner.invoke(see, ["--json", "--no-snapshot"])

        data = json.loads(result.output)

        def check(node):
            parent = node.get("parent_ref")
            if parent is not None:
                assert re.fullmatch(r"e\d+", parent), (
                    f"parent_ref '{parent}' is not a naturo ref (eN)"
                )
            for c in node.get("children", []):
                check(c)

        check(data)
