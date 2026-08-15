"""Regression tests for #1213 — raw-view fallback for ScrollViewer-wrapped edits.

Some multiline text controls expose only a ScrollViewer (ControlType 50033, a
Pane) at the text location in the UIA *control* view. The ScrollViewer advertises
Value/Text yet ValuePattern/TextPattern/Legacy all read empty, and the inner
Edit/Document that actually holds the text is hidden from the control view but
present in the RAW view. ``get_element_value_uia`` now, ONLY when every
control-view attempt returned empty AND the element advertises Value/Text, walks
the raw view for an inner Edit (50004) / Document (50030) descendant and reads
its TextPattern/ValuePattern.

These tests assert the fallback's SELECTION logic and — crucially — its
non-regression guarantee (an element that already reads a value never triggers
the raw-view walk), plus the depth/count bound on the raw-view search. They
instantiate the backend and mock UIA, so they are desktop-independent and send
no input.
"""

import platform
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="UIA value read is Windows-only",
)


def _backend():
    from naturo.backends.windows import WindowsBackend
    return WindowsBackend.__new__(WindowsBackend)


def _null_ptr():
    """A comtypes-style NULL COM pointer: non-None but falsy."""
    p = MagicMock()
    p.__bool__.return_value = False
    return p


def _live_ptr(iface_obj):
    """A live (truthy) COM pointer whose QueryInterface yields ``iface_obj``."""
    p = MagicMock()
    p.__bool__.return_value = True
    p.QueryInterface.return_value = iface_obj
    return p


def _mod():
    mod = MagicMock()
    mod.UIA_ValuePatternId = 10002
    mod.UIA_TextPatternId = 10014
    mod.UIA_TogglePatternId = 10015
    return mod


def _text_pattern(text):
    tp = MagicMock()
    tp.DocumentRange.GetText.return_value = text
    return tp


def _value_pattern(val):
    vp = MagicMock()
    vp.CurrentValue = val
    return vp


def _elem(control_type, mod, patterns=None, name="", aid="",
          adv_value=False, adv_text=False):
    """A mock UIA element.

    ``patterns`` maps a ``UIA_*PatternId`` to its live pattern iface; any pattern
    not listed reports a NULL COM pointer (unsupported), exactly as comtypes does.
    """
    patterns = patterns or {}
    e = MagicMock()
    e.CurrentControlType = control_type
    e.CurrentName = name
    e.CurrentAutomationId = aid
    e.CurrentIsValuePatternAvailable = adv_value
    e.CurrentIsTextPatternAvailable = adv_text

    def _get(pid):
        if pid in patterns:
            return _live_ptr(patterns[pid])
        return _null_ptr()

    e.GetCurrentPattern.side_effect = _get
    return e


def _walker(children_of):
    """A RawViewWalker over ``children_of``: ``{id(parent): [child, ...]}``."""
    walker = MagicMock()

    def first(node):
        kids = children_of.get(id(node), [])
        return kids[0] if kids else None

    def sibling(node):
        for kids in children_of.values():
            for i, k in enumerate(kids):
                if k is node:
                    return kids[i + 1] if i + 1 < len(kids) else None
        return None

    walker.GetFirstChildElement.side_effect = first
    walker.GetNextSiblingElement.side_effect = sibling
    return walker


# ── the fallback engages when the control view reads empty ───────────────────


class TestScrollViewerFallback:
    def test_reads_inner_edit_via_raw_view(self):
        """The #1213 case: a ScrollViewer (Pane, 50033) whose control-view read
        is empty but advertises Text — the raw-view inner Edit carries the text.
        The read must fall through to the raw-view fallback and return it."""
        b = _backend()
        mod = _mod()

        inner_edit = _elem(
            50004, mod, patterns={mod.UIA_TextPatternId: _text_pattern(
                "line one\nline two")},
        )
        scrollviewer = _elem(
            50033, mod, patterns={}, name="", adv_text=True,
        )
        walker = _walker({id(scrollviewer): [inner_edit]})
        uia = MagicMock()
        uia.RawViewWalker = walker

        with patch.object(b, "_init_comtypes_uia", return_value=(uia, mod)), \
             patch.object(b, "_resolve_interaction_element",
                          return_value=scrollviewer):
            out = b.get_element_value_uia(hwnd=1, x=10, y=20)

        assert out is not None
        assert out["value"] == "line one\nline two"
        assert out["pattern"] == "RawViewFallback"

    def test_inner_edit_read_via_valuepattern_when_no_text(self):
        """The raw-view helper prefers TextPattern but falls back to ValuePattern
        on the inner descendant."""
        b = _backend()
        mod = _mod()
        inner_edit = _elem(
            50004, mod,
            patterns={mod.UIA_ValuePatternId: _value_pattern("val text")},
        )
        scrollviewer = _elem(50033, mod, adv_value=True)
        walker = _walker({id(scrollviewer): [inner_edit]})
        uia = MagicMock()
        uia.RawViewWalker = walker

        with patch.object(b, "_init_comtypes_uia", return_value=(uia, mod)), \
             patch.object(b, "_resolve_interaction_element",
                          return_value=scrollviewer):
            out = b.get_element_value_uia(hwnd=1)

        assert out["value"] == "val text"
        assert out["pattern"] == "RawViewFallback"


# ── non-regression: an element that already reads never triggers the walk ────


class TestNonRegression:
    def test_live_value_skips_raw_view_fallback(self):
        """A normal Edit with a live ValuePattern reads through the existing path;
        the raw-view fallback must NOT be invoked (proves it is strictly
        additive)."""
        b = _backend()
        mod = _mod()
        elem = _elem(
            50004, mod,
            patterns={mod.UIA_ValuePatternId: _value_pattern("visible")},
            aid="txt", adv_value=True, adv_text=True,
        )

        spy = MagicMock()
        with patch.object(b, "_init_comtypes_uia",
                          return_value=(MagicMock(), mod)), \
             patch.object(b, "_resolve_interaction_element", return_value=elem), \
             patch.object(b, "_raw_view_find_inner_text", spy):
            out = b.get_element_value_uia(hwnd=1, automation_id="txt")

        assert out["value"] == "visible"
        assert out["pattern"] == "ValuePattern"
        spy.assert_not_called()

    def test_no_advertised_patterns_skips_raw_view_fallback(self):
        """An empty element that does NOT advertise Value/Text (not a
        ScrollViewer) must not trigger the raw-view walk — the gate keeps the
        fallback targeted."""
        b = _backend()
        mod = _mod()
        elem = _elem(50033, mod, patterns={}, name="",
                     adv_value=False, adv_text=False)

        spy = MagicMock()
        with patch.object(b, "_init_comtypes_uia",
                          return_value=(MagicMock(), mod)), \
             patch.object(b, "_resolve_interaction_element", return_value=elem), \
             patch.object(b, "_raw_view_find_inner_text", spy):
            out = b.get_element_value_uia(hwnd=1)

        assert out is None
        spy.assert_not_called()


# ── the raw-view search is bounded (depth + count) ───────────────────────────


class TestSearchBound:
    def test_count_budget_stops_search(self):
        """With a small node budget the walk stops before reaching a late Edit."""
        b = _backend()
        mod = _mod()
        edit = _elem(
            50004, mod,
            patterns={mod.UIA_TextPatternId: _text_pattern("found")},
        )
        groups = [_elem(50026, mod) for _ in range(4)]  # four empty Groups
        root = _elem(50033, mod, adv_text=True)
        walker = _walker({id(root): groups + [edit]})  # Edit is the 5th child
        uia = MagicMock()
        uia.RawViewWalker = walker

        # budget=3 visits only the first three Groups; the Edit is never reached.
        assert b._raw_view_find_inner_text(uia, mod, root, budget=3) is None
        # A generous budget finds it.
        assert b._raw_view_find_inner_text(
            uia, mod, root, budget=10) == "found"

    def test_depth_bound_stops_search(self):
        """An Edit nested below ``max_depth`` levels is not reached."""
        b = _backend()
        mod = _mod()
        edit = _elem(
            50004, mod,
            patterns={mod.UIA_TextPatternId: _text_pattern("deep")},
        )
        n3 = _elem(50026, mod)
        n2 = _elem(50026, mod)
        n1 = _elem(50026, mod)
        root = _elem(50033, mod, adv_text=True)
        walker = _walker({
            id(root): [n1], id(n1): [n2], id(n2): [n3], id(n3): [edit],
        })
        uia = MagicMock()
        uia.RawViewWalker = walker

        # Edit sits at level 4; a max_depth of 2 cannot reach it.
        assert b._raw_view_find_inner_text(
            uia, mod, root, max_depth=2) is None
        # A deeper cap finds it.
        assert b._raw_view_find_inner_text(
            uia, mod, root, max_depth=10) == "deep"
