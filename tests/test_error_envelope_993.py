"""Contract for the ``-j`` *error* envelope of record / selector / visual.

Background (issue #993)
-----------------------
The success-envelope contract (#979, ``test_json_envelope_contract``) pins the
shape of ``-j`` *success* output for collection reads. It says nothing about the
*error* output, and QA found that the ``record`` / ``selector`` / ``visual``
command families had each hand-rolled their ``-j`` failure payload::

    json.dumps({"success": False, "error": "<message string>"})   # bare string
    json.dumps({"success": deleted, "name": name})                # no error at all

A bare-string ``error`` breaks every scripted caller that does
``resp["error"]["code"]`` (the shape the rest of the CLI emits via
:func:`naturo.cli.error_helpers.json_error`), and ``visual delete`` of a missing
baseline carried *no* diagnostic at all.

This module is the structural guard for the error side: it drives each affected
command into its failure path against an isolated, empty on-disk store (no DLL,
no desktop, no Pillow) and asserts the canonical envelope
``{"success": False, "error": {"code", "message", ...}}`` — so the error shape
can no longer drift back to a bare string or vanish entirely.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Iterator

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.errors import ErrorCode


@pytest.fixture()
def isolated_stores(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point every file-backed store at a fresh, empty temp directory.

    Uses :func:`tempfile.mkdtemp` rather than the ``tmp_path`` fixture because the
    shared pytest temp base on the agent host is contended by concurrent loop
    cycles and intermittently raises ``WinError 5`` (mirrors the note in
    ``test_json_envelope_contract``). An empty store guarantees every lookup below
    misses, so each command takes its not-found branch deterministically.
    """
    root = Path(tempfile.mkdtemp(prefix="naturo-error-envelope-993-"))
    import naturo.cli.selector_cmd as selector_cmd
    import naturo.recording as recording
    import naturo.visual as visual

    monkeypatch.setattr(selector_cmd, "SELECTORS_DIR", root / "selectors")
    monkeypatch.setattr(recording, "RECORDINGS_DIR", root / "recordings")
    monkeypatch.setattr(visual, "BASELINES_DIR", root / "baselines")
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _run(args: list[str]) -> dict:
    """Invoke the CLI with ``-j`` and return the parsed JSON payload."""
    result = CliRunner().invoke(main, [*args, "-j"])
    assert result.exit_code != 0, f"expected failure, got success: {result.output!r}"
    return json.loads(result.output)


def _assert_canonical_error(payload: dict, expected_code: str) -> None:
    """Assert ``payload`` is exactly the canonical failure envelope."""
    assert payload["success"] is False
    error = payload.get("error")
    assert isinstance(error, dict), f"error must be an object, got {type(error).__name__}: {error!r}"
    assert error.get("code") == expected_code, f"unexpected code: {error.get('code')!r}"
    assert isinstance(error.get("message"), str) and error["message"], "message must be a non-empty string"


# ── record: missing recording → RECORDING_NOT_FOUND ───────────────────────────

@pytest.mark.parametrize(
    "args",
    [
        ["record", "play", "rec_zzz_nonexistent"],
        ["record", "show", "rec_zzz_nonexistent"],
        ["record", "delete", "rec_zzz_nonexistent", "--force"],
        ["record", "export", "rec_zzz_nonexistent"],
    ],
    ids=lambda a: " ".join(a),
)
def test_record_missing_emits_canonical_error(args: list[str], isolated_stores: Path) -> None:
    _assert_canonical_error(_run(args), ErrorCode.RECORDING_NOT_FOUND)


# ── selector: missing selector → SELECTOR_NOT_FOUND ───────────────────────────

@pytest.mark.parametrize(
    "args",
    [
        ["selector", "load", "zzz_app", "zzz_key"],
        ["selector", "show", "zzz_app"],
        ["selector", "test", "zzz_app", "zzz_key"],
        ["selector", "delete", "zzz_app", "zzz_key", "--force"],
        ["selector", "clear", "zzz_app", "--force"],
        ["selector", "export", "zzz_app"],
    ],
    ids=lambda a: " ".join(a),
)
def test_selector_missing_emits_canonical_error(args: list[str], isolated_stores: Path) -> None:
    _assert_canonical_error(_run(args), ErrorCode.SELECTOR_NOT_FOUND)


# ── visual delete: missing baseline → BASELINE_NOT_FOUND (was: no error field) ─

def test_visual_delete_missing_emits_error(isolated_stores: Path) -> None:
    """Regression for the ``visual delete`` path that dropped the error entirely."""
    payload = _run(["visual", "delete", "zzz_nonexistent_baseline", "--force"])
    _assert_canonical_error(payload, ErrorCode.BASELINE_NOT_FOUND)


# ── visual compare: classify the exception paths ──────────────────────────────

def _dummy_image(root: Path) -> str:
    img = root / "current.png"
    img.write_bytes(b"not-a-real-image")  # underlying compare is mocked, contents unused
    return str(img)


def test_visual_compare_missing_baseline_emits_canonical_error(
    isolated_stores: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing baseline (``FileNotFoundError``) maps to ``BASELINE_NOT_FOUND``."""
    import naturo.cli.visual_cmd as visual_cmd

    def _raise(*args: object, **kwargs: object) -> object:
        raise FileNotFoundError("Baseline not found: zzz")

    monkeypatch.setattr(visual_cmd, "compare_with_baseline", _raise)
    payload = _run(["visual", "compare", "zzz", "--current", _dummy_image(isolated_stores)])
    _assert_canonical_error(payload, ErrorCode.BASELINE_NOT_FOUND)


def test_visual_compare_missing_dependency_emits_canonical_error(
    isolated_stores: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing optional dep (``ImportError``) maps to ``DEPENDENCY_MISSING``."""
    import naturo.cli.visual_cmd as visual_cmd

    def _raise(*args: object, **kwargs: object) -> object:
        raise ImportError("Pillow is required for visual comparison")

    monkeypatch.setattr(visual_cmd, "compare_with_baseline", _raise)
    payload = _run(["visual", "compare", "zzz", "--current", _dummy_image(isolated_stores)])
    _assert_canonical_error(payload, ErrorCode.DEPENDENCY_MISSING)
