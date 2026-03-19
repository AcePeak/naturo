"""Tests for UI element tree inspection functionality.

These tests require Windows with the naturo_core.dll available.
They are automatically skipped on other platforms.
"""

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
    """get_element_tree should return an ElementInfo or None."""
    from naturo.bridge import ElementInfo

    result = core.get_element_tree(hwnd=0, depth=2)
    # In CI, there may be no foreground window, so None is acceptable
    if result is not None:
        assert isinstance(result, ElementInfo)
        assert isinstance(result.role, str)
        assert isinstance(result.name, str)
        assert isinstance(result.children, list)


def test_get_element_tree_depth_clamp(core):
    """Depth values should be clamped to 1-10 range without error."""
    # These should not raise, even with extreme depth values
    core.get_element_tree(hwnd=0, depth=0)   # Will be clamped to 1
    core.get_element_tree(hwnd=0, depth=100)  # Will be clamped to 10


def test_get_element_tree_has_children(core):
    """If tree is returned, root should have structured children."""
    result = core.get_element_tree(hwnd=0, depth=3)
    if result is not None and len(result.children) > 0:
        child = result.children[0]
        assert hasattr(child, "role")
        assert hasattr(child, "name")
        assert hasattr(child, "children")


def test_find_element_not_found(core):
    """Searching for a non-existent element should return None."""
    result = core.find_element(hwnd=0, name="ThisElementDoesNotExist12345")
    assert result is None


def test_find_element_requires_filter(core):
    """find_element with no role and no name should raise NaturoCoreError."""
    from naturo.bridge import NaturoCoreError

    with pytest.raises(NaturoCoreError):
        core.find_element(hwnd=0, role=None, name=None)


def test_backend_get_element_tree(backend):
    """WindowsBackend.get_element_tree should work without error."""
    result = backend.get_element_tree(depth=2)
    # None is acceptable (no foreground window in CI)
    if result is not None:
        from naturo.backends.base import ElementInfo

        assert isinstance(result, ElementInfo)


def test_backend_find_element_not_found(backend):
    """WindowsBackend.find_element for non-existent should return None."""
    result = backend.find_element(selector="SomethingThatDoesNotExist999")
    assert result is None
