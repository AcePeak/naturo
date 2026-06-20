"""#871: window-targeting flag harmonization for the ``app`` window-state subgroup.

Sibling to :mod:`test_window_targeting_flags_871` (which covers the element/menu
*discovery* commands ``find``/``highlight``/``menu-inspect``).  This module covers
the ``app`` window-state subgroup — ``focus``, ``close``, ``minimize``,
``maximize``, ``restore``, ``move`` — which previously exposed an inconsistent
flag matrix (per QA round 132): ``--app`` was missing from
``minimize``/``maximize``/``restore``/``move`` and ``--pid`` was missing from the
whole subgroup.

The gold standard for these commands is ``{--app, --window, --hwnd, --pid}`` plus
positional NAME (app-id ``aN`` resolves through the positional argument).  Because
the backend window methods accept only ``title``/``hwnd``, ``--pid`` is resolved
to a concrete handle in the CLI via the canonical ``_resolve_hwnd`` resolver —
the same path ``see``/``capture``/``click`` use — so no backend method-signature
change is required.

``app quit`` (process-lifecycle path) and ``get``/``set`` (value-pattern path)
route through different resolution and are tracked as follow-ups on #871.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.app_cmd import (
    app_close,
    app_focus,
    app_maximize,
    app_minimize,
    app_move,
    app_restore,
)

runner = CliRunner()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    # Canonical resolver returns a concrete handle for --pid resolution.
    backend._resolve_hwnd.return_value = 999
    return backend


# Window-state commands harmonised by this change and the backend method each
# delegates to.  ``move`` is exercised separately (it needs --x/--y).
_STATE_COMMANDS = [
    (app_focus, "focus_window"),
    (app_close, "close_window"),
    (app_minimize, "minimize_window"),
    (app_maximize, "maximize_window"),
    (app_restore, "restore_window"),
]
_GOLD_STANDARD_FLAGS = ["--app", "--window", "--hwnd", "--pid"]


@pytest.mark.parametrize("cmd,_backend_method", _STATE_COMMANDS)
@pytest.mark.parametrize("flag", _GOLD_STANDARD_FLAGS)
def test_state_command_help_lists_flag(cmd, _backend_method, flag):
    """Each window-state command's --help must list the full flag set."""
    result = runner.invoke(cmd, ["--help"])
    assert result.exit_code == 0, result.output
    assert flag in result.output, f"{cmd.name} --help missing {flag}:\n{result.output}"


@pytest.mark.parametrize("cmd,_backend_method", _STATE_COMMANDS)
@pytest.mark.parametrize(
    "flag_with_value",
    [["--app", "Notepad"], ["--window", "Untitled"], ["--hwnd", "12345"], ["--pid", "4321"]],
)
def test_state_command_flag_not_rejected(cmd, _backend_method, mock_backend, flag_with_value):
    """No flag may be rejected at the Click layer with 'No such option'."""
    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(cmd, flag_with_value)
    assert "No such option" not in result.output, (
        f"{cmd.name} {' '.join(flag_with_value)} rejected the flag:\n{result.output}"
    )


@pytest.mark.parametrize("cmd,backend_method", _STATE_COMMANDS)
def test_pid_resolves_to_hwnd(cmd, backend_method, mock_backend):
    """--pid is resolved to a concrete hwnd via _resolve_hwnd, then passed on."""
    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(cmd, ["--pid", "4321"])
    assert result.exit_code == 0, result.output
    mock_backend._resolve_hwnd.assert_called_once_with(app=None, window_title=None, pid=4321)
    # ``close`` additionally threads ``force`` — assert the target kwargs only.
    call_kwargs = getattr(mock_backend, backend_method).call_args.kwargs
    assert call_kwargs["title"] is None
    assert call_kwargs["hwnd"] == 999


@pytest.mark.parametrize("cmd,backend_method", _STATE_COMMANDS)
def test_app_flag_targets_by_name(cmd, backend_method, mock_backend):
    """--app is accepted on every window-state command and targets by title."""
    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(cmd, ["--app", "Notepad"])
    assert result.exit_code == 0, result.output
    mock_backend._resolve_hwnd.assert_not_called()
    call_kwargs = getattr(mock_backend, backend_method).call_args.kwargs
    assert call_kwargs["title"] == "Notepad"
    assert call_kwargs["hwnd"] is None


@pytest.mark.parametrize("cmd,backend_method", _STATE_COMMANDS)
def test_pid_not_found_exits_nonzero(cmd, backend_method, mock_backend):
    """An unresolvable --pid surfaces the WindowNotFoundError loudly (exit 1)."""
    from naturo.errors import WindowNotFoundError

    mock_backend._resolve_hwnd.side_effect = WindowNotFoundError("PID 4321")
    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(cmd, ["--pid", "4321"])
    assert result.exit_code != 0
    getattr(mock_backend, backend_method).assert_not_called()


def test_move_accepts_app_and_pid(mock_backend):
    """app move gains --app and --pid alongside its geometry flags."""
    help_result = runner.invoke(app_move, ["--help"])
    assert "--app" in help_result.output
    assert "--pid" in help_result.output

    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(app_move, ["--pid", "4321", "--x", "10", "--y", "20"])
    assert result.exit_code == 0, result.output
    mock_backend._resolve_hwnd.assert_called_once_with(app=None, window_title=None, pid=4321)
    mock_backend.move_window.assert_called_once_with(x=10, y=20, title=None, hwnd=999)


def test_move_app_flag_targets_by_name(mock_backend):
    """app move --app targets by title (parity with the other state commands)."""
    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(app_move, ["--app", "Notepad", "--x", "10", "--y", "20"])
    assert result.exit_code == 0, result.output
    mock_backend.move_window.assert_called_once_with(x=10, y=20, title="Notepad", hwnd=None)


def test_pid_combined_with_window_filter(mock_backend):
    """--pid + --window narrows the PID match through the resolver."""
    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(app_focus, ["--pid", "4321", "--window", "Chat"])
    assert result.exit_code == 0, result.output
    mock_backend._resolve_hwnd.assert_called_once_with(app=None, window_title="Chat", pid=4321)


def test_explicit_hwnd_wins_over_pid(mock_backend):
    """An explicit --hwnd short-circuits PID resolution (most specific wins)."""
    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(app_focus, ["--hwnd", "555", "--pid", "4321"])
    assert result.exit_code == 0, result.output
    mock_backend._resolve_hwnd.assert_not_called()
    mock_backend.focus_window.assert_called_once_with(title=None, hwnd=555)


def test_pid_json_success_envelope(mock_backend):
    """--pid path still emits the standard JSON success envelope."""
    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(app_minimize, ["--pid", "4321", "--json"])
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["action"] == "minimize"
