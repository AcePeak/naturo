"""Regression tests for #1208 (read side) — get must read any element naturo found.

``get_element_value`` previously refused an element that had no AutomationId and
no name ("Element eN has no AutomationId, role, or name for value lookup"), even
though naturo had captured its bounding box and source window. It now captures
the cached point + window handle and reads the value live from the element
inside its own window's UIA tree (``get_element_value_uia``).

These tests instantiate the mixin and mock the snapshot manager, the C++ core,
and the UIA reader, so they are desktop-independent and send no input.
"""

import types
from unittest.mock import MagicMock, patch

import pytest

from naturo.backends.windows._element._tree import ElementTreeMixin
from naturo.errors import NaturoError


class _Stub(ElementTreeMixin):
    """Concrete carrier of the mixin for isolated method testing."""


def _unnamed_element(frame):
    """A resolved snapshot element with no AutomationId / title / label."""
    return types.SimpleNamespace(
        identifier=None, role="Edit", title=None, label=None, frame=frame,
    )


def _make_backend(reader_result):
    backend = _Stub()
    backend._ensure_core = MagicMock(return_value=MagicMock())
    backend._resolve_hwnd = MagicMock(return_value=0)
    backend.get_element_value_uia = MagicMock(return_value=reader_result)
    return backend


@patch("naturo.snapshot.get_snapshot_manager")
def test_unnamed_element_read_via_cached_point(mock_get_mgr):
    """An unnamed Edit is read via the cached point inside its source window."""
    mgr = MagicMock()
    mgr.resolve_ref_element.return_value = (
        _unnamed_element((2249, 423, 419, 150)), "snap1",
    )
    mgr.get_snapshot.return_value = types.SimpleNamespace(window_handle=727448)
    mock_get_mgr.return_value = mgr

    backend = _make_backend(
        {"value": "hello", "pattern": "TextPattern", "role": "Edit",
         "name": "", "automation_id": ""},
    )

    result = backend.get_element_value(ref="e55")

    assert result["value"] == "hello"
    backend.get_element_value_uia.assert_called_once()
    _, kwargs = backend.get_element_value_uia.call_args
    assert kwargs["x"] == 2249 + 419 // 2
    assert kwargs["y"] == 423 + 150 // 2
    assert kwargs["hwnd"] == 727448


@patch("naturo.snapshot.get_snapshot_manager")
def test_unnamed_element_without_geometry_raises(mock_get_mgr):
    """No identity AND no usable bounding box → loud failure, no false success."""
    mgr = MagicMock()
    mgr.resolve_ref_element.return_value = (
        _unnamed_element((0, 0, 0, 0)), "snap1",
    )
    mgr.get_snapshot.return_value = types.SimpleNamespace(window_handle=None)
    mock_get_mgr.return_value = mgr

    backend = _make_backend(None)

    with pytest.raises(NaturoError):
        backend.get_element_value(ref="e55")
    backend.get_element_value_uia.assert_not_called()
