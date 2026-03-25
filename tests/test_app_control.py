"""Tests for Phase 2 application control: launch, quit, switch, list.

Tests are organized by category:
  - Method signature / API existence (all platforms)
  - CLI option validation (all platforms)
  - Windows-only functional tests guarded by @pytest.mark.ui
  - E2E tests guarded by @pytest.mark.e2e
"""

from __future__ import annotations

import json
import os
import platform

import pytest
from click.testing import CliRunner
from naturo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


# ── T150-T158: App control method signatures ──────────────────────────────────


class TestAppControlMethodSignatures:
    """Backend app control methods exist with correct signatures (all platforms)."""

    def test_launch_app_method_exists(self):
        """T150 – launch_app method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "launch_app")

    def test_quit_app_method_exists(self):
        """T154 – quit_app method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "quit_app")

    def test_list_apps_method_exists(self):
        """T158 – list_apps method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "list_apps")

    def test_launch_app_signature(self):
        """T150/T151/T152 – launch_app accepts name param."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.launch_app)
        assert "name" in sig.parameters

    def test_quit_app_signature(self):
        """T154/T155 – quit_app accepts name and force params."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.quit_app)
        params = sig.parameters
        assert "name" in params
        assert "force" in params

    def test_quit_app_force_default_false(self):
        """T154 – quit_app force defaults to False."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.quit_app)
        assert sig.parameters["force"].default is False


# ── CLI option validation (all platforms) ─────────────────────────────────────


class TestAppCLIOptions:
    """app CLI option validation (T150-T158)."""

    def test_app_group_in_main_help(self, runner):
        """app group is in main help."""
        result = runner.invoke(main, ["--help"])
        assert "app" in result.output

    def test_app_launch_subcommand(self, runner):
        """T150 – app launch subcommand is documented."""
        result = runner.invoke(main, ["app", "--help"])
        assert result.exit_code == 0
        assert "launch" in result.output

    def test_app_quit_subcommand(self, runner):
        """T154 – app quit subcommand is documented."""
        result = runner.invoke(main, ["app", "--help"])
        assert "quit" in result.output

    def test_app_list_subcommand(self, runner):
        """T158 – app list subcommand is documented."""
        result = runner.invoke(main, ["app", "--help"])
        assert "list" in result.output

    def test_app_focus_subcommand(self, runner):
        """T157 – app focus subcommand is documented (replaced switch)."""
        result = runner.invoke(main, ["app", "--help"])
        assert "focus" in result.output

    def test_app_window_commands_in_help(self, runner):
        """T170 – window operations appear under app group."""
        result = runner.invoke(main, ["app", "--help"])
        for cmd in ("focus", "close", "minimize", "maximize", "restore", "move", "windows"):
            assert cmd in result.output, f"'{cmd}' missing from app --help"

    def test_app_launch_args_option(self, runner):
        """T152 – app launch --args option is documented."""
        result = runner.invoke(main, ["app", "launch", "--help"])
        assert result.exit_code == 0
        assert "--args" in result.output

    def test_app_quit_force_option(self, runner):
        """T155 – app quit --force option is documented."""
        result = runner.invoke(main, ["app", "quit", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output

    def test_app_quit_pid_option(self, runner):
        """T154 – app quit --pid option is documented."""
        result = runner.invoke(main, ["app", "quit", "--help"])
        assert "--pid" in result.output

    def test_app_launch_json_option(self, runner):
        """T297 – app launch --json option is documented."""
        result = runner.invoke(main, ["app", "launch", "--help"])
        assert "--json" in result.output

    def test_app_list_json_option(self, runner):
        """T297 – app list --json option is documented."""
        result = runner.invoke(main, ["app", "list", "--help"])
        assert "--json" in result.output

    def test_app_launch_no_name_fails(self, runner):
        """T150 – app launch with no name should fail."""
        result = runner.invoke(main, ["app", "launch"])
        assert result.exit_code != 0

    def test_app_quit_no_name_fails(self, runner):
        """T154 – app quit with no name should fail."""
        result = runner.invoke(main, ["app", "quit"])
        assert result.exit_code != 0

    def test_app_switch_no_name_fails(self, runner):
        """T157 – app switch with no name should fail."""
        result = runner.invoke(main, ["app", "switch"])
        assert result.exit_code != 0


# ── Window management method signatures ────────────────────────────────────────


class TestWindowManagementMethodSignatures:
    """T039, T044-T054: Window management methods (all platforms)."""

    def test_focus_window_method_exists(self):
        """T044 – focus_window method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "focus_window")

    def test_close_window_method_exists(self):
        """T045 – close_window method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "close_window")

    def test_minimize_window_method_exists(self):
        """T046 – minimize_window method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "minimize_window")

    def test_maximize_window_method_exists(self):
        """T047 – maximize_window method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "maximize_window")

    def test_move_window_method_exists(self):
        """T048 – move_window method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "move_window")

    def test_resize_window_method_exists(self):
        """T049 – resize_window method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "resize_window")

    def test_focus_window_signature(self):
        """T044 – focus_window accepts title and hwnd."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.focus_window)
        params = sig.parameters
        assert "title" in params
        assert "hwnd" in params

    def test_close_window_signature(self):
        """T045 – close_window accepts title and hwnd."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.close_window)
        params = sig.parameters
        assert "title" in params
        assert "hwnd" in params

    def test_minimize_window_signature(self):
        """T046 – minimize_window accepts title and hwnd."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.minimize_window)
        params = sig.parameters
        assert "title" in params
        assert "hwnd" in params

    def test_move_window_signature(self):
        """T048 – move_window accepts x, y, title, hwnd."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.move_window)
        params = sig.parameters
        assert "x" in params
        assert "y" in params
        assert "title" in params
        assert "hwnd" in params

    def test_resize_window_signature(self):
        """T049 – resize_window accepts width, height, title, hwnd."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.resize_window)
        params = sig.parameters
        assert "width" in params
        assert "height" in params
        assert "title" in params
        assert "hwnd" in params


# ── Window CLI option validation ───────────────────────────────────────────────


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
class TestWindowCLIOptions:
    """window CLI option validation (T039, T044-T054)."""

    def test_window_group_in_main_help(self, runner):
        """window group is in main help."""
        result = runner.invoke(main, ["--help"])
        assert "window" in result.output

    def test_window_close_subcommand(self, runner):
        """T045 – window close subcommand is documented."""
        result = runner.invoke(main, ["window", "--help"])
        assert result.exit_code == 0
        assert "close" in result.output

    def test_window_minimize_subcommand(self, runner):
        """T046 – window minimize subcommand is documented."""
        result = runner.invoke(main, ["window", "--help"])
        assert "minimize" in result.output

    def test_window_maximize_subcommand(self, runner):
        """T047 – window maximize subcommand is documented."""
        result = runner.invoke(main, ["window", "--help"])
        assert "maximize" in result.output

    def test_window_move_subcommand(self, runner):
        """T048 – window move subcommand is documented."""
        result = runner.invoke(main, ["window", "--help"])
        assert "move" in result.output

    def test_window_resize_subcommand(self, runner):
        """T049 – window resize subcommand is documented."""
        result = runner.invoke(main, ["window", "--help"])
        assert "resize" in result.output

    def test_window_set_bounds_subcommand(self, runner):
        """T054 – window set-bounds subcommand is documented."""
        result = runner.invoke(main, ["window", "--help"])
        assert "set-bounds" in result.output

    def test_window_focus_subcommand(self, runner):
        """T044 – window focus subcommand is documented."""
        result = runner.invoke(main, ["window", "--help"])
        assert "focus" in result.output

    def test_window_list_subcommand(self, runner):
        """T039 – window list subcommand is documented."""
        result = runner.invoke(main, ["window", "--help"])
        assert "list" in result.output

    def test_window_move_requires_x_y(self, runner):
        """T048 – window move without --x and --y should fail."""
        result = runner.invoke(main, ["window", "move"])
        assert result.exit_code != 0

    def test_window_resize_requires_width_height(self, runner):
        """T049 – window resize without --width and --height should fail."""
        result = runner.invoke(main, ["window", "resize"])
        assert result.exit_code != 0

    def test_window_set_bounds_x_option(self, runner):
        """T054 – window set-bounds --x is documented."""
        result = runner.invoke(main, ["window", "set-bounds", "--help"])
        assert "--x" in result.output

    def test_window_set_bounds_y_option(self, runner):
        """T054 – window set-bounds --y is documented."""
        result = runner.invoke(main, ["window", "set-bounds", "--help"])
        assert "--y" in result.output

    def test_window_set_bounds_width_option(self, runner):
        """T054 – window set-bounds --width is documented."""
        result = runner.invoke(main, ["window", "set-bounds", "--help"])
        assert "--width" in result.output

    def test_window_set_bounds_height_option(self, runner):
        """T054 – window set-bounds --height is documented."""
        result = runner.invoke(main, ["window", "set-bounds", "--help"])
        assert "--height" in result.output


# ── UWP deduplication unit test (all platforms, mocked) ───────────────────────


class TestUwpAppListDedup:
    """Regression test for #244 — UWP app list deduplication."""

    def test_uwp_duplicate_pid_title_deduplicated(self):
        """list_apps should not list the same UWP app twice when it has
        multiple top-level windows with identical PID and title (#244)."""
        from unittest.mock import patch, PropertyMock
        from naturo.backends.windows import WindowsBackend
        from naturo.backends.base import WindowInfo as BaseWindowInfo

        # Two Calculator windows with same PID and title (UWP duplicate)
        # Plus one 设置 window with same PID but different title (should keep)
        # Use ntpath-style basename via patch so os.path.basename works
        # cross-platform in the test.
        afh = "ApplicationFrameHost.exe"
        fake_windows = [
            BaseWindowInfo(
                handle=0x1001, title="计算器",
                process_name=afh,
                pid=9984, x=0, y=0, width=400, height=500,
                is_visible=True, is_minimized=False,
            ),
            BaseWindowInfo(
                handle=0x1002, title="计算器",
                process_name=afh,
                pid=9984, x=0, y=0, width=400, height=500,
                is_visible=True, is_minimized=False,
            ),
            BaseWindowInfo(
                handle=0x1003, title="设置",
                process_name=afh,
                pid=9984, x=0, y=0, width=600, height=700,
                is_visible=True, is_minimized=False,
            ),
        ]

        backend = WindowsBackend.__new__(WindowsBackend)
        with patch.object(backend, "list_windows", return_value=fake_windows):
            apps = backend.list_apps()

        uwp_names = [a["name"] for a in apps]
        assert uwp_names.count("计算器") == 1, (
            f"Calculator should appear once, got {uwp_names.count('计算器')}"
        )
        assert "设置" in uwp_names, "设置 should still appear"


# ── Windows-only functional tests ─────────────────────────────────────────────


@pytest.mark.ui
@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="App control functional tests require Windows with desktop session",
)
class TestAppControlFunctionalWindows:
    """T150-T158 – Windows functional app control tests."""

    def test_app_list_returns_list(self):
        """T158 – list_apps returns a list."""
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        apps = backend.list_apps()
        assert isinstance(apps, list)

    def test_app_list_items_have_name(self):
        """T158 – list_apps items have a name field."""
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        apps = backend.list_apps()
        if apps:
            assert "name" in apps[0] or hasattr(apps[0], "name")

    def test_cli_app_list_runs(self, runner):
        """T158 – naturo app list runs on Windows."""
        result = runner.invoke(main, ["app", "list"])
        assert result.exit_code == 0


def _window_management_implemented():
    """Check if window management methods are implemented (not placeholder stubs)."""
    try:
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        backend.close_window(hwnd=0)
        return True
    except NotImplementedError:
        return False
    except Exception:
        return True  # Other errors mean it's implemented


@pytest.mark.e2e
@pytest.mark.ui
@pytest.mark.skipif(
    platform.system() != "Windows" or not _window_management_implemented(),
    reason="E2E app control tests require Windows with implemented window management methods",
)
@pytest.mark.skipif(
    os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true",
    reason="Requires interactive desktop session (not available in CI)",
)
class TestAppLifecycleE2EWindows:
    """T039 – Window lifecycle E2E: launch → appears → close → disappears."""

    @pytest.mark.xfail(reason="window close/minimize not yet implemented", raises=NotImplementedError)
    def test_notepad_lifecycle(self):
        """T039 – launch notepad, verify in list, close, verify gone."""
        import subprocess
        import time
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()

        proc = subprocess.Popen(["notepad.exe"])
        try:
            time.sleep(1.5)

            windows = backend.list_windows()
            notepad_wins = [
                w for w in windows
                if "notepad" in w.process_name.lower() and w.is_visible
            ]
            assert len(notepad_wins) >= 1, "Notepad not found in window list after launch"

            handle = notepad_wins[0].handle
            backend.close_window(hwnd=handle)
            time.sleep(1.0)

            windows_after = backend.list_windows()
            still_open = [
                w for w in windows_after
                if w.handle == handle
            ]
            assert len(still_open) == 0, "Notepad window still in list after close"

        finally:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                pass

    @pytest.mark.xfail(reason="window minimize not yet implemented", raises=NotImplementedError)
    def test_window_minimize_restore_cycle(self):
        """T052 – minimize then restore window state transition."""
        import subprocess
        import time
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()

        proc = subprocess.Popen(["notepad.exe"])
        try:
            time.sleep(1.5)

            windows = backend.list_windows()
            notepad = next(
                (w for w in windows if "notepad" in w.process_name.lower() and w.is_visible),
                None
            )
            assert notepad is not None

            # Minimize
            backend.minimize_window(hwnd=notepad.handle)
            time.sleep(0.5)

            # Restore / focus
            backend.focus_window(hwnd=notepad.handle)
            time.sleep(0.5)

            windows_after = backend.list_windows()
            target = next((w for w in windows_after if w.handle == notepad.handle), None)
            assert target is not None

        finally:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                pass


# ── _match_windows helper tests (fixes #151) ─────────────────────────────────


class _FakeWindow:
    """Minimal window stub for testing _match_windows."""

    def __init__(self, process_name: str, title: str, pid: int):
        self.process_name = process_name
        self.title = title
        self.pid = pid
        self.handle = 0


class TestMatchWindows:
    """Unit tests for the _match_windows helper that excludes the calling
    process and prioritizes process-name matches over title-only matches."""

    def test_excludes_own_pid(self):
        """Windows belonging to the calling process are excluded."""
        from naturo.cli.app_cmd import _match_windows

        own_pid = os.getpid()
        safe_pid = own_pid + 90000
        windows = [
            _FakeWindow("feishu", "Feishu Chat", safe_pid),
            _FakeWindow("cmd", "naturo app switch feishu", own_pid),
        ]
        matched = _match_windows(windows, "feishu")
        assert len(matched) == 1
        assert matched[0].process_name == "feishu"

    def test_excludes_parent_pid(self):
        """Windows belonging to the parent process are also excluded."""
        from naturo.cli.app_cmd import _match_windows

        parent_pid = os.getppid()
        safe_pid = os.getpid() + 90000
        windows = [
            _FakeWindow("feishu", "Feishu Chat", safe_pid),
            _FakeWindow("bash", "naturo app switch feishu", parent_pid),
        ]
        matched = _match_windows(windows, "feishu")
        assert len(matched) == 1
        assert matched[0].process_name == "feishu"

    def test_process_name_match_before_title_match(self):
        """Process-name matches appear before title-only matches."""
        from naturo.cli.app_cmd import _match_windows

        # Use PIDs that cannot collide with the test runner's own PID/PPID
        safe_pid_a = os.getpid() + 90000
        safe_pid_b = os.getpid() + 90001
        windows = [
            _FakeWindow("explorer", "feishu download folder", safe_pid_a),
            _FakeWindow("feishu", "Feishu Main Window", safe_pid_b),
        ]
        matched = _match_windows(windows, "feishu")
        assert len(matched) == 2
        assert matched[0].process_name == "feishu"
        assert matched[1].process_name == "explorer"

    def test_no_match_returns_empty(self):
        """When nothing matches, an empty list is returned."""
        from naturo.cli.app_cmd import _match_windows

        windows = [_FakeWindow("notepad", "Untitled - Notepad", os.getpid() + 90002)]
        assert _match_windows(windows, "feishu") == []

    def test_case_insensitive_matching(self):
        """Matching is case-insensitive."""
        from naturo.cli.app_cmd import _match_windows

        windows = [_FakeWindow("Feishu", "FEISHU Chat", os.getpid() + 90003)]
        matched = _match_windows(windows, "feishu")
        assert len(matched) == 1
