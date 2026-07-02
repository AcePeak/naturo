"""Tests for #1190: a wildcard-host (``app://*``) selector must round-trip.

``see`` and ``find`` emit their reusable locator with the portable wildcard host
``app://*`` (e.g. ``app://*/Window[@name="无标题 - Notepad"]/Document[@name="…"]``).
Before this fix, pasting that exact string back into ``find --selector`` /
``click --selector`` *without* an extra ``--hwnd``/``--app`` flag failed with
``SELECTOR_NOT_FOUND``: the resolver fetched only the single default (foreground)
window's tree, so the window the selector actually names was never searched.

The fix resolves a target-less wildcard host across ALL top-level windows. These
tests pin both directions:

* **Round-trip** — emit a selector via ``find`` (over a concrete ``--hwnd``),
  feed it straight back into ``find --selector`` with no target flag, assert it
  resolves to the same element.
* **Click family** — the shared ``_resolve_selector_target`` (used by
  ``click``/``type``/``press``/mouse) resolves the same wildcard host to the
  named element's coordinates.

The fixture is **discriminating**: the foreground window that the default
``get_element_tree()`` path returns is a *different* app that does NOT contain
the target element, so a passing test proves the across-windows search — not the
ambient desktop — is what makes the selector resolve (negative control included).

Hermetic: a small UIA-shaped tree behind a mocked backend; no real desktop, so
this runs on headless CI.
"""

import json

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from naturo.backends.base import ElementInfo, WindowInfo
from naturo.cli.core._find import find_cmd

NOTEPAD_HWND = 111
OTHER_HWND = 222
NOTEPAD_TITLE = "无标题 - Notepad"
DOCUMENT_NAME = "文本编辑器"


def _node(role, name, children=None, el_id=""):
    """Build a backend ElementInfo node for the fixture tree."""
    return ElementInfo(
        id=el_id,
        role=role,
        name=name,
        value=None,
        x=10,
        y=20,
        width=100,
        height=40,
        children=children or [],
        properties={},
    )


@pytest.fixture
def notepad_tree():
    """A Notepad-shaped tree: Window > Pane > Document (the #1190 repro shape)."""
    document = _node("Document", DOCUMENT_NAME)
    pane = _node("Pane", "", children=[document])
    return _node("Window", NOTEPAD_TITLE, children=[pane])


@pytest.fixture
def other_tree():
    """A different foreground window WITHOUT the target Document (negative control)."""
    return _node("Window", "Some Other App", children=[_node("Button", "OK")])


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend(notepad_tree, other_tree):
    """Backend where the Notepad window is NOT the default/foreground window.

    * ``get_element_tree(hwnd=NOTEPAD_HWND)`` → the Notepad tree.
    * ``get_element_tree(hwnd=OTHER_HWND)``   → the other app's tree.
    * ``get_element_tree()`` with no hwnd (the old single-window path) → the
      *other* window, which lacks the target — so the only way to resolve the
      Notepad selector is the across-windows search.
    * ``_resolve_hwnds(window_title=NOTEPAD_TITLE)`` → ``[NOTEPAD_HWND]``.
    * ``list_windows()`` → both windows.
    """
    def _get_tree(*args, **kwargs):
        hwnd = kwargs.get("hwnd")
        if hwnd == NOTEPAD_HWND:
            return notepad_tree
        if hwnd == OTHER_HWND:
            return other_tree
        # No explicit hwnd → emulate "foreground window" = the other app.
        return other_tree

    def _resolve_hwnds(app=None, window_title=None):
        if window_title and window_title in NOTEPAD_TITLE:
            return [NOTEPAD_HWND]
        return []

    mock_be = MagicMock()
    mock_be.get_element_tree.side_effect = _get_tree
    mock_be._resolve_hwnds.side_effect = _resolve_hwnds
    mock_be.list_windows.return_value = [
        WindowInfo(handle=OTHER_HWND, title="Some Other App",
                   process_name="other.exe", pid=2, x=0, y=0,
                   width=100, height=100, is_visible=True, is_minimized=False),
        WindowInfo(handle=NOTEPAD_HWND, title=NOTEPAD_TITLE,
                   process_name="notepad.exe", pid=1, x=0, y=0,
                   width=100, height=100, is_visible=True, is_minimized=False),
    ]
    with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
         patch("naturo.cli.core._common._get_backend", return_value=mock_be):
        yield mock_be


class TestFindSelectorWildcardRoundTrip:
    """The emitted app://* selector must resolve back through find --selector."""

    def test_emitted_selector_round_trips_without_target_flag(self, runner, mock_backend):
        """Emit via find --hwnd, paste back into find --selector with no target."""
        # 1) Emit: a concrete --hwnd query yields the reusable selector field.
        emit = runner.invoke(
            find_cmd, ["role:Document", "--hwnd", str(NOTEPAD_HWND), "--json"]
        )
        assert emit.exit_code == 0, emit.output
        emitted = json.loads(emit.output)["elements"][0]["selector"]
        # The emitted locator uses the portable wildcard host.
        assert emitted.startswith("app://*/"), emitted

        # 2) Round-trip: feed that exact string back with NO --hwnd/--app.
        back = runner.invoke(find_cmd, ["--selector", emitted, "--json"])
        assert back.exit_code == 0, (
            f"emitted selector did not round-trip: {emitted}\n{back.output}"
        )
        payload = json.loads(back.output)
        assert payload["success"] is True, payload
        assert payload["count"] == 1, payload
        assert payload["elements"][0]["name"] == DOCUMENT_NAME, payload

    def test_explicit_wildcard_selector_resolves_across_windows(self, runner, mock_backend):
        """A hand-written app://* selector resolves even though it is not the foreground window."""
        selector = (
            f'app://*/Window[@name="{NOTEPAD_TITLE}"]/Document[@name="{DOCUMENT_NAME}"]'
        )
        result = runner.invoke(find_cmd, ["--selector", selector, "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is True and payload["count"] == 1, payload

    def test_unknown_wildcard_selector_still_reports_not_found(self, runner, mock_backend):
        """A wildcard host naming a non-existent element fails honestly (no false match)."""
        selector = 'app://*/Window[@name="无标题 - Notepad"]/Document[@name="does-not-exist"]'
        result = runner.invoke(find_cmd, ["--selector", selector, "--json"])
        assert result.exit_code != 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is False
        assert payload["error"]["code"] == "SELECTOR_NOT_FOUND", payload


class TestClickFamilyWildcardResolution:
    """The shared click/type/press resolver honors a target-less wildcard host."""

    def test_resolve_selector_target_finds_named_window(self, mock_backend):
        from naturo.cli.interaction._common import _resolve_selector_target

        selector = (
            f'app://*/Window[@name="{NOTEPAD_TITLE}"]/Document[@name="{DOCUMENT_NAME}"]'
        )
        coords = _resolve_selector_target(
            selector, mock_backend, app=None, window_title=None,
            hwnd=None, pid=None, json_output=True,
        )
        # The Document sits at x=10,y=20,w=100,h=40 → center (60, 40).
        assert coords == (60, 40), coords

    def test_resolve_selector_target_negative_control(self, mock_backend):
        """A wildcard host naming a missing element fails honestly (no false match).

        ``_resolve_selector_target`` reports the failure via ``_json_err``, which
        exits non-zero rather than returning — so the across-windows search never
        fabricates a match for an element that is in no window.
        """
        from naturo.cli.interaction._common import _resolve_selector_target

        selector = 'app://*/Window[@name="无标题 - Notepad"]/Document[@name="missing"]'
        with pytest.raises(SystemExit) as exc_info:
            _resolve_selector_target(
                selector, mock_backend, app=None, window_title=None,
                hwnd=None, pid=None, json_output=True,
            )
        assert exc_info.value.code != 0
