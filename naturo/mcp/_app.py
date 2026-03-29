"""MCP tools for application control and menu inspection."""
from __future__ import annotations

from typing import Optional


def register_app_tools(server, _get_backend, _safe_tool, *, launch_app_fn):
    """Register application control MCP tools.

    Args:
        server: FastMCP server instance.
        _get_backend: Callable returning the platform backend.
        _safe_tool: Decorator for error handling.
        launch_app_fn: Callable to launch an application by name.
    """

    @server.tool()
    @_safe_tool
    def list_apps() -> dict:
        """List running applications.

        Returns:
            Dict with success flag and list of running applications.
        """
        backend = _get_backend()
        apps = backend.list_apps()
        return {"success": True, "apps": apps}

    @server.tool()
    @_safe_tool
    def launch_app(name: str) -> dict:
        """Launch an application by name.

        Args:
            name: Application name or executable path.

        Returns:
            Dict with success flag, pid, and process info.
        """
        info = launch_app_fn(name=name)
        return {
            "success": True,
            "pid": info.pid,
            "name": info.name,
            "path": info.path,
            "is_running": info.is_running,
            "window_count": info.window_count,
        }

    @server.tool()
    @_safe_tool
    def quit_app(name: str, force: bool = False) -> dict:
        """Quit an application.

        Args:
            name: Application name.
            force: Force quit if True.

        Returns:
            Dict with success flag.
        """
        backend = _get_backend()
        backend.quit_app(name=name, force=force)
        return {"success": True}

    @server.tool()
    @_safe_tool
    def menu_inspect(app: Optional[str] = None) -> dict:
        """Inspect the menu bar of an application.

        Returns the hierarchical menu structure with item names, shortcuts, and states.

        Args:
            app: Application name (optional, defaults to foreground app).

        Returns:
            Dict with success flag and menu items.
        """
        backend = _get_backend()
        items = backend.get_menu_items(window_title=app)

        def _serialize_menu(item) -> dict:
            d = {"name": item.name}
            if item.shortcut:
                d["shortcut"] = item.shortcut
            if hasattr(item, "enabled"):
                d["enabled"] = item.enabled
            if hasattr(item, "checked"):
                d["checked"] = item.checked
            if hasattr(item, "children") and item.children:
                d["children"] = [_serialize_menu(c) for c in item.children]
            return d

        return {
            "success": True,
            "menu_items": [_serialize_menu(m) for m in items],
        }
