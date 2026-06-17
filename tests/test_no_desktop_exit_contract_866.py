"""Exit-code contract for runtime NO_DESKTOP_SESSION failures (#866).

A missing interactive desktop is a runtime/environment failure, not a CLI
*usage* error.  It must therefore exit with code 1 and a clean ``Error: ...``
message — never Click's exit-2 ``Usage:`` banner.  The banner is reserved for
genuine argument errors; emitting it for an environment failure misleads the
standard scripting branch ``case $? in 2) usage_error ;; 1) op_failed ;; esac``
into classifying a no-desktop session as a CLI-argument bug.

Before this fix the input/runtime commands ``type``/``press``/``click``/
``drag``/``highlight`` raised :class:`click.UsageError` in their no-desktop
path (``naturo.cli.interaction._common._get_backend`` and the sister
``naturo.cli.core._common._enforce_desktop_session``), exiting 2 with a
``Usage:`` banner, while the read commands ``see``/``list apps`` already
exited 1 cleanly.  This module locks every command onto the same exit-1,
no-banner contract in both plain and ``-j`` mode.

Closes #866.
"""
from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from naturo.errors import NoDesktopSessionError


@pytest.fixture
def no_desktop(monkeypatch):
    """Force the desktop-session pre-flight to fail at both guard sites.

    ``naturo.cli.interaction._common._get_backend`` (input commands) calls the
    module-local ``_check_desktop_session``, while
    ``naturo.cli.core._common._enforce_desktop_session`` imports it from the
    ``naturo.cli.interaction`` package; both names are patched so every command
    under test takes the no-desktop branch regardless of which guard it hits.
    """
    def _raise() -> None:
        raise NoDesktopSessionError()

    monkeypatch.setattr(
        "naturo.cli.interaction._common._check_desktop_session", _raise
    )
    monkeypatch.setattr(
        "naturo.cli.interaction._check_desktop_session", _raise
    )


def _run(argv):
    """Invoke the naturo CLI with *argv* and return the Click result."""
    from naturo.cli import main

    return CliRunner().invoke(main, argv, catch_exceptions=False)


# Input/runtime commands that previously raised UsageError (exit 2 + banner)
# on NO_DESKTOP_SESSION.  Arguments are valid so parsing succeeds and the
# desktop guard is what trips.
_RUNTIME_COMMANDS = [
    pytest.param(["type", "hello", "--app", "notepad"], id="type"),
    pytest.param(["press", "enter", "--app", "notepad"], id="press"),
    pytest.param(["click", "e1", "--app", "notepad"], id="click"),
    pytest.param(["drag", "--from", "e1", "--to", "e2"], id="drag"),
    pytest.param(["highlight"], id="highlight"),
]


@pytest.mark.parametrize("argv", _RUNTIME_COMMANDS)
def test_plain_mode_exits_1_without_usage_banner(no_desktop, argv):
    """Each runtime command exits 1 with a clean message and no Usage banner."""
    result = _run(argv)
    assert result.exit_code == 1, result.output
    assert "Usage:" not in result.output, result.output
    assert "desktop" in result.output.lower(), result.output


@pytest.mark.parametrize("argv", _RUNTIME_COMMANDS)
def test_json_mode_exits_1_with_no_desktop_envelope(no_desktop, argv):
    """The -j path already exits 1; lock it down so the contract stays symmetric."""
    result = _run([*argv, "-j"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload.get("success") is False, payload
    code = payload.get("code") or payload.get("error", {}).get("code")
    assert code == "NO_DESKTOP_SESSION", payload


# Read commands that already satisfied the contract — guard against regression.
_REFERENCE_COMMANDS = [
    pytest.param(["see", "--app", "notepad"], id="see"),
    pytest.param(["list", "apps"], id="list-apps"),
]


@pytest.mark.parametrize("argv", _REFERENCE_COMMANDS)
def test_reference_read_commands_still_exit_1(no_desktop, argv):
    """see / list apps must keep exiting 1 with no Usage banner."""
    result = _run(argv)
    assert result.exit_code == 1, result.output
    assert "Usage:" not in result.output, result.output
