"""CLI error output helpers with agent-friendly recovery hints.

Provides a consistent way to output JSON error responses from CLI commands,
including suggested_action and recoverable fields that help AI agents
self-correct when operations fail.

Phase 4.7 — Agent-friendly Error Messages.
"""

from __future__ import annotations

from naturo.cli._jsonio import json_dumps
import sys
from typing import Any, Callable, Iterable, NoReturn, Optional, TypeVar

import click

from naturo.errors import NaturoError, category_for_code

_CommandT = TypeVar("_CommandT", bound=click.Command)


def success_envelope(collection_key: str, items: Iterable[Any]) -> dict[str, Any]:
    """Build the canonical ``-j`` success envelope for a collection read.

    Every ``list``-style command that returns a collection under ``-j`` must emit
    the same three-key shape so scripters and AI agents can rely on it. Routing
    those callsites through this single helper keeps the shape from drifting (see
    issue #979) — the matching contract test in ``tests/test_json_envelope_contract``
    pins it.

    Args:
        collection_key: Top-level key under which the collection is published
            (e.g. ``"selectors"``, ``"baselines"``, ``"recordings"``).
        items: The collection to publish. Materialised into a fresh list so the
            envelope never aliases (or is mutated by) the caller's sequence.

    Returns:
        A dict ``{"success": True, collection_key: [...], "count": len([...])}``,
        with keys in that exact order, ready for ``json_dumps``.
    """
    materialised = list(items)
    return {"success": True, collection_key: materialised, "count": len(materialised)}


def collection_read(collection_key: str) -> Callable[[_CommandT], _CommandT]:
    """Tag a Click command as a ``-j`` collection read for the contract test.

    The decorator records ``collection_key`` on the command object so the
    self-maintaining contract test can auto-enumerate the Click tree and assert
    every tagged command emits :func:`success_envelope`'s canonical shape. It does
    not alter the command's behaviour.

    Apply it *above* ``@click.command`` so it receives the constructed command::

        @collection_read("selectors")
        @click.command("list")
        def selector_list(...): ...

    Args:
        collection_key: The top-level collection key the command publishes; must
            match the key it passes to :func:`success_envelope`.

    Returns:
        A decorator that annotates the command and returns it unchanged.
    """

    def decorator(command: _CommandT) -> _CommandT:
        command._naturo_collection_key = collection_key  # type: ignore[attr-defined]
        return command

    return decorator

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
    "INVALID_TEMPLATE": (
        "The --image template file exists but could not be decoded. Check that it "
        "is a valid PNG/JPG image smaller than the target window/screen.",
        False,
    ),
    "INVALID_SCREENSHOT": (
        "The --screenshot file exists but could not be decoded. Check that it is a "
        "valid PNG/JPG screenshot to match against.",
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
    "STALE_SNAPSHOT_CACHE": (
        "Run 'naturo see' to capture a fresh element snapshot, then retry.",
        True,
    ),
    "RECORDING_NOT_FOUND": (
        "Recording not found. Use 'naturo record list' to see saved recordings.",
        False,
    ),
    "SELECTOR_NOT_FOUND": (
        "Selector not found. Use 'naturo selector list' to see saved selectors, "
        "or 'naturo selector list --builtin' for built-in templates.",
        False,
    ),
    # find/click/type --selector resolution faults (#1182/#1183). SELECTOR_REF_ERROR
    # reaches parity with SELECTOR_NOT_FOUND's guidance (same condition, different
    # entry point); INVALID_SELECTOR points at the selector grammar; TREE_ERROR is a
    # transient automation fault worth retrying once the window is confirmed present.
    "SELECTOR_REF_ERROR": (
        "The saved selector reference (@app/name) could not be resolved. Use "
        "'naturo selector list' to see saved selectors, or 'naturo selector list "
        "--builtin' for built-in templates.",
        False,
    ),
    "INVALID_SELECTOR": (
        "The selector string is malformed. Check the selector syntax — e.g. "
        "'Role:Name', '//Button[@name=\"OK\"]', or '@app/saved-name'. Use --help "
        "for the supported selector formats.",
        False,
    ),
    "TREE_ERROR": (
        "Failed to read the UI tree while resolving the selector. Ensure the target "
        "window is open and responsive (use 'naturo list windows' to verify), then "
        "retry.",
        True,
    ),
    "BASELINE_NOT_FOUND": (
        "Visual baseline not found. Use 'naturo visual list' to see saved baselines, "
        "or 'naturo visual baseline <name> --from <image>' to create one.",
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
    "SCREENSHOT_FAILED": (
        "Browser screenshot failed. Ensure the page has finished loading and the "
        "target element is visible (not display:none or zero-area), then retry. "
        "Use 'naturo browser screenshot' without --selector to capture the viewport.",
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
    "OCR_NOT_AVAILABLE": (
        "The optional OCR engine is not installed. Install it with "
        "'pip install naturo[ocr]' (RapidOCR — offline, bundled ONNX models), "
        "then retry 'naturo find --ocr'.",
        True,
    ),
    "OCR_FAILED": (
        "OCR text recognition failed. Verify the target window/screenshot is "
        "readable and contains visible text, then retry. For a saved image use "
        "'naturo find --ocr <text> --screenshot <file>'.",
        True,
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
        "The application is not Electron-based. Try using Playwright or "
        "browser automation tools for Electron/Chrome apps.",
        False,
    ),
    "NO_DEBUG_PORT": (
        "The Electron app is running but without remote debugging. Try "
        "restarting it with --remote-debugging-port=9229. Use Playwright "
        "or browser automation tools for CDP access.",
        True,
    ),
    "ELECTRON_ERROR": (
        "An error occurred during Electron app detection. Try using "
        "Playwright or browser automation tools for Electron/Chrome apps.",
        True,
    ),
    "BROWSER_CONNECTION_ERROR": (
        "Start Chrome/Chromium/Edge with --remote-debugging-port=<port> "
        "and retry. Check that the port number matches.",
        True,
    ),
}


def build_error_object(
    code: str,
    message: str,
    *,
    category: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
    suggested_action: Optional[str] = None,
    recoverable: Optional[bool] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build the canonical six-key ``error`` object (without the envelope wrapper).

    This is the single source of truth for the *shape* of the ``error`` member —
    ``code``, ``message``, ``category``, ``context``, ``suggested_action`` and
    ``recoverable``, in that order, identical to
    :meth:`naturo.errors.NaturoError.to_dict` (#884). :func:`json_error` wraps the
    result in the ``{"success": False, "error": ...}`` envelope, but a command that
    has *already* built a partial result dict and needs to merge in a standard
    error block — without raising through ``json_error`` — calls this directly. For
    example ``wait`` reports a predicate **timeout** as ``success:false`` without
    raising, so it attaches the block to its existing ``mode``/``wait_time`` payload
    rather than discarding those keys (issue #1089).

    If ``category``, ``suggested_action`` or ``recoverable`` are not provided, they
    are resolved from the error code: the category from
    :func:`naturo.errors.category_for_code`, and the recovery hint/recoverability
    from the local registry.

    Args:
        code: Error code string (e.g., 'INVALID_INPUT', 'TIMEOUT').
        message: Human-readable error message.
        category: Error class (environment/validation/automation/...). Resolved
            from the code when None, defaulting to 'unknown'.
        context: Structured detail for the error. Defaults to an empty dict.
        suggested_action: Recovery hint for AI agents (auto-populated if None;
            may remain ``null`` when the code has no registered hint).
        recoverable: Whether retrying might help (auto-populated if None).
        extra: Additional key-value pairs to merge into the error object on top of
            the canonical keys.

    Returns:
        The ``error`` object as a dict, ready to embed in a JSON response.
    """
    # Look up defaults from registry
    hint_action, hint_recoverable = _RECOVERY_HINTS.get(code, (None, False))

    action = suggested_action if suggested_action is not None else hint_action
    is_recoverable = recoverable if recoverable is not None else hint_recoverable

    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "category": category if category is not None else category_for_code(code),
        "context": context if context is not None else {},
        "suggested_action": action,
        "recoverable": bool(is_recoverable),
    }

    if extra:
        error.update(extra)

    return error


def json_error(
    code: str,
    message: str,
    *,
    category: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
    suggested_action: Optional[str] = None,
    recoverable: Optional[bool] = None,
    extra: Optional[dict[str, Any]] = None,
) -> str:
    """Build a JSON error response string in the canonical envelope shape.

    Every command's ``-j`` error path funnels through here, so the emitted shape
    is the single source of truth for the CLI error contract. The ``error`` object
    always carries the same six keys, in the same order, as
    :meth:`naturo.errors.NaturoError.to_json_response` — ``code``, ``message``,
    ``category``, ``context``, ``suggested_action`` and ``recoverable`` — so a
    scripted consumer can rely on every field being present regardless of which
    command failed or whether the code is recognised (see issue #884). Unspecified
    fields fall back to sensible defaults rather than being omitted.

    If ``category``, ``suggested_action`` or ``recoverable`` are not provided, they
    are resolved from the error code: the category from
    :func:`naturo.errors.category_for_code`, and the recovery hint/recoverability
    from the local registry.

    Args:
        code: Error code string (e.g., 'INVALID_INPUT', 'WINDOW_NOT_FOUND').
        message: Human-readable error message.
        category: Error class (environment/validation/automation/...). Resolved
            from the code when None, defaulting to 'unknown'.
        context: Structured detail for the error. Defaults to an empty dict.
        suggested_action: Recovery hint for AI agents (auto-populated if None;
            may remain ``null`` when the code has no registered hint).
        recoverable: Whether retrying might help (auto-populated if None).
        extra: Additional key-value pairs to merge into the error object on top of
            the canonical keys.

    Returns:
        JSON string ready for click.echo().
    """
    error = build_error_object(
        code,
        message,
        category=category,
        context=context,
        suggested_action=suggested_action,
        recoverable=recoverable,
        extra=extra,
    )
    return json_dumps({"success": False, "error": error})


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
        # to_json_response() already yields the canonical six-key envelope, so the
        # exception path and the raw-code path emit an identical shape (#884).
        return json_dumps(exc.to_json_response())

    return json_error("UNKNOWN_ERROR", str(exc))


def emit_error(
    code: str,
    message: str,
    json_output: bool,
    *,
    suggested_action: Optional[str] = None,
    recoverable: Optional[bool] = None,
    exit_code: int = 1,
) -> NoReturn:
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
) -> NoReturn:
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
