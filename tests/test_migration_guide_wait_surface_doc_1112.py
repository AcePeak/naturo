"""Never-lie guard for the migration guide's browser *wait* surface (#1112).

``docs/MIGRATION_FROM_RPA_SCRIPTS.md`` documented a waiting surface that does
not exist in the shipped product (the same defect class as the cookie/JS-click
gap #1106, the network gap #1088, and the iframe gap #1082). A user copying the
guide's ``Waiting`` examples would hit ``AttributeError`` / ``TypeError`` /
``No such option``:

* Python SDK -- ``page.wait_for_eval(...)`` (the method is
  ``wait_for_function``), ``page.wait_for_navigation(url_contains=...)`` (URL
  matching is ``wait_for_url(pattern)``; ``wait_for_navigation`` takes no
  ``url_contains``), and ``page.wait_for_network_idle(time=...)`` (the kwarg is
  ``idle_time`` and the unit is *seconds*).
* CLI -- ``naturo browser wait --load`` / ``--dom-ready`` / ``--network-idle``
  / ``--navigate`` / ``--eval`` / ``--url-contains``. The shipped ``wait``
  command has none of those flags; load-waiting lives on
  ``navigate --wait-until``, and the other waits are *separate* subcommands
  (``wait-navigation`` / ``wait-url`` / ``wait-function`` /
  ``wait-network-idle``).

Unlike #1106 (caveat-not-prune, because shipping those APIs is Ace's call),
this is a pure doc error: correcting the names adds and removes no public
surface, so the resolution is to *fix the guide to match shipped reality*. This
module pins that contract from both directions:

* It derives the *real* wait surface at runtime -- ``BrowserPage``'s wait
  methods and their signatures, plus the registered ``browser`` subcommands and
  the ``browser wait`` options -- and asserts the shipped shape is what the
  corrected guide now claims. If the surface ever drifts (a method renamed, a
  flag added), these assertions fire so the guide is revisited.
* It asserts the guide no longer contains any of the fictional wait tokens, so
  the published guide can never re-advertise a wait API that does not exist.

The tests read only the on-disk Markdown and import pure Python metadata, so
they need no browser/desktop and run on every CI lane.

Relates to #1112. Sibling never-lie doc guard to #1082 / #1088 / #1106 and the
#766 equivalence suite (``test_wait_state_equivalence``).
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

from naturo.browser import BrowserPage
from naturo.cli import main

_GUIDE_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "MIGRATION_FROM_RPA_SCRIPTS.md"
)

# naturo-specific tokens for the wait surfaces the guide documented but does not
# ship. Each matches only the *naturo* CLI/SDK form, never the Selenium /
# DrissionPage "Before" snippets (e.g. ``page.wait.doc_loaded()``), which
# legitimately describe the other tool. The ``--network-idle`` / ``--navigate``
# forms use a literal ``wait <space>--`` so they match the fictional flag form
# but never the real ``wait-network-idle`` / ``wait-navigation`` subcommands
# (which use a hyphen, not a space).
_FICTIONAL_TOKENS: tuple[re.Pattern[str], ...] = (
    re.compile(r"wait_for_eval"),
    re.compile(r"wait_for_navigation\([^)]*url_contains"),
    re.compile(r"wait_for_network_idle\([^)]*\btime="),
    re.compile(r"naturo browser wait --load"),
    re.compile(r"naturo browser wait --dom-ready"),
    re.compile(r"naturo browser wait --network-idle"),
    re.compile(r"naturo browser wait --navigate"),
    re.compile(r"naturo browser wait --eval"),
    re.compile(r"--url-contains"),
)


def _guide_text() -> str:
    """Return the full migration-guide Markdown as text."""
    return _GUIDE_PATH.read_text(encoding="utf-8")


def _real_browser_subcommands() -> set[str]:
    """Return the set of registered ``naturo browser`` leaf subcommand names."""
    browser_group = main.commands["browser"]
    return set(browser_group.commands.keys())  # type: ignore[attr-defined]


def _wait_command_option_names() -> set[str]:
    """Return the long-option strings on the ``naturo browser wait`` command."""
    wait_command = main.commands["browser"].commands["wait"]  # type: ignore[attr-defined]
    return {
        opt
        for param in wait_command.params
        for opt in getattr(param, "opts", [])
        if opt.startswith("--")
    }


def test_real_python_wait_surface_matches_corrected_guide() -> None:
    """The shipped ``BrowserPage`` wait methods are what the corrected guide claims.

    Pins the names/signatures the guide was corrected to: ``wait_for_function``,
    ``wait_for_url(pattern)``, and ``wait_for_network_idle(idle_time=...)`` — and
    the absence of the fictional ``wait_for_eval`` / ``wait_for_navigation(
    url_contains=...)`` / ``wait_for_network_idle(time=...)`` forms. If this
    drifts, revisit the guide's Waiting section and the two API-mapping rows.
    """
    assert hasattr(BrowserPage, "wait_for_function"), (
        "BrowserPage.wait_for_function vanished — the migration guide's "
        "Waiting section now claims it."
    )
    assert hasattr(BrowserPage, "wait_for_url"), (
        "BrowserPage.wait_for_url vanished — the guide maps URL waits to it."
    )
    assert not hasattr(BrowserPage, "wait_for_eval"), (
        "BrowserPage.wait_for_eval now exists — it used to be fictional; "
        "update the migration guide and this guard."
    )

    navigation_params = inspect.signature(BrowserPage.wait_for_navigation).parameters
    assert "url_contains" not in navigation_params, (
        "wait_for_navigation now accepts url_contains — the guide was corrected "
        "to use wait_for_url(pattern); revisit the Waiting section."
    )

    idle_params = inspect.signature(BrowserPage.wait_for_network_idle).parameters
    assert "idle_time" in idle_params, (
        "wait_for_network_idle no longer takes idle_time — the guide claims it."
    )
    assert "time" not in idle_params, (
        "wait_for_network_idle now takes a `time` kwarg — the guide was "
        "corrected away from it; revisit the Waiting section."
    )


def test_real_cli_wait_surface_matches_corrected_guide() -> None:
    """The shipped ``browser`` wait subcommands/flags match the corrected guide.

    The guide was corrected to the real separate subcommands
    (``wait-navigation`` / ``wait-url`` / ``wait-function`` /
    ``wait-network-idle``) and to ``navigate --wait-until`` for load waiting; the
    single ``wait`` command exposes none of the fictional lifecycle flags.
    """
    subcommands = _real_browser_subcommands()
    for required in ("wait", "wait-navigation", "wait-url", "wait-function",
                     "wait-network-idle"):
        assert required in subcommands, (
            f"`browser {required}` subcommand is missing — the migration guide "
            "documents it as the shipped wait surface."
        )

    wait_options = _wait_command_option_names()
    for fictional in ("--load", "--dom-ready", "--network-idle", "--navigate",
                      "--eval", "--url-contains"):
        assert fictional not in wait_options, (
            f"`browser wait {fictional}` now exists — it used to be fictional; "
            "update the migration guide's Waiting section and this guard."
        )


def test_guide_has_no_fictional_wait_tokens() -> None:
    """The migration guide no longer advertises any non-existent wait API.

    Every faithful row is proven end-to-end by
    ``tests/browser/test_migration_equivalence.py``; this guard ensures the
    guide's prose can never reintroduce a wait method/flag that the shipped
    product does not provide.
    """
    text = _guide_text()
    offending = sorted(
        token.pattern for token in _FICTIONAL_TOKENS if token.search(text)
    )
    assert not offending, (
        "MIGRATION_FROM_RPA_SCRIPTS.md still documents non-existent wait "
        f"surface(s): {offending}. Correct them to the shipped names "
        "(wait_for_function / wait_for_url / wait_for_network_idle(idle_time=) "
        "and the wait-navigation / wait-url / wait-function / wait-network-idle "
        "subcommands; load-waiting via `navigate --wait-until`)."
    )
