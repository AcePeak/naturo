"""MCP tools for Win32 API hooking (#40).

Exposes the MinHook-backed, in-process hook engine to MCP clients: install /
list / remove hooks on supported Win32 APIs and drain the monitored-call log.

SECURITY NOTE for agents
------------------------
These tools intercept real Win32 API calls made by the current process. The
``block`` action makes a hooked API *return a failure sentinel without
executing* — a deliberately intrusive behavior. Cross-process DLL injection is
intentionally NOT exposed as an MCP tool: it is an administrator-only operation
that loads code into another process, and is available only through the
``naturo.hooks.injector`` Python API where its elevation and target can be
controlled explicitly. Use these tools only to observe or gate APIs in a
process you own.
"""
from __future__ import annotations


def register_hook_tools(server, _get_backend, _safe_tool):
    """Register Win32 API hooking MCP tools.

    Args:
        server: The FastMCP server.
        _get_backend: Desktop-backend accessor (unused — hooking does not touch
            the UI automation backend; it drives the native hook engine).
        _safe_tool: Decorator that wraps handlers with structured error handling.
    """

    def _manager():
        from naturo.hooks.manager import HookManager

        return HookManager()

    @server.tool()
    @_safe_tool
    def hook_install(module: str, function: str, action: str = "log") -> dict:
        """Install (or re-arm) an in-process hook on a supported Win32 API.

        Intercepts calls to MODULE!FUNCTION inside the current process. SECURITY:
        ``action="block"`` makes the API return a failure sentinel WITHOUT
        calling the real implementation (e.g. CreateFileW returns
        INVALID_HANDLE_VALUE, MessageBoxW returns 0). Use ``log`` to observe
        only. Call ``hook_supported`` for the list of hookable APIs.

        Args:
            module: Module/DLL name (e.g. "user32" or "user32.dll").
            function: Exported function name (e.g. "MessageBoxW").
            action: "log" (record and forward) or "block" (record and return a
                sentinel without forwarding).

        Returns:
            module, function, action: The installed hook's parameters.
        """
        info = _manager().install(module, function, action)
        return {"success": True, **info}

    @server.tool()
    @_safe_tool
    def hook_list() -> dict:
        """List the currently installed in-process hooks.

        Returns:
            hooks: List of {module, function, action, call_count}.
            count: Number of installed hooks.
        """
        hooks = _manager().list()
        return {"success": True, "hooks": hooks, "count": len(hooks)}

    @server.tool()
    @_safe_tool
    def hook_remove(module: str, function: str) -> dict:
        """Remove a previously installed hook on MODULE!FUNCTION.

        Args:
            module: Module/DLL name.
            function: Exported function name.

        Returns:
            removed: True if a hook was removed, False if none was installed.
        """
        removed = _manager().remove(module, function)
        return {"success": True, "module": module, "function": function, "removed": removed}

    @server.tool()
    @_safe_tool
    def hook_monitor() -> dict:
        """Drain and return the monitored-call log (clears the native buffer).

        Each record describes one intercepted call. Records are ordered
        oldest-first and removed from the buffer once returned.

        Returns:
            events: List of {seq, module, function, action, detail}.
            count: Number of records returned.
        """
        events = _manager().monitor()
        return {"success": True, "events": events, "count": len(events)}

    @server.tool()
    @_safe_tool
    def hook_supported() -> dict:
        """List the Win32 APIs this build knows how to hook.

        Returns:
            apis: List of {module, function} entries accepted by hook_install.
        """
        apis = _manager().supported()
        return {"success": True, "apis": apis}
