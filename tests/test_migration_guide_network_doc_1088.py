"""Never-lie guard for the migration guide's network section (#1088).

``docs/MIGRATION_FROM_RPA_SCRIPTS.md`` previously documented a *Network Request
Interception* API that does not exist in the shipped surface -- a ``naturo
browser listen`` command plus ``page.listen`` / ``page.wait_for_response`` /
``page.collect_responses`` Python methods (the same defect class as the iframe
gap #1082). A user following the guide would invoke commands and call methods
that simply are not there, violating the SOUL.md never-lie contract for our own
documentation.

This module pins the fix and prevents regression. Rather than hard-coding the
allowed strings, it derives the *real* surface at runtime -- the registered
``browser`` subcommands from the Click tree and the public
:class:`~naturo.browser._network.NetworkMonitor` methods -- and asserts the
guide's network section references **only** that real surface, and that the
known-fictional symbols appear nowhere in the guide. If someone re-documents an
unimplemented capability (or renames a real command without updating the guide),
these tests fail.

The tests read only the on-disk Markdown and import pure Python metadata, so
they need no browser/desktop and run on every CI lane.

Relates to #1088. Sibling never-lie doc guard to the #766 equivalence suite.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

from naturo.browser._network import NetworkMonitor
from naturo.cli import main

_GUIDE_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "MIGRATION_FROM_RPA_SCRIPTS.md"
)

# Symbols the guide used to promise that the shipped surface never exposed.
# The implemented network surface observes request *metadata* and intercepts
# (abort / mock); it has no response-*body* streaming API. Re-introducing any of
# these names means the guide is lying again.
_FICTIONAL_SYMBOLS = (
    "browser listen",
    "page.listen",
    "wait_for_response",
    "collect_responses",
)


def _guide_text() -> str:
    """Return the full migration-guide Markdown as text."""
    return _GUIDE_PATH.read_text(encoding="utf-8")


def _network_section() -> str:
    """Return the body of the guide's *Network Request Interception* section.

    Slices from the ``### Network Request Interception`` heading up to the next
    Markdown section boundary (``### `` / ``## `` / a horizontal rule), so the
    assertions are scoped to the section under test rather than the whole guide.

    Returns:
        The section body, or the empty string if the heading is absent.
    """
    text = _guide_text()
    start = text.find("### Network Request Interception")
    assert start != -1, "Network Request Interception section not found in guide"
    rest = text[start + len("### Network Request Interception"):]
    boundary = re.search(r"^(?:### |## |---)", rest, re.MULTILINE)
    return rest[: boundary.start()] if boundary else rest


def _real_browser_subcommands() -> set[str]:
    """Return the set of registered ``naturo browser`` leaf subcommand names."""
    browser_group = main.commands["browser"]
    return set(browser_group.commands.keys())  # type: ignore[attr-defined]


def _real_network_methods() -> set[str]:
    """Return the public method names of :class:`NetworkMonitor`."""
    return {
        name
        for name, _ in inspect.getmembers(NetworkMonitor, predicate=inspect.isfunction)
        if not name.startswith("_")
    }


def test_guide_does_not_document_fictional_network_symbols() -> None:
    """No known-fictional network symbol appears anywhere in the guide."""
    text = _guide_text()
    leaked = [symbol for symbol in _FICTIONAL_SYMBOLS if symbol in text]
    assert not leaked, (
        f"Migration guide documents network API that does not exist: {leaked}. "
        "The shipped surface is `browser requests` / `browser intercept` and "
        "`page.network.*` (no response-body streaming) -- see #1088."
    )


def test_network_section_uses_only_real_browser_commands() -> None:
    """Every ``naturo browser <sub>`` in the section is a registered command."""
    section = _network_section()
    real = _real_browser_subcommands()
    documented = set(re.findall(r"naturo browser (\w[\w-]*)", section))
    unknown = documented - real
    assert not unknown, (
        f"Network section documents non-existent browser subcommand(s): "
        f"{sorted(unknown)}. Registered subcommands: {sorted(real)}."
    )
    # Guard against a vacuous pass if the examples are ever dropped entirely.
    assert {"requests", "intercept"} <= documented, (
        "Network section should demonstrate the real `browser requests` / "
        "`browser intercept` surface."
    )


def test_network_section_uses_only_real_page_network_methods() -> None:
    """Every ``page.network.<method>(`` in the section exists on NetworkMonitor."""
    section = _network_section()
    real = _real_network_methods()
    documented = set(re.findall(r"page\.network\.(\w+)\s*\(", section))
    unknown = documented - real
    assert not unknown, (
        f"Network section documents non-existent NetworkMonitor method(s): "
        f"{sorted(unknown)}. Public methods: {sorted(real)}."
    )
    assert documented, (
        "Network section should show the real `page.network.*` Python API."
    )
