"""Tests for naturo.backends.windows._shell.ShellMixin.

All Windows API calls are mocked — these tests run on any platform.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from naturo.backends.base import ElementInfo, WindowInfo
from naturo.backends.windows._shell import ShellMixin
from naturo.errors import NaturoError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _win(
    handle: int = 1,
    title: str = "Untitled - Notepad",
    process_name: str = "C:\\Windows\\notepad.exe",
    pid: int = 1000,
    is_visible: bool = True,
    is_minimized: bool = False,
) -> WindowInfo:
    return WindowInfo(
        handle=handle, title=title, process_name=process_name,
        pid=pid, x=0, y=0, width=800, height=600,
        is_visible=is_visible, is_minimized=is_minimized,
    )


def _elem(
    role: str = "Button",
    name: str = "OK",
    value: Optional[str] = None,
    children: list | None = None,
    x: int = 100,
    y: int = 100,
    width: int = 80,
    height: int = 30,
) -> ElementInfo:
    return ElementInfo(
        id="e1", role=role, name=name, value=value,
        x=x, y=y, width=width, height=height,
        children=children or [], properties={},
    )


class FakeShell(ShellMixin):
    """Concrete subclass providing stubs for abstract backend methods."""

    _SYSTEM_PROCESS_NAMES: set[str] = {
        "textinputhost.exe", "shellexperiencehost.exe", "dwm.exe",
        "runtimebroker.exe",
    }
    _UWP_HOST_PROCESS: str = "applicationframehost.exe"

    def __init__(self):
        self._windows: list[WindowInfo] = []
        self._tree: ElementInfo | None = None
        self._clicked: list[tuple] = []
        self._typed: list[str] = []
        self._hotkeys: list[tuple] = []
        self._focused: list[int] = []

    # Stubs called by ShellMixin methods
    def list_windows(self):
        return self._windows

    def _list_windows_unresolved(self):
        # list_apps consumes the unresolved view so it can run its own UWP
        # host-PID resolution (#958); the fake serves the same raw windows.
        return self._windows

    def _resolve_uwp_child_pid(self, hwnd):
        return (0, "")

    def _resolve_hwnd(self, **kwargs):
        return 12345

    def _ensure_core(self):
        mock = MagicMock()
        mock.get_element_tree.return_value = self._tree
        return mock

    def _ensure_win32(self):
        pass

    def get_element_tree(self, hwnd=None, depth=5):
        return self._tree

    def click(self, x=0, y=0, **kwargs):
        self._clicked.append((x, y))

    def type_text(self, text, **kwargs):
        self._typed.append(text)

    def hotkey(self, *keys):
        self._hotkeys.append(keys)

    def focus_window(self, hwnd=None, **kwargs):
        self._focused.append(hwnd)


# ===================================================================
# list_apps
# ===================================================================

class TestListApps:
    def test_returns_visible_non_minimized_windows(self):
        shell = FakeShell()
        shell._windows = [
            _win(handle=1, title="Notepad", pid=100, process_name="C:\\notepad.exe"),
            _win(handle=2, title="Chrome", pid=200, process_name="C:\\chrome.exe"),
        ]
        apps = shell.list_apps()
        assert len(apps) == 2
        assert apps[0]["title"] == "Notepad"
        assert apps[1]["title"] == "Chrome"

    def test_skips_invisible_windows(self):
        shell = FakeShell()
        shell._windows = [
            _win(handle=1, title="Notepad", pid=100, is_visible=False),
        ]
        assert shell.list_apps() == []

    def test_skips_minimized_windows(self):
        shell = FakeShell()
        shell._windows = [
            _win(handle=1, title="Notepad", pid=100, is_minimized=True),
        ]
        assert shell.list_apps() == []

    def test_deduplicates_by_pid(self):
        shell = FakeShell()
        shell._windows = [
            _win(handle=1, title="Notepad", pid=100, process_name="C:\\notepad.exe"),
            _win(handle=2, title="Notepad - file.txt", pid=100, process_name="C:\\notepad.exe"),
        ]
        apps = shell.list_apps()
        assert len(apps) == 1

    def test_skips_system_processes(self):
        shell = FakeShell()
        # Use bare filenames — on Linux os.path.basename won't split on backslash
        shell._windows = [
            _win(handle=1, title="DWM", pid=4, process_name="dwm.exe"),
            _win(handle=2, title="Notepad", pid=100, process_name="notepad.exe"),
        ]
        apps = shell.list_apps()
        assert len(apps) == 1
        assert apps[0]["title"] == "Notepad"

    def test_skips_empty_title_windows(self):
        shell = FakeShell()
        shell._windows = [
            _win(handle=1, title="", pid=100, process_name="C:\\app.exe"),
            _win(handle=2, title="   ", pid=200, process_name="C:\\app2.exe"),
        ]
        assert shell.list_apps() == []

    def test_uwp_app_resolves_child_pid(self):
        shell = FakeShell()
        shell._resolve_uwp_child_pid = lambda hwnd: (999, "Calculator.exe")
        shell._windows = [
            _win(
                handle=1, title="Calculator", pid=50,
                process_name="applicationframehost.exe",
            ),
        ]
        apps = shell.list_apps()
        assert len(apps) == 1
        assert apps[0]["pid"] == 999
        assert apps[0]["path"] == "Calculator.exe"

    def test_uwp_deduplicates_by_pid_and_title(self):
        shell = FakeShell()
        shell._resolve_uwp_child_pid = lambda hwnd: (999, "Calculator.exe")
        shell._windows = [
            _win(handle=1, title="Calculator", pid=50,
                 process_name="applicationframehost.exe"),
            _win(handle=2, title="Calculator", pid=51,
                 process_name="applicationframehost.exe"),
        ]
        apps = shell.list_apps()
        assert len(apps) == 1

    def test_uwp_fallback_when_child_not_resolved(self):
        shell = FakeShell()
        shell._resolve_uwp_child_pid = lambda hwnd: (0, "")
        shell._windows = [
            _win(handle=1, title="Settings", pid=50,
                 process_name="applicationframehost.exe"),
        ]
        apps = shell.list_apps()
        assert len(apps) == 1
        assert apps[0]["pid"] == 50

    def test_app_dict_keys(self):
        shell = FakeShell()
        shell._windows = [
            _win(handle=1, title="Notepad", pid=100,
                 process_name="C:\\Windows\\notepad.exe"),
        ]
        app = shell.list_apps()[0]
        assert set(app.keys()) == {"name", "pid", "title", "path", "process"}


# ===================================================================
# open_uri
# ===================================================================

class TestOpenUri:
    @patch("subprocess.Popen")
    def test_opens_url_with_popen(self, mock_popen):
        shell = FakeShell()
        shell.open_uri("https://example.com")
        mock_popen.assert_called_once()
        args = mock_popen.call_args
        assert "https://example.com" in args[0][0]

    @patch("subprocess.run")
    @patch("os.path.exists", return_value=True)
    def test_opens_file_with_run(self, mock_exists, mock_run):
        shell = FakeShell()
        shell.open_uri("C:\\report.pdf")
        mock_run.assert_called_once()

    def test_raises_for_nonexistent_file(self):
        shell = FakeShell()
        with pytest.raises(NaturoError, match="File not found"):
            shell.open_uri("C:\\nonexistent.txt")

    @patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("start", 15))
    @patch("os.path.exists", return_value=True)
    def test_raises_on_timeout(self, mock_exists, mock_run):
        shell = FakeShell()
        with pytest.raises(NaturoError, match="timed out"):
            shell.open_uri("C:\\slow_app.exe")

    @patch("subprocess.Popen")
    def test_url_schemes(self, mock_popen):
        shell = FakeShell()
        for scheme in ["http://x", "https://x", "ftp://x", "mailto:x"]:
            shell.open_uri(scheme)
        assert mock_popen.call_count == 4


# ===================================================================
# _flatten_elements
# ===================================================================

class TestFlattenElements:
    def test_single_element(self):
        shell = FakeShell()
        root = _elem(name="root")
        flat = shell._flatten_elements(root)
        assert len(flat) == 1
        assert flat[0].name == "root"

    def test_nested_tree(self):
        shell = FakeShell()
        child1 = _elem(name="child1")
        child2 = _elem(name="child2")
        grandchild = _elem(name="grandchild")
        child1.children = [grandchild]
        root = _elem(name="root", children=[child1, child2])
        flat = shell._flatten_elements(root)
        assert len(flat) == 4
        names = [e.name for e in flat]
        assert names == ["root", "child1", "grandchild", "child2"]


# ===================================================================
# _collect_taskbar_buttons
# ===================================================================

class TestCollectTaskbarButtons:
    def test_collects_named_buttons(self):
        shell = FakeShell()
        btn1 = _elem(role="Button", name="Chrome", x=10, y=900, width=50, height=40)
        btn2 = _elem(role="Button", name="Notepad", x=60, y=900, width=50, height=40)
        toolbar = _elem(role="ToolBar", name="Taskbar", children=[btn1, btn2])
        items: list[dict] = []
        shell._collect_taskbar_buttons(toolbar, items)
        assert len(items) == 2
        assert items[0]["name"] == "Chrome"
        assert items[1]["name"] == "Notepad"

    def test_skips_unnamed_buttons(self):
        shell = FakeShell()
        btn = _elem(role="Button", name="")
        toolbar = _elem(role="ToolBar", name="Taskbar", children=[btn])
        items: list[dict] = []
        shell._collect_taskbar_buttons(toolbar, items)
        assert len(items) == 0

    def test_skips_non_button_roles(self):
        shell = FakeShell()
        txt = _elem(role="Text", name="Clock")
        toolbar = _elem(role="ToolBar", name="Taskbar", children=[txt])
        items: list[dict] = []
        shell._collect_taskbar_buttons(toolbar, items)
        assert len(items) == 0

    def test_deep_nesting(self):
        shell = FakeShell()
        btn = _elem(role="Button", name="App")
        group = _elem(role="Group", name="", children=[btn])
        toolbar = _elem(role="ToolBar", name="Taskbar", children=[group])
        items: list[dict] = []
        shell._collect_taskbar_buttons(toolbar, items)
        assert len(items) == 1
        assert items[0]["name"] == "App"


# ===================================================================
# dialog_click_button
# ===================================================================

class TestDialogClickButton:
    def _make_dialog(self, buttons):
        from naturo.dialog import DialogInfo, DialogButton
        return DialogInfo(
            hwnd=100, title="Save?", dialog_type="confirmation",
            message="Save changes?", buttons=buttons,
            has_input=False, input_value="", owner_app="notepad.exe",
            owner_hwnd=50,
        )

    def test_clicks_exact_match(self):
        from naturo.dialog import DialogButton
        shell = FakeShell()
        btn = DialogButton(name="Yes", element_id="e1", x=200, y=300,
                           is_default=True)
        dialog = self._make_dialog([btn])
        shell.detect_dialogs = lambda **kw: [dialog]
        result = shell.dialog_click_button("Yes")
        assert result["button_clicked"] == "Yes"
        assert (200, 300) in shell._clicked

    def test_clicks_partial_match(self):
        from naturo.dialog import DialogButton
        shell = FakeShell()
        btn = DialogButton(name="Don't Save", element_id="e1", x=100, y=100)
        dialog = self._make_dialog([btn])
        shell.detect_dialogs = lambda **kw: [dialog]
        result = shell.dialog_click_button("save")
        assert result["button_clicked"] == "Don't Save"

    def test_raises_when_no_dialog(self):
        shell = FakeShell()
        shell.detect_dialogs = lambda **kw: []
        with pytest.raises(NaturoError, match="No dialog detected"):
            shell.dialog_click_button("OK")

    def test_raises_when_button_not_found(self):
        from naturo.dialog import DialogButton
        from naturo.errors import ElementNotFoundError
        shell = FakeShell()
        btn = DialogButton(name="OK", element_id="e1", x=100, y=100,
                           is_default=True)
        dialog = self._make_dialog([btn])
        shell.detect_dialogs = lambda **kw: [dialog]
        with pytest.raises(ElementNotFoundError):
            shell.dialog_click_button("NonExistent")


# ===================================================================
# dialog_set_input
# ===================================================================

class TestDialogSetInput:
    def _make_dialog(self, has_input=True):
        from naturo.dialog import DialogInfo
        return DialogInfo(
            hwnd=100, title="Open", dialog_type="file_open",
            message="", buttons=[], has_input=has_input,
            input_value="", owner_app="notepad.exe", owner_hwnd=50,
        )

    def test_types_into_edit_field(self):
        shell = FakeShell()
        edit = _elem(role="Edit", name="File name:", x=100, y=200, width=300, height=25)
        shell._tree = _elem(role="Dialog", name="Open", children=[edit])
        dialog = self._make_dialog(has_input=True)
        shell.detect_dialogs = lambda **kw: [dialog]
        result = shell.dialog_set_input("hello.txt")
        assert result["text_entered"] == "hello.txt"
        assert len(shell._clicked) == 1
        assert "hello.txt" in shell._typed

    def test_raises_when_no_dialog(self):
        shell = FakeShell()
        shell.detect_dialogs = lambda **kw: []
        with pytest.raises(NaturoError, match="No dialog detected"):
            shell.dialog_set_input("test")

    def test_raises_when_no_input_field(self):
        shell = FakeShell()
        dialog = self._make_dialog(has_input=False)
        shell.detect_dialogs = lambda **kw: [dialog]
        with pytest.raises(NaturoError, match="no input field"):
            shell.dialog_set_input("test")


# ===================================================================
# launch_app / quit_app
# ===================================================================

class TestLaunchQuitApp:
    @patch("subprocess.Popen")
    def test_launch_app(self, mock_popen):
        shell = FakeShell()
        shell.launch_app("notepad")
        mock_popen.assert_called_once_with(["notepad"], shell=True)

    @patch("subprocess.run")
    def test_quit_app_normal(self, mock_run):
        shell = FakeShell()
        shell.quit_app("notepad.exe")
        cmd = mock_run.call_args[0][0]
        assert "notepad.exe" in cmd
        assert "/F" not in cmd

    @patch("subprocess.run")
    def test_quit_app_force(self, mock_run):
        shell = FakeShell()
        shell.quit_app("notepad.exe", force=True)
        cmd = mock_run.call_args[0][0]
        assert "/F" in cmd


# ===================================================================
# virtual_desktop_list
# ===================================================================

class TestVirtualDesktopList:
    def test_returns_desktop_list(self):
        shell = FakeShell()
        mock_desktop_0 = MagicMock(name="D0", number=0)
        mock_desktop_0.name = "Main"
        mock_desktop_0.id = "id-0"
        mock_desktop_1 = MagicMock(name="D1", number=1)
        mock_desktop_1.name = "Work"
        mock_desktop_1.id = "id-1"
        mock_current = MagicMock(number=0)

        with patch.dict("sys.modules", {"pyvda": MagicMock()}):
            import sys
            pyvda = sys.modules["pyvda"]
            pyvda.get_virtual_desktops.return_value = [mock_desktop_0, mock_desktop_1]
            pyvda.VirtualDesktop.current.return_value = mock_current
            result = shell.virtual_desktop_list()

        assert len(result) == 2
        assert result[0]["name"] == "Main"
        assert result[0]["is_current"] is True
        assert result[1]["name"] == "Work"
        assert result[1]["is_current"] is False

    def test_raises_when_pyvda_missing(self):
        shell = FakeShell()
        with patch.dict("sys.modules", {"pyvda": None}):
            with pytest.raises(NaturoError, match="pyvda"):
                shell.virtual_desktop_list()


# ===================================================================
# virtual_desktop_switch
# ===================================================================

class TestVirtualDesktopSwitch:
    def test_switches_to_valid_index(self):
        shell = FakeShell()
        mock_desktop = MagicMock(number=1)
        mock_desktop.name = "Work"

        with patch.dict("sys.modules", {"pyvda": MagicMock()}):
            import sys
            pyvda = sys.modules["pyvda"]
            pyvda.get_virtual_desktops.return_value = [MagicMock(), mock_desktop]
            result = shell.virtual_desktop_switch(1)

        assert result["index"] == 1
        assert result["name"] == "Work"
        mock_desktop.go.assert_called_once()

    def test_raises_for_invalid_index(self):
        shell = FakeShell()
        with patch.dict("sys.modules", {"pyvda": MagicMock()}):
            import sys
            pyvda = sys.modules["pyvda"]
            pyvda.get_virtual_desktops.return_value = [MagicMock()]
            with pytest.raises(NaturoError, match="out of range"):
                shell.virtual_desktop_switch(5)


# ===================================================================
# virtual_desktop_create
# ===================================================================

class TestVirtualDesktopCreate:
    def test_creates_desktop_with_name(self):
        shell = FakeShell()
        mock_new = MagicMock()
        mock_new.id = "new-id"

        with patch.dict("sys.modules", {"pyvda": MagicMock()}):
            import sys
            pyvda = sys.modules["pyvda"]
            pyvda.VirtualDesktop.create.return_value = mock_new
            pyvda.get_virtual_desktops.return_value = [MagicMock(), mock_new]
            result = shell.virtual_desktop_create(name="Dev")

        assert result["name"] == "Dev"
        assert result["index"] == 1
        mock_new.rename.assert_called_once_with("Dev")

    def test_creates_desktop_without_name(self):
        shell = FakeShell()
        mock_new = MagicMock()
        mock_new.id = "new-id"

        with patch.dict("sys.modules", {"pyvda": MagicMock()}):
            import sys
            pyvda = sys.modules["pyvda"]
            pyvda.VirtualDesktop.create.return_value = mock_new
            pyvda.get_virtual_desktops.return_value = [MagicMock(), MagicMock(), mock_new]
            result = shell.virtual_desktop_create()

        assert result["name"] == "Desktop 3"
        assert result["index"] == 2


# ===================================================================
# virtual_desktop_close
# ===================================================================

class TestVirtualDesktopClose:
    def test_closes_by_index(self):
        shell = FakeShell()
        mock_d0 = MagicMock(number=0)
        mock_d0.name = "Main"
        mock_d1 = MagicMock(number=1)
        mock_d1.name = "Work"

        with patch.dict("sys.modules", {"pyvda": MagicMock()}):
            import sys
            pyvda = sys.modules["pyvda"]
            pyvda.get_virtual_desktops.return_value = [mock_d0, mock_d1]
            result = shell.virtual_desktop_close(index=1)

        assert result["name"] == "Work"
        mock_d1.remove.assert_called_once()

    def test_raises_when_only_one_desktop(self):
        shell = FakeShell()
        with patch.dict("sys.modules", {"pyvda": MagicMock()}):
            import sys
            pyvda = sys.modules["pyvda"]
            pyvda.get_virtual_desktops.return_value = [MagicMock()]
            with pytest.raises(NaturoError, match="last virtual desktop"):
                shell.virtual_desktop_close()

    def test_raises_for_invalid_index(self):
        shell = FakeShell()
        with patch.dict("sys.modules", {"pyvda": MagicMock()}):
            import sys
            pyvda = sys.modules["pyvda"]
            pyvda.get_virtual_desktops.return_value = [MagicMock(), MagicMock()]
            with pytest.raises(NaturoError, match="out of range"):
                shell.virtual_desktop_close(index=5)


# ===================================================================
# menu_click (not implemented)
# ===================================================================

class TestMenuClick:
    def test_raises_not_implemented(self):
        shell = FakeShell()
        with pytest.raises(NotImplementedError):
            shell.menu_click("File > Save")


# ===================================================================
# menu_list
# ===================================================================

class TestMenuList:
    def test_returns_list_of_dicts(self):
        from naturo.models.menu import MenuItem
        shell = FakeShell()
        items = [
            MenuItem(name="File", shortcut="", submenu=[
                MenuItem(name="New", shortcut="Ctrl+N"),
            ]),
        ]
        shell.get_menu_items = lambda **kw: items
        result = shell.menu_list()
        assert len(result) == 1
        assert result[0]["name"] == "File"
        assert len(result[0]["submenu"]) == 1
