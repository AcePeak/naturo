"""Hermetic regression tests for #1212 — single-path single-element value read.

These prove the two behavioural guarantees of #1212 without a live desktop:

1. **Single reader, no stack.** ``get_element_value`` no longer stacks the
   comtypes point reader (:meth:`get_element_value_uia`) on top of the native
   ``core.get_element_value``. Whichever reader a given resolution scenario
   selects is the *only* one invoked — and, the exact old drift bug, a
   coords-only read the comtypes point reader cannot satisfy does NOT fall
   through to a native editable-role probe.
2. **see/get agree.** The ``see``/snapshot tree walk fills Edit/Document/Text
   values through the SAME consolidated reader (``_read_element_value``) that
   ``get`` uses, so both report the identical value for one element.

Everything is mocked (snapshot manager, native core, comtypes reader), so these
tests run on any platform and send no input.
"""

import types
from unittest.mock import MagicMock, patch

from naturo.backends.windows._element._tree import ElementTreeMixin
from naturo.bridge import ElementInfo


class _Stub(ElementTreeMixin):
    """Concrete carrier of the mixin for isolated method testing."""


def _unnamed_elem(frame, value=None):
    """A resolved snapshot element with no AutomationId / title / label."""
    return types.SimpleNamespace(
        identifier=None, role="Edit", title=None, label=None,
        frame=frame, value=value,
    )


# ── (a) single reader — identity read touches only the native reader ─────────

def test_identity_read_uses_only_native_reader():
    """An AutomationId/role+name read goes through the native core reader alone;
    the comtypes point reader is never called (no stacking)."""
    backend = _Stub()
    core = MagicMock()
    core.get_element_value.return_value = {
        "value": "hi", "pattern": "ValuePattern", "role": "Edit",
        "name": "Body", "automation_id": "txt",
    }
    backend._ensure_core = MagicMock(return_value=core)
    backend._resolve_hwnd = MagicMock(return_value=1)
    backend.get_element_value_uia = MagicMock()  # comtypes reader — must NOT run

    out = backend.get_element_value(role="Edit", name="Body", hwnd=1)

    assert out["value"] == "hi"
    core.get_element_value.assert_called_once()
    backend.get_element_value_uia.assert_not_called()


# ── (a) single reader — coords-only read touches only the comtypes reader ────

@patch("naturo.snapshot.get_snapshot_manager")
def test_coords_only_read_uses_only_comtypes_reader(mock_get_mgr):
    """A located-but-unnamed element (only a cached point) reads via the comtypes
    point reader alone — the native core reader is never called."""
    mgr = MagicMock()
    mgr.resolve_ref_element.return_value = (
        _unnamed_elem((100, 100, 40, 20)), "s1",
    )
    mgr.get_snapshot.return_value = types.SimpleNamespace(window_handle=999)
    mock_get_mgr.return_value = mgr

    backend = _Stub()
    core = MagicMock()  # native reader — must NOT run for a coords-only read
    backend._ensure_core = MagicMock(return_value=core)
    backend._resolve_hwnd = MagicMock(return_value=0)
    backend.get_element_value_uia = MagicMock(
        return_value={"value": "point", "pattern": "TextPattern",
                      "role": "Edit", "name": "", "automation_id": ""},
    )

    out = backend.get_element_value(ref="e1")

    assert out["value"] == "point"
    backend.get_element_value_uia.assert_called_once()
    core.get_element_value.assert_not_called()  # no stacked native reader


@patch("naturo.snapshot.get_snapshot_manager")
def test_coords_only_miss_does_not_stack_native_probe(mock_get_mgr):
    """The exact #1212 stack, now removed: a coords-only read that the comtypes
    point reader cannot satisfy must NOT fall through to a native editable-role
    probe. The snapshot-metadata fallback returns the last-known value instead —
    exactly one reader is exercised."""
    elem = _unnamed_elem((100, 100, 40, 20), value="cached")
    mgr = MagicMock()
    mgr.resolve_ref_element.return_value = (elem, "s1")
    mgr.get_snapshot.return_value = types.SimpleNamespace(window_handle=999)
    mock_get_mgr.return_value = mgr

    backend = _Stub()
    core = MagicMock()  # native reader — must stay untouched
    backend._ensure_core = MagicMock(return_value=core)
    backend._resolve_hwnd = MagicMock(return_value=0)
    backend.get_element_value_uia = MagicMock(return_value=None)  # point read miss

    out = backend.get_element_value(ref="e1")

    backend.get_element_value_uia.assert_called_once()
    core.get_element_value.assert_not_called()  # the stacked probe is gone
    assert out["value"] == "cached"             # snapshot-metadata fallback
    assert out["source"] == "snapshot"


# ── (b) see and get agree on an element's value ──────────────────────────────

def test_see_and_get_agree_on_edit_value():
    """The ``see`` tree walk and single ``get`` report the SAME value for one
    Edit, because both funnel through the consolidated ``_read_element_value``.

    The native tree walk emits ``value=None`` for the Edit (element.cpp hardcodes
    it); ``see`` fills it via the same reader ``get`` uses, so the two agree."""
    backend = _Stub()
    core = MagicMock()

    edit = ElementInfo(id="", role="Edit", name="Body", value=None,
                       x=10, y=10, width=200, height=30)
    root = ElementInfo(id="", role="Window", name="Notepad", value=None,
                       x=0, y=0, width=800, height=600, children=[edit])
    core.get_element_tree.return_value = root
    core.get_element_value.return_value = {
        "value": "hello world", "pattern": "TextPattern",
        "role": "Edit", "name": "Body", "automation_id": "",
    }

    backend._ensure_core = MagicMock(return_value=core)
    backend._resolve_hwnd = MagicMock(return_value=1)
    backend._is_afh_window = MagicMock(return_value=False)
    backend._fixup_element_coords = MagicMock(side_effect=lambda r, h: r)
    backend.get_element_value_uia = MagicMock()  # identity path — not used

    tree = backend.get_element_tree(hwnd=1, backend="uia")
    see_edit = tree.children[0]

    get_result = backend.get_element_value(role="Edit", name="Body", hwnd=1)

    assert see_edit.value == "hello world"          # see populated the Edit
    assert get_result["value"] == "hello world"     # get read the same
    assert see_edit.value == get_result["value"]    # they agree
