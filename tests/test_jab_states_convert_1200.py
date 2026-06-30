"""`states` survives the bridge→backend conversion in ``get_element_tree`` (#1200).

The Java Access Bridge native layer emits a per-element ``states`` string, the
bridge parser surfaces it on ``ElementInfo.states`` (the ``_models`` model), and
the Windows backend's ``get_element_tree`` must carry it into the returned
element's ``properties`` so a consumer — e.g. the #932 checkbox-via-JAB
verify-after-action proof — can read a control's checked/unchecked state.

Before #1200 the bridge ``ElementInfo`` dropped ``states`` in its parser, and the
backend ``convert()`` step (bridge ``ElementInfo`` → ``backends.base.ElementInfo``)
never copied it — so a JAB control's state never reached any consumer. These
tests pin both halves of that path.

Cross-platform / hermetic: the core and resolver are mocked, so no DLL or
interactive desktop is needed and they run on CI.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from naturo.backends.windows._element._tree import ElementTreeMixin
from naturo.bridge._models import ElementInfo


def _make_backend(tree: ElementInfo) -> ElementTreeMixin:
    """Build a minimal backend whose JAB tree fetch returns ``tree``.

    Mirrors the real Windows backend's resolution path while stubbing the native
    core and the coordinate fixup (which needs a live window handle).
    """
    class _Harness(ElementTreeMixin):
        def __init__(self) -> None:
            self._core = MagicMock()
            self._core.jab_get_element_tree.return_value = tree

        def _ensure_core(self):
            return self._core

        def _resolve_hwnd(self, app=None, window_title=None, hwnd=None, pid=None):
            return hwnd or 1

        def _fixup_element_coords(self, result, handle):
            return result

    return _Harness()


def _element(**overrides) -> ElementInfo:
    """A bridge ``ElementInfo`` with sensible defaults for these tests."""
    fields = dict(
        id="", role="CheckBox", name="Express Shipping", value=None,
        x=0, y=0, width=10, height=10,
    )
    fields.update(overrides)
    return ElementInfo(**fields)


def test_jab_states_reach_backend_element_properties():
    """A JAB element's ``states`` reaches the backend element's ``properties`` (#1200)."""
    root = _element(role="Panel", name="Form", children=[
        _element(states="enabled,focusable,visible,checked"),
    ])
    backend = _make_backend(root)

    result = backend.get_element_tree(hwnd=42, backend="jab")

    assert result is not None
    checkbox = result.children[0]
    assert checkbox.properties.get("states") == "enabled,focusable,visible,checked"


def test_element_without_states_omits_property_key():
    """A UIA-style element with no ``states`` gets no spurious ``states`` key."""
    root = _element(role="Panel", name="Form", children=[_element(states=None)])
    backend = _make_backend(root)

    result = backend.get_element_tree(hwnd=42, backend="jab")

    assert result is not None
    assert "states" not in result.children[0].properties
