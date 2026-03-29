"""Tests for UWP ApplicationFrameHost fallback in _resolve_hwnd/_resolve_hwnds (#569).

UWP apps (Calculator, Settings, etc.) have their top-level windows owned by
ApplicationFrameHost.exe, not by their actual process.  When --app is used,
process-name matching fails because "calculator" doesn't match
"applicationframehost".  The UWP fallback probes each AFH window's content
child to discover the real app process and match against it.
"""

from naturo.backends.base import WindowInfo
from naturo.backends.windows import WindowsBackend
from naturo.errors import WindowNotFoundError
import pytest


def _make_backend(monkeypatch, windows):
    """Create a WindowsBackend with mocked window list and session helpers."""
    backend = WindowsBackend()
    monkeypatch.setattr(backend, "list_windows", lambda: windows)
    monkeypatch.setattr(backend, "_get_console_session_id", lambda: 1)
    monkeypatch.setattr(backend, "_get_process_session_id", lambda pid: 1)
    monkeypatch.setattr(backend, "_get_foreground_hwnd", lambda: 0)
    monkeypatch.setattr(backend, "_get_window_class_name", lambda h: "")
    return backend


# -- Window fixtures -----------------------------------------------------------

AFH_CALCULATOR = WindowInfo(
    handle=1000,
    title="计算器",
    process_name="ApplicationFrameHost.exe",
    pid=500,
    x=0, y=0, width=400, height=600,
    is_visible=True, is_minimized=False,
)

AFH_SETTINGS = WindowInfo(
    handle=2000,
    title="设置",
    process_name="ApplicationFrameHost.exe",
    pid=501,
    x=0, y=0, width=1000, height=700,
    is_visible=True, is_minimized=False,
)

NOTEPAD_WINDOW = WindowInfo(
    handle=3000,
    title="无标题 - 记事本",
    process_name="notepad.exe",
    pid=200,
    x=0, y=0, width=800, height=600,
    is_visible=True, is_minimized=False,
)


class TestUwpAfhFallbackResolveHwnd:
    """Tests for _resolve_hwnd UWP AFH fallback (#569)."""

    def test_calculator_english_name(self, monkeypatch):
        """--app calculator should match AFH-hosted Calculator via child PID."""
        backend = _make_backend(monkeypatch, [AFH_CALCULATOR, NOTEPAD_WINDOW])
        monkeypatch.setattr(
            backend, "_afh_has_content_window", lambda h: h == 1000,
        )
        monkeypatch.setattr(
            backend, "_resolve_uwp_child_pid",
            lambda h: (100, "C:\\Program Files\\CalculatorApp.exe")
            if h == 1000 else (None, None),
        )

        result = backend._resolve_hwnd(app="calculator")
        assert result == 1000

    def test_calculator_chinese_name(self, monkeypatch):
        """--app 计算器 should match AFH-hosted Calculator via child PID."""
        backend = _make_backend(monkeypatch, [AFH_CALCULATOR])
        monkeypatch.setattr(
            backend, "_afh_has_content_window", lambda h: True,
        )
        monkeypatch.setattr(
            backend, "_resolve_uwp_child_pid",
            lambda h: (100, "CalculatorApp.exe"),
        )

        result = backend._resolve_hwnd(app="计算器")
        assert result == 1000

    def test_no_fallback_when_process_matches(self, monkeypatch):
        """Should use normal matching when process name matches directly."""
        calc_direct = WindowInfo(
            handle=9000,
            title="Calculator",
            process_name="CalculatorApp.exe",
            pid=100,
            x=0, y=0, width=400, height=600,
            is_visible=True, is_minimized=False,
        )
        backend = _make_backend(monkeypatch, [calc_direct])

        result = backend._resolve_hwnd(app="calculatorapp")
        # Should match CalculatorApp.exe directly (score 4)
        assert result == 9000

    def test_fallback_skips_afh_without_content(self, monkeypatch):
        """AFH windows without content children should be skipped."""
        backend = _make_backend(monkeypatch, [AFH_CALCULATOR])
        monkeypatch.setattr(
            backend, "_afh_has_content_window", lambda h: False,
        )

        with pytest.raises(WindowNotFoundError):
            backend._resolve_hwnd(app="calculator")

    def test_fallback_skips_non_matching_child(self, monkeypatch):
        """AFH with non-matching child process should not match."""
        backend = _make_backend(monkeypatch, [AFH_CALCULATOR])
        monkeypatch.setattr(
            backend, "_afh_has_content_window", lambda h: True,
        )
        # Child is a different app
        monkeypatch.setattr(
            backend, "_resolve_uwp_child_pid",
            lambda h: (300, "SomeOtherApp.exe"),
        )

        with pytest.raises(WindowNotFoundError):
            backend._resolve_hwnd(app="calculator")

    def test_settings_english_name(self, monkeypatch):
        """--app settings should match AFH-hosted Settings."""
        backend = _make_backend(monkeypatch, [AFH_SETTINGS])
        monkeypatch.setattr(
            backend, "_afh_has_content_window", lambda h: True,
        )
        monkeypatch.setattr(
            backend, "_resolve_uwp_child_pid",
            lambda h: (301, "SystemSettings.exe"),
        )

        result = backend._resolve_hwnd(app="settings")
        assert result == 2000


class TestUwpAfhFallbackResolveHwnds:
    """Tests for _resolve_hwnds UWP AFH fallback (#569)."""

    def test_calculator_returns_afh_handle(self, monkeypatch):
        """_resolve_hwnds should return AFH handle for UWP apps."""
        backend = _make_backend(monkeypatch, [AFH_CALCULATOR])
        monkeypatch.setattr(
            backend, "_afh_has_content_window", lambda h: True,
        )
        monkeypatch.setattr(
            backend, "_resolve_uwp_child_pid",
            lambda h: (100, "CalculatorApp.exe"),
        )

        result = backend._resolve_hwnds(app="calculator")
        assert result == [1000]

    def test_empty_when_no_match(self, monkeypatch):
        """Should return empty list when no AFH child matches."""
        backend = _make_backend(monkeypatch, [AFH_CALCULATOR])
        monkeypatch.setattr(
            backend, "_afh_has_content_window", lambda h: True,
        )
        monkeypatch.setattr(
            backend, "_resolve_uwp_child_pid",
            lambda h: (300, "UnrelatedApp.exe"),
        )

        result = backend._resolve_hwnds(app="calculator")
        assert result == []

    def test_no_fallback_when_process_matches_directly(self, monkeypatch):
        """Should not use fallback when process name already matched."""
        calc_direct = WindowInfo(
            handle=9000,
            title="Calculator",
            process_name="CalculatorApp.exe",
            pid=100,
            x=0, y=0, width=400, height=600,
            is_visible=True, is_minimized=False,
        )
        backend = _make_backend(monkeypatch, [calc_direct])
        # The fallback should not be called since CalculatorApp matches
        # "calculator" via substring

        result = backend._resolve_hwnds(app="calculator")
        assert 9000 in result


class TestUwpAfhFallbackHelper:
    """Tests for _uwp_afh_fallback helper method."""

    def test_returns_none_when_no_afh_windows(self, monkeypatch):
        """Should return None when no AFH windows exist."""
        backend = _make_backend(monkeypatch, [NOTEPAD_WINDOW])

        result = backend._uwp_afh_fallback("calculator", [NOTEPAD_WINDOW], 1)
        assert result is None

    def test_returns_none_when_child_resolution_fails(self, monkeypatch):
        """Should return None when _resolve_uwp_child_pid returns None."""
        backend = _make_backend(monkeypatch, [AFH_CALCULATOR])
        monkeypatch.setattr(
            backend, "_afh_has_content_window", lambda h: True,
        )
        monkeypatch.setattr(
            backend, "_resolve_uwp_child_pid",
            lambda h: (None, None),
        )

        result = backend._uwp_afh_fallback(
            "calculator", [AFH_CALCULATOR], 1,
        )
        assert result is None

    def test_matches_via_alias(self, monkeypatch):
        """Should match via _APP_ALIASES (e.g. calc -> calculatorapp)."""
        backend = _make_backend(monkeypatch, [AFH_CALCULATOR])
        monkeypatch.setattr(
            backend, "_afh_has_content_window", lambda h: True,
        )
        monkeypatch.setattr(
            backend, "_resolve_uwp_child_pid",
            lambda h: (100, "CalculatorApp.exe"),
        )

        result = backend._uwp_afh_fallback(
            "calc", [AFH_CALCULATOR], 1,
        )
        assert result is not None
        assert result.handle == 1000
