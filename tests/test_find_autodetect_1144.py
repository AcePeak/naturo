"""Tests for ``naturo find`` strategy auto-detection (feature #1144, part of #809).

The unified find engine is meant to be a *universal locator*: a bare positional
(or ``-q/--query``) value should route to the right strategy from its shape,
without the caller having to spell out ``--image``/``--selector`` (#809 section 4):

| Input shape                       | Strategy            |
|-----------------------------------|---------------------|
| starts with ``app://`` or ``@``   | selector resolution |
| file path ending ``.png``/``.jpg``| image matching      |
| everything else                   | UIA tree search     |

These tests assert the *routing* decision by stubbing the per-strategy helpers
(``_find_with_selector`` / ``_find_with_image``) — so they neither touch the
native core nor a desktop session and run on every CI platform. A couple of
end-to-end cases reuse the selector resolver against an in-memory tree to prove
the auto-detected path produces the same envelope as the explicit flag.

Key invariants pinned here:

* explicit ``--image``/``--selector``/``--ai`` always win over auto-detection;
* an ordinary text/role query (``Save``, ``Button:Save``, ``role:Edit``) is
  never hijacked into the selector/image engines;
* ``-q/--query`` auto-detects identically to the positional argument.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch

from naturo.cli.core import find_cmd
from naturo.cli.core._find import _detect_query_strategy


class TestDetectQueryStrategy:
    """Unit-level coverage of the pure shape classifier."""

    @pytest.mark.parametrize("query", [
        "app://notepad.exe/Button[@name=\"Save\"]",
        "app://chrome.exe/Edit",
        "@save-btn",
        "@notepad/edit-area",
    ])
    def test_selector_shapes(self, query) -> None:
        assert _detect_query_strategy(query) == "selector"

    @pytest.mark.parametrize("query", [
        "button.png",
        "submit.PNG",
        "icon.jpg",
        "shot.jpeg",
        r"C:\images\save.bmp",
        "/tmp/widget.gif",
        "frame.webp",
        "scan.tiff",
    ])
    def test_image_shapes(self, query) -> None:
        assert _detect_query_strategy(query) == "image"

    @pytest.mark.parametrize("query", [
        "Save",
        "Button:Save",
        "role:Edit",
        "the save button",
        "*",
        # A ``//`` shorthand is intentionally NOT auto-detected (only ``app://``
        # and ``@`` are, per the #809 table) — it stays a text query unless the
        # caller passes it via the explicit --selector flag.
        "//Button[@name=\"Save\"]",
        # A name that merely contains a dot but no image extension.
        "v1.2.release",
    ])
    def test_text_shapes_fall_through(self, query) -> None:
        assert _detect_query_strategy(query) is None


@dataclass
class _FakeElement:
    """Minimal backend ``ElementInfo`` stand-in for the selector resolver."""

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
        role="Window", name="Untitled - Notepad", x=0, y=0, width=800, height=600,
        children=[
            _FakeElement(role="Edit", name="Text Editor", id="15",
                         x=10, y=40, width=780, height=520),
            _FakeElement(role="Button", name="Save", x=700, y=8, width=60, height=24),
        ],
    )


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestFindAutoDetectRouting:
    """Bare queries dispatch to the inferred strategy helper."""

    def test_image_path_routes_to_image(self, runner) -> None:
        with patch("naturo.cli.core._find._find_with_image") as image, \
             patch("naturo.cli.core._find._find_with_selector") as selector:
            result = runner.invoke(find_cmd, ["button.png", "--json"])
        assert result.exit_code == 0, result.output
        image.assert_called_once()
        # The detected path becomes the image template; no text query leaks in.
        assert image.call_args.args[0] == "button.png"
        selector.assert_not_called()

    def test_app_uri_routes_to_selector(self, runner) -> None:
        with patch("naturo.cli.core._find._find_with_selector") as selector, \
             patch("naturo.cli.core._find._find_with_image") as image:
            result = runner.invoke(
                find_cmd, ["app://notepad.exe/Button[@name=\"Save\"]", "--json"])
        assert result.exit_code == 0, result.output
        selector.assert_called_once()
        assert selector.call_args.args[0] == "app://notepad.exe/Button[@name=\"Save\"]"
        image.assert_not_called()

    def test_saved_ref_routes_to_selector(self, runner) -> None:
        with patch("naturo.cli.core._find._find_with_selector") as selector:
            result = runner.invoke(find_cmd, ["@save-btn", "--json"])
        assert result.exit_code == 0, result.output
        selector.assert_called_once()
        assert selector.call_args.args[0] == "@save-btn"

    def test_query_option_also_auto_detects(self, runner) -> None:
        with patch("naturo.cli.core._find._find_with_image") as image:
            result = runner.invoke(find_cmd, ["-q", "icon.png", "--json"])
        assert result.exit_code == 0, result.output
        image.assert_called_once()
        assert image.call_args.args[0] == "icon.png"

    def test_text_query_not_hijacked(self, runner) -> None:
        """An ordinary name query must reach the tree-search path, untouched."""
        backend = MagicMock()
        backend.get_element_tree.return_value = None  # short-circuit after routing
        with patch("naturo.cli.core._find._find_with_image") as image, \
             patch("naturo.cli.core._find._find_with_selector") as selector, \
             patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(find_cmd, ["Save", "--json"])
        image.assert_not_called()
        selector.assert_not_called()
        # Reached tree search (which returned None → WINDOW_NOT_FOUND).
        assert json.loads(result.output)["error"]["code"] == "WINDOW_NOT_FOUND"


class TestExplicitFlagsWinOverAutoDetect:
    def test_explicit_selector_with_image_like_value_unaffected(self, runner) -> None:
        """``--selector foo.png`` must still go to the selector engine."""
        with patch("naturo.cli.core._find._find_with_selector") as selector, \
             patch("naturo.cli.core._find._find_with_image") as image:
            result = runner.invoke(find_cmd, ["--selector", "@thing.png", "--json"])
        assert result.exit_code == 0, result.output
        selector.assert_called_once()
        image.assert_not_called()

    def test_ai_flag_suppresses_auto_detect(self, runner) -> None:
        """With --ai, an image-like positional is the AI query, not a template."""
        with patch("naturo.cli.core._find._find_with_ai") as ai_find, \
             patch("naturo.cli.core._find._find_with_image") as image:
            result = runner.invoke(find_cmd, ["button.png", "--ai", "--json"])
        assert result.exit_code == 0, result.output
        ai_find.assert_called_once()
        image.assert_not_called()


class TestAutoDetectEndToEndParity:
    """Auto-detected selector path yields the same envelope as the explicit flag."""

    def test_autodetect_selector_matches_explicit(self, runner) -> None:
        tree = _sample_tree()

        def run(args):
            backend = MagicMock()
            backend.get_element_tree.return_value = tree
            with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
                 patch("naturo.cli.core._common._get_backend", return_value=backend):
                return runner.invoke(find_cmd, args)

        selector = "app://notepad.exe/Button[@name=\"Save\"]"
        explicit = run(["--selector", selector, "--json"])
        auto = run([selector, "--json"])
        assert explicit.exit_code == 0 and auto.exit_code == 0, (
            explicit.output, auto.output)
        assert json.loads(explicit.output)["elements"] == \
            json.loads(auto.output)["elements"]
