"""CLI error output helpers with agent-friendly recovery hints.

Provides a consistent way to output JSON error responses from CLI commands,
including suggested_action and recoverable fields that help AI agents
self-correct when operations fail.

Phase 4.7 — Agent-friendly Error Messages.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

import click

from naturo.errors import NaturoError

# ── Recovery hint registry ───────────────────────────────────────────────────
# Maps error codes to (suggested_action, recoverable) when we don't have a
# NaturoError instance but only a raw code string.

_RECOVERY_HINTS: dict[str, tuple[str, bool]] = {
    "INVALID_INPUT": (
        "Check the parameter values and constraints. Use --help to see valid options.",
        False,
    ),
    "INVALID_COORDINATES": (
        "Coordinates may be out of screen bounds. Use 'naturo capture live' to check "
        "the screen resolution and verify the target position.",
        False,
    ),
    "APP_NOT_FOUND": (
        "The application is not running. Use 'naturo app list' to see running apps, "
        "or 'naturo app launch <name>' to start it.",
        True,
    ),
    "WINDOW_NOT_FOUND": (
        "No matching window found. Use 'naturo list windows' to see available windows, "
        "or launch the application first.",
        True,
    ),
    "DIALOG_NOT_FOUND": (
        "No active dialog detected. The dialog may have already closed, or none was triggered. "
        "Use 'naturo dialog detect' to check, or trigger the dialog first.",
        True,
    ),
    "ELEMENT_NOT_FOUND": (
        "UI element not found in the tree. Try: 1) 'naturo see' to inspect the current "
        "UI, 2) use a different selector format (Role:Name), 3) 'naturo wait --element' "
        "to wait for it to appear.",
        True,
    ),
    "MENU_NOT_FOUND": (
        "Menu item not found. Use 'naturo menu-inspect --app <name>' to see the "
        "application's menu structure.",
        True,
    ),
    "SNAPSHOT_NOT_FOUND": (
        "Snapshot ID not found. Use 'naturo snapshot list' to see available snapshots.",
        False,
    ),
    "FILE_NOT_FOUND": (
        "The specified file does not exist. Check the file path.",
        False,
    ),
    "CAPTURE_ERROR": (
        "Screenshot capture failed. Ensure the target window is not minimized and "
        "exists. Use 'naturo list windows' to verify.",
        True,
    ),
    "CAPTURE_FAILED": (
        "Screenshot capture failed. Ensure the target window is not minimized. "
        "Use 'naturo list windows' to verify.",
        True,
    ),
    "TIMEOUT": (
        "Operation timed out. Try: 1) increase --timeout, 2) verify the target window "
        "is in the foreground, 3) take a screenshot to check the current UI state.",
        True,
    ),
    "VERIFICATION_FAILED": (
        "The action was sent but had no detectable effect. The target element's state "
        "did not change. Possible causes: 1) wrong window is focused, 2) the element "
        "is not editable/clickable, 3) running in a non-interactive session (schtasks). "
        "Use --no-verify to skip verification, or use --see to inspect the UI state.",
        True,
    ),
    "NO_DESKTOP_SESSION": (
        "No interactive desktop session. Connect via RDP or VNC to get a "
        "desktop session, or run naturo on the machine's physical console.",
        False,
    ),
    "PLATFORM_ERROR": (
        "This command requires a platform feature not available in the current "
        "environment. Naturo GUI commands require Windows with a desktop session.",
        False,
    ),
    "NOT_IMPLEMENTED": (
        "This feature is not yet implemented. Check the roadmap for availability.",
        False,
    ),
    "AI_PROVIDER_UNAVAILABLE": (
        "No AI provider available. Set an API key: ANTHROPIC_API_KEY, OPENAI_API_KEY, "
        "or configure a local Ollama server.",
        False,
    ),
    "AI_ANALYSIS_FAILED": (
        "AI analysis failed. Try: 1) a different provider (--provider), 2) a simpler "
        "prompt, 3) check API key validity.",
        True,
    ),
    "AGENT_ERROR": (
        "Agent execution failed. Try: 1) simplify the instruction, 2) increase "
        "--max-steps, 3) specify the target --app.",
        True,
    ),
    "SERVER_ERROR": (
        "MCP server error. If port is in use, try a different --port. "
        "Check that dependencies are installed with 'naturo mcp install'.",
        True,
    ),
    "MISSING_DEPENDENCY": (
        "Required dependency not installed. Run 'pip install naturo[mcp]' or "
        "'naturo mcp install' to install MCP dependencies.",
        False,
    ),
    "INSTALL_FAILED": (
        "Package installation failed. Check network connectivity and pip configuration.",
        True,
    ),
    "PROCESS_NOT_FOUND": (
        "Process not found. It may have already exited. Use 'naturo app list' to "
        "check running applications.",
        True,
    ),
    "VIRTUAL_DESKTOP_ERROR": (
        "Virtual desktop operation failed. Ensure running on Windows 10/11 with "
        "virtual desktop support. Use 'naturo desktop list' to check available desktops.",
        True,
    ),
    "DEPENDENCY_MISSING": (
        "A required dependency is not installed. Run the suggested install command (e.g. 'pip install pyvda').",
        False,
    ),
    "PERMISSION_DENIED": (
        "Insufficient permissions. On Windows, try running as Administrator. "
        "Ensure accessibility permissions are granted.",
        False,
    ),
    "WINDOW_OPERATION_FAILED": (
        "Window operation failed. The window may have closed or changed state. "
        "Use 'naturo list windows' to verify the window still exists.",
        True,
    ),
    "REGISTRY_NOT_FOUND": (
        "Registry key or value not found. Use 'naturo registry list <path>' to "
        "browse available keys and values.",
        False,
    ),
    "REGISTRY_ERROR": (
        "Registry operation failed. Check the key path format (e.g., "
        "HKCU\\Software\\MyApp) and ensure you have the required permissions.",
        True,
    ),
    "REGISTRY_HAS_SUBKEYS": (
        "Cannot delete a key that has subkeys. Try running the command again "
        "with --recursive to delete the key and all its subkeys.",
        False,
    ),
    "SERVICE_NOT_FOUND": (
        "Service not found. Use 'naturo service list' to see available services. "
        "Use the short service name (e.g., 'Spooler'), not the display name.",
        False,
    ),
    "SERVICE_ERROR": (
        "Service operation failed. Ensure you have the required permissions "
        "(run as Administrator for start/stop operations).",
        True,
    ),
    "SERVICE_ALREADY_RUNNING": (
        "The service is already running. Use 'naturo service status <name>' to check.",
        False,
    ),
    "SERVICE_ALREADY_STOPPED": (
        "The service is already stopped. Use 'naturo service status <name>' to check.",
        False,
    ),
    "SERVICE_START_FAILED": (
        "Failed to start the service. Ensure you're running as Administrator "
        "and the service is properly configured. Check dependencies with "
        "'naturo service status <name>'.",
        True,
    ),
    "SERVICE_STOP_FAILED": (
        "Failed to stop the service. Try running as Administrator, or check "
        "for dependent services that must be stopped first.",
        True,
    ),
    "NOT_ELECTRON": (
        "The application is not Electron-based. Try running "
        "`naturo electron list` to see detected Electron apps.",
        False,
    ),
    "NO_DEBUG_PORT": (
        "The Electron app is running but without remote debugging. Try "
        "restarting it with --remote-debugging-port=9229 or run "
        "`naturo electron launch <path> --port 9229`.",
        True,
    ),
    "ELECTRON_ERROR": (
        "An error occurred during Electron app detection. Check that the "
        "application is running and try `naturo electron detect <app>`.",
        True,
    ),
}


def json_error(
    code: str,
    message: str,
    *,
    suggested_action: Optional[str] = None,
    recoverable: Optional[bool] = None,
    extra: Optional[dict[str, Any]] = None,
) -> str:
    """Build a JSON error response string with agent-friendly recovery hints.

    If suggested_action or recoverable are not provided, looks up defaults
    from the recovery hint registry based on the error code.

    Args:
        code: Error code string (e.g., 'INVALID_INPUT', 'WINDOW_NOT_FOUND').
        message: Human-readable error message.
        suggested_action: Recovery hint for AI agents (auto-populated if None).
        recoverable: Whether retrying might help (auto-populated if None).
        extra: Additional key-value pairs to include in the error object.

    Returns:
        JSON string ready for click.echo().
    """
    error: dict[str, Any] = {"code": code, "message": message}

    # Look up defaults from registry
    hint_action, hint_recoverable = _RECOVERY_HINTS.get(code, (None, False))

    action = suggested_action if suggested_action is not None else hint_action
    is_recoverable = recoverable if recoverable is not None else hint_recoverable

    if action:
        error["suggested_action"] = action
    if is_recoverable:
        error["recoverable"] = True

    if extra:
        error.update(extra)

    return json.dumps({"success": False, "error": error})


def json_error_from_exception(exc: Exception) -> str:
    """Build a JSON error response from an exception.

    If the exception is a NaturoError, uses its structured fields directly.
    Otherwise, falls back to UNKNOWN_ERROR with the exception message.

    Args:
        exc: The exception to convert.

    Returns:
        JSON string ready for click.echo().
    """
    if isinstance(exc, NaturoError):
        error: dict[str, Any] = {
            "code": exc.code,
            "message": exc.message,
        }
        if exc.suggested_action:
            error["suggested_action"] = exc.suggested_action
        if exc.is_recoverable:
            error["recoverable"] = True
        if exc.context:
            error["context"] = exc.context
        return json.dumps({"success": False, "error": error})

    return json_error("UNKNOWN_ERROR", str(exc))


def emit_error(
    code: str,
    message: str,
    json_output: bool,
    *,
    suggested_action: Optional[str] = None,
    recoverable: Optional[bool] = None,
    exit_code: int = 1,
) -> None:
    """Emit an error message and exit.

    In JSON mode, outputs a structured error with recovery hints.
    In text mode, outputs "Error: <message>" to stderr.

    Args:
        code: Error code string.
        message: Human-readable error message.
        json_output: Whether to emit JSON.
        suggested_action: Override recovery hint.
        recoverable: Override recoverable flag.
        exit_code: Process exit code (default 1).
    """
    if json_output:
        click.echo(json_error(code, message,
                               suggested_action=suggested_action,
                               recoverable=recoverable))
    else:
        click.echo(f"Error: {message}", err=True)
    sys.exit(exit_code)


def emit_exception_error(
    exc: Exception,
    json_output: bool,
    *,
    fallback_code: str = "UNKNOWN_ERROR",
    exit_code: int = 1,
) -> None:
    """Emit an error from an exception and exit.

    If the exception is a NaturoError, uses its full structured data.
    Otherwise, uses the fallback_code with the exception message.

    Args:
        exc: The exception to report.
        json_output: Whether to emit JSON.
        fallback_code: Error code for non-NaturoError exceptions.
        exit_code: Process exit code (default 1).
    """
    if isinstance(exc, NaturoError):
        if json_output:
            click.echo(json_error_from_exception(exc))
        else:
            click.echo(f"Error: {exc.message}", err=True)
        sys.exit(exit_code)

    if json_output:
        click.echo(json_error(fallback_code, str(exc)))
    else:
        click.echo(f"Error: {str(exc)}", err=True)
    sys.exit(exit_code)
