"""Loud-failure + window-scoping contract for ``find_element`` (#963).

Silent-failure class (same family as #957/#964): a surface accepts a window
selector (``window_title``), fails to resolve it, and *silently* searches the
foreground window — reporting a result (or ``ELEMENT_NOT_FOUND``) against the
**wrong** window. ``WindowsElementBackend.find_element`` was the last instance:
its ``window_title`` parameter was documented "Not yet used (reserved for
future)" and the search always ran against ``hwnd or 0`` (the foreground).

The fix resolves the selector up front through ``_resolve_hwnd`` (the same path
the sibling ``get_element_value`` uses, #964), letting ``WindowNotFoundError``
propagate so an unmatched ``window_title`` fails loudly with ``WINDOW_NOT_FOUND``
instead of degrading to the focused window. A matched title scopes the search to
that window's handle. With no selector the documented foreground default (HWND
``0``) is preserved.

These tests run cross-platform (no DLL/desktop): the backend core and resolver
are mocked so resolution behaves exactly as the real Windows backend does.

Closes #963.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from naturo.errors import WindowNotFoundError

# A window title guaranteed not to match any real window.
_BOGUS_TITLE = "__no_such_window_zzz_963__"


def _make_harness(resolved_hwnd=None):
    """Build a minimal ``ElementTreeMixin`` host with a stubbed core and resolver.

    ``_resolve_hwnd`` mimics the real backend: a supplied ``window_title`` that
    matches a configured window returns its handle, otherwise it raises
    ``WindowNotFoundError`` (never falling back to the foreground window).
    """
    from naturo.backends.windows._element._tree import ElementTreeMixin

    class _Harness(ElementTreeMixin):
        def __init__(self):
            self._core = MagicMock()
            self._resolved_hwnd = resolved_hwnd

        def _ensure_core(self):
            return self._core

        def _resolve_hwnd(self, app=None, window_title=None, hwnd=None, pid=None):
            if self._resolved_hwnd is not None:
                return self._resolved_hwnd
            raise WindowNotFoundError(window_title or app or "")

    return _Harness()


def test_backend_unmatched_window_title_raises_not_foreground():
    """An unmatched ``window_title`` must raise, never search the foreground."""
    harness = _make_harness(resolved_hwnd=None)
    with pytest.raises(WindowNotFoundError):
        harness.find_element(selector="Button:OK", window_title=_BOGUS_TITLE)
    # The foreground element search must never be reached on a bogus selector.
    harness._core.find_element.assert_not_called()


def test_backend_matched_window_title_scopes_search_to_hwnd():
    """A resolved ``window_title`` must scope the search to that window's HWND."""
    harness = _make_harness(resolved_hwnd=4242)
    harness._core.find_element.return_value = None
    harness.find_element(selector="Button:OK", window_title="Calculator")
    harness._core.find_element.assert_called_once_with(
        hwnd=4242, role="Button", name="OK"
    )


def test_backend_no_selector_keeps_foreground_default():
    """With no window selector the foreground default (HWND 0) is preserved."""
    harness = _make_harness(resolved_hwnd=None)
    harness._core.find_element.return_value = None
    harness.find_element(selector="Button:OK")
    harness._core.find_element.assert_called_once_with(
        hwnd=0, role="Button", name="OK"
    )


def test_backend_explicit_hwnd_takes_priority_over_title():
    """An explicit ``hwnd`` is honoured without re-resolving the title."""
    harness = _make_harness(resolved_hwnd=None)  # would raise if resolution ran
    harness._core.find_element.return_value = None
    harness.find_element(selector="Button:OK", window_title="ignored", hwnd=99)
    harness._core.find_element.assert_called_once_with(
        hwnd=99, role="Button", name="OK"
    )


def test_mcp_find_element_unmatched_window_title_fails_loudly():
    """The MCP ``find_element`` tool must surface WINDOW_NOT_FOUND, not success."""
    import asyncio

    mcp = pytest.importorskip("naturo.mcp_server")

    backend = MagicMock()
    backend.find_element.side_effect = WindowNotFoundError(_BOGUS_TITLE)

    from unittest.mock import patch

    with patch("naturo.mcp_server.get_backend", return_value=backend), \
         patch("naturo.cli.interaction._check_desktop_session"):
        server = mcp.create_server()
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                server.call_tool(
                    "find_element",
                    {"selector": "Button:OK", "window_title": _BOGUS_TITLE},
                )
            )
        finally:
            loop.close()

    content = result[0] if isinstance(result, tuple) else result
    payload = json.loads(content[0].text)
    assert payload.get("success") is False, (
        f"find_element fell back to the foreground on a bogus window_title: {payload}"
    )
    assert payload.get("error", {}).get("code") == "WINDOW_NOT_FOUND", payload
