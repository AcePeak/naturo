"""Regression tests for the `find` selector/query contract cluster.

Covers five sibling contract bugs closed together:

* **#1198** — ``find <query> --all`` silently discarded the positional query and
  matched every element as ``success:true``. Now a positional/``-q`` query
  combined with ``--all`` is a conflict → ``INVALID_INPUT`` (never a silent
  match-all).
* **#1201** — ``find <query> -q <other>`` silently dropped the positional query
  (``-q`` won). Same guard: more than one text-query source → ``INVALID_INPUT``.
* **#1169** — ``find --selector //Role`` short-form. A role-only structural
  selector must match by role, and the wildcard-host "any app" search must
  actually enumerate top-level windows instead of only the foreground one.
* **#1195** — the ``find`` element schema diverged by strategy: UIA results
  omitted ``center_x``/``center_y`` and reported ``coordinate_frame: null`` while
  ``--image`` populated both. Now every strategy emits one schema.
* **#1189** — ``SELECTOR_NOT_FOUND`` for a structural ``app://`` / ``//`` path
  suggested the *saved-selector* registry. The hint is now context-aware and
  points a structural selector at tree inspection (``see``).

Hermetic: small UIA-shaped trees behind a mocked backend — no real desktop, so
these run on headless CI.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch

from naturo.backends.base import WindowInfo
from naturo.cli.core import find_cmd


@dataclass
class _FakeElement:
    """Minimal stand-in for a backend ``ElementInfo`` node."""

    role: str
    name: str = ""
    id: str = ""
    value: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    children: list = field(default_factory=list)
    properties: dict = field(default_factory=dict)


def _sample_tree() -> _FakeElement:
    return _FakeElement(
        role="Window", name="Untitled - Notepad", width=800, height=600,
        children=[
            _FakeElement(role="Document", name="Text Editor",
                         x=10, y=40, width=780, height=520),
            _FakeElement(role="Button", name="Save",
                         x=700, y=8, width=60, height=24),
        ],
    )


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _invoke(runner, backend, args):
    with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
         patch("naturo.cli.core._common._get_backend", return_value=backend):
        return runner.invoke(find_cmd, args)


def _backend_returning(tree) -> MagicMock:
    backend = MagicMock()
    backend.get_element_tree.return_value = tree
    return backend


# ── #1198 / #1201 — text-query-source conflict guard ──────────────────────────


class TestTextQuerySourceConflict:
    """More than one text-query source must ERROR, never silently pick one."""

    @pytest.mark.parametrize("args", [
        pytest.param(["Save", "--all", "--json"], id="positional+--all (#1198)"),
        pytest.param(["Save", "-q", "Edit", "--json"], id="positional+-q (#1201)"),
        pytest.param(["-q", "Edit", "--all", "--json"], id="-q+--all (#1201)"),
        pytest.param(["zzNoSuch", "--all", "--json"], id="no-match query+--all"),
    ])
    def test_conflict_errors_invalid_input(self, runner, args):
        backend = _backend_returning(_sample_tree())
        result = _invoke(runner, backend, args)
        assert result.exit_code != 0, result.output
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT", data
        # The query must NOT have been silently dropped into a match-all dump.
        backend.get_element_tree.assert_not_called()

    def test_query_plus_all_does_not_match_all(self, runner):
        """The #1198 footgun: <query> --all must not return every element."""
        backend = _backend_returning(_sample_tree())
        result = _invoke(runner, backend, ["zzNoSuchElementzz", "--all", "--json"])
        data = json.loads(result.output)
        # Old (wrong) behavior: success:true with count == all elements. Now: error.
        assert data["success"] is False, data

    @pytest.mark.parametrize("args", [
        pytest.param(["--all", "--json"], id="--all alone"),
        pytest.param(["Save", "--json"], id="positional alone"),
        pytest.param(["-q", "Save", "--json"], id="-q alone"),
        pytest.param(["--all", "--role", "Button", "--json"], id="--all+--role"),
    ])
    def test_single_source_still_works(self, runner, args):
        """One text source (or --all + a filter) must remain valid."""
        backend = _backend_returning(_sample_tree())
        result = _invoke(runner, backend, args)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True, data


# ── #1195 — one element/envelope schema across strategies ─────────────────────


class TestSchemaParity:
    """UIA find results must carry center_x/center_y and a non-null frame."""

    def test_uia_find_populates_center_and_frame(self, runner):
        backend = _backend_returning(_sample_tree())
        result = _invoke(runner, backend,
                         ["--all", "--role", "Button", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        # Top-level coordinate_frame is populated (was null for UIA).
        assert payload["coordinate_frame"] == "screen", payload
        el = payload["elements"][0]
        # center_x/center_y present (were absent for UIA) and computed from bounds.
        assert "center_x" in el and "center_y" in el, el
        assert el["center_x"] == el["x"] + el["width"] // 2
        assert el["center_y"] == el["y"] + el["height"] // 2

    def test_selector_find_populates_center_and_frame(self, runner):
        backend = _backend_returning(_sample_tree())
        result = _invoke(runner, backend, ["--selector", "//Button", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["coordinate_frame"] == "screen", payload
        el = payload["elements"][0]
        assert "center_x" in el and "center_y" in el, el


# ── #1169 — role-only short-form + desktop-wide "any app" search ──────────────


class TestShortFormRoleOnly:
    """A role-only //Role short-form must resolve like role:Role / app://app/Role."""

    def test_role_only_shortform_matches_scoped(self, runner):
        backend = _backend_returning(_sample_tree())
        result = _invoke(runner, backend,
                         ["--selector", "//Document", "--hwnd", "398624", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is True and payload["count"] == 1, payload
        assert payload["elements"][0]["role"] == "Document", payload


DOC_HWND = 111
OTHER_HWND = 222


class TestShortFormDesktopWide:
    """A bare //Role with NO scope must search across ALL top-level windows."""

    @pytest.fixture
    def desktop_backend(self):
        """Two windows; the target Document lives only in the non-foreground one."""
        doc_tree = _FakeElement(
            role="Window", name="Doc Window", width=800, height=600,
            children=[_FakeElement(role="Document", name="Body",
                                   x=10, y=40, width=780, height=520)],
        )
        other_tree = _FakeElement(
            role="Window", name="Other", width=400, height=300,
            children=[_FakeElement(role="Button", name="OK")],
        )

        def _get_tree(*args, **kwargs):
            hwnd = kwargs.get("hwnd")
            if hwnd == DOC_HWND:
                return doc_tree
            # Foreground / no-hwnd path returns the window WITHOUT the Document,
            # so a pass proves the across-windows enumeration is what resolves it.
            return other_tree

        be = MagicMock()
        be.get_element_tree.side_effect = _get_tree
        be.list_windows.return_value = [
            WindowInfo(handle=OTHER_HWND, title="Other", process_name="other.exe",
                       pid=2, x=0, y=0, width=400, height=300,
                       is_visible=True, is_minimized=False),
            WindowInfo(handle=DOC_HWND, title="Doc Window", process_name="app.exe",
                       pid=1, x=0, y=0, width=800, height=600,
                       is_visible=True, is_minimized=False),
        ]
        return be

    def test_bare_shortform_searches_all_windows(self, runner, desktop_backend):
        result = _invoke(runner, desktop_backend,
                         ["--selector", "//Document", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is True and payload["count"] >= 1, payload
        assert payload["elements"][0]["role"] == "Document", payload
        # The desktop-wide path must actually enumerate windows (not a no-op).
        desktop_backend.list_windows.assert_called()

    def test_bare_shortform_no_match_is_honest(self, runner, desktop_backend):
        """A role present in no window still fails honestly (no false match)."""
        result = _invoke(runner, desktop_backend,
                         ["--selector", "//Slider", "--json"])
        assert result.exit_code != 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is False
        assert payload["error"]["code"] == "SELECTOR_NOT_FOUND", payload


# ── #1189 — context-aware SELECTOR_NOT_FOUND recovery hint ────────────────────


class TestSelectorNotFoundHint:
    """A structural no-match must not point at the saved-selector registry."""

    @pytest.mark.parametrize("selector", [
        '//Button[@name="DoesNotExist_QA_12345"]',
        'app://notepad/Document[@name="DoesNotExist_QA"]',
    ])
    def test_structural_hint_avoids_saved_selectors(self, runner, selector):
        backend = _backend_returning(_sample_tree())
        result = _invoke(runner, backend, ["--selector", selector, "--json"])
        assert result.exit_code != 0, result.output
        payload = json.loads(result.output)
        assert payload["error"]["code"] == "SELECTOR_NOT_FOUND", payload
        action = payload["error"]["suggested_action"] or ""
        # Must NOT misdirect to the saved-selector registry...
        assert "saved selector" not in action.lower(), action
        assert "selector list" not in action.lower(), action
        # ...and SHOULD point at live-tree inspection instead.
        assert "see" in action.lower(), action
