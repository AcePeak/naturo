"""Tests for the shared window resolver + landing-window helper (naturo/window.py)."""
from __future__ import annotations

from naturo.window import require_hwnd, window_root_at_point


class FakeBackend:
    def __init__(self):
        self.calls = []

    def _resolve_hwnd(self, **kwargs):
        self.calls.append(kwargs)
        return 4242


def test_require_hwnd_explicit_hwnd_wins_without_touching_backend():
    # object() has no _resolve_hwnd; must not be consulted when hwnd is given.
    assert require_hwnd(object(), hwnd=99) == 99


def test_require_hwnd_foreground_default_when_no_selector():
    assert require_hwnd(object()) == 0


def test_require_hwnd_passes_only_supplied_selectors():
    b = FakeBackend()
    assert require_hwnd(b, app="notepad") == 4242
    assert b.calls[-1] == {"app": "notepad"}
    require_hwnd(b, window_title="Untitled", pid=7)
    assert b.calls[-1] == {"window_title": "Untitled", "pid": 7}


def test_require_hwnd_backend_without_resolver_returns_foreground():
    assert require_hwnd(object(), window_title="X") == 0


def test_window_root_at_point_non_windows_returns_none(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    assert window_root_at_point(10, 20) is None
