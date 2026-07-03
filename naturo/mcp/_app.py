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
            Dict with success, pid, and the **window(s) that actually appeared**
            so the caller can ``focus_window``/``window_close`` exactly what it
            launched — and tear it down afterwards. ``hwnd`` is the primary new
            window (first one). Note: some apps (e.g. Win11 Notepad) restore
            their previous session on start, so ``windows`` may list several
            pre-existing documents that reappeared, not just a fresh one.
        """
        import time

        def _win_map() -> dict:
            try:
                out = {}
                for w in backend.list_windows():
                    h = getattr(w, "handle", None) or getattr(w, "hwnd", None)
                    out[h] = getattr(w, "title", "") or ""
                return out
            except Exception:
                return {}

        backend = _get_backend()
        before = set(_win_map())
        info = launch_app_fn(name=name)

        # The process layer returns a transient launcher PID for UWP apps and
        # hard-codes window_count=0, so the caller could not find (and later
        # close) what it opened — a root cause of window pile-up. Resolve the
        # real window(s) by diffing the window list, polling briefly.
        # launch_app_fn already waited for the process, so the window usually
        # exists on the first check (break immediately); the short cap only
        # covers a slow-drawing window without adding latency to the fast path.
        new_windows: list[dict] = []
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            new_windows = [
                {"hwnd": h, "title": t}
                for h, t in _win_map().items()
                if h is not None and h not in before
            ]
            if new_windows:
                break
            time.sleep(0.15)

        return {
            "success": True,
            "pid": info.pid,
            "name": info.name,
            "path": info.path,
            "is_running": info.is_running,
            "window_count": len(new_windows),
            "windows": new_windows,
            "hwnd": new_windows[0]["hwnd"] if new_windows else None,
        }

    @server.tool()
    @_safe_tool
    def launch_browser(
        url: Optional[str] = None,
        debug_port: int = 9222,
        profile: Optional[str] = None,
    ) -> dict:
        """Launch Chrome/Edge wired for automation (CDP) — the correct way to
        read web-page content as structured elements.

        A browser opened with ``launch_app`` exposes no DevTools endpoint, so
        ``see_ui_tree(cascade=True)`` recovers only the browser chrome (toolbar/
        tabs), never the page. This launches via naturo's browser subsystem with
        ``--remote-debugging-port`` + ``--remote-allow-origins=*`` and waits for
        the CDP endpoint, so a follow-up ``see_ui_tree(hwnd=..., cascade=True)``
        or ``find_element(hwnd=...)`` returns the real DOM as **deterministic,
        structured** elements — far more reliable than screenshot + OCR/vision.

        By default a dedicated throwaway profile is used so a fresh, debuggable
        instance starts even when Chrome is already open — launching into an
        already-running default-profile Chrome silently drops the debug-port
        flag, the #1 reason CDP attach fails. Pass ``profile`` to use one of your
        real Chrome profiles instead (that profile must not already be running).

        After this, target the returned ``hwnd`` with ``see_ui_tree(cascade=True)``
        to read the page structurally — no screenshot needed.

        Args:
            url: URL to open directly — loads before this returns, so there is no
                address-bar typing and no focus race.
            debug_port: DevTools port (default 9222; the cascade auto-discovers it).
            profile: Optional Chrome profile name/dir to reuse your logged-in
                session instead of a throwaway profile.

        Returns:
            Dict mirroring ``launch_app`` (``hwnd``, ``windows``, ``pid``) plus
            ``debug_port`` and ``url`` — target the exact window via ``hwnd``.
        """
        import os
        import tempfile
        import time

        from naturo.browser._launcher import launch_chrome

        backend = _get_backend()

        def _win_map() -> dict:
            try:
                return {
                    (getattr(w, "handle", None) or getattr(w, "hwnd", None)):
                        (getattr(w, "title", "") or "")
                    for w in backend.list_windows()
                }
            except Exception:
                return {}

        # A dedicated profile forces a fresh instance that honors the debug
        # port; only reuse the real profile when the caller explicitly asks.
        user_data_dir = None
        if profile is None:
            user_data_dir = os.path.join(
                tempfile.gettempdir(), f"naturo-cdp-{debug_port}"
            )

        before = set(_win_map())
        chrome = launch_chrome(
            port=debug_port,
            url=url,
            profile=profile,
            user_data_dir=user_data_dir,
            wait_ready=True,
            timeout=15.0,
        )

        # launch_chrome already blocked until the CDP endpoint answered, so the
        # window is usually present on the first diff; the short poll only covers
        # a slow first paint.
        new_windows: list[dict] = []
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            new_windows = [
                {"hwnd": h, "title": t}
                for h, t in _win_map().items()
                if h is not None and h not in before
            ]
            if new_windows:
                break
            time.sleep(0.15)

        return {
            "success": True,
            "debug_port": chrome.port,
            "url": url,
            "pid": chrome.pid,
            "window_count": len(new_windows),
            "windows": new_windows,
            "hwnd": new_windows[0]["hwnd"] if new_windows else None,
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
