"""Tests for naturo.cache — TTL, invalidation, stale detection."""
import time
import pytest
from naturo.cache import ElementCache
from naturo.backends.base import ElementInfo


def _make_tree(name="Root"):
    return ElementInfo(
        id="root", role="Window", name=name, value=None,
        x=0, y=0, width=800, height=600, children=[
            ElementInfo(
                id="btn1", role="Button", name="Save", value=None,
                x=10, y=10, width=80, height=30, children=[], properties={},
            ),
        ], properties={},
    )


class TestElementCache:
    def test_get_miss(self):
        cache = ElementCache(ttl=10.0)
        assert cache.get_tree("Notepad", depth=3) is None

    def test_set_and_get(self):
        cache = ElementCache(ttl=10.0)
        tree = _make_tree()
        cache.set_tree("Notepad", depth=3, tree=tree)
        result = cache.get_tree("Notepad", depth=3)
        assert result is not None
        assert result.name == "Root"

    def test_ttl_expiry(self):
        cache = ElementCache(ttl=0.05)
        cache.set_tree("Notepad", depth=3, tree=_make_tree())
        time.sleep(0.1)
        assert cache.get_tree("Notepad", depth=3) is None

    def test_depth_insufficient(self):
        cache = ElementCache(ttl=10.0)
        cache.set_tree("Notepad", depth=2, tree=_make_tree())
        # Requesting deeper depth should miss
        assert cache.get_tree("Notepad", depth=3) is None
        # Same or less depth should hit
        assert cache.get_tree("Notepad", depth=2) is not None
        assert cache.get_tree("Notepad", depth=1) is not None

    def test_invalidate_specific(self):
        cache = ElementCache(ttl=10.0)
        cache.set_tree("Notepad", depth=3, tree=_make_tree())
        cache.set_tree("Calculator", depth=3, tree=_make_tree("Calc"))
        cache.invalidate("Notepad")
        assert cache.get_tree("Notepad", depth=3) is None
        assert cache.get_tree("Calculator", depth=3) is not None

    def test_invalidate_all(self):
        cache = ElementCache(ttl=10.0)
        cache.set_tree("Notepad", depth=3, tree=_make_tree())
        cache.set_tree("Calculator", depth=3, tree=_make_tree())
        cache.invalidate()
        assert cache.get_tree("Notepad", depth=3) is None
        assert cache.get_tree("Calculator", depth=3) is None

    def test_is_stale_no_entry(self):
        cache = ElementCache(ttl=10.0)
        assert cache.is_stale("Notepad") is True

    def test_is_stale_fresh(self):
        cache = ElementCache(ttl=10.0)
        cache.set_tree("Notepad", depth=3, tree=_make_tree())
        assert cache.is_stale("Notepad") is False

    def test_is_stale_expired(self):
        cache = ElementCache(ttl=0.05)
        cache.set_tree("Notepad", depth=3, tree=_make_tree())
        time.sleep(0.1)
        assert cache.is_stale("Notepad") is True

    def test_size(self):
        cache = ElementCache(ttl=10.0)
        assert cache.size == 0
        cache.set_tree("A", depth=1, tree=_make_tree())
        assert cache.size == 1
        cache.set_tree("B", depth=1, tree=_make_tree())
        assert cache.size == 2

    def test_clear(self):
        cache = ElementCache(ttl=10.0)
        cache.set_tree("A", depth=1, tree=_make_tree())
        cache.set_tree("B", depth=1, tree=_make_tree())
        cache.clear()
        assert cache.size == 0

    def test_ttl_property(self):
        cache = ElementCache(ttl=5.0)
        assert cache.ttl == 5.0
        cache.ttl = 10.0
        assert cache.ttl == 10.0

    def test_ttl_non_negative(self):
        cache = ElementCache(ttl=5.0)
        cache.ttl = -1.0
        assert cache.ttl == 0.0

    def test_case_insensitive_keys(self):
        cache = ElementCache(ttl=10.0)
        cache.set_tree("Notepad", depth=3, tree=_make_tree())
        assert cache.get_tree("notepad", depth=3) is not None
        assert cache.get_tree("NOTEPAD", depth=3) is not None

    def test_overwrite_entry(self):
        cache = ElementCache(ttl=10.0)
        cache.set_tree("Win", depth=3, tree=_make_tree("First"))
        cache.set_tree("Win", depth=5, tree=_make_tree("Second"))
        result = cache.get_tree("Win", depth=5)
        assert result is not None
        assert result.name == "Second"
