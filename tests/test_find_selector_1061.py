"""Tests for ``naturo find --selector`` path resolution (feature #1061).

The third locator strategy of the unified find engine (#809): resolve an
existing selector path (URI / XML / ``@named`` / ``//`` shorthand) against the
live UI tree and report the matched element(s) as snapshot elements with stable
``eN`` refs — the same contract the text and image strategies emit.

These tests stub ``backend.get_element_tree`` with an in-memory element tree, so
they need neither a desktop session nor the native core DLL and run on every CI
platform.

A cross-command parity test pins the key invariant: ``find --selector`` resolves
a selector to the SAME element the click family's ``_resolve_selector_target``
targets — harmonizing the *accepted* flag is not enough; the *semantics* must
match the gold-standard resolver (lesson of #1058/#1065).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch

from naturo.cli.core import find_cmd


@dataclass
class _FakeElement:
    """Minimal stand-in for a backend ``ElementInfo`` node.

    Carries exactly the attributes ``_elementinfo_to_dict`` reads so the real
    ``SelectorResolver`` runs unchanged.
    """

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
    """A small Notepad-like tree with two buttons and an edit area."""
    return _FakeElement(
        role="Window", name="Untitled - Notepad", x=0, y=0, width=800, height=600,
        children=[
            _FakeElement(role="Edit", name="Text Editor", id="15",
                         x=10, y=40, width=780, height=520),
            _FakeElement(role="Button", name="Save", x=700, y=8, width=60, height=24),
            _FakeElement(role="Button", name="Cancel", x=620, y=8, width=60, height=24),
        ],
    )


def _backend_returning(tree) -> MagicMock:
    backend = MagicMock()
    backend.get_element_tree.return_value = tree
    return backend


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _invoke(runner, backend, args):
    with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
         patch("naturo.cli.core._common._get_backend", return_value=backend):
        return runner.invoke(find_cmd, args)


class TestFindSelectorMutualExclusion:
    def test_selector_and_ai_mutually_exclusive(self, runner) -> None:
        result = runner.invoke(
            find_cmd, ["--selector", "//Button[@name=\"Save\"]", "--ai", "--json"],
        )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INVALID_INPUT"

    def test_selector_and_image_mutually_exclusive(self, runner) -> None:
        # The conflict is detected before any file access, so the (absent) image
        # path need not exist.
        result = runner.invoke(
            find_cmd,
            ["--selector", "//Button[@name=\"Save\"]", "--image", "anything.png", "--json"],
        )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INVALID_INPUT"

    def test_selector_rejects_text_query(self, runner) -> None:
        result = runner.invoke(
            find_cmd, ["Save", "--selector", "//Button[@name=\"Save\"]", "--json"],
        )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INVALID_INPUT"


class TestFindSelectorResolution:
    def test_valid_selector_resolves_to_element(self, runner) -> None:
        backend = _backend_returning(_sample_tree())
        result = _invoke(
            runner, backend,
            ["--selector", "//Button[@name=\"Save\"]", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is True
        assert payload["count"] == 1
        el = payload["elements"][0]
        assert el["role"] == "Button"
        assert el["name"] == "Save"
        assert el["x"] == 700 and el["y"] == 8
        assert el["ref"].startswith("e")

    def test_uri_selector_with_app_resolves(self, runner) -> None:
        backend = _backend_returning(_sample_tree())
        result = _invoke(
            runner, backend,
            ["--selector", "app://notepad.exe/Edit[@automationid=\"15\"]", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["count"] == 1
        assert payload["elements"][0]["role"] == "Edit"

    def test_no_match_returns_selector_not_found(self, runner) -> None:
        backend = _backend_returning(_sample_tree())
        result = _invoke(
            runner, backend,
            ["--selector", "//Button[@name=\"Nonexistent\"]", "--json"],
        )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "SELECTOR_NOT_FOUND"

    def test_all_flag_returns_every_match(self, runner) -> None:
        backend = _backend_returning(_sample_tree())
        result = _invoke(
            runner, backend,
            ["--selector", "//Button", "--all", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["count"] == 2
        names = sorted(e["name"] for e in payload["elements"])
        assert names == ["Cancel", "Save"]

    def test_invalid_selector_syntax_recoverable_error(self, runner) -> None:
        backend = _backend_returning(_sample_tree())
        # "app://" with an empty body is a parse error.
        result = _invoke(runner, backend, ["--selector", "app://", "--json"])
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INVALID_SELECTOR"

    def test_window_not_found(self, runner) -> None:
        backend = _backend_returning(None)
        result = _invoke(
            runner, backend,
            ["--selector", "//Button[@name=\"Save\"]", "--json"],
        )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "WINDOW_NOT_FOUND"

    def test_unresolvable_named_selector(self, runner) -> None:
        backend = _backend_returning(_sample_tree())
        with patch("naturo.cli.selector_cmd.resolve_named_selector",
                   side_effect=KeyError("no such saved selector: @ghost")):
            result = _invoke(runner, backend, ["--selector", "@ghost", "--json"])
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "SELECTOR_REF_ERROR"

    def test_plain_text_output(self, runner) -> None:
        backend = _backend_returning(_sample_tree())
        result = _invoke(runner, backend, ["--selector", "//Button[@name=\"Save\"]"])
        assert result.exit_code == 0, result.output
        assert "Save" in result.output
        assert "Button" in result.output


class TestSelectorCrossCommandParity:
    """``find --selector`` must target the SAME element the click family does."""

    def test_find_selector_matches_click_resolution(self, runner) -> None:
        from naturo.cli.interaction._common import _resolve_selector_target

        selector = "//Button[@name=\"Save\"]"
        tree = _sample_tree()

        # Gold standard: what the click family would target.
        click_backend = _backend_returning(tree)
        click_xy = _resolve_selector_target(
            selector, click_backend, None, None, None, None, json_output=True,
        )
        assert click_xy is not None

        # find --selector must land on the same element's center.
        find_backend = _backend_returning(tree)
        result = _invoke(runner, find_backend, ["--selector", selector, "--json"])
        assert result.exit_code == 0, result.output
        el = json.loads(result.output)["elements"][0]
        find_xy = (el["x"] + el["width"] // 2, el["y"] + el["height"] // 2)
        assert find_xy == click_xy
