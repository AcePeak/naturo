"""Tests for stable element reference assignment (#456)."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pytest

from naturo.refs import (
    _build_identity_path,
    _get_real_automation_id,
    _hash_to_ref_number,
    assign_stable_refs,
)


# ── Minimal stubs ──────────────────────────────────────────────────────────


@dataclass
class FakeElement:
    """Minimal element stub matching the interface expected by assign_stable_refs."""

    id: str = ""
    role: str = ""
    name: str = ""
    value: Optional[str] = None
    x: int = 0
    y: int = 0
    width: int = 100
    height: int = 30
    children: list = field(default_factory=list)
    is_actionable: bool = False
    properties: dict = field(default_factory=dict)


@dataclass
class FakeUIElement:
    """Minimal UIElement stub for testing."""

    id: str = ""
    element_id: str = ""
    role: str = ""
    title: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None
    identifier: Optional[str] = None
    frame: Tuple[int, int, int, int] = (0, 0, 0, 0)
    is_actionable: bool = False
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    keyboard_shortcut: Optional[str] = None


# ── Unit tests for helpers ──────────────────────────────────────────────────


class TestGetRealAutomationId:

    def test_real_id(self):
        el = FakeElement(id="num7Button")
        assert _get_real_automation_id(el) == "num7Button"

    def test_tree_assigned_id_filtered(self):
        el = FakeElement(id="e42")
        assert _get_real_automation_id(el) is None

    def test_empty_id(self):
        el = FakeElement(id="")
        assert _get_real_automation_id(el) is None

    def test_none_id(self):
        el = FakeElement()
        el.id = None
        assert _get_real_automation_id(el) is None


class TestBuildIdentityPath:

    def test_with_automation_id(self):
        el = FakeElement(id="num7Button", role="Button", name="7")
        path = _build_identity_path(el, "/root", sibling_index=0)
        assert path == "/root/Button:num7Button"

    def test_without_automation_id(self):
        el = FakeElement(id="", role="Text", name="Status")
        path = _build_identity_path(el, "/root", sibling_index=2)
        assert path == "/root/Text:Status[2]"

    def test_tree_assigned_id_uses_fallback(self):
        el = FakeElement(id="e5", role="Button", name="OK")
        path = _build_identity_path(el, "/parent", sibling_index=0)
        assert path == "/parent/Button:OK[0]"


class TestHashToRefNumber:

    def test_returns_in_range(self):
        for path in ["/a/b/c", "/x/y/z", "", "/Button:num7Button"]:
            n = _hash_to_ref_number(path)
            assert 1 <= n <= 9999

    def test_deterministic(self):
        path = "/Window:Calculator/Button:num7Button"
        assert _hash_to_ref_number(path) == _hash_to_ref_number(path)

    def test_different_paths_different_numbers(self):
        n1 = _hash_to_ref_number("/Button:num7Button")
        n2 = _hash_to_ref_number("/Button:num8Button")
        assert n1 != n2


# ── Integration tests for assign_stable_refs ────────────────────────────────


def _make_calculator_tree(display_text="0"):
    """Build a simplified Calculator element tree."""
    display = FakeElement(
        id="CalculatorResults", role="Text", name=display_text,
        x=10, y=10, width=300, height=50,
    )
    btn_7 = FakeElement(
        id="num7Button", role="Button", name="七",
        x=10, y=100, width=70, height=50, is_actionable=True,
    )
    btn_plus = FakeElement(
        id="plusButton", role="Button", name="加",
        x=90, y=100, width=70, height=50, is_actionable=True,
    )
    btn_3 = FakeElement(
        id="num3Button", role="Button", name="三",
        x=170, y=100, width=70, height=50, is_actionable=True,
    )
    btn_eq = FakeElement(
        id="equalButton", role="Button", name="等于",
        x=250, y=100, width=70, height=50, is_actionable=True,
    )
    btn_clear = FakeElement(
        id="clearButton", role="Button", name="Clear",
        x=10, y=160, width=70, height=50, is_actionable=True,
    )
    root = FakeElement(
        id="Calculator", role="Window", name="Calculator",
        x=0, y=0, width=340, height=220,
        children=[display, btn_7, btn_plus, btn_3, btn_eq, btn_clear],
    )
    return root


class TestStableRefsAcrossSnapshots:
    """Core test: same element gets same eN across different snapshots."""

    def test_same_tree_same_refs(self):
        """Identical trees produce identical ref assignments."""
        tree1 = _make_calculator_tree("0")
        tree2 = _make_calculator_tree("0")
        ui_map1, _ = assign_stable_refs(tree1, FakeUIElement)
        ui_map2, _ = assign_stable_refs(tree2, FakeUIElement)

        refs1 = {el.identifier or el.title: ref for ref, el in ui_map1.items()}
        refs2 = {el.identifier or el.title: ref for ref, el in ui_map2.items()}
        assert refs1 == refs2

    def test_display_change_preserves_button_refs(self):
        """When display text changes (after Clear), button refs stay stable.

        This is the exact scenario from issue #456: pressing Clear changes
        the display element's name/value, but buttons should keep their eN.
        """
        tree_before = _make_calculator_tree("7 + 3 = 10")
        tree_after = _make_calculator_tree("0")

        ui_before, _ = assign_stable_refs(tree_before, FakeUIElement)
        ui_after, _ = assign_stable_refs(tree_after, FakeUIElement)

        # Collect button refs by AutomationId
        def button_refs(ui_map):
            return {
                el.identifier: ref
                for ref, el in ui_map.items()
                if el.identifier and el.identifier != "CalculatorResults"
            }

        before_buttons = button_refs(ui_before)
        after_buttons = button_refs(ui_after)

        # Every button must have the same eN in both snapshots
        assert before_buttons == after_buttons

    def test_element_added_preserves_existing_refs(self):
        """Adding a new child element does not shift existing elements' refs."""
        tree1 = _make_calculator_tree("0")
        ui_map1, _ = assign_stable_refs(tree1, FakeUIElement)

        # Add a history panel element
        tree2 = _make_calculator_tree("0")
        history = FakeElement(
            id="historyPanel", role="Group", name="History",
            x=10, y=220, width=300, height=100,
        )
        tree2.children.append(history)
        ui_map2, _ = assign_stable_refs(tree2, FakeUIElement)

        # All original elements should keep their refs
        refs1 = {el.identifier or el.title: ref for ref, el in ui_map1.items()}
        refs2 = {el.identifier or el.title: ref for ref, el in ui_map2.items()}
        for key in refs1:
            assert refs1[key] == refs2[key], f"Ref shifted for {key}: {refs1[key]} → {refs2[key]}"

    def test_element_removed_preserves_remaining_refs(self):
        """Removing an element does not shift remaining elements' refs."""
        tree1 = _make_calculator_tree("0")
        ui_map1, _ = assign_stable_refs(tree1, FakeUIElement)

        # Remove the Clear button
        tree2 = _make_calculator_tree("0")
        tree2.children = [c for c in tree2.children if c.id != "clearButton"]
        ui_map2, _ = assign_stable_refs(tree2, FakeUIElement)

        # Remaining elements should keep their refs
        refs1 = {el.identifier or el.title: ref for ref, el in ui_map1.items()}
        refs2 = {el.identifier or el.title: ref for ref, el in ui_map2.items()}
        for key in refs2:
            assert refs1[key] == refs2[key], f"Ref shifted for {key}: {refs1[key]} → {refs2[key]}"


class TestAssignStableRefsBasics:

    def test_all_elements_get_unique_refs(self):
        tree = _make_calculator_tree("0")
        ui_map, _ = assign_stable_refs(tree, FakeUIElement)
        refs = list(ui_map.keys())
        assert len(refs) == len(set(refs)), "Duplicate refs found"

    def test_ref_format(self):
        tree = _make_calculator_tree("0")
        ui_map, _ = assign_stable_refs(tree, FakeUIElement)
        import re
        for ref in ui_map:
            assert re.fullmatch(r"e\d+", ref), f"Bad ref format: {ref}"

    def test_ref_map_matches_ui_map_keys(self):
        tree = _make_calculator_tree("0")
        ui_map, ref_map = assign_stable_refs(tree, FakeUIElement)
        assert set(ui_map.keys()) == set(ref_map.keys())

    def test_parent_child_refs_consistent(self):
        tree = _make_calculator_tree("0")
        ui_map, _ = assign_stable_refs(tree, FakeUIElement)

        for ref, el in ui_map.items():
            for child_ref in el.children:
                assert child_ref in ui_map, f"Child ref {child_ref} not in ui_map"
                assert ui_map[child_ref].parent_id == ref

    def test_root_has_no_parent(self):
        tree = _make_calculator_tree("0")
        ui_map, _ = assign_stable_refs(tree, FakeUIElement)
        root_els = [el for el in ui_map.values() if el.parent_id is None]
        assert len(root_els) == 1
        assert root_els[0].role == "Window"

    def test_element_obj_to_ref_mapping(self):
        tree = _make_calculator_tree("0")
        obj_map: dict[int, str] = {}
        ui_map, _ = assign_stable_refs(tree, FakeUIElement, element_obj_to_ref=obj_map)

        # Every element in the tree should have an entry
        assert id(tree) in obj_map
        for child in tree.children:
            assert id(child) in obj_map

        # Refs should match ui_map
        for obj_id, ref in obj_map.items():
            assert ref in ui_map

    def test_identifier_preserved(self):
        tree = _make_calculator_tree("0")
        ui_map, _ = assign_stable_refs(tree, FakeUIElement)

        identifiers = {el.identifier for el in ui_map.values() if el.identifier}
        assert "num7Button" in identifiers
        assert "clearButton" in identifiers

    def test_siblings_same_role_name_get_different_refs(self):
        """Two unnamed Text elements under the same parent get different refs."""
        text1 = FakeElement(role="Text", name="", x=0, y=0, width=50, height=20)
        text2 = FakeElement(role="Text", name="", x=60, y=0, width=50, height=20)
        root = FakeElement(
            id="root", role="Window", name="App",
            children=[text1, text2],
        )
        ui_map, _ = assign_stable_refs(root, FakeUIElement)
        refs = list(ui_map.keys())
        assert len(refs) == 3  # root + 2 texts
        assert len(set(refs)) == 3  # all unique
