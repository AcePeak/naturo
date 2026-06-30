"""Regression tests for #1208 — set/get must operate any element naturo found.

``_resolve_element_identifiers`` must NOT refuse an element just because it has
no AutomationId and no name. When naturo already located the element it has the
element's bounding box and source window, so it returns a point + window-handle
fallback that the backend resolves via the window's own UIA tree (occlusion-
independent), instead of pushing identifier discovery onto the caller.

These tests mock the snapshot manager, so they are desktop-independent and run
on the GitHub-hosted runner (no ``@pytest.mark.desktop``).
"""

import types
from unittest.mock import MagicMock, patch

import pytest

from naturo.cli.values._set import _resolve_element_identifiers
from naturo.errors import NaturoError


def _element(identifier=None, role="Edit", title=None, label=None,
             frame=(0, 0, 0, 0)):
    """Build a minimal stand-in for a resolved snapshot ``UIElement``."""
    return types.SimpleNamespace(
        identifier=identifier, role=role, title=title, label=label, frame=frame,
    )


def _manager(element, window_handle=None, snap_id="snap1"):
    """Build a mock snapshot manager returning ``element`` for any ref."""
    mgr = MagicMock()
    mgr.resolve_ref_element.return_value = (element, snap_id)
    mgr.get_snapshot.return_value = types.SimpleNamespace(
        window_handle=window_handle,
    )
    return mgr


@patch("naturo.snapshot.get_snapshot_manager")
def test_unnamed_element_resolves_via_coords_and_window(mock_get_mgr):
    """An unnamed, AutomationId-less Edit yields cached point + window handle."""
    mock_get_mgr.return_value = _manager(
        _element(frame=(2249, 423, 419, 150)), window_handle=727448,
    )

    aid, role, name, coords, hwnd = _resolve_element_identifiers(
        "e55", None, None, None,
    )

    assert aid is None
    assert name is None
    # centre of the cached bounding box
    assert coords == (2249 + 419 // 2, 423 + 150 // 2)
    assert hwnd == 727448


@patch("naturo.snapshot.get_snapshot_manager")
def test_no_identity_and_no_geometry_raises(mock_get_mgr):
    """With neither identity nor a usable bounding box, set must fail loudly."""
    mock_get_mgr.return_value = _manager(
        _element(frame=(0, 0, 0, 0)), window_handle=None,
    )

    with pytest.raises(NaturoError):
        _resolve_element_identifiers("e55", None, None, None)


@patch("naturo.snapshot.get_snapshot_manager")
def test_automation_id_is_preferred_over_point(mock_get_mgr):
    """A real AutomationId still wins; coords are captured as a backup."""
    mock_get_mgr.return_value = _manager(
        _element(identifier="txtSearch", frame=(10, 10, 50, 20)),
        window_handle=123,
    )

    aid, role, name, coords, hwnd = _resolve_element_identifiers(
        "e1", None, None, None,
    )

    assert aid == "txtSearch"
    assert coords == (10 + 50 // 2, 10 + 20 // 2)
    assert hwnd == 123


@patch("naturo.snapshot.get_snapshot_manager")
def test_role_plus_name_still_resolves(mock_get_mgr):
    """An element with role+title resolves by identity (coords still returned)."""
    mock_get_mgr.return_value = _manager(
        _element(role="Button", title="OK", frame=(5, 5, 40, 20)),
        window_handle=99,
    )

    aid, role, name, coords, hwnd = _resolve_element_identifiers(
        "e3", None, None, None,
    )

    assert aid is None
    assert role == "Button"
    assert name == "OK"
    assert coords == (5 + 40 // 2, 5 + 20 // 2)
