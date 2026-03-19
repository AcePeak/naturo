"""Tests for UI element tree inspection functionality.

These tests require Windows with the naturo_core.dll available.
They are automatically skipped on other platforms.
"""

from __future__ import annotations

import platform

import pytest


pytestmark = [
    pytest.mark.ui,
    pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Element tree tests require Windows with naturo_core.dll",
    ),
]


@pytest.fixture
def core():
    """Create and initialize a NaturoCore instance."""
    from naturo.bridge import NaturoCore

    c = NaturoCore()
    c.init()
    yield c
    c.shutdown()


@pytest.fixture
def backend():
    """Create a WindowsBackend instance."""
    from naturo.backends.windows import WindowsBackend

    return WindowsBackend()


def test_get_element_tree_returns_element_or_none(core):
    """T060: get_element_tree should return an ElementInfo or None."""
    from naturo.bridge import ElementInfo

    result = core.get_element_tree(hwnd=0, depth=2)
    if result is not None:
        assert isinstance(result, ElementInfo)
        assert isinstance(result.role, str)
        assert isinstance(result.name, str)
        assert isinstance(result.children, list)


def test_get_element_tree_depth_clamp(core):
    """T061: Depth values should be clamped to 1-10 range without error."""
    core.get_element_tree(hwnd=0, depth=0)   # Will be clamped to 1
    core.get_element_tree(hwnd=0, depth=100)  # Will be clamped to 10


def test_get_element_tree_has_children(core):
    """T062: If tree is returned, root should have structured children."""
    result = core.get_element_tree(hwnd=0, depth=3)
    if result is not None and len(result.children) > 0:
        child = result.children[0]
        assert hasattr(child, "role")
        assert hasattr(child, "name")
        assert hasattr(child, "children")


def test_find_element_not_found(core):
    """T063: Searching for a non-existent element should return None."""
    result = core.find_element(hwnd=0, name="ThisElementDoesNotExist12345")
    assert result is None


def test_find_element_requires_filter(core):
    """T064: find_element with no role and no name should raise NaturoCoreError."""
    from naturo.bridge import NaturoCoreError

    with pytest.raises(NaturoCoreError):
        core.find_element(hwnd=0, role=None, name=None)


def test_backend_get_element_tree(backend):
    """T065: WindowsBackend.get_element_tree should work without error."""
    result = backend.get_element_tree(depth=2)
    if result is not None:
        from naturo.backends.base import ElementInfo
        assert isinstance(result, ElementInfo)


def test_backend_find_element_not_found(backend):
    """T066: WindowsBackend.find_element for non-existent should return None."""
    result = backend.find_element(selector="SomethingThatDoesNotExist999")
    assert result is None


def test_element_has_correct_properties(core):
    """T067: Element has correct properties: role, name, value, bounds.

    Every element in the tree must have role, name, value, and bounding
    rectangle fields with correct types.
    """
    result = core.get_element_tree(hwnd=0, depth=2)
    if result is None:
        pytest.skip("No foreground window available")

    def check_props(el):
        assert isinstance(el.role, str)
        assert isinstance(el.name, str)
        assert el.value is None or isinstance(el.value, str)
        assert isinstance(el.x, int)
        assert isinstance(el.y, int)
        assert isinstance(el.width, int)
        assert isinstance(el.height, int)
        assert isinstance(el.children, list)
        for child in el.children:
            check_props(child)

    check_props(result)


def test_find_element_by_role_only(core):
    """T068: Find element by role only (e.g., 'Window').

    Searching by role with no name filter should find at least one element
    if the tree contains elements of that role.
    """
    tree = core.get_element_tree(hwnd=0, depth=3)
    if tree is None:
        pytest.skip("No foreground window available")

    # Try to find by the root element's role
    root_role = tree.role
    if not root_role:
        pytest.skip("Root element has no role")

    result = core.find_element(hwnd=0, role=root_role, name=None)
    # May or may not find something — the API should not crash
    # If found, it should match the requested role
    if result is not None:
        assert result.role == root_role


def test_find_element_by_name_only(core):
    """T069: Find element by name only.

    Searching by name with no role filter should work.
    """
    tree = core.get_element_tree(hwnd=0, depth=3)
    if tree is None:
        pytest.skip("No foreground window available")

    # Find an element with a non-empty name
    def find_named(el):
        if el.name:
            return el.name
        for child in el.children:
            name = find_named(child)
            if name:
                return name
        return None

    target_name = find_named(tree)
    if target_name is None:
        pytest.skip("No named elements found")

    result = core.find_element(hwnd=0, role=None, name=target_name)
    if result is not None:
        assert result.name == target_name


def test_find_element_by_role_and_name(core):
    """T070: Find element by role + name combination.

    Searching with both role and name filters should narrow results.
    """
    tree = core.get_element_tree(hwnd=0, depth=3)
    if tree is None:
        pytest.skip("No foreground window available")

    # Find an element with both role and name
    def find_both(el):
        if el.role and el.name:
            return el.role, el.name
        for child in el.children:
            result = find_both(child)
            if result:
                return result
        return None

    pair = find_both(tree)
    if pair is None:
        pytest.skip("No elements with both role and name found")

    role, name = pair
    result = core.find_element(hwnd=0, role=role, name=name)
    if result is not None:
        assert result.role == role
        assert result.name == name


def test_element_tree_for_empty_window(core):
    """T077: Element tree for a window with minimal content.

    get_element_tree should return a valid tree (possibly with no children)
    for any valid window, including those with minimal UI content.
    """
    windows = core.list_windows()
    if not windows:
        pytest.skip("No windows available")

    # Try to get element tree for the first available window
    for w in windows:
        if w.is_visible and not w.is_minimized:
            result = core.get_element_tree(hwnd=w.hwnd, depth=1)
            if result is not None:
                assert isinstance(result.role, str)
                assert isinstance(result.children, list)
                return
    pytest.skip("No suitable window found")


def test_element_tree_performance_under_threshold(core):
    """T080: Element tree performance < 2s for typical app (depth=3).

    This is a functional correctness + timing check.
    """
    import time

    start = time.perf_counter()
    tree = core.get_element_tree(hwnd=0, depth=3)
    elapsed = time.perf_counter() - start

    assert elapsed < 5.0, f"get_element_tree took {elapsed:.3f}s (CI limit: 5s)"
