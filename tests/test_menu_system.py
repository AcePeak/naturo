"""Tests for Phase 2 menu and system commands.

Tests are organized by category:
  - Method signature / API existence (all platforms)
  - CLI option validation (all platforms)
  - Windows-only functional tests guarded by @pytest.mark.ui
"""

from __future__ import annotations

import json
import platform

import pytest
from click.testing import CliRunner
from naturo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


# ── T170-T172: Menu method signatures ─────────────────────────────────────────


class TestMenuMethodSignatures:
    """Backend menu methods exist with correct signatures (all platforms)."""

    def test_menu_list_method_exists(self):
        """T170 – menu_list method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "menu_list")

    def test_menu_click_method_exists(self):
        """T171/T172 – menu_click method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "menu_click")

    def test_menu_list_signature(self):
        """T170 – menu_list accepts app param."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.menu_list)
        assert "app" in sig.parameters

    def test_menu_click_signature(self):
        """T171/T172 – menu_click accepts path and app params."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.menu_click)
        params = sig.parameters
        assert "path" in params
        assert "app" in params

    def test_win32_menu_methods_exist(self):
        """Win32 menu API methods exist on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "_get_menu_items_win32")
        assert hasattr(WindowsBackend, "_walk_win32_menu")
        assert hasattr(WindowsBackend, "_get_menu_items_uia")

    def test_get_menu_items_uses_resolve_hwnd(self):
        """get_menu_items resolves app name via _resolve_hwnd (fixes #158)."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        source = inspect.getsource(WindowsBackend.get_menu_items)
        assert "_resolve_hwnd" in source, (
            "get_menu_items should use _resolve_hwnd to respect --app flag"
        )

    def test_open_uri_method_exists(self):
        """T183 – open_uri method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "open_uri")

    def test_open_uri_signature(self):
        """T183/T184 – open_uri accepts uri param."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.open_uri)
        assert "uri" in sig.parameters


# ── Menu CLI option validation (all platforms) ────────────────────────────────


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
class TestMenuCLIOptions:
    """menu CLI option validation (T170-T172)."""

    def test_menu_group_in_main_help(self, runner):
        """menu group is in main help."""
        result = runner.invoke(main, ["--help"])
        assert "menu" in result.output

    def test_menu_click_subcommand(self, runner):
        """T171/T172 – menu click subcommand is documented."""
        result = runner.invoke(main, ["menu", "--help"])
        assert result.exit_code == 0
        assert "click" in result.output

    def test_menu_list_subcommand(self, runner):
        """T170 – menu list subcommand is documented."""
        result = runner.invoke(main, ["menu", "--help"])
        assert "list" in result.output

    def test_menu_click_app_option(self, runner):
        """T171 – menu click --app option is documented."""
        result = runner.invoke(main, ["menu", "click", "--help"])
        assert result.exit_code == 0
        assert "--app" in result.output

    def test_menu_click_path_argument(self, runner):
        """T172 – menu click PATH argument is documented."""
        result = runner.invoke(main, ["menu", "click", "--help"])
        assert "PATH" in result.output or "path" in result.output.lower()

    def test_menu_list_depth_option(self, runner):
        """T170 – menu list --depth option is documented."""
        result = runner.invoke(main, ["menu", "list", "--help"])
        assert "--depth" in result.output

    def test_menu_click_no_path_fails(self, runner):
        """T171 – menu click with no PATH should fail."""
        result = runner.invoke(main, ["menu", "click"])
        assert result.exit_code != 0

    def test_menu_click_json_option(self, runner):
        """T297 – menu click --json option is documented."""
        result = runner.invoke(main, ["menu", "click", "--help"])
        assert "--json" in result.output


# ── System CLI option validation (all platforms) ──────────────────────────────


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
# ── BUG-065/066/067: open command validation ──────────────────────────────────


# ── T297, T299: JSON output and exit codes ────────────────────────────────────


class TestCLIJsonAndExitCodes:
    """T297 – JSON output validation; T299 – exit code conventions."""

    def test_click_success_exit_zero(self, runner):
        """T299 – successful commands exit with code 0."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0

    def test_click_failure_exit_nonzero(self, runner):
        """T299 – failed commands exit with non-zero code."""
        result = runner.invoke(main, ["click"])  # no target
        assert result.exit_code != 0

    def test_version_json_not_required(self, runner):
        """T297 – version command outputs version string."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert len(result.output.strip()) > 0

    def test_system_commands_help_exit_zero(self, runner):
        """T299 – system commands --help exit 0."""
        commands = ["app"]
        for cmd in commands:
            result = runner.invoke(main, [cmd, "--help"])
            assert result.exit_code == 0, f"'{cmd} --help' exited {result.exit_code}"

    def test_type_json_output_structure(self, runner):
        """T297 – type error --json emits success+error structure."""
        # type with no text → error
        result = runner.invoke(main, ["type", "--json"])
        assert result.exit_code != 0
        output = result.output.strip()
        if output:
            try:
                data = json.loads(output)
                assert "success" in data
                assert data["success"] is False
            except json.JSONDecodeError:
                pass  # Non-JSON error output is also acceptable

    def test_drag_json_error_structure(self, runner):
        """T297 – drag error --json emits success+error structure."""
        result = runner.invoke(main, ["drag", "--json"])
        assert result.exit_code != 0
        output = result.output.strip()
        if output:
            try:
                data = json.loads(output)
                assert "success" in data
                assert data["success"] is False
            except json.JSONDecodeError:
                pass

    def test_move_json_error_structure(self, runner):
        """T297 – move error --json emits success+error structure."""
        result = runner.invoke(main, ["move", "--json"])
        assert result.exit_code != 0
        output = result.output.strip()
        if output:
            try:
                data = json.loads(output)
                assert "success" in data
            except json.JSONDecodeError:
                pass


# ── Windows-only open/menu functional tests ───────────────────────────────────


@pytest.mark.ui
@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Menu/system functional tests require Windows with desktop session",
)
class TestMenuSystemFunctionalWindows:
    """T170-T172, T183-T184 – Windows functional tests."""

    @pytest.mark.skip(reason="open command removed — Eyes+Hands focus")
    def test_open_uri_https(self, runner):
        """T183 – naturo open with HTTPS URL runs on Windows."""
        import time
        result = runner.invoke(main, ["open", "https://example.com"])
        assert result.exit_code == 0
        time.sleep(0.5)

    @pytest.mark.skip(reason="open command removed — Eyes+Hands focus")
    def test_open_file_path(self, runner):
        """T184 – naturo open with local file path runs on Windows."""
        import tempfile
        import os
        # Create a temp text file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("test")
            path = f.name
        try:
            result = runner.invoke(main, ["open", path])
            assert result.exit_code == 0
        finally:
            os.unlink(path)
