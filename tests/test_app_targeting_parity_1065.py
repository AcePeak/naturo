"""#1065: ``app`` window-state ``--app``/NAME must mean *process name*, not title.

The #871 harmonization (#1056) added ``--app``/positional-NAME to the ``app``
window-state subgroup (``focus``/``close``/``minimize``/``maximize``/``restore``/
``move``) but resolved the value as a **window-title** substring only — it never
consulted the process name.  That contradicts the gold-standard commands
(``see``/``capture``/``click``) and ``list windows --app``, whose ``--app``
matches the **process name** via ``backend._resolve_hwnd(app=...)``.  The result
was that ``naturo app focus --app Calculator`` failed for any localized app whose
window title differs from its process name (e.g. Calculator → ``计算器``).

These tests pin the corrected contract: ``--app``/NAME routes through the same
process-aware resolver as the gold-standard commands, while ``--window`` stays a
title-substring selector.  They are hermetic (no real desktop) — the parity bug
lives entirely in the CLI routing helper ``_resolve_window_target``.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli._app._common import _resolve_window_target
from naturo.cli.app_cmd import (
    app_close,
    app_focus,
    app_maximize,
    app_minimize,
    app_move,
    app_restore,
)

runner = CliRunner()

# The window-state commands and the backend method each delegates to.  ``move``
# is exercised separately because it needs geometry flags.
_STATE_COMMANDS = [
    (app_focus, "focus_window"),
    (app_close, "close_window"),
    (app_minimize, "minimize_window"),
    (app_maximize, "maximize_window"),
    (app_restore, "restore_window"),
]


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    # The canonical resolver returns a concrete handle, exactly as the real
    # WindowsBackend._resolve_hwnd does.
    backend._resolve_hwnd.return_value = 4242
    return backend


@pytest.mark.parametrize("cmd,backend_method", _STATE_COMMANDS)
def test_app_flag_routes_through_process_aware_resolver(cmd, backend_method, mock_backend):
    """``--app NAME`` must resolve via ``_resolve_hwnd(app=NAME, ...)`` (process
    name), not be dropped into the backend's ``title=`` kwarg (#1065)."""
    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(cmd, ["--app", "Calculator"])
    assert result.exit_code == 0, result.output
    mock_backend._resolve_hwnd.assert_called_once_with(
        app="Calculator", window_title=None, pid=None
    )
    call_kwargs = getattr(mock_backend, backend_method).call_args.kwargs
    assert call_kwargs["title"] is None
    assert call_kwargs["hwnd"] == 4242


@pytest.mark.parametrize("cmd,backend_method", _STATE_COMMANDS)
def test_positional_name_routes_through_process_aware_resolver(cmd, backend_method, mock_backend):
    """The positional NAME form resolves identically to ``--app`` (#1065)."""
    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(cmd, ["Calculator"])
    assert result.exit_code == 0, result.output
    mock_backend._resolve_hwnd.assert_called_once_with(
        app="Calculator", window_title=None, pid=None
    )


@pytest.mark.parametrize("cmd,backend_method", _STATE_COMMANDS)
def test_window_flag_stays_title_substring(cmd, backend_method, mock_backend):
    """``--window`` alone keeps title-substring semantics — the backend method
    resolves the title itself, so no CLI-layer ``_resolve_hwnd`` call."""
    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(cmd, ["--window", "Untitled"])
    assert result.exit_code == 0, result.output
    mock_backend._resolve_hwnd.assert_not_called()
    call_kwargs = getattr(mock_backend, backend_method).call_args.kwargs
    assert call_kwargs["title"] == "Untitled"
    assert call_kwargs["hwnd"] is None


@pytest.mark.parametrize("cmd,backend_method", _STATE_COMMANDS)
def test_app_not_found_surfaces_window_not_found(cmd, backend_method, mock_backend):
    """An unresolvable ``--app`` surfaces ``WindowNotFoundError`` (exit 1) rather
    than silently substring-matching a wrong window's title."""
    from naturo.errors import WindowNotFoundError

    mock_backend._resolve_hwnd.side_effect = WindowNotFoundError("Calculator")
    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(cmd, ["--app", "Calculator"])
    assert result.exit_code != 0
    getattr(mock_backend, backend_method).assert_not_called()


def test_move_app_flag_routes_through_process_aware_resolver(mock_backend):
    """``app move --app NAME`` resolves by process name like the others (#1065)."""
    with patch("naturo.backends.base.get_backend", return_value=mock_backend):
        result = runner.invoke(app_move, ["--app", "Calculator", "--x", "10", "--y", "20"])
    assert result.exit_code == 0, result.output
    mock_backend._resolve_hwnd.assert_called_once_with(
        app="Calculator", window_title=None, pid=None
    )
    mock_backend.move_window.assert_called_once_with(x=10, y=20, title=None, hwnd=4242)


def test_process_name_match_wins_over_localized_title():
    """End-to-end parity: ``--app`` matches the *process name* even when the
    window TITLE differs (the localized-Calculator trap from #1065).

    Drives a fake ``_resolve_hwnd`` that mimics the real process-name-first
    matching over a window list whose title (``计算器``) shares no substring with
    the app name (``Calculator``).  A title-only resolver (the old bug) would
    raise ``WindowNotFoundError``; the corrected routing finds it by exe name.
    """
    from naturo.errors import WindowNotFoundError

    windows = [
        SimpleNamespace(handle=777, title="计算器", process_name="CalculatorApp.exe", pid=10),
        SimpleNamespace(handle=888, title="Untitled - Notepad", process_name="notepad.exe", pid=20),
    ]

    def fake_resolve_hwnd(app=None, window_title=None, pid=None):
        term = (app or window_title or "").lower()
        for w in windows:
            if app and term in w.process_name.lower():
                return w.handle
        for w in windows:
            if term and term in w.title.lower():
                return w.handle
        raise WindowNotFoundError(term)

    backend = MagicMock()
    backend._resolve_hwnd.side_effect = fake_resolve_hwnd

    with patch("naturo.backends.base.get_backend", return_value=backend):
        result = runner.invoke(app_focus, ["--app", "Calculator", "-j"])
    assert result.exit_code == 0, result.output
    backend.focus_window.assert_called_once_with(title=None, hwnd=777)


# ---------------------------------------------------------------------------
# Direct unit tests for the routing helper.
# ---------------------------------------------------------------------------


def test_resolve_target_name_uses_app_dimension():
    backend = MagicMock()
    backend._resolve_hwnd.return_value = 4242
    kwargs = _resolve_window_target(backend, "Calculator")
    backend._resolve_hwnd.assert_called_once_with(
        app="Calculator", window_title=None, pid=None
    )
    assert kwargs == {"title": None, "hwnd": 4242}


def test_resolve_target_window_only_stays_title():
    backend = MagicMock()
    kwargs = _resolve_window_target(backend, None, window_title="Chat")
    backend._resolve_hwnd.assert_not_called()
    assert kwargs == {"title": "Chat", "hwnd": None}


def test_resolve_target_explicit_hwnd_wins():
    backend = MagicMock()
    kwargs = _resolve_window_target(backend, "Calculator", hwnd=555)
    backend._resolve_hwnd.assert_not_called()
    assert kwargs["hwnd"] == 555


def test_resolve_target_app_and_window_combine():
    backend = MagicMock()
    backend._resolve_hwnd.return_value = 4242
    kwargs = _resolve_window_target(backend, "Calculator", window_title="Chat")
    backend._resolve_hwnd.assert_called_once_with(
        app="Calculator", window_title="Chat", pid=None
    )
    assert kwargs == {"title": None, "hwnd": 4242}
