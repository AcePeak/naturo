"""MCP tools for application control and menu inspection."""
from __future__ import annotations

import socket
from typing import Optional


def _free_debug_port(preferred: int) -> int:
    """Return ``preferred`` if it is bindable on loopback, else a free port.

    ``launch_browser`` starts a fresh browser instance per call. If the
    requested debug port is already serving — a previous ``launch_browser``
    instance still running, or the user's own debuggable Chrome — the new
    instance cannot bind it, yet the DevTools HTTP endpoint still answers (from
    the *other* instance), so CDP would silently attach to the wrong browser and
    read the wrong page. Picking a free port keeps each instance's CDP isolated;
    the cascade discovers the actual port from the window's command line.
    """
    # Prefer the ports the cascade blind-probes (9222/9229/9333) so a single
    # instance stays CDP-discoverable even where the per-process command-line
    # lookup is unavailable; fall back to an ephemeral port only if all are
    # taken (correct multi-instance discovery then relies on that lookup).
    seen: set[int] = set()
    for candidate in (preferred, 9222, 9229, 9333, 0):
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", candidate))
                return s.getsockname()[1]
        except OSError:
            continue
    return preferred


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
        """Launch a CDP-wired Chrome/Edge to read rendered or logged-in web pages.

        The way to read web content structurally — a JS-rendered DOM, or a page
        behind the user's login (pass ``profile``) — which a plain web fetch
        cannot reach. (For static public text a web fetch is faster; use this
        only when you must drive a real browser.)

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
            debug_port: Preferred DevTools port (default 9222). If it is already
                in use, a free port is chosen automatically so instances never
                collide; the actual port is returned as ``debug_port``.
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

        # Bind-test the requested port and fall back to a free one if it is
        # taken, so a second launch_browser (or a stray debuggable Chrome) never
        # collides on 9222 and attaches CDP to the wrong instance.
        port = _free_debug_port(debug_port)

        # A dedicated profile forces a fresh instance that honors the debug
        # port; only reuse the real profile when the caller explicitly asks.
        # Keyed by the resolved port so concurrent instances never share a dir.
        user_data_dir = None
        if profile is None:
            user_data_dir = os.path.join(
                tempfile.gettempdir(), f"naturo-cdp-{port}"
            )

        # Suppress the first-run experience. A brand-new throwaway profile
        # otherwise opens Chrome's welcome / "Sign in to Chrome" / search-engine
        # choice screen as the active tab, which covers the target page — so CDP
        # attaches to that empty interstitial and see_ui_tree(cascade) recovers
        # only the browser chrome, not the page. These flags open the URL clean.
        first_run_flags = [
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-search-engine-choice-screen",
            "--disable-fre",
        ]

        before = set(_win_map())
        chrome = launch_chrome(
            port=port,
            url=url,
            profile=profile,
            user_data_dir=user_data_dir,
            extra_args=first_run_flags,
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
