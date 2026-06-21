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
3. **Action-phase semantic identity (interaction commands).** #884 converged the
   envelope *shape* and #877 fixed the *semantics* for ``get``/``set``, but the
   interaction commands' action-phase catch-alls still flattened a real
   :class:`~naturo.errors.NaturoError` to ``ACTION_ERROR``/``unknown``/
   ``recoverable:false`` — defeating the agent self-correction contract on the
   single most-used command, ``click`` (#1004). This layer drives every
   interaction command (``click``/``type``/``press``/``scroll``/``drag``/``move``)
   with a backend whose action raises an ``ElementNotFoundError`` and asserts the
   envelope keeps the exception's *code* and *category* — not just its shape — so
   a future catch-all that drops ``exc=`` re-flattens here on day one.
4. **Source-of-truth completeness.** Every code in the recovery-hint registry,
   and the base :class:`NaturoError` serializer, must yield the canonical schema —
   so the per-command paths above cannot drift from the contract they target.

The test is pure-Python (no DLL, no desktop, no input injection — every case
fails during parsing or pure validation/lookup), so it runs on every CI lane.
"""

from __future__ import annotations

import json
from typing import Iterator
from unittest.mock import MagicMock

import click
import pytest
from click.testing import CliRunner

from naturo.cli import main, run
from naturo.cli.error_helpers import _RECOVERY_HINTS, json_error
from naturo.errors import ElementNotFoundError, NaturoError, category_for_code

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


# ── 3. action-phase semantic identity (interaction commands, #1004) ──────────

# (argv, backend-action-method) for every interaction command, driven through a
# backend whose action method raises a semantic NaturoError. Coordinate / no-target
# invocations are used so the failure is born in the action call itself — not in
# element resolution — and reaches the command's action-phase catch-all. The
# method name is the single backend call each command makes inside that try block.
_INTERACTION_ACTION_FAILURES = [
    (["click", "--coords", "500", "300"], "click"),
    (["type", "hello"], "type_text"),
    (["press", "enter"], "press_key"),
    (["scroll", "down"], "scroll"),
    (["drag", "--from-coords", "100", "100", "--to-coords", "500", "300"], "drag"),
    (["move", "--coords", "500", "300"], "move_mouse"),
]


@pytest.mark.parametrize(
    "argv,action_method",
    _INTERACTION_ACTION_FAILURES,
    ids=[argv[0] for argv, _ in _INTERACTION_ACTION_FAILURES],
)
def test_interaction_action_error_keeps_semantic_identity(argv, action_method, monkeypatch) -> None:
    """An action-phase ``NaturoError`` keeps its code/category, not just its shape.

    The interaction catch-alls used to flatten a real ``ElementNotFoundError`` to
    ``ACTION_ERROR``/``unknown``/``recoverable:false`` (#1004), so an agent that
    dispatches on ``error.code == "ELEMENT_NOT_FOUND"`` (the #877 contract) got the
    wrong code from the most-used command. With a backend whose action raises that
    error, every interaction command must now surface its *semantic* envelope —
    identical code/category to ``get``/``scroll`` — and stay canonical in shape.
    """
    backend = MagicMock()
    getattr(backend, action_method).side_effect = ElementNotFoundError(_ABSENT_ENTITY)
    # Every interaction command obtains its backend through this one seam, so the
    # patch covers click/type/press/scroll/drag/move (and any future command) alike.
    monkeypatch.setattr(
        "naturo.cli.interaction._common._get_backend",
        lambda *args, **kwargs: backend,
    )

    result = CliRunner().invoke(main, [*argv, "-j"], catch_exceptions=True)

    error = _single_error_object(result.output)
    assert list(error.keys())[:6] == _CANONICAL_KEYS, (
        f"{' '.join(argv)} -j error drifted from the canonical schema: {list(error.keys())}"
    )
    assert error["code"] == "ELEMENT_NOT_FOUND", (
        f"{' '.join(argv)} flattened the semantic error to {error['code']} (#1004 regression)"
    )
    assert error["category"] == "automation", (
        f"{' '.join(argv)} lost the error category: {error['category']}"
    )
    assert error["recoverable"] is True, f"{' '.join(argv)} dropped recoverable=true"
    assert error["suggested_action"], f"{' '.join(argv)} dropped the recovery hint"


@pytest.mark.parametrize(
    "argv,wait_fn",
    [
        (["wait", "--element", "Button:ZZZabsent", "--app", "Notepad", "--timeout", "1"],
         "wait_for_element"),
        (["wait", "--window", "ZZZabsentWindow", "--timeout", "1"], "wait_for_window"),
        (["wait", "--gone", "Dialog:ZZZpresent", "--timeout", "1"], "wait_until_gone"),
    ],
    ids=["element", "window", "gone"],
)
def test_wait_timeout_success_false_is_canonical(argv, wait_fn, monkeypatch) -> None:
    """A ``wait`` predicate *timeout* surfaces the canonical error envelope (#1089).

    ``wait`` returns ``success:false`` on timeout **without raising**, so the
    failure slips past the fast-fail ``json_error`` path that layers 1–2 above
    enumerate (#895 fixed the success shape; this leg pins the failure shape).
    The wait backend and the desktop pre-flight gate are stubbed so the timeout
    is driven deterministically with no desktop and no DLL — the timeout path is
    asserted to attach the same six canonical keys every other failure carries,
    keeping the #895 ``mode``/``wait_time``/``found``/``warnings`` keys intact.
    """
    timeout_result = MagicMock(found=False, wait_time=1.0, warnings=[], element=None)
    monkeypatch.setattr(f"naturo.wait.{wait_fn}", lambda *a, **k: timeout_result)
    monkeypatch.setattr(
        "naturo.cli.core._common._enforce_desktop_session", lambda *a, **k: None
    )

    result = CliRunner().invoke(main, [*argv, "-j"], catch_exceptions=True)

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    # #895 success-shape keys must coexist with the #1089 error block.
    assert {"success", "mode", "wait_time", "found", "warnings"} <= set(payload)
    error = _single_error_object(result.output)
    assert list(error.keys())[:6] == _CANONICAL_KEYS, (
        f"{' '.join(argv)} -j timeout error drifted from the canonical schema: "
        f"{list(error.keys())}"
    )
    assert error["code"] == "TIMEOUT"
    assert error["category"] == "automation"
    assert error["recoverable"] is True
    assert error["suggested_action"]


def test_json_err_preserves_naturoerror_but_falls_back_for_plain_exception(capsys) -> None:
    """``_common._json_err`` is the funnel #1004 fixed — pin both of its branches.

    A ``NaturoError`` passed via ``exc=`` must keep its structured identity even
    when the caller supplies a generic ``code``; a plain exception must fall back
    to that ``code``. Both stay canonical in shape. Pinning the funnel directly
    guards the mechanism even for callsites the command-level parametrization
    above does not enumerate.
    """
    from naturo.cli.interaction import _common

    # NaturoError: identity preserved, generic fallback code ("ACTION_ERROR") ignored.
    with pytest.raises(SystemExit) as semantic_exit:
        _common._json_err("flat message", json_output=True, code="ACTION_ERROR",
                          exc=ElementNotFoundError("x"))
    assert semantic_exit.value.code == 1
    semantic = _single_error_object(capsys.readouterr().out)
    assert list(semantic.keys())[:6] == _CANONICAL_KEYS
    assert semantic["code"] == "ELEMENT_NOT_FOUND"
    assert semantic["category"] == "automation"
    assert semantic["recoverable"] is True

    # Plain exception: falls back to the supplied code, shape still canonical.
    with pytest.raises(SystemExit) as plain_exit:
        _common._json_err("boom", json_output=True, code="ACTION_ERROR",
                          exc=ValueError("boom"))
    assert plain_exit.value.code == 1
    plain = _single_error_object(capsys.readouterr().out)
    assert list(plain.keys()) == _CANONICAL_KEYS
    assert plain["code"] == "ACTION_ERROR"


# ── 4. source-of-truth completeness ──────────────────────────────────────────

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
