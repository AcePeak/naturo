"""Regression tests for #1135: ``browser screenshot`` error-code taxonomy.

``naturo browser screenshot`` errored with ``fallback_code="SCREENSHOT_FAILED"``,
but that code was **not** a registered :class:`~naturo.errors.ErrorCode` and had
no ``_RECOVERY_HINTS`` entry, so the envelope silently degraded to
``category: unknown`` / ``recoverable: false`` / no hint — even for a plain
"selector matched no element" condition. That breaks the agent self-correction
contract (an unrecognised code looks like an internal failure rather than a
recoverable not-found).

These tests pin two things:

1. **Registration** — ``SCREENSHOT_FAILED`` is a real ``ErrorCode`` with a
   non-``unknown`` category and a recovery hint, so a genuine capture failure is
   categorised and recoverable.
2. **Error attribution** (dev-cycle rule) — a *missing selector* is reported as
   ``ELEMENT_NOT_FOUND`` (recoverable, automation), distinct from a genuine
   *capture* failure (``SCREENSHOT_FAILED``); the two no longer share one code.

A family-wide sweep also guards against any *other* ``browser`` command emitting
a bare, unregistered ``fallback_code`` string in future.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import click.testing
import pytest

from naturo.browser._page import BrowserElementNotFoundError
from naturo.cli._browser._group import browser
from naturo.cli.error_helpers import _RECOVERY_HINTS
from naturo.errors import ErrorCategory, ErrorCode, category_for_code


def _invoke(args, mock_page):
    runner = click.testing.CliRunner()
    with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page):
        return runner.invoke(browser, args, catch_exceptions=False)


# ── Registration ──────────────────────────────────────────────────────────────


class TestScreenshotFailedRegistered:
    """``SCREENSHOT_FAILED`` must be a first-class, categorised, recoverable code."""

    def test_is_a_registered_error_code(self):
        assert getattr(ErrorCode, "SCREENSHOT_FAILED", None) == "SCREENSHOT_FAILED"

    def test_category_is_not_unknown(self):
        assert category_for_code("SCREENSHOT_FAILED") == ErrorCategory.AUTOMATION

    def test_has_a_recovery_hint(self):
        hint, recoverable = _RECOVERY_HINTS["SCREENSHOT_FAILED"]
        assert hint
        assert recoverable is True


# ── Error attribution at the CLI ──────────────────────────────────────────────


class TestScreenshotErrorAttribution:
    """The ``-j`` error envelope must name the real culprit with a real code."""

    def test_missing_selector_is_element_not_found(self):
        """A selector that matches nothing → recoverable ELEMENT_NOT_FOUND."""
        mock_page = MagicMock()
        mock_page.screenshot.side_effect = BrowserElementNotFoundError(
            "No element found for selector: #ghost"
        )

        result = _invoke(
            ["screenshot", "--selector", "#ghost", "--json"], mock_page
        )

        assert result.exit_code != 0
        payload = json.loads(result.output)
        err = payload["error"]
        assert err["code"] == "ELEMENT_NOT_FOUND"
        assert err["category"] == ErrorCategory.AUTOMATION
        assert err["recoverable"] is True
        assert err["suggested_action"]

    def test_capture_failure_is_screenshot_failed(self):
        """A genuine capture failure → registered SCREENSHOT_FAILED, not 'unknown'."""
        mock_page = MagicMock()
        mock_page.screenshot.side_effect = RuntimeError(
            "Cannot screenshot element '#hidden': it has no rendered layout box"
        )

        result = _invoke(
            ["screenshot", "--selector", "#hidden", "--json"], mock_page
        )

        assert result.exit_code != 0
        payload = json.loads(result.output)
        err = payload["error"]
        assert err["code"] == "SCREENSHOT_FAILED"
        assert err["category"] == ErrorCategory.AUTOMATION
        # No longer 'unknown'/non-recoverable — the contract the issue flagged.
        assert err["category"] != ErrorCategory.UNKNOWN
        assert err["recoverable"] is True
        assert err["suggested_action"]

    def test_selector_and_full_page_is_invalid_input(self):
        """The mutually-exclusive validation error stays INVALID_INPUT."""
        mock_page = MagicMock()
        mock_page.screenshot.side_effect = ValueError(
            "screenshot: 'selector' and 'full_page' are mutually exclusive"
        )

        result = _invoke(
            ["screenshot", "--selector", "#x", "--full-page", "--json"], mock_page
        )

        assert result.exit_code != 0
        assert json.loads(result.output)["error"]["code"] == "INVALID_INPUT"


class TestBrowserElementNotFoundErrorType:
    """The typed not-found error must stay a ``RuntimeError`` for back-compat."""

    def test_is_a_runtime_error_subclass(self):
        # Existing handlers / tests that ``except RuntimeError`` must keep working.
        assert issubclass(BrowserElementNotFoundError, RuntimeError)


# ── Family-wide sweep ─────────────────────────────────────────────────────────


def _registered_codes() -> set[str]:
    return {
        getattr(ErrorCode, name)
        for name in dir(ErrorCode)
        if not name.startswith("_") and isinstance(getattr(ErrorCode, name), str)
    }


def test_no_browser_command_emits_an_unregistered_fallback_code():
    """Every ``fallback_code=`` literal in the browser CLI must be a real code.

    A bare, unregistered code degrades to ``category: unknown`` /
    ``recoverable: false`` (the #1135 defect). This sweep keeps the whole
    ``naturo browser`` family honest, not just ``screenshot``.
    """
    browser_pkg = Path(__file__).resolve().parents[1] / "naturo" / "cli" / "_browser"
    registered = _registered_codes()

    offenders: list[str] = []
    for source in browser_pkg.rglob("*.py"):
        text = source.read_text(encoding="utf-8")
        for code in re.findall(r"""fallback_code\s*=\s*["']([A-Z_]+)["']""", text):
            if code not in registered:
                offenders.append(f"{source.name}: {code}")

    assert not offenders, (
        "Unregistered fallback_code(s) found — register them in "
        f"ErrorCode + _ERROR_CATEGORIES + _RECOVERY_HINTS: {offenders}"
    )
