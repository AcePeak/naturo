"""Exit-code contract for argument/usage validation failures (#897).

POSIX reserves exit code **2** for usage errors ("the caller invoked me
wrong") and exit code 1 for operation failures ("called correctly, operation
failed"). Click's own parser already exits 2 for the errors it catches (unknown
subcommand, missing flag value). naturo's *custom* pre-execution validators —
which reject a missing required positional or a missing required flag — used to
exit 1 with an ``INVALID_INPUT`` envelope, so a scripter's standard
``case $? in 2) usage ;; 1) retry ;; esac`` dispatcher misclassified the most
common authoring mistake (forgot the positional) as a transient op failure and
could infinite-retry.

This module pins BOTH sides of the boundary so the contract can't silently
drift again:

* **Usage class → exit 2** — every command with a custom "specify a
  target / a duration / a name" validator (``type``/``press``/``find``/
  ``wait``/``get``/``set``/``app launch``), plus the two Click-level cases
  (unknown subcommand, missing flag value) that already exit 2.
* **Runtime-invalid *value* → exit 1** — a value supplied but rejected during
  execution (``--wpm 0``, a negative duration, ``--limit 0``, ``--count 0``)
  stays an operation failure.

The JSON envelope ``error.code`` stays ``INVALID_INPUT`` throughout — only the
process exit code changed. Envelope code and exit code are independent.

Pure CLI level: no DLL, no desktop session, no input injection. Every case
fails during pre-execution validation, before any command body acts.

Closes #897.
"""
from __future__ import annotations

import json

import pytest
from click.testing import CliRunner


def _run(argv):
    """Invoke the naturo CLI with *argv* and return the Click result."""
    from naturo.cli import main

    return CliRunner().invoke(main, argv, catch_exceptions=False)


# ── Usage class: missing required positional / flag → exit 2 ─────────────────
# naturo's custom validators (each command invoked with the required arg absent).
_MISSING_ARG_COMMANDS = [
    pytest.param(["type"], id="type-missing-text"),
    pytest.param(["press"], id="press-missing-key"),
    pytest.param(["find"], id="find-missing-query"),
    pytest.param(["wait"], id="wait-missing-duration-or-condition"),
    pytest.param(["get"], id="get-missing-target"),
    pytest.param(["set"], id="set-missing-target"),
    pytest.param(["app", "launch"], id="app-launch-missing-name"),
    pytest.param(["get", "--all"], id="get-all-missing-role-or-name"),
    pytest.param(["set", "e47"], id="set-missing-value-or-action"),
]

# Click's own parser path — already exit 2, pinned here so the whole
# usage-error axis is asserted in one place and can't regress the other way.
_CLICK_USAGE_COMMANDS = [
    pytest.param(["nonexistentcmd"], id="unknown-subcommand"),
    pytest.param(["see", "--app"], id="missing-flag-value"),
]


@pytest.mark.parametrize("argv", _MISSING_ARG_COMMANDS)
def test_missing_arg_exits_2_plain(argv):
    """Each custom missing-arg validator exits 2 (POSIX usage error)."""
    result = _run(argv)
    assert result.exit_code == 2, result.output


@pytest.mark.parametrize("argv", _CLICK_USAGE_COMMANDS)
def test_click_usage_exits_2_plain(argv):
    """Click's own parse-time usage errors exit 2 — the code we align to."""
    result = _run(argv)
    assert result.exit_code == 2, result.output


@pytest.mark.parametrize("argv", _MISSING_ARG_COMMANDS)
def test_missing_arg_json_envelope_and_exit_2(argv):
    """Under -j the envelope stays INVALID_INPUT while the exit code is 2.

    Envelope ``code`` and process exit code are independent (#897): only the
    exit code changed, so a JSON consumer still sees ``INVALID_INPUT``.
    """
    result = _run([*argv, "-j"])
    assert result.exit_code == 2, result.output
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_INPUT"


# ── Runtime-invalid *value* → stays exit 1 ───────────────────────────────────
# Called correctly (the required arg IS present) but the value is out of range;
# this is an operation failure, NOT a usage error, so it stays on exit 1.
_INVALID_VALUE_COMMANDS = [
    pytest.param(["type", "hello", "--wpm", "0"], id="type-wpm-zero"),
    pytest.param(["wait", "--", "-3"], id="wait-negative-duration"),
    pytest.param(["find", "button", "--limit", "0"], id="find-limit-zero"),
    pytest.param(["press", "enter", "--count", "0"], id="press-count-zero"),
]


@pytest.mark.parametrize("argv", _INVALID_VALUE_COMMANDS)
def test_runtime_invalid_value_stays_exit_1(argv):
    """A supplied-but-rejected value is an operation failure → exit 1, not 2."""
    result = _run(argv)
    assert result.exit_code == 1, result.output


@pytest.mark.parametrize("argv", _INVALID_VALUE_COMMANDS)
def test_runtime_invalid_value_json_envelope_and_exit_1(argv):
    """The runtime-invalid-value class keeps INVALID_INPUT + exit 1 under -j.

    The global ``--json`` flag is placed *before* the subcommand so it is never
    swallowed by a ``--`` end-of-options marker (e.g. the negative-duration
    case ``wait -- -3``).
    """
    result = _run(["--json", *argv])
    assert result.exit_code == 1, result.output
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_INPUT"
