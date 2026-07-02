"""Never-lie guard for the migration guide's browser *timeout unit* (#1115).

``docs/MIGRATION_FROM_RPA_SCRIPTS.md`` passed naturo browser timeouts in
**milliseconds** (e.g. ``--timeout 10000``, ``timeout=30000``), but every
shipped naturo browser timeout is in **seconds**:

* CLI -- ``naturo browser wait`` / ``wait-navigation`` / ``wait-url`` /
  ``wait-function`` / ``wait-network-idle`` all declare ``--timeout`` as
  ``type=float, default=30.0, help="Timeout in seconds"``
  (``naturo/cli/_browser/waits.py``).
* SDK -- ``BrowserPage.wait_for`` / ``wait_for_url`` / ``wait_for_function`` /
  ``wait_for_network_idle`` / ``wait_for_download`` all document ``timeout`` as
  "Max wait time in **seconds**" (``naturo/browser/_page.py``).

So a user copying ``naturo browser wait ".results" --timeout 10000`` would wait
**10000 seconds (~2.8h)**, not 10s -- the example does not do what it appears to
(SOUL.md "Never Lie"). Same never-lie doc class as the wait-surface gap #1112,
the cookie/JS-click gap #1106, the network gap #1088, and the iframe gap #1082.

Unlike #1106 (caveat-not-prune, because shipping those APIs is Ace's call), this
is a pure doc error: the unit is already *seconds* in shipped code, so the
resolution is to *fix the guide to match shipped reality* (ms -> s). This module
pins that contract from both directions:

* It derives the *real* unit at runtime -- the ``browser wait`` ``--timeout``
  help string and the ``BrowserPage`` wait-method docstrings -- and asserts the
  shipped surface declares *seconds*. If the unit ever drifts to milliseconds,
  these assertions fire so the guide is revisited.
* It scans the guide and asserts no naturo ``--timeout``/``timeout=`` literal is
  an implausibly large value (>= 1000). Every legitimate naturo example waits a
  handful of seconds (<= 60); the only ">= 1000" values were the ms bug. The
  Selenium / DrissionPage "Before" snippets legitimately use ``timeout=`` too,
  but always with small values (``timeout=0.5`` / ``10`` / ``30``), so the
  >= 1000 threshold matches only the naturo ms regressions and never the
  "Before" tool's own seconds-based calls.

The tests read only the on-disk Markdown and import pure Python metadata, so
they need no browser/desktop and run on every CI lane.

Relates to #1115. Sibling never-lie doc guard to #1082 / #1088 / #1106 / #1112
and the #766 equivalence suite (``test_wait_state_equivalence``).
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

# Any naturo timeout literal >= this value (in the guide's nominal "seconds"
# unit) is an implausible wait (~17 min .. hours) and is therefore a leftover
# millisecond value. Every faithful naturo example waits <= 60 s; the "Before"
# tool snippets use <= 30 s. So this threshold separates the ms bug from every
# legitimate timeout without touching the "Before" snippets.
_IMPLAUSIBLE_TIMEOUT_SECONDS = 1000

# CLI form ``--timeout <N>`` (naturo only -- the "Before" snippets are Python,
# never CLI) and SDK keyword form ``timeout=<N>`` (both tools), each capturing
# the leading integer part of the numeric literal.
_TIMEOUT_LITERALS: tuple[re.Pattern[str], ...] = (
    re.compile(r"--timeout\s+(\d+)"),
    re.compile(r"\btimeout=(\d+)"),
)


def _guide_text() -> str:
    """Return the full migration-guide Markdown as text."""
    return _GUIDE_PATH.read_text(encoding="utf-8")


def _wait_timeout_help() -> str:
    """Return the ``--timeout`` help string on ``naturo browser wait``."""
    wait_command = main.commands["browser"].commands["wait"]  # type: ignore[attr-defined]
    for param in wait_command.params:
        if "--timeout" in getattr(param, "opts", []):
            return param.help or ""
    raise AssertionError(
        "`naturo browser wait` no longer exposes a --timeout option — the "
        "migration guide documents it."
    )


def test_real_timeout_unit_is_seconds_cli() -> None:
    """The shipped ``browser wait --timeout`` declares *seconds*, as the guide claims.

    If the CLI ever re-defined ``--timeout`` in milliseconds, this fires so the
    guide's timeout values are revisited rather than silently lying again.
    """
    help_text = _wait_timeout_help().lower()
    assert "second" in help_text, (
        "`naturo browser wait --timeout` help no longer says 'seconds' "
        f"(got: {help_text!r}) — the migration guide passes its timeouts in "
        "seconds; revisit the guide if the unit changed."
    )
    assert "millisecond" not in help_text and " ms" not in help_text, (
        "`naturo browser wait --timeout` now documents milliseconds — the "
        "migration guide uses seconds; revisit the guide and this guard."
    )


def test_real_timeout_unit_is_seconds_sdk() -> None:
    """The shipped ``BrowserPage`` wait methods document ``timeout`` in *seconds*."""
    for method_name in (
        "wait_for",
        "wait_for_url",
        "wait_for_function",
        "wait_for_network_idle",
    ):
        method = getattr(BrowserPage, method_name, None)
        assert method is not None, (
            f"BrowserPage.{method_name} vanished — the migration guide documents it."
        )
        doc = (inspect.getdoc(method) or "").lower()
        assert "second" in doc, (
            f"BrowserPage.{method_name} docstring no longer documents its timeout "
            "in seconds — the migration guide assumes seconds; revisit both."
        )


def test_guide_has_no_millisecond_timeout_literals() -> None:
    """The migration guide never passes a naturo timeout as a millisecond value.

    Every faithful row is proven end-to-end by
    ``tests/browser/test_migration_equivalence.py``; this guard ensures the
    guide's prose can never reintroduce a millisecond timeout that the shipped
    seconds-based API would silently misinterpret as a multi-hour wait.
    """
    text = _guide_text()
    offending = sorted(
        {
            int(match)
            for pattern in _TIMEOUT_LITERALS
            for match in pattern.findall(text)
            if int(match) >= _IMPLAUSIBLE_TIMEOUT_SECONDS
        }
    )
    assert not offending, (
        "MIGRATION_FROM_RPA_SCRIPTS.md passes naturo timeout(s) as millisecond "
        f"values {offending} — every shipped naturo browser timeout is in "
        "seconds, so these would wait thousands of seconds. Convert them to "
        "seconds (10000 -> 10, 30000 -> 30, 60000 -> 60, etc.)."
    )
