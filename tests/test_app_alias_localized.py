"""Tests for localized (Chinese) app name matching via _APP_ALIASES (#469).

When --app is used with a Chinese app name like 计算器 or 记事本, the alias
map should resolve it to the correct process name.  This prevents breakage
on non-English Windows systems where users naturally type app names in their
locale language.
"""

import pytest
from naturo.backends.windows import WindowsBackend
from naturo.backends.base import WindowInfo
from naturo.errors import WindowNotFoundError


def _make_backend(monkeypatch, windows):
    """Create a WindowsBackend with mocked window list."""
    backend = WindowsBackend()
    monkeypatch.setattr(backend, "list_windows", lambda: windows)
    monkeypatch.setattr("naturo.backends.windows._element._get_console_session_id", lambda: 1)
    monkeypatch.setattr("naturo.backends.windows._element._get_process_session_id", lambda pid: 1)
    return backend


# -- Fixtures: common window sets for reuse ----------------------------------

CALCULATOR_WINDOW = WindowInfo(
    handle=1000,
    title="计算器",
    process_name="CalculatorApp.exe",
    pid=100,
    x=0, y=0, width=400, height=600,
    is_visible=True, is_minimized=False,
)

NOTEPAD_WINDOW = WindowInfo(
    handle=2000,
    title="无标题 - 记事本",
    process_name="notepad.exe",
    pid=200,
    x=0, y=0, width=800, height=600,
    is_visible=True, is_minimized=False,
)

SETTINGS_WINDOW = WindowInfo(
    handle=3000,
    title="设置",
    process_name="SystemSettings.exe",
    pid=300,
    x=0, y=0, width=1000, height=700,
    is_visible=True, is_minimized=False,
)

PAINT_WINDOW = WindowInfo(
    handle=4000,
    title="画图",
    process_name="mspaint.exe",
    pid=400,
    x=0, y=0, width=900, height=600,
    is_visible=True, is_minimized=False,
)

EXPLORER_WINDOW = WindowInfo(
    handle=5000,
    title="文件资源管理器",
    process_name="explorer.exe",
    pid=500,
    x=0, y=0, width=1200, height=800,
    is_visible=True, is_minimized=False,
)

TERMINAL_WINDOW = WindowInfo(
    handle=6000,
    title="终端",
    process_name="WindowsTerminal.exe",
    pid=600,
    x=0, y=0, width=800, height=500,
    is_visible=True, is_minimized=False,
)

TASK_MANAGER_WINDOW = WindowInfo(
    handle=7000,
    title="任务管理器",
    process_name="Taskmgr.exe",
    pid=700,
    x=0, y=0, width=700, height=500,
    is_visible=True, is_minimized=False,
)

CMD_WINDOW = WindowInfo(
    handle=8000,
    title="命令提示符",
    process_name="cmd.exe",
    pid=800,
    x=0, y=0, width=800, height=400,
    is_visible=True, is_minimized=False,
)


class TestChineseAliasResolveSingle:
    """--app with Chinese name should resolve via alias to correct process."""

    def test_calculator_chinese(self, monkeypatch):
        """--app 计算器 resolves to CalculatorApp.exe via alias."""
        backend = _make_backend(monkeypatch, [CALCULATOR_WINDOW])
        result = backend._resolve_hwnd(app="计算器")
        assert result == 1000

    def test_notepad_chinese(self, monkeypatch):
        """--app 记事本 resolves to notepad.exe via alias."""
        backend = _make_backend(monkeypatch, [NOTEPAD_WINDOW])
        result = backend._resolve_hwnd(app="记事本")
        assert result == 2000

    def test_settings_chinese(self, monkeypatch):
        """--app 设置 resolves to SystemSettings.exe via alias."""
        backend = _make_backend(monkeypatch, [SETTINGS_WINDOW])
        result = backend._resolve_hwnd(app="设置")
        assert result == 3000

    def test_paint_chinese(self, monkeypatch):
        """--app 画图 resolves to mspaint.exe via alias."""
        backend = _make_backend(monkeypatch, [PAINT_WINDOW])
        result = backend._resolve_hwnd(app="画图")
        assert result == 4000

    def test_explorer_chinese(self, monkeypatch):
        """--app 文件资源管理器 resolves to explorer.exe via alias."""
        backend = _make_backend(monkeypatch, [EXPLORER_WINDOW])
        result = backend._resolve_hwnd(app="文件资源管理器")
        assert result == 5000

    def test_terminal_chinese(self, monkeypatch):
        """--app 终端 resolves to WindowsTerminal.exe via alias."""
        backend = _make_backend(monkeypatch, [TERMINAL_WINDOW])
        result = backend._resolve_hwnd(app="终端")
        assert result == 6000

    def test_task_manager_chinese(self, monkeypatch):
        """--app 任务管理器 resolves to Taskmgr.exe via alias."""
        backend = _make_backend(monkeypatch, [TASK_MANAGER_WINDOW])
        result = backend._resolve_hwnd(app="任务管理器")
        assert result == 7000

    def test_cmd_chinese(self, monkeypatch):
        """--app 命令提示符 resolves to cmd.exe via alias."""
        backend = _make_backend(monkeypatch, [CMD_WINDOW])
        result = backend._resolve_hwnd(app="命令提示符")
        assert result == 8000


class TestChineseAliasAmongMultipleWindows:
    """Chinese alias matching should pick the right window among many."""

    def test_chinese_calc_among_many(self, monkeypatch):
        """--app 计算器 picks CalculatorApp.exe not others."""
        backend = _make_backend(monkeypatch, [
            NOTEPAD_WINDOW, CALCULATOR_WINDOW, SETTINGS_WINDOW,
        ])
        result = backend._resolve_hwnd(app="计算器")
        assert result == 1000

    def test_chinese_notepad_among_many(self, monkeypatch):
        """--app 记事本 picks notepad.exe not others."""
        backend = _make_backend(monkeypatch, [
            CALCULATOR_WINDOW, NOTEPAD_WINDOW, TERMINAL_WINDOW,
        ])
        result = backend._resolve_hwnd(app="记事本")
        assert result == 2000


class TestChineseAliasBulkResolve:
    """_resolve_hwnds with Chinese alias should work for bulk enumeration."""

    def test_bulk_resolve_chinese_calc(self, monkeypatch):
        """_resolve_hwnds with --app 计算器 returns correct windows."""
        backend = _make_backend(monkeypatch, [
            NOTEPAD_WINDOW, CALCULATOR_WINDOW,
        ])
        result = backend._resolve_hwnds(app="计算器")
        assert result == [1000]

    def test_bulk_resolve_chinese_notepad(self, monkeypatch):
        """_resolve_hwnds with --app 记事本 returns correct windows."""
        backend = _make_backend(monkeypatch, [
            CALCULATOR_WINDOW, NOTEPAD_WINDOW, TERMINAL_WINDOW,
        ])
        result = backend._resolve_hwnds(app="记事本")
        assert result == [2000]


class TestEnglishToChineseProcessBidirectional:
    """English aliases should still work when window has Chinese title."""

    def test_english_calculator_matches_chinese_titled(self, monkeypatch):
        """--app calculator matches CalculatorApp.exe even with Chinese title."""
        backend = _make_backend(monkeypatch, [CALCULATOR_WINDOW])
        result = backend._resolve_hwnd(app="calculator")
        assert result == 1000

    def test_english_notepad_matches_chinese_titled(self, monkeypatch):
        """--app notepad matches notepad.exe even with Chinese title."""
        backend = _make_backend(monkeypatch, [NOTEPAD_WINDOW])
        result = backend._resolve_hwnd(app="notepad")
        assert result == 2000


class TestNoFalsePositiveFromChineseAlias:
    """Chinese alias should prefer process matches over title matches."""

    def test_chinese_calc_prefers_process_over_chrome_title(self, monkeypatch):
        """--app 计算器 should prefer CalculatorApp.exe over Chrome with '计算器' in title."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=9000,
                title="计算器 - 百度搜索 - Google Chrome",
                process_name="chrome.exe",
                pid=900,
                x=0, y=0, width=1920, height=1080,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=9001,
                title="计算器",
                process_name="CalculatorApp.exe",
                pid=901,
                x=0, y=0, width=400, height=600,
                is_visible=True, is_minimized=False,
            ),
        ])
        result = backend._resolve_hwnd(app="计算器")
        assert result == 9001, "Process/alias match must beat title fallback"

    def test_chinese_calc_falls_back_to_title(self, monkeypatch):
        """--app 计算器 falls back to title match when Calculator not running (#671)."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=9000,
                title="计算器 - 百度搜索 - Google Chrome",
                process_name="chrome.exe",
                pid=900,
                x=0, y=0, width=1920, height=1080,
                is_visible=True, is_minimized=False,
            ),
        ])
        result = backend._resolve_hwnd(app="计算器")
        assert result == 9000, "Title fallback should match when no process matches"


class TestAliasMapCompleteness:
    """Verify the alias map contains expected entries."""

    def test_all_chinese_aliases_exist(self):
        """All documented Chinese aliases are present in _APP_ALIASES."""
        aliases = WindowsBackend._APP_ALIASES
        expected_chinese = [
            "计算器", "记事本", "设置", "画图",
            "文件资源管理器", "任务管理器", "命令提示符", "终端",
            "写字板", "截图工具",
        ]
        for name in expected_chinese:
            assert name in aliases, f"Missing Chinese alias: {name}"

    def test_chinese_aliases_contain_process_names(self):
        """Chinese aliases must map to actual process name stems."""
        aliases = WindowsBackend._APP_ALIASES
        expected_mappings = {
            "计算器": {"calculatorapp", "calc"},
            "记事本": {"notepad"},
            "设置": {"systemsettings"},
            "画图": {"mspaint"},
            "文件资源管理器": {"explorer"},
            "任务管理器": {"taskmgr"},
            "命令提示符": {"cmd"},
            "终端": {"windowsterminal"},
            "写字板": {"wordpad"},
            "截图工具": {"snippingtool", "screensketch"},
        }
        for chinese, expected_procs in expected_mappings.items():
            actual = aliases[chinese]
            for proc in expected_procs:
                assert proc in actual, (
                    f"Alias '{chinese}' missing process stem '{proc}', "
                    f"has: {actual}"
                )

    def test_alias_values_are_english_process_stems(self):
        """All alias values should be lowercase English process name stems."""
        aliases = WindowsBackend._APP_ALIASES
        for key, values in aliases.items():
            for v in values:
                assert v.isascii(), (
                    f"Alias '{key}' has non-ASCII value '{v}' — "
                    f"values must be English process name stems"
                )
