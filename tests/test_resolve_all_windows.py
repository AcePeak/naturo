"""Tests for _resolve_hwnds (Issue #304)."""
import pytest
from naturo.backends.windows import WindowsBackend
from naturo.backends.base import WindowInfo


class TestResolveAllWindows:
    """Verify _resolve_hwnds returns all matching windows."""

    def test_resolve_all_matching_process_windows(self, monkeypatch):
        """_resolve_hwnds should return all windows for a given process."""
        backend = WindowsBackend()

        def mock_list_windows():
            return [
                WindowInfo(
                    handle=1000,
                    title="Feishu - Main",
                    process_name="Lark.exe",
                    pid=100,
                    x=0, y=0, width=1920, height=1080,
                    is_visible=True,
                    is_minimized=False,
                ),
                WindowInfo(
                    handle=2000,
                    title="Feishu - Video Call",
                    process_name="Lark.exe",
                    pid=100,
                    x=200, y=100, width=800, height=600,
                    is_visible=True,
                    is_minimized=False,
                ),
                WindowInfo(
                    handle=3000,
                    title="Feishu - Image Preview",
                    process_name="Lark.exe",
                    pid=100,
                    x=400, y=300, width=1024, height=768,
                    is_visible=True,
                    is_minimized=False,
                ),
                WindowInfo(
                    handle=4000,
                    title="Notepad",
                    process_name="notepad.exe",
                    pid=200,
                    x=100, y=100, width=640, height=480,
                    is_visible=True,
                    is_minimized=False,
                ),
            ]

        def mock_console_session():
            return 1

        def mock_process_session(pid):
            return 1

        monkeypatch.setattr(backend, "list_windows", mock_list_windows)
        monkeypatch.setattr(backend, "_get_console_session_id", mock_console_session)
        monkeypatch.setattr(backend, "_get_process_session_id", mock_process_session)

        # --app "Lark" should return all 3 Feishu windows
        result = backend._resolve_hwnds(app="Lark")
        assert len(result) == 3
        assert set(result) == {1000, 2000, 3000}

    def test_resolve_hwnds_empty_when_no_match(self, monkeypatch):
        """_resolve_hwnds should return empty list when nothing matches."""
        backend = WindowsBackend()

        def mock_list_windows():
            return [
                WindowInfo(
                    handle=1000,
                    title="Notepad",
                    process_name="notepad.exe",
                    pid=100,
                    x=0, y=0, width=640, height=480,
                    is_visible=True,
                    is_minimized=False,
                ),
            ]

        def mock_console_session():
            return 1

        def mock_process_session(pid):
            return 1

        monkeypatch.setattr(backend, "list_windows", mock_list_windows)
        monkeypatch.setattr(backend, "_get_console_session_id", mock_console_session)
        monkeypatch.setattr(backend, "_get_process_session_id", mock_process_session)

        result = backend._resolve_hwnds(app="Feishu")
        assert result == []

    def test_resolve_hwnds_sorted_by_score(self, monkeypatch):
        """_resolve_hwnds should sort results by match quality."""
        backend = WindowsBackend()

        def mock_list_windows():
            return [
                WindowInfo(
                    handle=1000,
                    title="My App - Window 1",
                    process_name="otherapp.exe",
                    pid=100,
                    x=0, y=0, width=800, height=600,
                    is_visible=True,
                    is_minimized=False,
                ),
                WindowInfo(
                    handle=2000,
                    title="MyApp",
                    process_name="myapp.exe",
                    pid=200,
                    x=0, y=0, width=800, height=600,
                    is_visible=True,
                    is_minimized=False,
                ),
                WindowInfo(
                    handle=3000,
                    title="MyApp - Settings",
                    process_name="myapp.exe",
                    pid=200,
                    x=100, y=100, width=400, height=300,
                    is_visible=True,
                    is_minimized=False,
                ),
            ]

        def mock_console_session():
            return 1

        def mock_process_session(pid):
            return 1

        monkeypatch.setattr(backend, "list_windows", mock_list_windows)
        monkeypatch.setattr(backend, "_get_console_session_id", mock_console_session)
        monkeypatch.setattr(backend, "_get_process_session_id", mock_process_session)

        result = backend._resolve_hwnds(app="myapp")
        # Exact process name match (score 4) should come first
        # Both myapp.exe windows should be included
        assert len(result) == 2
        assert result[0] in (2000, 3000)  # Both have score 4
        assert result[1] in (2000, 3000)
        # Title substring match (1000) should NOT be included (different process)

    def test_resolve_hwnds_no_search_term_returns_empty(self, monkeypatch):
        """_resolve_hwnds should return [] when no search term provided."""
        backend = WindowsBackend()

        def mock_list_windows():
            return [
                WindowInfo(
                    handle=1000,
                    title="Notepad",
                    process_name="notepad.exe",
                    pid=100,
                    x=0, y=0, width=640, height=480,
                    is_visible=True,
                    is_minimized=False,
                ),
            ]

        monkeypatch.setattr(backend, "list_windows", mock_list_windows)

        # No app or window_title → empty list
        result = backend._resolve_hwnds()
        assert result == []

    def test_resolve_hwnds_uwp_afh_fixup_searches_all_windows(self, monkeypatch):
        """_resolve_hwnds AFH fixup must search ALL windows, not just scored matches.

        Regression test for #559: UWP Calculator's CalculatorApp.exe window
        matches via alias, but its ApplicationFrameHost.exe window (which
        contains the actual UI tree) scores 0 for the search term "计算器".
        The fixup must find the AFH window in the full window list.
        """
        backend = WindowsBackend()

        calculator_app = WindowInfo(
            handle=1000,
            title="计算器",
            process_name="CalculatorApp.exe",
            pid=100,
            x=0, y=0, width=400, height=600,
            is_visible=True, is_minimized=False,
        )
        afh_calculator = WindowInfo(
            handle=2000,
            title="计算器",
            process_name="ApplicationFrameHost.exe",
            pid=200,
            x=0, y=0, width=400, height=600,
            is_visible=True, is_minimized=False,
        )
        notepad_window = WindowInfo(
            handle=3000,
            title="无标题 - 记事本",
            process_name="notepad.exe",
            pid=300,
            x=0, y=0, width=800, height=600,
            is_visible=True, is_minimized=False,
        )

        monkeypatch.setattr(backend, "list_windows",
                            lambda: [calculator_app, afh_calculator, notepad_window])
        monkeypatch.setattr(backend, "_get_console_session_id", lambda: 1)
        monkeypatch.setattr(backend, "_get_process_session_id", lambda pid: 1)
        # AFH window has a content child (CoreWindow)
        monkeypatch.setattr(WindowsBackend, "_afh_has_content_window",
                            staticmethod(lambda hwnd: hwnd == 2000))

        result = backend._resolve_hwnds(app="计算器")
        # Should return the AFH window (2000), not CalculatorApp (1000)
        assert result == [2000]

    def test_resolve_hwnds_uwp_afh_fixup_prefers_content_window(self, monkeypatch):
        """AFH fixup in _resolve_hwnds should prefer AFH with content child.

        When multiple AFH windows exist with the same title (e.g. stale
        windows from schtasks), prefer the one with CoreWindow/XAML child.
        """
        backend = WindowsBackend()

        calculator_app = WindowInfo(
            handle=1000,
            title="计算器",
            process_name="CalculatorApp.exe",
            pid=100,
            x=0, y=0, width=400, height=600,
            is_visible=True, is_minimized=False,
        )
        stale_afh = WindowInfo(
            handle=2000,
            title="计算器",
            process_name="ApplicationFrameHost.exe",
            pid=200,
            x=0, y=0, width=400, height=600,
            is_visible=True, is_minimized=False,
        )
        live_afh = WindowInfo(
            handle=3000,
            title="计算器",
            process_name="ApplicationFrameHost.exe",
            pid=201,
            x=0, y=0, width=400, height=600,
            is_visible=True, is_minimized=False,
        )

        monkeypatch.setattr(backend, "list_windows",
                            lambda: [calculator_app, stale_afh, live_afh])
        monkeypatch.setattr(backend, "_get_console_session_id", lambda: 1)
        monkeypatch.setattr(backend, "_get_process_session_id", lambda pid: 1)
        # Only live_afh (3000) has content child
        monkeypatch.setattr(WindowsBackend, "_afh_has_content_window",
                            staticmethod(lambda hwnd: hwnd == 3000))

        result = backend._resolve_hwnds(app="计算器")
        # Should pick the live AFH (3000), not the stale one (2000)
        assert result == [3000]
