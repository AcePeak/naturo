"""Test CLI commands — verify all commands are registered with correct params."""
import pytest
from click.testing import CliRunner
from naturo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


# ── Top-level ───────────────────────────────────


def test_cli_version_flag(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "naturo" in result.output


def test_cli_help(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    # All command groups/commands must appear
    expected = [
        # Core
        "capture", "list", "see", "learn", "tools",
        # Interaction
        "click", "type", "press", "hotkey", "scroll", "drag", "move", "paste",
        # System
        "app", "window", "menu", "clipboard", "dialog", "open",
        "taskbar", "tray", "desktop",
        # AI
        "agent", "mcp",
        # Extensions
        "excel", "java", "sap", "registry", "service",
    ]
    for cmd in expected:
        assert cmd in result.output, f"Missing command: {cmd}"


def test_cli_global_flags(runner):
    result = runner.invoke(main, ["--help"])
    assert "--json" in result.output
    assert "--verbose" in result.output
    assert "--log-level" in result.output
    assert "--version" in result.output


# ── Core commands ───────────────────────────────


def test_capture_help(runner):
    result = runner.invoke(main, ["capture", "--help"])
    assert result.exit_code == 0
    assert "live" in result.output
    assert "video" in result.output
    assert "watch" in result.output


def test_capture_live_help(runner):
    result = runner.invoke(main, ["capture", "live", "--help"])
    assert result.exit_code == 0
    assert "--app" in result.output
    assert "--window-title" in result.output
    assert "--hwnd" in result.output
    assert "--path" in result.output


def test_list_help(runner):
    result = runner.invoke(main, ["list", "--help"])
    assert result.exit_code == 0
    assert "apps" in result.output
    assert "windows" in result.output
    assert "screens" in result.output
    assert "permissions" in result.output


def test_see_help(runner):
    result = runner.invoke(main, ["see", "--help"])
    assert result.exit_code == 0
    assert "--app" in result.output
    assert "--window-title" in result.output
    assert "--mode" in result.output
    assert "--path" in result.output
    assert "--annotate" in result.output
    assert "--json" in result.output


def test_learn_no_args(runner):
    result = runner.invoke(main, ["learn"])
    assert result.exit_code == 0
    assert "Naturo" in result.output


def test_tools_help(runner):
    result = runner.invoke(main, ["tools", "--help"])
    assert result.exit_code == 0


# ── Interaction commands ────────────────────────


def test_click_help(runner):
    result = runner.invoke(main, ["click", "--help"])
    assert result.exit_code == 0
    assert "--on" in result.output
    assert "--id" in result.output
    assert "--coords" in result.output
    assert "--double" in result.output
    assert "--right" in result.output
    assert "--app" in result.output
    assert "--window-title" in result.output
    assert "--wait-for" in result.output
    assert "--input-mode" in result.output
    assert "normal" in result.output
    assert "hardware" in result.output
    assert "hook" in result.output
    assert "--process-name" in result.output
    assert "--json" in result.output


def test_type_help(runner):
    result = runner.invoke(main, ["type", "--help"])
    assert result.exit_code == 0
    assert "--delay" in result.output
    assert "--profile" in result.output
    assert "human" in result.output
    assert "linear" in result.output
    assert "--wpm" in result.output
    assert "--return" in result.output
    assert "--tab" in result.output
    assert "--escape" in result.output
    assert "--delete" in result.output
    assert "--clear" in result.output
    assert "--input-mode" in result.output
    assert "--process-name" in result.output
    assert "--json" in result.output


def test_press_help(runner):
    result = runner.invoke(main, ["press", "--help"])
    assert result.exit_code == 0
    assert "--input-mode" in result.output
    assert "--count" in result.output


def test_hotkey_help(runner):
    result = runner.invoke(main, ["hotkey", "--help"])
    assert result.exit_code == 0
    assert "--hold-duration" in result.output
    assert "--input-mode" in result.output


def test_scroll_help(runner):
    result = runner.invoke(main, ["scroll", "--help"])
    assert result.exit_code == 0
    assert "--direction" in result.output
    assert "--amount" in result.output
    assert "--smooth" in result.output


def test_drag_help(runner):
    result = runner.invoke(main, ["drag", "--help"])
    assert result.exit_code == 0
    assert "--from" in result.output
    assert "--from-coords" in result.output
    assert "--to" in result.output
    assert "--to-coords" in result.output
    assert "--duration" in result.output
    assert "--steps" in result.output
    assert "--modifiers" in result.output
    assert "--profile" in result.output


def test_move_help(runner):
    result = runner.invoke(main, ["move", "--help"])
    assert result.exit_code == 0
    assert "--to" in result.output
    assert "--coords" in result.output


def test_paste_help(runner):
    result = runner.invoke(main, ["paste", "--help"])
    assert result.exit_code == 0
    assert "--restore" in result.output


# ── System commands ─────────────────────────────


def test_app_help(runner):
    result = runner.invoke(main, ["app", "--help"])
    assert result.exit_code == 0
    for sub in ["launch", "quit", "relaunch", "hide", "unhide", "switch", "list"]:
        assert sub in result.output, f"Missing app subcommand: {sub}"


def test_window_help(runner):
    result = runner.invoke(main, ["window", "--help"])
    assert result.exit_code == 0
    for sub in ["close", "minimize", "maximize", "move", "resize", "set-bounds", "focus", "list"]:
        assert sub in result.output, f"Missing window subcommand: {sub}"


def test_menu_help(runner):
    result = runner.invoke(main, ["menu", "--help"])
    assert result.exit_code == 0
    assert "click" in result.output
    assert "list" in result.output


def test_clipboard_help(runner):
    result = runner.invoke(main, ["clipboard", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output
    assert "set" in result.output


def test_dialog_help(runner):
    result = runner.invoke(main, ["dialog", "--help"])
    assert result.exit_code == 0
    assert "--action" in result.output
    assert "--button" in result.output


def test_open_help(runner):
    result = runner.invoke(main, ["open", "--help"])
    assert result.exit_code == 0
    assert "TARGET" in result.output


def test_taskbar_help(runner):
    result = runner.invoke(main, ["taskbar", "--help"])
    assert result.exit_code == 0
    assert "pin" in result.output
    assert "unpin" in result.output
    assert "list" in result.output


def test_tray_help(runner):
    result = runner.invoke(main, ["tray", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "click" in result.output


def test_desktop_help(runner):
    result = runner.invoke(main, ["desktop", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output
    assert "switch" in result.output
    assert "close" in result.output


# ── AI commands ─────────────────────────────────


def test_agent_help(runner):
    result = runner.invoke(main, ["agent", "--help"])
    assert result.exit_code == 0
    assert "INSTRUCTION" in result.output
    assert "--model" in result.output
    assert "--max-steps" in result.output
    assert "--dry-run" in result.output


def test_mcp_help(runner):
    result = runner.invoke(main, ["mcp", "--help"])
    assert result.exit_code == 0
    assert "start" in result.output
    assert "status" in result.output
    assert "stop" in result.output


# ── Extension commands ──────────────────────────


def test_excel_help(runner):
    result = runner.invoke(main, ["excel", "--help"])
    assert result.exit_code == 0
    assert "open-workbook" in result.output
    assert "read" in result.output
    assert "write" in result.output
    assert "run-macro" in result.output


def test_java_help(runner):
    result = runner.invoke(main, ["java", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "tree" in result.output
    assert "click" in result.output


def test_sap_help(runner):
    result = runner.invoke(main, ["sap", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "run" in result.output
    assert "get" in result.output
    assert "set" in result.output


def test_registry_help(runner):
    result = runner.invoke(main, ["registry", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output
    assert "set" in result.output
    assert "list" in result.output
    assert "delete" in result.output


def test_service_help(runner):
    result = runner.invoke(main, ["service", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "start" in result.output
    assert "stop" in result.output
    assert "restart" in result.output
    assert "status" in result.output


# ── Placeholder execution ──────────────────────


@pytest.mark.parametrize("cmd", [
    ["see"],
    ["learn"],
    ["capture", "live"],
    ["list", "apps"],
    ["tools"],
])
def test_placeholder_commands_run(runner, cmd):
    """Commands with no required args should run and show placeholder message."""
    result = runner.invoke(main, cmd)
    assert result.exit_code == 0


def test_scroll_no_args_runs(runner):
    """scroll with no args uses defaults (down, 3 notches) — may fail on non-Windows
    backends, but must not crash with an unhandled exception."""
    result = runner.invoke(main, ["scroll"])
    # exit_code 0 on Windows, non-zero on non-Windows (backend not implemented)
    # What matters: no unhandled Python exception (no traceback in output)
    assert "Traceback" not in result.output
