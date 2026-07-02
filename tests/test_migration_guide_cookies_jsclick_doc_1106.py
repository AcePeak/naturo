"""Never-lie guard for the migration guide's cookie + JS-click surfaces (#1106).

``docs/MIGRATION_FROM_RPA_SCRIPTS.md`` documents two browser surfaces that do
not exist in the shipped product (the same defect class as the network gap
#1088 and the iframe gap #1082):

* a ``naturo browser cookies`` command family (``save``/``clear``/``load``/
  ``delete``) plus a ``BrowserPage.cookies`` property, and
* a JS-click fallback -- ``naturo browser click <selector> --js`` and
  ``BrowserElement.click(js=True)``.

A user following the guide would hit ``No such command`` /
``unexpected keyword argument``, violating the SOUL.md never-lie contract for
our own documentation.

The resolution chosen for #1106 (per the orchestrator triage) is to **caveat,
not prune or implement**: deciding whether to ship those public APIs or delete
the claims is Ace's call, so the guide keeps the examples but flags each one as
"not yet implemented". This module pins that contract from both directions:

* It derives the *real* surface at runtime -- the registered ``browser``
  subcommands, ``BrowserPage``'s attributes, and the ``browser click`` /
  ``BrowserElement.click`` signatures -- and asserts the four surfaces are still
  absent. If anyone later *implements* them, these assertions fail, forcing the
  caveats (and this test) to be revisited.
* It asserts that every Markdown region mentioning one of the not-yet-shipped
  surfaces also carries the ``#1106`` "not yet implemented" caveat, so the guide
  can never silently advertise a surface that does not exist.

The tests read only the on-disk Markdown and import pure Python metadata, so
they need no browser/desktop and run on every CI lane.

Relates to #1106. Sibling never-lie doc guard to #1082 / #1088 and the #766
equivalence suite.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

from naturo.browser import BrowserElement, BrowserPage
from naturo.cli import main

_GUIDE_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "MIGRATION_FROM_RPA_SCRIPTS.md"
)

# naturo-specific tokens for the surfaces the guide documents but does not ship.
# These match only the *naturo* CLI/SDK forms, never the Selenium/DrissionPage
# "Before" snippets (e.g. ``ele.click(by_js=True)``), which legitimately
# describe the other tool. ``--js`` is word-bounded so it does not match
# ``--json``.
_FICTIONAL_TOKENS: tuple[re.Pattern[str], ...] = (
    re.compile(r"naturo browser cookies"),
    re.compile(r"page\.cookies"),
    re.compile(r"\.click\(js="),
    re.compile(r"--js\b"),
)

_CAVEAT_REFERENCE = "#1106"


def _guide_text() -> str:
    """Return the full migration-guide Markdown as text."""
    return _GUIDE_PATH.read_text(encoding="utf-8")


def _regions(text: str) -> list[str]:
    """Split the guide into regions at Markdown section boundaries.

    A boundary is a top/second-level heading (``## ``/``### ``) or a horizontal
    rule (``---``). Each returned region is the text from one boundary up to the
    next, so a documented surface and the caveat that immediately follows it in
    the same section land in the same region.

    Args:
        text: The full guide Markdown.

    Returns:
        The list of region bodies in document order.
    """
    boundary = re.compile(r"^(?:#{2,3} |---\s*$)")
    regions: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if boundary.match(line):
            if current:
                regions.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        regions.append("\n".join(current))
    return regions


def _real_browser_subcommands() -> set[str]:
    """Return the set of registered ``naturo browser`` leaf subcommand names."""
    browser_group = main.commands["browser"]
    return set(browser_group.commands.keys())  # type: ignore[attr-defined]


def _click_command_option_names() -> set[str]:
    """Return the long-option strings on the ``naturo browser click`` command."""
    click_command = main.commands["browser"].commands["click"]  # type: ignore[attr-defined]
    return {
        opt
        for param in click_command.params
        for opt in getattr(param, "opts", [])
        if opt.startswith("--")
    }


def test_cookies_surface_is_absent_from_shipped_code() -> None:
    """No ``browser cookies`` command and no ``BrowserPage.cookies`` exist.

    Justifies the guide's "not yet implemented" caveat. If this fails because the
    surface was implemented, drop the #1106 caveat from the guide and retire this
    assertion.
    """
    assert "cookies" not in _real_browser_subcommands(), (
        "A `browser cookies` subcommand now exists -- remove the #1106 "
        "'not yet implemented' caveat from MIGRATION_FROM_RPA_SCRIPTS.md."
    )
    assert not hasattr(BrowserPage, "cookies"), (
        "BrowserPage.cookies now exists -- remove the #1106 caveat from the "
        "migration guide's Cookie Management section."
    )


def test_js_click_surface_is_absent_from_shipped_code() -> None:
    """No ``browser click --js`` option and no ``click(js=...)`` parameter exist.

    Justifies the guide's "not yet implemented" caveat. If this fails because the
    surface was implemented, drop the #1106 caveat from the guide and retire this
    assertion.
    """
    assert "--js" not in _click_command_option_names(), (
        "`browser click --js` now exists -- remove the #1106 caveat from the "
        "migration guide's JavaScript Execution section."
    )
    click_parameters = inspect.signature(BrowserElement.click).parameters
    assert "js" not in click_parameters, (
        "BrowserElement.click now accepts a `js` parameter -- remove the #1106 "
        "caveat from the migration guide."
    )


def test_every_fictional_mention_carries_the_1106_caveat() -> None:
    """Each guide region naming a not-yet-shipped surface references #1106.

    The guide intentionally keeps the cookie/JS-click examples (pruning vs.
    implementing is Ace's call) but must flag every one of them, so the published
    guide never advertises a surface that does not exist without a caveat.
    """
    offending: list[str] = []
    for region in _regions(_guide_text()):
        if any(token.search(region) for token in _FICTIONAL_TOKENS):
            if _CAVEAT_REFERENCE not in region:
                heading = region.splitlines()[0].strip()
                offending.append(heading)
    assert not offending, (
        "Migration-guide region(s) document the not-yet-shipped `browser "
        f"cookies` / `--js` surface without a {_CAVEAT_REFERENCE} caveat: "
        f"{offending}. Add a '🚧 Not yet implemented' note referencing #1106."
    )
