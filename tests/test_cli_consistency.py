"""Test that every exposed CLI command works (no "Not implemented" stubs visible)."""
import os
import platform
import re

import pytest
from click.testing import CliRunner
from naturo.cli import main


runner = CliRunner()

NOT_IMPLEMENTED_RE = re.compile(r"Not implemented yet", re.IGNORECASE)

# Commands that call DLL/UIA directly when invoked with no args — will segfault
# on Windows without an interactive desktop session.
_DESKTOP_REQUIRED_COMMANDS = {
    ("see",),
    ("scroll",),
    ("capture"),
    ("app", "list"),
    ("app", "focus"),
    ("app", "close"),
    ("app", "minimize"),
    ("app", "maximize"),
    ("app", "restore"),
    ("app", "switch"),
    ("app", "inspect"),
    ("app", "windows"),
    ("app", "launch"),
    ("app", "quit"),
    ("app", "relaunch"),
    ("find",),
    ("get",),
    ("click",),
    ("type",),
    ("press",),
    ("drag",),
    ("tray",),
    ("taskbar",),
    ("menu-inspect",),
    ("dialog",),
    ("highlight",),
    ("list", "apps"),
    ("list", "screens"),
}

_ON_CI = os.environ.get("CI") == "true"
# On CI, always skip desktop commands — GitHub Actions Windows runners
# have unreliable desktop sessions even when explorer.exe is running.
_NO_DESKTOP = _ON_CI and platform.system() == "Windows"


def _visible_subcommands(group, parent_args=None):
    """Yield (full_args_list, command) for every non-hidden leaf/group."""
    parent_args = parent_args or []
    for name, cmd in sorted(group.commands.items()):
        if getattr(cmd, "hidden", False):
            continue
        full = parent_args + [name]
        yield full, cmd
        # Recurse into subgroups
        if hasattr(cmd, "commands"):
            yield from _visible_subcommands(cmd, full)


def test_no_stub_in_help():
    """Top-level --help must not mention 'Not implemented'."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0, result.output
    assert not NOT_IMPLEMENTED_RE.search(result.output), (
        f"Top-level --help contains stub text:\n{result.output}"
    )


def test_all_visible_commands_respond():
    """Every visible command must produce --help output without 'Not implemented'."""
    for args, cmd in _visible_subcommands(main):
        help_args = args + ["--help"]
        result = runner.invoke(main, help_args)
        assert result.exit_code == 0, (
            f"naturo {' '.join(help_args)} failed (exit {result.exit_code}):\n{result.output}"
        )
        assert not NOT_IMPLEMENTED_RE.search(result.output), (
            f"naturo {' '.join(help_args)} contains stub text:\n{result.output}"
        )


def test_no_visible_command_prints_not_implemented():
    """Invoking any visible leaf command (with no args) must not print 'Not implemented'."""
    # Long-running server commands that take over stdio — skip bare invocation
    SKIP_BARE_INVOKE = {("mcp", "start")}
    skipped = []
    for args, cmd in _visible_subcommands(main):
        # Skip groups — they just show help when invoked bare
        if hasattr(cmd, "commands"):
            continue
        if tuple(args) in SKIP_BARE_INVOKE:
            continue
        # Skip desktop-dependent commands on headless CI to avoid DLL segfault (#296)
        if _NO_DESKTOP and tuple(args) in _DESKTOP_REQUIRED_COMMANDS:
            skipped.append(args)
            continue
        result = runner.invoke(main, args)
        # Some commands legitimately fail due to missing args or Windows-only —
        # that's fine. They just must NOT say "Not implemented".
        assert not NOT_IMPLEMENTED_RE.search(result.output), (
            f"naturo {' '.join(args)} returned stub text:\n{result.output}"
        )
    if skipped:
        pytest.skip(f"Skipped {len(skipped)} desktop-dependent commands on headless CI")


def test_hidden_stubs_return_error_exit_code():
    """BUG-046: Hidden stub commands must return exit code 1, not 0."""
    import json
    hidden_stubs = [
        # ["list", "screens"],  # Implemented in Phase 5A
        # ["list", "apps"],  # Now delegates to app list (#114)
        ["list", "permissions"],
        # ["capture", "video"],  # Removed in PR #325 (capture is now flat)
        # ["capture", "watch"],  # Removed in PR #325
    ]
    for args in hidden_stubs:
        # Plain mode: exit code must be non-zero
        result = runner.invoke(main, args)
        assert result.exit_code != 0, (
            f"naturo {' '.join(args)} returned exit code 0 (should be non-zero):\n{result.output}"
        )
        # JSON mode: must output valid JSON with success=false
        result_json = runner.invoke(main, args + ["--json"])
        assert result_json.exit_code != 0, (
            f"naturo {' '.join(args)} --json returned exit code 0:\n{result_json.output}"
        )
        parsed = json.loads(result_json.output.strip())
        assert parsed["success"] is False, (
            f"naturo {' '.join(args)} --json missing success=false:\n{result_json.output}"
        )
        assert parsed["error"]["code"] == "NOT_IMPLEMENTED", (
            f"naturo {' '.join(args)} --json wrong error code:\n{result_json.output}"
        )


def test_list_apps_delegates_to_app_list():
    """list apps should delegate to app list, not return NOT_IMPLEMENTED (#114)."""
    import json
    result = runner.invoke(main, ["list", "apps", "--json"])
    parsed = json.loads(result.output.strip())
    # On non-Windows, backend may return BACKEND_ERROR (expected).
    # The key check is that it never returns NOT_IMPLEMENTED.
    assert parsed.get("error", {}).get("code") != "NOT_IMPLEMENTED", (
        f"naturo list apps should not return NOT_IMPLEMENTED:\n{result.output}"
    )
    # On platforms with a backend, it should succeed
    if parsed.get("success") is True:
        assert "apps" in parsed or "windows" in parsed, (
            "Response should contain 'apps' or 'windows' key"
        )


def test_hidden_commands_not_in_help():
    """Hidden commands must not appear in any --help output."""
    # Check top level
    result = runner.invoke(main, ["--help"])
    # Known hidden top-level groups that were removed entirely
    for name in ["menu",
                 "excel", "java", "sap",
                 "tools"]:
        # These should not appear as commands in help
        # (they may appear in description text, so check the Commands section)
        lines = result.output.split("\n")
        in_commands = False
        for line in lines:
            if line.strip().startswith("Commands:"):
                in_commands = True
                continue
            if in_commands:
                # Each command line starts with spaces then the command name
                stripped = line.strip()
                cmd_name = stripped.split()[0] if stripped else ""
                assert cmd_name != name, (
                    f"Hidden group '{name}' is visible in top-level --help"
                )
