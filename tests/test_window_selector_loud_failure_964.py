"""Loud-failure contract for CLI ``get`` / ``set`` window-selector resolution (#964).

Silent-failure class (same family as #957, fixed for the MCP surface): a command
accepts ``--window <title>``, fails to resolve it, and *silently* falls back to
the foreground window — returning success against whatever happens to be focused.
For ``set`` this writes to the wrong window (data-integrity hazard).

Both surfaces shared the same defect: ``backend._resolve_hwnd`` raises
:class:`~naturo.errors.WindowNotFoundError` on no match, but the call sites
wrapped it in ``except Exception`` and degraded to ``target_hwnd = 0``
(foreground). The fix routes both through the resolver without swallowing, so an
explicitly-provided selector that matches nothing fails loudly with
``WINDOW_NOT_FOUND`` — mirroring the sibling ``capture --window`` and the #957
``require_hwnd`` contract. These tests run cross-platform (no DLL/desktop): the
backend is mocked so its resolver raises exactly as the real one does.

Closes #964.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from naturo.errors import WindowNotFoundError

# A window title guaranteed not to match any real window.
_BOGUS_TITLE = "__no_such_window_zzz_964__"


def test_get_backend_unmatched_window_title_raises_not_foreground():
    """``get_element_value`` must re-raise WindowNotFoundError, never read the
    foreground window when a window_title was given but resolves to nothing."""
    from naturo.backends.windows._element._tree import ElementTreeMixin

    class _Harness(ElementTreeMixin):
        """Minimal ElementTreeMixin host with a resolver that mimics the real
        backend: an unmatched window_title raises WindowNotFoundError."""

        def __init__(self) -> None:
            self._core = MagicMock()
            self._core.list_windows.return_value = []

        def _ensure_core(self):
            return self._core

        def _resolve_hwnd(self, app=None, window_title=None):
            raise WindowNotFoundError(window_title or app or "")

    harness = _Harness()
    with pytest.raises(WindowNotFoundError):
        harness.get_element_value(
            automation_id="AddButton", window_title=_BOGUS_TITLE
        )
    # The foreground value lookup must never be reached on a bogus selector.
    harness._core.get_element_value.assert_not_called()


def _invoke(command, args, backend, monkeypatch, module):
    """Run a CLI *command* with a mocked backend, on a simulated Windows host."""
    monkeypatch.setattr(module, "_get_backend", lambda: backend)
    monkeypatch.setattr(module.platform, "system", lambda: "Windows")
    return CliRunner().invoke(command, args)


def _make_backend():
    backend = MagicMock()
    backend._resolve_hwnd.side_effect = WindowNotFoundError(_BOGUS_TITLE)
    backend._ensure_core.return_value.list_windows.return_value = []
    return backend


def test_cli_set_unmatched_window_fails_loud(monkeypatch):
    """``set --window <unmatched>`` must emit WINDOW_NOT_FOUND, never write to
    the foreground window."""
    import naturo.cli.values._set as set_mod

    backend = _make_backend()
    result = _invoke(
        set_mod.set_cmd,
        ["AddButton", "hello", "--window", _BOGUS_TITLE, "-j"],
        backend,
        monkeypatch,
        set_mod,
    )
    payload = json.loads(result.output)
    assert payload.get("success") is False, (
        f"set fell back to the foreground on a bogus --window: {payload}"
    )
    assert payload.get("error", {}).get("code") == "WINDOW_NOT_FOUND", payload
    backend.set_element_value.assert_not_called()


def test_cli_get_unmatched_window_fails_loud(monkeypatch):
    """``get --window <unmatched>`` must emit WINDOW_NOT_FOUND end-to-end."""
    import naturo.cli.values._get as get_mod

    backend = _make_backend()
    backend.get_element_value.side_effect = WindowNotFoundError(_BOGUS_TITLE)
    result = _invoke(
        get_mod.get_cmd,
        ["AddButton", "--window", _BOGUS_TITLE, "-j"],
        backend,
        monkeypatch,
        get_mod,
    )
    payload = json.loads(result.output)
    assert payload.get("success") is False, payload
    assert payload.get("error", {}).get("code") == "WINDOW_NOT_FOUND", payload
