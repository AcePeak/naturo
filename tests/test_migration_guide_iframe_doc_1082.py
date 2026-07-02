"""Never-lie guard for the migration guide's iframe section (#1082).

``docs/MIGRATION_FROM_RPA_SCRIPTS.md`` -> "iframe Handling" previously documented
a browser-frame API that does not exist in the shipped surface:

* a stateful ``naturo browser frame <selector>`` / ``naturo browser frame --top``
  CLI (the real surface is the stateless ``frames`` / ``frame-find`` /
  ``frame-eval`` trio -- each addresses its target frame by argument), and
* Python ``page.in_frame(...)`` context manager plus a
  ``page.find(..., all_frames=True)`` parameter.

Neither ``BrowserPage.in_frame`` nor an ``all_frames`` find parameter exists; the
shipped API is the scoped-frame object ``page.frame(selector=/name=/url=)`` ->
:class:`~naturo.browser._frame.BrowserFrame` (with ``find`` / ``find_all`` /
``evaluate`` and a nested ``.frame()`` chain). A reader copying the old snippets
got ``AttributeError`` / ``TypeError`` / "no such command", violating the
SOUL.md never-lie contract for our own documentation.

This module pins the fix and prevents regression. Rather than hard-coding the
allowed strings, it derives the *real* surface at runtime -- the registered
``browser`` subcommands from the Click tree and the public
:class:`~naturo.browser._page.BrowserPage` methods -- and asserts the guide's
iframe section references **only** that real surface, and that the
known-fictional symbols appear nowhere in the guide.

The tests read only the on-disk Markdown and import pure Python metadata, so they
need no browser/desktop and run on every CI lane.

Relates to #1082. Sibling never-lie doc guard to the #1088 network-section suite.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

from naturo.browser._page import BrowserPage
from naturo.cli import main

_GUIDE_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "MIGRATION_FROM_RPA_SCRIPTS.md"
)

# Symbols the guide used to promise that the shipped surface never exposed.
# Re-introducing any of these names means the guide is lying again. The bare
# ``naturo browser frame`` command (not the real ``frame-find`` / ``frame-eval`` /
# ``frames``) is matched separately below because it is a substring of the real
# names.
_FICTIONAL_SYMBOLS = (
    "in_frame",
    "all_frames",
    "frame --top",
)

# A bare ``naturo browser frame`` invocation -- ``frame`` NOT followed by ``-``
# (frame-find / frame-eval) or ``s`` (frames) or another word character.
_BARE_FRAME_CMD = re.compile(r"naturo browser frame(?![-\w])")


def _guide_text() -> str:
    """Return the full migration-guide Markdown as text."""
    return _GUIDE_PATH.read_text(encoding="utf-8")


def _iframe_section() -> str:
    """Return the body of the guide's *iframe Handling* section.

    Slices from the ``### iframe Handling`` heading up to the next Markdown
    section boundary (``### `` / ``## `` / a horizontal rule), so the assertions
    are scoped to the section under test rather than the whole guide.

    Returns:
        The section body (heading excluded).
    """
    text = _guide_text()
    start = text.find("### iframe Handling")
    assert start != -1, "iframe Handling section not found in guide"
    rest = text[start + len("### iframe Handling"):]
    boundary = re.search(r"^(?:### |## |---)", rest, re.MULTILINE)
    return rest[: boundary.start()] if boundary else rest


def _real_browser_subcommands() -> set[str]:
    """Return the set of registered ``naturo browser`` leaf subcommand names."""
    browser_group = main.commands["browser"]
    return set(browser_group.commands.keys())  # type: ignore[attr-defined]


def _real_page_methods() -> set[str]:
    """Return the public method names of :class:`BrowserPage`."""
    return {
        name
        for name, _ in inspect.getmembers(BrowserPage, predicate=inspect.isfunction)
        if not name.startswith("_")
    }


def test_guide_does_not_document_fictional_iframe_symbols() -> None:
    """No known-fictional iframe symbol appears anywhere in the guide."""
    text = _guide_text()
    leaked = [symbol for symbol in _FICTIONAL_SYMBOLS if symbol in text]
    if _BARE_FRAME_CMD.search(text):
        leaked.append("naturo browser frame <...>")
    assert not leaked, (
        f"Migration guide documents an iframe API that does not exist: {leaked}. "
        "The shipped surface is `browser frames` / `browser frame-find` / "
        "`browser frame-eval` and `page.frame(selector=/name=/url=)` -> "
        "BrowserFrame -- see #1082."
    )


def test_iframe_section_uses_only_real_browser_commands() -> None:
    """Every ``naturo browser <sub>`` in the section is a registered command."""
    section = _iframe_section()
    real = _real_browser_subcommands()
    documented = set(re.findall(r"naturo browser ([\w-]+)", section))
    unknown = documented - real
    assert not unknown, (
        f"iframe section documents non-existent browser subcommand(s): "
        f"{sorted(unknown)}. Registered subcommands: {sorted(real)}."
    )
    # Guard against a vacuous pass if the examples are ever dropped entirely.
    assert "frame-find" in documented, (
        "iframe section should demonstrate the real `browser frame-find` surface."
    )


def test_iframe_section_uses_only_real_page_methods() -> None:
    """Every ``page.<method>(`` in the section exists on BrowserPage."""
    section = _iframe_section()
    real = _real_page_methods()
    documented = set(re.findall(r"page\.(\w+)\s*\(", section))
    unknown = documented - real
    assert not unknown, (
        f"iframe section documents non-existent BrowserPage method(s): "
        f"{sorted(unknown)}. Public methods: {sorted(real)}."
    )
    assert "frame" in documented, (
        "iframe section should show the real `page.frame(...)` Python API."
    )
