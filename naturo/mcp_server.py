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

from naturo.backends.base import get_backend, Backend
from naturo.errors import NaturoError
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


def create_server(host: str = "localhost", port: int = 3100) -> FastMCP:
    """Create and configure the Naturo MCP server."""
    server = FastMCP(
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

    def _get_backend() -> Backend:
        """Get the platform backend, raising clear errors."""
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
                error_info: dict = {"code": e.code, "message": str(e)}
                if e.suggested_action:
                    error_info["suggested_action"] = e.suggested_action
                if e.is_recoverable:
                    error_info["recoverable"] = True
                return {"success": False, "error": error_info}
            except Exception as e:
                # (#844) Catch Pydantic ValidationError separately to avoid
                # leaking internal field paths, validator names, and raw repr.
                msg = _format_validation_error(e) if _is_validation_error(e) else f"{type(e).__name__}: {e}"
                code = "INVALID_INPUT" if _is_validation_error(e) else "INTERNAL_ERROR"
                if code == "INTERNAL_ERROR":
                    logger.exception("Unhandled error in tool %s", fn.__name__)
                else:
                    logger.warning("Validation error in tool %s: %s", fn.__name__, msg)
                return {"success": False, "error": {"code": code, "message": msg}}
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

    # (#844) Intercept ToolError from Pydantic validation and sanitize the
    # error message.  FastMCP validates tool parameters via Pydantic BEFORE
    # calling the wrapped function, so _safe_tool cannot catch these.  When
    # validation fails, Tool.run() wraps the Pydantic ValidationError in a
    # ToolError whose __cause__ has an .errors() method.  We override
    # call_tool to detect this and return a clean, user-facing message.
    _original_call_tool = server.call_tool

    async def _sanitized_call_tool(
        name: str, arguments: dict[str, Any],
    ) -> Sequence[Any] | dict[str, Any]:
        try:
            return await _original_call_tool(name, arguments)
        except ToolError as exc:
            cause = exc.__cause__
            if cause is not None and hasattr(cause, "errors"):
                raise ToolError(
                    _format_tool_validation_error(name, cause),
                ) from None
            raise

    server.call_tool = _sanitized_call_tool  # type: ignore[assignment]

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
