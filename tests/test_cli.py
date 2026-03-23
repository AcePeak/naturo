"""Test CLI commands — verify all commands are registered with correct params."""
import platform
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
        "capture", "list", "see",
        # Interaction
        "click", "type", "press", "hotkey", "scroll", "drag", "move",
        # System
        "app",
        # Snapshot & Phase 3
        "snapshot", "wait", "diff",
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
    assert "--window" in result.output
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
    assert "--window" in result.output
    assert "--mode" in result.output
    assert "--path" in result.output
    assert "--annotate" in result.output
    assert "--json" in result.output


@pytest.mark.skip(reason="learn command removed in v0.2.0")
def test_learn_no_args(runner):
    result = runner.invoke(main, ["learn"])
    assert result.exit_code == 0
    assert "Naturo" in result.output


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
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
    assert "--window" in result.output
    # --wait-for is hidden (BUG-035: declared but not implemented)
    assert "--wait-for" not in result.output
    assert "--input-mode" in result.output
    assert "normal" in result.output
    assert "hardware" in result.output
    assert "hook" in result.output
    # --process-name is now a hidden alias for --app
    assert "--process-name" not in result.output
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
    # --process-name is now a hidden alias for --app
    assert "--process-name" not in result.output
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


@pytest.mark.skip(reason="paste command removed in v0.2.0")
def test_paste_help(runner):
    result = runner.invoke(main, ["paste", "--help"])
    assert result.exit_code == 0
    assert "--restore" in result.output


# ── System commands ─────────────────────────────


def test_app_help(runner):
    result = runner.invoke(main, ["app", "--help"])
    assert result.exit_code == 0
    for sub in ["launch", "quit", "relaunch", "list", "find"]:
        assert sub in result.output, f"Missing app subcommand: {sub}"


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
def test_window_help(runner):
    result = runner.invoke(main, ["window", "--help"])
    assert result.exit_code == 0
    for sub in ["close", "minimize", "maximize", "move", "resize", "set-bounds", "focus", "list"]:
        assert sub in result.output, f"Missing window subcommand: {sub}"


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
def test_menu_help(runner):
    result = runner.invoke(main, ["menu", "--help"])
    assert result.exit_code == 0
    assert "click" in result.output
    assert "list" in result.output


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
@pytest.mark.skip(reason="clipboard command removed in v0.2.0")
def test_clipboard_help(runner):
    result = runner.invoke(main, ["clipboard", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output
    assert "set" in result.output


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
def test_dialog_help(runner):
    result = runner.invoke(main, ["dialog", "--help"])
    assert result.exit_code == 0
    assert "--action" in result.output
    assert "--button" in result.output


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
@pytest.mark.skip(reason="open command removed in v0.2.0")
def test_open_help(runner):
    result = runner.invoke(main, ["open", "--help"])
    assert result.exit_code == 0
    assert "TARGET" in result.output


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
def test_taskbar_help(runner):
    result = runner.invoke(main, ["taskbar", "--help"])
    assert result.exit_code == 0
    assert "pin" in result.output
    assert "unpin" in result.output
    assert "list" in result.output


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
def test_tray_help(runner):
    result = runner.invoke(main, ["tray", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "click" in result.output


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
def test_desktop_help(runner):
    result = runner.invoke(main, ["desktop", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output
    assert "switch" in result.output
    assert "close" in result.output


# ── AI commands ─────────────────────────────────


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
@pytest.mark.skip(reason="agent command removed in v0.2.0")
def test_agent_help(runner):
    result = runner.invoke(main, ["agent", "--help"])
    assert result.exit_code == 0
    assert "INSTRUCTION" in result.output
    assert "--model" in result.output
    assert "--max-steps" in result.output
    assert "--dry-run" in result.output


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
def test_mcp_help(runner):
    result = runner.invoke(main, ["mcp", "--help"])
    assert result.exit_code == 0
    assert "start" in result.output
    assert "status" in result.output
    assert "stop" in result.output


# ── Extension commands ──────────────────────────


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
def test_excel_help(runner):
    result = runner.invoke(main, ["excel", "--help"])
    assert result.exit_code == 0
    assert "open-workbook" in result.output
    assert "read" in result.output
    assert "write" in result.output
    assert "run-macro" in result.output


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
def test_java_help(runner):
    result = runner.invoke(main, ["java", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "tree" in result.output
    assert "click" in result.output


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
def test_sap_help(runner):
    result = runner.invoke(main, ["sap", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "run" in result.output
    assert "get" in result.output
    assert "set" in result.output


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
@pytest.mark.skip(reason="registry command removed in v0.2.0")
def test_registry_help(runner):
    result = runner.invoke(main, ["registry", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output
    assert "set" in result.output
    assert "list" in result.output
    assert "delete" in result.output


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
@pytest.mark.skip(reason="service command removed in v0.2.0")
def test_service_help(runner):
    result = runner.invoke(main, ["service", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "start" in result.output
    assert "stop" in result.output
    assert "restart" in result.output
    assert "status" in result.output


# ── Placeholder execution ──────────────────────


def _has_gui_backend() -> bool:
    """True when a GUI automation backend is available (Windows always, macOS with peekaboo)."""
    system = platform.system()
    if system == "Windows":
        return True
    if system == "Darwin":
        import shutil
        return shutil.which("peekaboo") is not None
    return False


_GUI = _has_gui_backend()


def _has_desktop_session() -> bool:
    """Detect whether we have an interactive desktop session on Windows.

    SSH sessions (SESSIONNAME='') without an active console session cannot
    perform screen capture or SendInput.  RDP sessions (SESSIONNAME like
    'RDP-Tcp#N') and console sessions (SESSIONNAME='Console') can.
    """
    if platform.system() != "Windows":
        return False
    import os
    session = os.environ.get("SESSIONNAME", "")
    # Console or RDP sessions have desktop access
    if session == "Console" or session.startswith("RDP-Tcp"):
        return True
    # SSH sessions: SESSIONNAME is empty or 'Services' — no desktop
    # Even if explorer.exe is running, SendInput/capture may not work
    # in a different session
    return False


def _expected_see_exit() -> int:
    """Return expected exit code for ``see`` with no args.

    On Windows ``see`` succeeds (0) — UIA works even in headless/CI
    sessions (SESSIONNAME='Services').  On non-Windows it returns 1
    (no Windows backend).
    """
    return 0 if platform.system() == "Windows" else 1


@pytest.mark.parametrize("cmd,expected_exit", [
    (["see"], _expected_see_exit()),
    pytest.param(["capture", "live"], 0, marks=pytest.mark.skipif(platform.system() != "Windows", reason="capture live needs desktop session")),
])
def test_placeholder_commands_run(runner, cmd, expected_exit):
    """Commands with no required args should run and show placeholder message."""
    result = runner.invoke(main, cmd)
    assert result.exit_code == expected_exit


def test_scroll_no_args_runs(runner):
    """scroll with no args uses defaults (down, 3 notches) — may fail on non-Windows
    backends, but must not crash with an unhandled exception."""
    result = runner.invoke(main, ["scroll"])
    # exit_code 0 on Windows, non-zero on non-Windows (backend not implemented)
    # What matters: no unhandled Python exception (no traceback in output)
    assert "Traceback" not in result.output
