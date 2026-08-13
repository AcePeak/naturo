"""Regression tests for #1212 — one UIA gate for value read AND write.

Element value read (:meth:`get_element_value_uia`) and write
(:meth:`set_element_value`), plus toggle/select/expand, now acquire their UIA
patterns through a single shared helper, :meth:`WindowsBackend._get_uia_pattern`.
That helper owns the one subtlety the two directions had already drifted on
(#1212): comtypes returns a **non-None NULL COM pointer** for a pattern an
element does not support, so it must be gated on truthiness — ``is not None``
is ``True`` for it and then ``QueryInterface`` raises "NULL COM pointer access".

Before consolidation the WRITE side used the correct ``if ptr`` gate while the
READ side used ``if pat is not None`` and bailed the *entire* read to ``None``
for any element lacking ValuePattern — never reaching its TextPattern/Toggle/
Name fallbacks. These tests instantiate the backend and mock UIA, so they are
desktop-independent and send no input.
"""

import platform
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="UIA value read/write is Windows-only",
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
    mod.UIA_RangeValuePatternId = 10003
    mod.UIA_TextPatternId = 10014
    mod.UIA_TogglePatternId = 10015
    return mod


# ── the shared gate itself ───────────────────────────────────────────────────

class TestGetUiaPatternGate:
    def test_null_pointer_returns_none_not_raise(self):
        """A NULL (falsy) pattern pointer must be skipped, never QueryInterface'd."""
        b = _backend()
        null = _null_ptr()
        elem = MagicMock()
        elem.GetCurrentPattern.return_value = null
        out = b._get_uia_pattern(elem, 10002, MagicMock())
        assert out is None
        null.QueryInterface.assert_not_called()

    def test_live_pointer_is_queried(self):
        b = _backend()
        iface = MagicMock()
        elem = MagicMock()
        elem.GetCurrentPattern.return_value = _live_ptr(iface)
        assert b._get_uia_pattern(elem, 10002, MagicMock()) is iface

    def test_none_pattern_returns_none(self):
        b = _backend()
        elem = MagicMock()
        elem.GetCurrentPattern.return_value = None
        assert b._get_uia_pattern(elem, 10002, MagicMock()) is None


# ── read-side drift fix: no ValuePattern must fall through, not bail ──────────

class TestReadFallsThroughOnNullValuePattern:
    def test_checkbox_without_valuepattern_reads_toggle(self):
        """The exact drift bug: ValuePattern is a NULL pointer (CheckBox has
        none) but TogglePattern is live. The read must fall through to Toggle
        and return "On" — before #1212 it raised on the NULL pointer and the
        whole read returned None."""
        b = _backend()
        mod = _mod()

        toggle_pat = MagicMock()
        toggle_pat.CurrentToggleState = 1  # On

        def _get(pid):
            if pid == mod.UIA_TogglePatternId:
                return _live_ptr(toggle_pat)
            return _null_ptr()  # ValuePattern + TextPattern unsupported

        elem = MagicMock()
        elem.GetCurrentPattern.side_effect = _get
        elem.CurrentControlType = 50002  # CheckBox
        elem.CurrentName = "Bold"
        elem.CurrentAutomationId = ""

        with patch.object(b, "_init_comtypes_uia", return_value=(MagicMock(), mod)), \
             patch.object(b, "_resolve_interaction_element", return_value=elem):
            out = b.get_element_value_uia(hwnd=1, name="Bold")

        assert out is not None, "read bailed on NULL ValuePattern (the #1212 bug)"
        assert out["value"] == "On"
        assert out["pattern"] == "TogglePattern"

    def test_edit_with_live_valuepattern_reads_value(self):
        """Sanity: a live ValuePattern still reads through the shared gate."""
        b = _backend()
        mod = _mod()
        vp = MagicMock()
        vp.CurrentValue = "hello"
        elem = MagicMock()
        elem.GetCurrentPattern.side_effect = (
            lambda pid: _live_ptr(vp) if pid == mod.UIA_ValuePatternId
            else _null_ptr()
        )
        elem.CurrentControlType = 50004  # Edit
        elem.CurrentName = ""
        elem.CurrentAutomationId = "txt"

        with patch.object(b, "_init_comtypes_uia", return_value=(MagicMock(), mod)), \
             patch.object(b, "_resolve_interaction_element", return_value=elem):
            out = b.get_element_value_uia(hwnd=1, automation_id="txt")

        assert out["value"] == "hello"
        assert out["pattern"] == "ValuePattern"


# ── shared-path guarantee: one gate fix reaches BOTH read and write ──────────

class TestReadAndWriteShareOneGate:
    def test_both_directions_route_through_get_uia_pattern(self):
        """Read and write both acquire ValuePattern via ``_get_uia_pattern``, so
        a single fix to the gate (or the resolver it sits behind) covers both.

        Patching the gate to report "no pattern" makes the write fail cleanly
        and the read skip ValuePattern — and the spy proves each direction went
        through the one shared helper with the ValuePatternId."""
        b = _backend()
        mod = _mod()
        elem = MagicMock()
        # Empty name so the read's Name fallback does not fabricate a value.
        elem.CurrentName = ""
        elem.CurrentAutomationId = ""
        elem.CurrentControlType = 50004  # Edit

        gate = MagicMock(return_value=None)  # every pattern reported unsupported
        with patch.object(b, "_init_comtypes_uia", return_value=(MagicMock(), mod)), \
             patch.object(b, "_resolve_interaction_element", return_value=elem), \
             patch.object(b, "_get_uia_pattern", gate):
            wrote = b.set_element_value("x", hwnd=1, name="F", role="Edit")
            read = b.get_element_value_uia(hwnd=1, name="F")

        assert wrote is False          # no writable ValuePattern/RangeValue
        assert read is None            # no readable pattern, no name value
        value_pat_calls = [
            c for c in gate.call_args_list if c.args[1] == mod.UIA_ValuePatternId
        ]
        # At least one ValuePattern acquisition from the write path AND one from
        # the read path — the same helper served both directions.
        assert len(value_pat_calls) >= 2

    def test_both_directions_share_one_resolver(self):
        """Read and write both resolve their target element through the single
        ``_resolve_interaction_element`` — the shared locator behind the gate."""
        b = _backend()
        mod = _mod()
        resolver = MagicMock(return_value=None)  # element not found either way
        with patch.object(b, "_init_comtypes_uia", return_value=(MagicMock(), mod)), \
             patch.object(b, "_resolve_interaction_element", resolver):
            b.set_element_value("x", hwnd=7, name="F")
            b.get_element_value_uia(hwnd=7, name="F")
        assert resolver.call_count == 2
