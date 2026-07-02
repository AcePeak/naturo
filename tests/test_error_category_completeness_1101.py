"""Every ``ErrorCode`` must map to a real category — contract for #1101.

Background (issue #1101)
------------------------
The ``-j`` error envelope's ``category`` field is resolved for the *raw-code*
path (``json_error(ErrorCode.X, msg)``) via
:func:`naturo.errors.category_for_code`, which looks the code up in the canonical
:data:`naturo.errors._ERROR_CATEGORIES` map and falls back to
:attr:`ErrorCategory.UNKNOWN` for anything missing. Nine of the 34
:class:`ErrorCode` members were absent from that map, so every error raised with
one of them emitted ``"category": "unknown"`` across six whole command families
(``selector``, ``visual``, ``record``, registry ops, ``tray``, ``taskbar``) —
defeating the category field's purpose of grouping related errors for
programmatic agents.

The pre-existing contract test (``test_error_envelope_884.py`` ::
``test_category_for_code_matches_subclass``) only iterates codes that have a
:class:`NaturoError` **subclass** fixing a category, so codes emitted purely by
raw string slipped through. This module closes that gap permanently: it asserts
**every** ``ErrorCode`` member (except the intentionally-unknown
``UNKNOWN_ERROR``) carries a concrete, non-``unknown`` category — so a newly
added code can never silently default to ``unknown`` again.

The test is pure-Python (no DLL, no desktop), so it runs on every CI lane.
"""

from __future__ import annotations

import json

import pytest

from naturo.cli.error_helpers import json_error
from naturo.errors import (
    ErrorCategory,
    ErrorCode,
    _ERROR_CATEGORIES,
    category_for_code,
)


def _error_codes() -> dict[str, str]:
    """Return ``{attribute_name: code_string}`` for every ``ErrorCode`` member."""
    return {
        name: value
        for name, value in vars(ErrorCode).items()
        if name.isupper() and isinstance(value, str)
    }


# ── 1. Completeness: every code maps to a concrete category ──────────────────


def test_every_error_code_has_a_category() -> None:
    """No ``ErrorCode`` (bar ``UNKNOWN_ERROR``) may fall through to ``unknown``.

    This is the permanent drift guard requested by #1101: it fails the moment a
    code is added to :class:`ErrorCode` without a matching
    :data:`_ERROR_CATEGORIES` entry, which is exactly how the original nine codes
    silently degraded to ``category:"unknown"``.
    """
    codes = _error_codes()
    # UNKNOWN_ERROR is the one code whose category is *meant* to be 'unknown'.
    missing = sorted(
        value
        for name, value in codes.items()
        if name != "UNKNOWN_ERROR" and value not in _ERROR_CATEGORIES
    )
    assert missing == [], f"ErrorCode members missing from _ERROR_CATEGORIES: {missing}"


@pytest.mark.parametrize(
    "code_name",
    sorted(name for name in _error_codes() if name != "UNKNOWN_ERROR"),
)
def test_category_for_code_is_never_unknown(code_name: str) -> None:
    """``category_for_code`` returns a concrete category for every real code."""
    code = getattr(ErrorCode, code_name)
    assert category_for_code(code) != ErrorCategory.UNKNOWN


def test_unknown_error_stays_unknown() -> None:
    """``UNKNOWN_ERROR`` is the sole intentional ``unknown`` — pin that intent."""
    assert category_for_code(ErrorCode.UNKNOWN_ERROR) == ErrorCategory.UNKNOWN


# ── 2. The nine previously-broken codes carry their finalized categories ──────

# The exact codes #1101 reported as missing, with the categories chosen to match
# their already-mapped peers (named saved artifacts → session, like snapshots;
# UI-element lookups → automation, like app/window/element; registry → io;
# CANCELLED groups with the other operation-lifecycle outcome, TIMEOUT).
_EXPECTED_CATEGORIES = {
    ErrorCode.SELECTOR_NOT_FOUND: ErrorCategory.SESSION,
    ErrorCode.BASELINE_NOT_FOUND: ErrorCategory.SESSION,
    ErrorCode.RECORDING_NOT_FOUND: ErrorCategory.SESSION,
    ErrorCode.TRAY_ICON_NOT_FOUND: ErrorCategory.AUTOMATION,
    ErrorCode.TASKBAR_ITEM_NOT_FOUND: ErrorCategory.AUTOMATION,
    ErrorCode.REGISTRY_NOT_FOUND: ErrorCategory.IO,
    ErrorCode.REGISTRY_ERROR: ErrorCategory.IO,
    ErrorCode.REGISTRY_HAS_SUBKEYS: ErrorCategory.IO,
    ErrorCode.CANCELLED: ErrorCategory.AUTOMATION,
}


@pytest.mark.parametrize(
    "code,expected",
    sorted(_EXPECTED_CATEGORIES.items()),
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_previously_unmapped_code_has_expected_category(code: str, expected: str) -> None:
    """Each of the nine #1101 codes resolves to its finalized category."""
    assert category_for_code(code) == expected


# ── 3. End-to-end: the raw-code envelope carries the category ────────────────


@pytest.mark.parametrize("code", sorted(_EXPECTED_CATEGORIES))
def test_json_error_envelope_category_is_not_unknown(code: str) -> None:
    """``json_error`` — the path these commands use — emits a real category.

    Mirrors the issue's live repro (``selector load``/``visual delete`` etc.)
    without a desktop: every one of these commands funnels its raw code through
    :func:`json_error`, so asserting the envelope here proves the user-visible
    fix without DLL/UI dependencies.
    """
    payload = json.loads(json_error(code, "artifact not found"))
    assert payload["success"] is False
    assert payload["error"]["code"] == code
    assert payload["error"]["category"] == _EXPECTED_CATEGORIES[code]
    assert payload["error"]["category"] != ErrorCategory.UNKNOWN
