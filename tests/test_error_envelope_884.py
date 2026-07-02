"""Canonical ``-j`` error-envelope contract for #884.

Background (issue #884)
-----------------------
The CLI emitted **three different shapes** for the ``error`` object under ``-j``,
all keyed under ``{success: false, error: {...}}`` but with different field sets
for the very same error code:

* **A (rich, 6)** ``code, message, category, context, suggested_action, recoverable``
  — ``app launch``/``quit``/``focus``/``maximize`` (via :meth:`NaturoError.to_json_response`).
* **B (flat, 3)** ``code, message, suggested_action`` — ``see``/``capture``/``list``/
  ``type``/``press``/``click``/``find`` (via :func:`json_error`).
* **C (minimal, 2)** ``code, message`` — ``get``/``set`` UNKNOWN_ERROR path.

Scripted callers could not rely on ``error.category``, ``error.context`` or
``error.recoverable`` being present and had to fall back to message-string
matching. The fix routes every raw-code error through :func:`json_error`, which
now emits the **full canonical schema unconditionally** — the same six keys, in
the same order, as :meth:`NaturoError.to_json_response`. This module pins that
single shape so a future command cannot silently re-introduce drift.

The test is pure-Python (no DLL, no desktop), so it runs on every CI lane.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.cli.error_helpers import json_error, json_error_from_exception
from naturo.errors import (
    AppNotFoundError,
    DialogNotFoundError,
    ElementNotFoundError,
    ErrorCategory,
    InvalidInputError,
    NaturoError,
    NoDesktopSessionError,
    StaleSnapshotCacheError,
    category_for_code,
)

# The canonical six keys, in canonical order, matching NaturoError.to_dict().
_CANONICAL_KEYS = ["code", "message", "category", "context", "suggested_action", "recoverable"]


def _error_of(raw: str) -> dict:
    """Parse a ``json_error``-style string and return its ``error`` object."""
    payload = json.loads(raw)
    assert payload["success"] is False
    return payload["error"]


# ── 1. json_error always emits the full canonical schema ─────────────────────


def test_json_error_emits_all_canonical_keys_in_order() -> None:
    """A known code emits exactly the six canonical keys, in canonical order."""
    error = _error_of(json_error("WINDOW_NOT_FOUND", "Window not found: Notepad"))

    assert list(error.keys()) == _CANONICAL_KEYS
    assert error["code"] == "WINDOW_NOT_FOUND"
    assert error["category"] == ErrorCategory.AUTOMATION
    assert error["context"] == {}
    assert error["suggested_action"]  # registry hint present
    assert error["recoverable"] is True


def test_json_error_unknown_code_still_emits_all_keys() -> None:
    """An unrecognised code keeps the full shape — no key is dropped.

    This is the heart of #884: the field set must not depend on whether the code
    is known. Unknown codes get ``category='unknown'``, ``context={}``,
    ``suggested_action=None`` and ``recoverable=False`` — every key present.
    """
    error = _error_of(json_error("CUSTOM_ERROR", "Something went wrong"))

    assert list(error.keys()) == _CANONICAL_KEYS
    assert error["category"] == ErrorCategory.UNKNOWN
    assert error["context"] == {}
    assert error["suggested_action"] is None
    assert error["recoverable"] is False


def test_json_error_validation_code_carries_category() -> None:
    """INVALID_INPUT — the most common raw-code error — is categorised."""
    error = _error_of(json_error("INVALID_INPUT", "Bad value"))

    assert error["category"] == ErrorCategory.VALIDATION
    assert error["recoverable"] is False


def test_json_error_explicit_category_and_context_override() -> None:
    """Callers may supply ``category``/``context`` explicitly."""
    error = _error_of(
        json_error(
            "INVALID_INPUT",
            "Bad value",
            category=ErrorCategory.CONFIGURATION,
            context={"parameter": "--depth"},
        )
    )

    assert error["category"] == ErrorCategory.CONFIGURATION
    assert error["context"] == {"parameter": "--depth"}


def test_json_error_extra_fields_supplement_canonical_keys() -> None:
    """``extra`` adds fields on top of — never instead of — the canonical six."""
    error = _error_of(
        json_error("INVALID_INPUT", "Bad value", extra={"valid_range": "1-10"})
    )

    assert set(_CANONICAL_KEYS).issubset(error.keys())
    assert error["valid_range"] == "1-10"


def test_json_error_recoverable_false_is_still_present() -> None:
    """``recoverable=False`` must serialise as a present ``false``, not be omitted."""
    error = _error_of(json_error("WINDOW_NOT_FOUND", "x", recoverable=False))

    assert error["recoverable"] is False
    assert "recoverable" in error


# ── 2. json_error == NaturoError shape (the convergence guarantee) ───────────


def test_json_error_shape_matches_naturo_error_shape() -> None:
    """The raw-code path emits the same key set as the NaturoError path."""
    raw = _error_of(json_error("APP_NOT_FOUND", "Application not found: notepad"))
    rich = AppNotFoundError("notepad").to_dict()

    assert list(raw.keys()) == list(rich.keys()) == _CANONICAL_KEYS


def test_json_error_from_exception_emits_full_canonical_schema() -> None:
    """NaturoError exceptions serialise to the canonical six keys."""
    error = _error_of(json_error_from_exception(StaleSnapshotCacheError("e1")))

    assert list(error.keys()) == _CANONICAL_KEYS
    assert error["code"] == "STALE_SNAPSHOT_CACHE"
    assert error["category"] == ErrorCategory.SESSION
    assert error["context"] == {"ref": "e1"}
    assert error["recoverable"] is True


def test_json_error_from_plain_exception_is_canonical_unknown() -> None:
    """A non-NaturoError exception becomes a full-shape UNKNOWN_ERROR."""
    error = _error_of(json_error_from_exception(ValueError("boom")))

    assert list(error.keys()) == _CANONICAL_KEYS
    assert error["code"] == "UNKNOWN_ERROR"
    assert error["category"] == ErrorCategory.UNKNOWN
    assert error["message"] == "boom"


# ── 3. category_for_code agrees with every NaturoError subclass ──────────────

# Representative instances of every NaturoError subclass that fixes a category.
# Guards against the code→category map drifting away from the subclass that
# defines the authoritative category.
_SUBCLASS_INSTANCES: list[NaturoError] = [
    AppNotFoundError("x"),
    ElementNotFoundError("x"),
    DialogNotFoundError(),
    InvalidInputError(),
    NoDesktopSessionError(),
    StaleSnapshotCacheError("e1"),
]


@pytest.mark.parametrize("exc", _SUBCLASS_INSTANCES, ids=lambda e: type(e).__name__)
def test_category_for_code_matches_subclass(exc: NaturoError) -> None:
    """``category_for_code`` returns the same category the subclass assigns."""
    assert category_for_code(exc.code) == exc.category


def test_category_for_code_unknown_defaults_to_unknown() -> None:
    """An unmapped code degrades gracefully to the 'unknown' category."""
    assert category_for_code("TOTALLY_MADE_UP") == ErrorCategory.UNKNOWN


# ── 4. End-to-end: a real CLI command emits the canonical shape ──────────────


def test_see_invalid_depth_emits_canonical_envelope() -> None:
    """``naturo see -j --depth -1`` fails validation with the canonical shape.

    Pure validation error (``depth`` out of range) — no DLL or desktop needed,
    so this proves the convergence holds through an actual CLI invocation on CI.
    """
    result = CliRunner().invoke(main, ["see", "-j", "--depth", "-1"])

    assert result.exit_code != 0
    error = _error_of(result.output)
    assert list(error.keys()) == _CANONICAL_KEYS
    assert error["code"] == "INVALID_INPUT"
    assert error["category"] == ErrorCategory.VALIDATION
