"""Naturo MCP Server — expose desktop automation as MCP tools.

Provides AI agents with structured access to Windows desktop automation:
capture, inspect, click, type, find elements, manage windows/apps.
"""
from __future__ import annotations

import functools
import io
import logging
import sys
from collections.abc import Sequence
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ContentBlock

from naturo.version import __version__
from naturo.backends.base import get_backend, Backend
from naturo.bridge import NaturoCoreError
from naturo.errors import ErrorCode, NaturoError
from naturo.process import launch_app as _launch_app

from naturo.mcp._capture import register_capture_tools
from naturo.mcp._window import register_window_tools
from naturo.mcp._inspect import register_inspect_tools
from naturo.mcp._input import register_input_tools
from naturo.mcp._app import register_app_tools
from naturo.mcp._wait import register_wait_tools
from naturo.mcp._snapshot import register_snapshot_tools
from naturo.mcp._clipboard import register_clipboard_tools
from naturo.mcp._dialog import register_dialog_tools
from naturo.mcp._system import register_system_tools
from naturo.mcp._excel import register_excel_tools

logger = logging.getLogger(__name__)

# The MCP envelope's generic "something broke" code.  Mirrors the CLI's
# catch-all; not part of the typed ErrorCode catalog because it carries no
# actionable meaning beyond "unexpected internal failure".
_INTERNAL_ERROR_CODE = "INTERNAL_ERROR"

# (#881) ``NaturoCoreError`` carries only an integer native code; translate it
# to the typed :class:`ErrorCode` catalog so MCP clients receive a documented
# ``error.code`` instead of an opaque ``INTERNAL_ERROR``.  Native codes ``-2``
# (System/COM error) and ``-4`` (buffer too small) have no more-specific typed
# peer and honestly remain the generic internal-error code.
_CORE_ERROR_CODE_MAP: dict[int, str] = {
    -1: ErrorCode.INVALID_INPUT,   # Invalid argument
    -3: ErrorCode.FILE_IO_ERROR,   # File I/O error
}


def _core_error_envelope(exc: NaturoCoreError) -> dict[str, Any]:
    """Build a leak-free MCP error envelope for a bridge ``NaturoCoreError``.

    The client-facing message uses the native error *description*
    (:attr:`NaturoCoreError.ERROR_MESSAGES`) rather than ``str(exc)``.  The
    latter embeds the failing call's context, which for keyboard/mouse
    operations includes a ``repr()`` of the arguments (e.g. ``key_press('F1')``);
    using only the description guarantees the message never exposes the
    ``NaturoCoreError`` class name or argument values (#881).

    Args:
        exc: The bridge error raised by a native ``naturo_core`` call.

    Returns:
        A ``{"success": False, "error": {"code", "message"}}`` envelope whose
        ``code`` is drawn from the typed :class:`ErrorCode` catalog when a
        specific peer exists, and :data:`_INTERNAL_ERROR_CODE` otherwise.
    """
    code = _CORE_ERROR_CODE_MAP.get(exc.code, _INTERNAL_ERROR_CODE)
    message = NaturoCoreError.ERROR_MESSAGES.get(exc.code, f"Unknown error ({exc.code})")
    return {"success": False, "error": {"code": code, "message": message}}


class _SanitizingFastMCP(FastMCP):
    """FastMCP subclass that sanitizes Pydantic parameter-validation errors (#844).

    FastMCP validates each tool's arguments with Pydantic *before* the tool
    function runs, so the ``_safe_tool`` decorator — which wraps the function
    body — never sees these failures.  When validation fails, ``Tool.run``
    wraps the Pydantic ``ValidationError`` in a :class:`ToolError` whose
    ``__cause__`` exposes an ``.errors()`` method, and the low-level MCP server
    renders that error's ``str()`` straight into the client-facing text —
    leaking the internal Pydantic model name (``launch_appArguments``), the raw
    error format, and the ``errors.pydantic.dev`` URL.

    Overriding :meth:`call_tool` is the only interception point that survives
    real JSON-RPC dispatch.  ``FastMCP.__init__`` registers ``self.call_tool``
    as the ``CallToolRequest`` handler while constructing the instance, so the
    bound method captured there must *already* be the sanitizing one — which a
    subclass override guarantees.  The previous approach (#853) reassigned
    ``server.call_tool`` after construction; that only rebound a Python
    attribute and never reached the handler the server actually invokes, so the
    leak persisted in production while a direct-call unit test passed.
    """

    async def call_tool(  # type: ignore[override]
        self, name: str, arguments: dict[str, Any],
    ) -> Sequence[ContentBlock] | dict[str, Any]:
        """Dispatch a tool call, replacing Pydantic validation leaks with clean text.

        Args:
            name: Name of the MCP tool being invoked.
            arguments: Raw arguments supplied by the client.

        Returns:
            The tool's content, exactly as :meth:`FastMCP.call_tool` returns it.

        Raises:
            ToolError: On failure.  When the failure is a Pydantic
                parameter-validation error, the message is sanitized via
                :func:`_format_tool_validation_error`; all other errors
                propagate unchanged so genuine failures stay diagnosable.
        """
        try:
            return await super().call_tool(name, arguments)
        except ToolError as exc:
            cause = exc.__cause__
            if cause is not None and hasattr(cause, "errors"):
                raise ToolError(_format_tool_validation_error(name, cause)) from None
            raise


def create_server(host: str = "localhost", port: int = 3100) -> FastMCP:
    """Create and configure the Naturo MCP server."""
    server = _SanitizingFastMCP(
        name="naturo",
        host=host,
        port=port,
        instructions=(
            "Naturo — Windows desktop automation engine. "
            "Use these tools to see, click, type, and automate Windows applications. "
            "Start with capture_screen or list_windows to understand the current state, "
            "then use find_element or see_ui_tree to locate UI elements, "
            "and interact with click, type_text, press_key, etc."
        ),
    )
    # (#873) Advertise naturo's own version in the MCP ``serverInfo`` handshake.
    # FastMCP exposes no ``version=`` argument and never forwards one to its
    # low-level ``Server``; left unset, the initialize handler falls back to the
    # installed ``mcp`` package version (e.g. ``1.26.0``), misleading clients
    # that branch on ``serverInfo.version`` for naturo capability detection.
    # Setting the low-level server's version is the only interception point.
    server._mcp_server.version = __version__

    def _get_backend() -> Backend:
        """Get the platform backend, raising clear errors.

        Performs the same ``NO_DESKTOP_SESSION`` pre-flight check the CLI uses
        (#885).  Every read/enumeration tool (``capture_screen``,
        ``list_windows``, ``list_apps``, ``app_inspect``, ``capture_window``,
        ``list_monitors``, …) obtains its backend through this single
        entrypoint, so guarding here makes wrong-data-on-no-session
        structurally impossible across the MCP surface — these tools previously
        returned fabricated success (black PNGs, real-looking window lists)
        with ``isError:false``.

        Raises:
            NoDesktopSessionError: If no interactive desktop session exists.
            NaturoError: If no backend is available for this platform.
        """
        from naturo.cli.interaction import _check_desktop_session
        _check_desktop_session()
        try:
            return get_backend()
        except RuntimeError as e:
            raise NaturoError(str(e))

    def _safe_tool(fn: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator: wraps MCP tool handlers with try/except to return structured errors."""
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except NaturoError as e:
                # (#885) A missing desktop session must fail *loudly* — re-raise
                # so the MCP transport flags isError:true instead of returning a
                # success:false dict (isError:false) an agent may overlook.
                if e.code == ErrorCode.NO_DESKTOP_SESSION:
                    raise
                error_info: dict = {"code": e.code, "message": str(e)}
                if e.suggested_action:
                    error_info["suggested_action"] = e.suggested_action
                if e.is_recoverable:
                    error_info["recoverable"] = True
                return {"success": False, "error": error_info}
            except NaturoCoreError as e:
                # (#881) Map the native bridge error to a typed code and a
                # message free of the C++/Python class name and argument repr,
                # rather than leaking "NaturoCoreError: <op>(<args>): ...".
                logger.exception("Core error in tool %s", fn.__name__)
                return _core_error_envelope(e)
            except Exception as e:
                # (#844) Catch Pydantic ValidationError separately to avoid
                # leaking internal field paths, validator names, and raw repr.
                if _is_validation_error(e):
                    msg = _format_validation_error(e)
                    logger.warning("Validation error in tool %s: %s", fn.__name__, msg)
                    return {"success": False, "error": {"code": ErrorCode.INVALID_INPUT, "message": msg}}
                # (#881) Surface the message via str(e) — without the
                # type(e).__name__ prefix that leaked exception class names
                # (NaturoCoreError, TypeError, ValueError, …) to MCP clients.
                logger.exception("Unhandled error in tool %s", fn.__name__)
                return {"success": False, "error": {"code": _INTERNAL_ERROR_CODE, "message": str(e)}}
        return wrapper

    def _is_validation_error(exc: Exception) -> bool:
        """Check if *exc* is a Pydantic ValidationError without importing Pydantic."""
        return type(exc).__name__ == "ValidationError" and hasattr(exc, "errors")

    def _format_validation_error(exc: Exception) -> str:
        """Format a Pydantic ValidationError into a user-friendly message."""
        try:
            parts: list[str] = []
            for err in exc.errors():  # type: ignore[union-attr]
                loc = " → ".join(str(l) for l in err.get("loc", ()))
                msg = err.get("msg", "invalid value")
                if loc:
                    parts.append(f"{loc}: {msg}")
                else:
                    parts.append(msg)
            return "Invalid input: " + "; ".join(parts) if parts else f"Invalid input: {exc}"
        except Exception:
            # Defensive fallback — never leak raw Pydantic repr
            return "Invalid input: one or more parameters failed validation"

    # Register all tool groups
    register_capture_tools(server, _get_backend, _safe_tool)
    register_window_tools(server, _get_backend, _safe_tool)
    register_inspect_tools(server, _get_backend, _safe_tool)
    register_input_tools(server, _get_backend, _safe_tool)
    register_app_tools(server, _get_backend, _safe_tool, launch_app_fn=_launch_app)
    register_wait_tools(server, _get_backend, _safe_tool)
    register_snapshot_tools(server, _get_backend, _safe_tool)
    register_clipboard_tools(server, _get_backend, _safe_tool)
    register_dialog_tools(server, _get_backend, _safe_tool)
    register_system_tools(server, _get_backend, _safe_tool)
    register_excel_tools(server, _get_backend, _safe_tool)

    # Pydantic parameter-validation errors are sanitized by the
    # _SanitizingFastMCP.call_tool override, which is wired into the low-level
    # JSON-RPC handler at construction time (see the class docstring, #844).
    return server


def _format_tool_validation_error(tool_name: str, cause: BaseException) -> str:
    """Build a clean error message from a Pydantic ValidationError at the tool level.

    This handles errors raised by FastMCP's parameter validation (before the
    tool function runs).  Uses duck-typing (``cause.errors()``) so we never
    import Pydantic directly — the dependency is optional.

    Args:
        tool_name: Name of the MCP tool that was called.
        cause: The Pydantic ``ValidationError`` instance.

    Returns:
        Human-readable error string without Pydantic internals.
    """
    try:
        errors = cause.errors()  # type: ignore[union-attr]
        parts: list[str] = []
        for err in errors:
            locs = err.get("loc", ())
            field = ".".join(str(loc) for loc in locs if loc != "__root__")
            msg = err.get("msg", "invalid value")
            parts.append(f"{field}: {msg}" if field else msg)
        return f"Invalid parameters for {tool_name}: {'; '.join(parts)}"
    except Exception:
        return f"Invalid parameters for {tool_name}"


def run_server(transport: str = "stdio", host: str = "localhost", port: int = 3100):
    """Run the MCP server with the specified transport.

    When *transport* is ``"stdio"``, two layers of stdout protection are
    applied so that nothing except the JSON-RPC byte stream can reach the
    client (#810):

    1. **Logging layer** — every ``StreamHandler`` that targets
       ``sys.stdout`` is redirected to ``sys.stderr``.
    2. **Print / direct-write layer** — ``sys.stdout`` is replaced with a
       :class:`_StdoutGuard` wrapper whose ``.write()`` method forwards
       text to ``sys.stderr``, while its ``.buffer`` attribute still
       exposes the *real* ``stdout`` binary buffer so that the MCP
       ``stdio_server()`` context-manager can perform its JSON-RPC I/O
       on the correct file descriptor.
    """
    if transport == "stdio":
        _suppress_stdout_logging()
        guard = _StdoutGuard(sys.stdout)
        sys.stdout = guard  # type: ignore[assignment]
        try:
            server = create_server(host=host, port=port)
            server.run(transport=transport)
        finally:
            sys.stdout = guard._real_stdout
    else:
        server = create_server(host=host, port=port)
        server.run(transport=transport)


class _StdoutGuard(io.TextIOBase):
    """Stdout proxy that redirects text writes to stderr (#810).

    The MCP ``stdio_server()`` transport grabs ``sys.stdout.buffer`` to
    perform raw binary JSON-RPC I/O.  By exposing the *real* stdout
    buffer via ``.buffer`` while redirecting all text writes to stderr,
    this guard ensures that:

    * ``print()`` calls and any library code that writes to ``sys.stdout``
      end up on stderr (invisible to the MCP client).
    * The MCP transport still has access to the correct file descriptor
      for its JSON-RPC output.
    """

    def __init__(self, real_stdout: io.TextIOWrapper) -> None:
        super().__init__()
        self._real_stdout = real_stdout
        # Expose the real binary buffer so mcp.server.stdio can wrap it.
        self.buffer: io.RawIOBase = real_stdout.buffer  # type: ignore[assignment]

    # --- text-layer writes are silently diverted to stderr ---------------

    def write(self, s: str) -> int:  # type: ignore[override]
        return sys.stderr.write(s)

    def writelines(self, lines):  # type: ignore[override]
        sys.stderr.writelines(lines)

    def flush(self) -> None:
        sys.stderr.flush()

    # --- delegate read-side and encoding properties ----------------------

    @property
    def encoding(self) -> str:
        return self._real_stdout.encoding

    @property
    def errors(self):
        return self._real_stdout.errors

    def readable(self) -> bool:
        return False

    def writable(self) -> bool:
        return True

    def fileno(self) -> int:  # needed by some libraries
        return self._real_stdout.fileno()


def _suppress_stdout_logging() -> None:
    """Redirect or remove any logging handler that writes to stdout.

    JSON-RPC over stdio uses stdout as the transport channel.  Any log
    message that lands on stdout breaks the protocol.  This function
    walks every registered handler on the root logger (and known
    library loggers) and either redirects ``StreamHandler(sys.stdout)``
    to ``sys.stderr`` or removes it entirely.
    """
    root = logging.getLogger()

    for handler in list(root.handlers):
        if isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout:
            handler.setStream(sys.stderr)

    # Silence chatty library loggers that may add their own handlers.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "mcp",
                 "httpx", "httpcore"):
        lib_logger = logging.getLogger(name)
        lib_logger.setLevel(logging.WARNING)
        for handler in list(lib_logger.handlers):
            if isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout:
                handler.setStream(sys.stderr)
