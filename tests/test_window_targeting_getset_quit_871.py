"""#871: close the last window-targeting-flag gaps — ``get``/``set`` ``--pid``
and ``app quit`` ``--window``/``--hwnd``.

The window-targeting flag family (``--app``, ``--window``, ``--hwnd``, ``--pid``,
``--app-id``) is the "gold standard" exposed by ``see``/``capture``/``click``.
Sibling modules already harmonised the discovery commands
(:mod:`test_window_targeting_flags_871`) and the ``app`` window-state subgroup
(:mod:`test_app_window_targeting_871`).  This module closes the two rows those
modules explicitly deferred as follow-ups:

* ``get`` / ``set`` — the UIA *value-pattern* path.  ``get_element_value`` /
  ``set_element_value`` target a window by ``hwnd`` and take no ``pid``, so
  ``--pid`` is resolved to a concrete handle in the CLI via the canonical
  ``_resolve_hwnd`` resolver (the same path the app window-state commands use),
  needing no backend method-signature change.
* ``app quit`` — the process-lifecycle path.  ``quit`` terminates a process, so
  a ``--window``/``--hwnd`` target is resolved to its owning PID via the same
  resolver plus the backend window list.

All mock-based, CI-safe (no real desktop / DLL).
"""
from __future__ import annotations

import json
import platform
import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.backends.base import WindowInfo
from naturo.cli import main
from naturo.cli.app_cmd import app_quit

runner = CliRunner()

_get_mod = sys.modules["naturo.cli.values._get"]
_set_mod = sys.modules["naturo.cli.values._set"]


# ── get / set : --pid flag surface ───────────────────────────────────────────

_VALUE_COMMANDS = [["get"], ["set"]]


@pytest.mark.parametrize("cmd_args", _VALUE_COMMANDS)
def test_pid_flag_in_help(cmd_args):
    """``get``/``set`` --help must now advertise ``--pid`` (the last gap in the
    window-targeting family for the value-pattern path)."""
    result = runner.invoke(main, cmd_args + ["--help"])
    assert result.exit_code == 0, result.output
    assert "--pid" in result.output, (
        f"naturo {' '.join(cmd_args)} --help missing --pid:\n{result.output}"
    )


@pytest.mark.parametrize("cmd_args", _VALUE_COMMANDS)
def test_pid_flag_not_rejected(cmd_args):
    """``--pid`` must reach the handler, not abort at the Click layer."""
    result = runner.invoke(main, cmd_args + ["--pid", "4321", "e1"])
    assert "No such option" not in result.output, (
        f"naturo {' '.join(cmd_args)} --pid rejected the flag:\n{result.output}"
    )


@pytest.mark.parametrize("cmd_args", _VALUE_COMMANDS)
def test_full_window_target_family_present(cmd_args):
    """The full gold-standard family (minus --app-id, tracked #522) is exposed."""
    result = runner.invoke(main, cmd_args + ["--help"])
    for flag in ["--app", "--window", "--hwnd", "--pid"]:
        assert flag in result.output, (
            f"naturo {' '.join(cmd_args)} --help missing {flag}:\n{result.output}"
        )


# ── get : --pid resolves to a concrete hwnd ──────────────────────────────────


def _windows_platform_patch(module):
    """Force the module's platform gate to see Windows on non-Windows CI."""
    if platform.system() == "Windows":
        from contextlib import nullcontext
        return nullcontext()
    mock_plat = MagicMock()
    mock_plat.system.return_value = "Windows"
    return patch.object(module, "platform", mock_plat)


def test_get_pid_resolves_to_hwnd_single_element():
    """``get --pid`` resolves the PID to a handle via ``_resolve_hwnd`` and reads
    the element value scoped to that handle."""
    backend = MagicMock()
    backend._resolve_hwnd.return_value = 999
    backend.get_element_value.return_value = {
        "value": "hi", "role": "Edit", "name": "Search",
        "pattern": "ValuePattern", "automation_id": "x",
        "x": 0, "y": 0, "width": 1, "height": 1,
    }
    with patch.object(_get_mod, "_get_backend", return_value=backend), \
            _windows_platform_patch(_get_mod):
        result = runner.invoke(main, ["get", "--pid", "4321", "e1"])
    assert result.exit_code == 0, result.output
    backend._resolve_hwnd.assert_called_once_with(
        app=None, window_title=None, pid=4321
    )
    assert backend.get_element_value.call_args.kwargs["hwnd"] == 999


def test_get_pid_resolves_to_hwnd_all_mode():
    """``get --all --pid`` threads the resolved handle into ``get_element_tree``."""
    backend = MagicMock()
    backend._resolve_hwnd.return_value = 999
    backend.get_element_tree.return_value = None  # no elements → clean exit
    with patch.object(_get_mod, "_get_backend", return_value=backend), \
            _windows_platform_patch(_get_mod):
        result = runner.invoke(
            main, ["get", "--all", "--role", "Button", "--pid", "4321", "-j"]
        )
    backend._resolve_hwnd.assert_called_once_with(
        app=None, window_title=None, pid=4321
    )
    assert backend.get_element_tree.call_args.kwargs["hwnd"] == 999


def test_get_explicit_hwnd_wins_over_pid():
    """An explicit ``--hwnd`` short-circuits PID resolution (most specific wins)."""
    backend = MagicMock()
    backend.get_element_value.return_value = {
        "value": "hi", "role": "Edit", "name": None,
        "pattern": "ValuePattern", "automation_id": None,
        "x": 0, "y": 0, "width": 1, "height": 1,
    }
    with patch.object(_get_mod, "_get_backend", return_value=backend), \
            _windows_platform_patch(_get_mod):
        result = runner.invoke(main, ["get", "--hwnd", "555", "--pid", "4321", "e1"])
    assert result.exit_code == 0, result.output
    backend._resolve_hwnd.assert_not_called()
    assert backend.get_element_value.call_args.kwargs["hwnd"] == 555


def test_get_pid_not_found_exits_nonzero():
    """An unresolvable ``--pid`` surfaces WindowNotFoundError loudly (exit 1)."""
    from naturo.errors import WindowNotFoundError

    backend = MagicMock()
    backend._resolve_hwnd.side_effect = WindowNotFoundError("PID 4321")
    with patch.object(_get_mod, "_get_backend", return_value=backend), \
            _windows_platform_patch(_get_mod):
        result = runner.invoke(main, ["get", "--pid", "4321", "e1"])
    assert result.exit_code != 0
    backend.get_element_value.assert_not_called()


# ── set : --pid resolves to a concrete hwnd ──────────────────────────────────


def _patch_set(backend):
    """Patch set_cmd's backend + ref resolver (identity mode, no cached point)."""
    return (
        patch.object(_set_mod, "_get_backend", return_value=backend),
        patch.object(
            _set_mod, "_resolve_element_identifiers",
            return_value=("aid", "Edit", "Search", None, None),
        ),
        _windows_platform_patch(_set_mod),
    )


def test_set_pid_resolves_to_hwnd():
    """``set --pid`` resolves the PID to a handle and writes the value there."""
    backend = MagicMock()
    backend._resolve_hwnd.return_value = 999
    backend.set_element_value.return_value = True
    p1, p2, p3 = _patch_set(backend)
    with p1, p2, p3:
        result = runner.invoke(main, ["set", "--pid", "4321", "e1", "hello"])
    assert result.exit_code == 0, result.output
    backend._resolve_hwnd.assert_called_once_with(
        app=None, window_title=None, pid=4321
    )
    assert backend.set_element_value.call_args.kwargs["hwnd"] == 999


def test_set_pid_combined_with_window_filter():
    """``--pid`` + ``--window`` narrows the PID match through the resolver."""
    backend = MagicMock()
    backend._resolve_hwnd.return_value = 999
    backend.set_element_value.return_value = True
    p1, p2, p3 = _patch_set(backend)
    with p1, p2, p3:
        result = runner.invoke(
            main, ["set", "--pid", "4321", "--window", "Chat", "e1", "hi"]
        )
    assert result.exit_code == 0, result.output
    backend._resolve_hwnd.assert_called_once_with(
        app=None, window_title="Chat", pid=4321
    )


def test_set_explicit_hwnd_wins_over_pid():
    """An explicit ``--hwnd`` short-circuits PID resolution for ``set`` too."""
    backend = MagicMock()
    backend.set_element_value.return_value = True
    p1, p2, p3 = _patch_set(backend)
    with p1, p2, p3:
        result = runner.invoke(main, ["set", "--hwnd", "555", "--pid", "4321", "e1", "hi"])
    assert result.exit_code == 0, result.output
    backend._resolve_hwnd.assert_not_called()
    assert backend.set_element_value.call_args.kwargs["hwnd"] == 555


# ── app quit : --window / --hwnd resolve to the owning PID ────────────────────


def _make_window(handle, pid, title="Untitled - Notepad"):
    return WindowInfo(
        handle=handle, title=title, process_name="notepad.exe", pid=pid,
        x=0, y=0, width=800, height=600, is_visible=True, is_minimized=False,
    )


@pytest.mark.parametrize("flag", ["--window", "--hwnd"])
def test_quit_window_target_in_help(flag):
    """``app quit --help`` must advertise the window-targeting flags."""
    result = runner.invoke(app_quit, ["--help"])
    assert result.exit_code == 0, result.output
    assert flag in result.output, f"app quit --help missing {flag}:\n{result.output}"


def test_quit_hwnd_resolves_to_owning_pid():
    """``app quit --hwnd`` resolves the handle to its process and quits by PID."""
    backend = MagicMock()
    backend._resolve_hwnd.return_value = 999
    backend.list_windows.return_value = [_make_window(999, 4321)]
    with patch("naturo.backends.base.get_backend", return_value=backend), \
            patch("naturo.process.quit_app") as mock_quit:
        result = runner.invoke(app_quit, ["--hwnd", "999"])
    assert result.exit_code == 0, result.output
    backend._resolve_hwnd.assert_called_once_with(window_title=None, hwnd=999)
    assert mock_quit.call_args.kwargs["pid"] == 4321


def test_quit_window_resolves_to_owning_pid():
    """``app quit --window`` resolves the title to a handle then to its PID."""
    backend = MagicMock()
    backend._resolve_hwnd.return_value = 999
    backend.list_windows.return_value = [_make_window(999, 4321)]
    with patch("naturo.backends.base.get_backend", return_value=backend), \
            patch("naturo.process.quit_app") as mock_quit:
        result = runner.invoke(app_quit, ["--window", "Notepad"])
    assert result.exit_code == 0, result.output
    backend._resolve_hwnd.assert_called_once_with(window_title="Notepad", hwnd=None)
    assert mock_quit.call_args.kwargs["pid"] == 4321


def test_quit_explicit_name_wins_over_window():
    """A positional NAME still wins — no window resolution when a name is given."""
    backend = MagicMock()
    with patch("naturo.backends.base.get_backend", return_value=backend), \
            patch("naturo.process.quit_app") as mock_quit:
        result = runner.invoke(app_quit, ["notepad", "--hwnd", "999"])
    assert result.exit_code == 0, result.output
    backend._resolve_hwnd.assert_not_called()
    assert mock_quit.call_args.kwargs["name"] == "notepad"


def test_quit_window_not_found_exits_nonzero():
    """A window target that matches no window fails loudly (exit 1), not silently."""
    from naturo.errors import WindowNotFoundError

    backend = MagicMock()
    backend._resolve_hwnd.side_effect = WindowNotFoundError("hwnd 999")
    with patch("naturo.backends.base.get_backend", return_value=backend), \
            patch("naturo.process.quit_app") as mock_quit:
        result = runner.invoke(app_quit, ["--hwnd", "999"])
    assert result.exit_code != 0
    mock_quit.assert_not_called()


def test_quit_hwnd_no_matching_pid_exits_nonzero():
    """When the resolved handle owns no listed window, quit errors (no silent no-op)."""
    backend = MagicMock()
    backend._resolve_hwnd.return_value = 999
    backend.list_windows.return_value = [_make_window(111, 4321)]  # different handle
    with patch("naturo.backends.base.get_backend", return_value=backend), \
            patch("naturo.process.quit_app") as mock_quit:
        result = runner.invoke(app_quit, ["--hwnd", "999", "-j"])
    assert result.exit_code != 0
    mock_quit.assert_not_called()
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert payload["error"]["code"] == "WINDOW_NOT_FOUND"
