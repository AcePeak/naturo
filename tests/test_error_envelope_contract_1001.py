"""Self-maintaining contract for the ``-j`` ERROR envelope (issue #1001).

Background
----------
The ``-j`` **error** envelope kept drifting across commands, one family at a
time — shape A (rich, 6 keys), shape B (flat, 3), shape C (minimal, 2), shape D
(a bare ``error`` *string*), and the ``wait`` family with no ``error`` field at
all. Each drift was found reactively by QA and fixed per-command (#993, #877,
#991), then converged onto a single serializer by #884 / #1002: every ``-j``
error now funnels through :func:`naturo.cli.error_helpers.json_error` (raw-code
path) or :meth:`naturo.errors.NaturoError.to_json_response` (exception path),
both emitting the same six canonical keys, in order::

    code, message, category, context, suggested_action, recoverable

#884 fixed the *instances*. This module is the *enforcement layer* that makes a
future re-drift unmergeable — the same role :mod:`test_json_envelope_contract`
(#979) and :mod:`test_json_stdout_purity_contract` (#987) play for the *success*
envelope. It walks the live Click command tree so a newly-added command is
covered automatically, with no per-command opt-in.

Three layers, by where an error can be born:

1. **Parse-stage usage errors (full tree).** Every leaf command is driven through
   the real console-script entrypoint :func:`naturo.cli.run` with an unknown
   option. Click rejects it during argument parsing — *before* any command body
   runs — so the trigger is uniform, side-effect-free, desktop-free, and
   deterministic on every CI lane. The wrapper must emit exactly the canonical
   envelope (exit 1). This is the auto-enumerating guard: a new command, or a new
   subgroup that prints Click's banner instead of JSON, fails here on day one.
2. **Runtime callback errors (representative families).** A curated set of
   failures that reach the command body and surface through ``json_error`` —
   validation rejections and not-found lookups across the families that
   historically drifted (``app``/``see``/``find``/``get``/``set``/``click``/
   ``type``/``drag``/``record``/``selector``/``visual``). Proves the runtime path,
   not just the parse wrapper, stays canonical.
3. **Source-of-truth completeness.** Every code in the recovery-hint registry,
   and the base :class:`NaturoError` serializer, must yield the canonical schema —
   so the per-command paths above cannot drift from the contract they target.

The test is pure-Python (no DLL, no desktop, no input injection — every case
fails during parsing or pure validation/lookup), so it runs on every CI lane.
"""

from __future__ import annotations

import json
from typing import Iterator

import click
import pytest
from click.testing import CliRunner

from naturo.cli import main, run
from naturo.cli.error_helpers import _RECOVERY_HINTS, json_error
from naturo.errors import NaturoError, category_for_code

# The six canonical keys, in canonical order — identical to NaturoError.to_dict()
# and the object json_error builds. The single shape every -j error must carry.
_CANONICAL_KEYS = ["code", "message", "category", "context", "suggested_action", "recoverable"]

# An option no command defines, so Click raises NoSuchOption at parse time for
# every leaf — a universal failure trigger that never reaches a command body.
_BOGUS_OPTION = "--naturo-error-contract-probe-zzz"

# A name no on-disk store holds, so record/selector/visual lookups miss
# deterministically without needing an isolated store fixture.
_ABSENT_ENTITY = "__naturo_error_contract_absent_entity__"


# ── command-tree discovery ───────────────────────────────────────────────────

def _walk(group: click.Group, prefix: tuple[str, ...] = ()) -> Iterator[tuple[str, ...]]:
    """Yield the path of every leaf command under ``group``."""
    for name, command in group.commands.items():
        path = prefix + (name,)
        if isinstance(command, click.Group):
            yield from _walk(command, path)
        else:
            yield path


_LEAF_COMMANDS: list[tuple[str, ...]] = sorted(_walk(main))

# Commands that must always be present; if the walk stops finding them the
# discovery mechanism itself has broken and the contract would silently cover
# nothing — assert it loudly instead.
_SENTINEL_COMMANDS = [
    ("see",),
    ("click",),
    ("app", "launch"),
    ("record", "show"),
    ("visual", "delete"),
]


# ── helpers ──────────────────────────────────────────────────────────────────

def _drive_entrypoint(monkeypatch, capsys, argv: list[str]) -> tuple[int, str]:
    """Run the real console-script wrapper with *argv*; return ``(exit_code, stdout)``.

    ``click.testing.CliRunner`` invokes the Click group directly and bypasses the
    ``run()`` wrapper that converts parse-time usage errors into the JSON
    envelope, so the parse-stage contract must exercise ``run()`` itself (see
    #872). The wrapper reads ``sys.argv`` and calls ``sys.exit``.
    """
    monkeypatch.setattr("sys.argv", ["naturo", *argv])
    with pytest.raises(SystemExit) as excinfo:
        run()
    code = excinfo.value.code
    return (0 if code is None else int(code)), capsys.readouterr().out


def _single_error_object(stdout: str) -> dict:
    """Parse *stdout* as exactly one JSON error document and return ``error``.

    Asserts the output is a single parseable JSON object (no banner, no second
    document) with ``success: false`` and an ``error`` *object* — the bare-string
    shape D and the missing-field ``wait`` shape both fail here.
    """
    payload = json.loads(stdout)  # raises if not exactly one JSON document
    assert payload.get("success") is False, payload
    error = payload.get("error")
    assert isinstance(error, dict), f"error must be an object, got {type(error).__name__}: {error!r}"
    return error


# ── 0. discovery sanity ──────────────────────────────────────────────────────

def test_command_tree_discovery_is_healthy() -> None:
    """The walk finds the full tree, including every sentinel command."""
    assert len(_LEAF_COMMANDS) >= 100, (
        f"only {len(_LEAF_COMMANDS)} leaf commands discovered — the walk likely "
        f"broke, which would make the error-envelope contract cover almost nothing."
    )
    for sentinel in _SENTINEL_COMMANDS:
        assert sentinel in _LEAF_COMMANDS, (
            f"{' '.join(sentinel)} vanished from the command tree — the discovery "
            f"mechanism (or the command) regressed."
        )


# ── 1. parse-stage usage-error contract (full tree, auto-enumerating) ─────────

@pytest.mark.parametrize(
    "path",
    _LEAF_COMMANDS,
    ids=[" ".join(path) for path in _LEAF_COMMANDS],
)
def test_every_command_usage_error_is_canonical(path, monkeypatch, capsys) -> None:
    """Each leaf command emits the canonical ``-j`` error envelope for a parse error.

    An unknown option fails during Click parsing, so this asserts the wrapper's
    envelope without ever running the command body — uniform across all commands,
    no desktop, no side effects. A new command (or a subgroup that doesn't route
    its parse errors through ``run()``) lands here on day one instead of in QA.
    """
    code, stdout = _drive_entrypoint(monkeypatch, capsys, [*path, "-j", _BOGUS_OPTION])

    assert code == 1, f"{' '.join(path)} -j usage error should exit 1, got {code}"
    error = _single_error_object(stdout)
    # Usage errors carry no extra fields — assert the exact canonical key set.
    assert list(error.keys()) == _CANONICAL_KEYS, (
        f"{' '.join(path)} -j error drifted from the canonical schema: {list(error.keys())}"
    )


# ── 2. runtime callback-error contract (representative families) ──────────────

# (argv, expected_code) for failures that reach the command body and surface via
# json_error. Validation rejections need no desktop; not-found lookups use an
# absent name so they miss on any host. Each was verified to fail in the command
# body (not parsing) and to touch no real UI.
_RUNTIME_FAILURES = [
    (["see", "--depth", "-1", "-j"], "INVALID_INPUT"),
    (["app", "launch", "-j"], "INVALID_INPUT"),
    (["click", "-j"], "INVALID_INPUT"),
    (["find", "-j"], "INVALID_INPUT"),
    (["get", "-j"], "INVALID_INPUT"),
    (["set", "-j"], "INVALID_INPUT"),
    (["type", "--delay", "-9", "-j"], "INVALID_INPUT"),
    (["drag", "-j"], "INVALID_INPUT"),
    (["hotkey", "-j"], "INVALID_INPUT"),
    (["record", "show", _ABSENT_ENTITY, "-j"], "RECORDING_NOT_FOUND"),
    (["selector", "show", _ABSENT_ENTITY, "-j"], "SELECTOR_NOT_FOUND"),
    (["visual", "delete", _ABSENT_ENTITY, "-j"], "BASELINE_NOT_FOUND"),
]


@pytest.mark.parametrize(
    "argv,expected_code",
    _RUNTIME_FAILURES,
    ids=[" ".join(argv) for argv, _ in _RUNTIME_FAILURES],
)
def test_runtime_failure_is_canonical(argv, expected_code) -> None:
    """A representative runtime failure surfaces the canonical error envelope.

    Driven through ``CliRunner`` because these errors are raised inside the
    command body (``json_error``), which the wrapper passes through unchanged.
    The canonical six keys must be present and lead the object; commands may add
    supplementary fields afterwards (e.g. ``visual`` echoes ``name``), so the
    leading-six order is asserted rather than an exact set.
    """
    result = CliRunner().invoke(main, argv, catch_exceptions=True)

    error = _single_error_object(result.output)
    assert list(error.keys())[:6] == _CANONICAL_KEYS, (
        f"{' '.join(argv)} -j error drifted from the canonical schema: {list(error.keys())}"
    )
    assert error["code"] == expected_code, (
        f"{' '.join(argv)} should surface {expected_code}, got {error['code']}"
    )


# ── 3. source-of-truth completeness ──────────────────────────────────────────

def test_naturo_error_serializer_is_canonical() -> None:
    """The base exception serializer pins the canonical schema in one place."""
    error = NaturoError("boom")

    assert list(error.to_dict().keys()) == _CANONICAL_KEYS
    assert list(error.to_json_response()["error"].keys()) == _CANONICAL_KEYS
    assert error.to_json_response()["success"] is False


@pytest.mark.parametrize("code", sorted(_RECOVERY_HINTS))
def test_every_recovery_hint_code_yields_canonical_envelope(code: str) -> None:
    """Every registered raw-code emits the canonical schema with a resolved category.

    The recovery-hint registry is the source of truth for the raw-code error
    path. Pinning the whole registry — not a hand-picked sample — guarantees a
    newly-registered code cannot ship a malformed envelope or an unresolved
    category.
    """
    error = json.loads(json_error(code, "message"))["error"]

    assert list(error.keys()) == _CANONICAL_KEYS, (
        f"json_error({code!r}) drifted from the canonical schema: {list(error.keys())}"
    )
    assert error["code"] == code
    assert error["category"] == category_for_code(code)
    assert isinstance(error["recoverable"], bool)
    assert error["suggested_action"], f"{code} has a registry hint but emitted none"
