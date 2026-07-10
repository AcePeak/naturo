"""Main cascade orchestration: run_cascade and _run_cdp_only."""
from __future__ import annotations

import logging
import time
from typing import List, Optional

from naturo.backends.base import ElementInfo
from naturo.cascade._types import CascadeResult, CascadeStats, ProviderStat
from naturo.cascade._coverage import (
    _estimate_coverage,
    _flatten,
    _is_shallow_tree,
    _tag_source,
    _window_area,
)
logger = logging.getLogger(__name__)


def _get_cascade_pkg():
    """Get the naturo.cascade package module for late-bound attribute access.

    This allows tests to patch functions on the package (e.g.
    ``naturo.cascade._fetch_ai_elements``) and have those patches take effect
    even though this module is a submodule of the package.
    """
    import naturo.cascade as _pkg
    return _pkg


# ── CDP-only mode ────────────────────────────────────────────────────────────


def _run_cdp_only(
    backend,
    *,
    app: Optional[str] = None,
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    pid: Optional[int] = None,
    depth: int = 3,
) -> CascadeResult:
    """Run CDP as the primary provider, with UIA for window chrome.

    Used when ``--backend cdp`` is specified explicitly.  Fetches web
    content via CDP and optionally enriches with UIA for non-web UI
    (address bar, tabs, toolbars).

    Args:
        backend: Platform backend instance.
        app: Target application name.
        window_title: Window title filter.
        hwnd: Window handle.
        pid: Process ID.
        depth: Max tree depth for UIA fallback.

    Returns:
        CascadeResult with CDP elements (and optional UIA chrome).
    """
    stats = CascadeStats()

    # Resolve PID if only app name given
    resolved_pid = pid
    if resolved_pid is None and app is not None:
        try:
            from naturo.process import find_process
            proc = find_process(name=app)
            if proc is not None:
                resolved_pid = proc.pid
        except Exception as exc:
            logger.debug("Process lookup failed for app '%s': %s", app, exc)

    # Find CDP port
    debug_port = _get_cascade_pkg().find_cdp_port(resolved_pid)

    if debug_port is None:
        logger.warning(
            "CDP: No debug port found. Start Chrome/Electron with "
            "--remote-debugging-port=9222 to enable CDP."
        )
        stats.providers.append(ProviderStat(
            name="cdp", status="error",
        ))
        return CascadeResult(tree=None, stats=stats, primary_provider="cdp")

    # Get UIA tree first for window structure (address bar, tabs, etc.)
    t0 = time.monotonic()
    root_tree: Optional[ElementInfo] = None
    try:
        tree = backend.get_element_tree(
            app=app, window_title=window_title, hwnd=hwnd, pid=pid,
            depth=depth, backend="uia",
        )
        if tree is not None:
            root_tree = _tag_source(tree, "uia")
    except Exception as exc:
        logger.debug("CDP mode: UIA tree failed (non-fatal): %s", exc)
    uia_elapsed = (time.monotonic() - t0) * 1000

    if root_tree is not None:
        uia_flat = _flatten(root_tree)
        stats.providers.append(ProviderStat(
            name="uia", elements=len(uia_flat),
            elapsed_ms=uia_elapsed, status="ok",
        ))

    # Fetch CDP elements
    t0 = time.monotonic()
    bounds = (
        (root_tree.x, root_tree.y, root_tree.width, root_tree.height)
        if root_tree is not None
        else (0, 0, 1920, 1080)
    )
    cdp_elements = _get_cascade_pkg()._fetch_cdp_elements(resolved_pid or 0, debug_port, bounds)
    cdp_elapsed = (time.monotonic() - t0) * 1000

    if cdp_elements:
        stats.providers.append(ProviderStat(
            name="cdp", elements=len(cdp_elements),
            elapsed_ms=cdp_elapsed, status="ok",
        ))
        # Merge CDP elements into root tree (or create a synthetic root)
        if root_tree is not None:
            _graft_cdp(root_tree, cdp_elements)
        else:
            root_tree = ElementInfo(
                id="root",
                role="Window",
                name=app or window_title or "Browser",
                value=None,
                x=bounds[0], y=bounds[1],
                width=bounds[2], height=bounds[3],
                children=[_tag_source(el, "cdp") for el in cdp_elements],
                properties={"source": "cdp"},
            )
    else:
        stats.providers.append(ProviderStat(
            name="cdp", elapsed_ms=cdp_elapsed, status="no_elements",
        ))

    # Final stats
    if root_tree is not None:
        all_flat = _flatten(root_tree)
        stats.total_elements = len(all_flat)
        window_area = _window_area(root_tree)
        if window_area > 0:
            stats.coverage_estimate = _estimate_coverage(all_flat[1:], window_area)

    return CascadeResult(
        tree=root_tree, stats=stats, primary_provider="cdp",
    )


# ── Main cascade entry point ──────────────────────────────────────────────────


def _dedup_tree(root):
    """Drop subtrees whose (role, name, bounds) signature repeats.

    Some backends — notably MSAA navigation — loop and re-emit the same window
    chrome many times (charmap: the title bar / buttons appeared ~25×, inflating
    a ~40-element window to 922 phantom nodes). Identical bounds mean the same
    physical element was revisited, so it is safe to drop the repeat. Genuinely
    repeated controls (list items, grid cells) have DISTINCT bounds and are kept.
    Blank structural containers (no name, zero size) are never collapsed.
    """
    if root is None:
        return root

    def sig(n):
        role = (getattr(n, "role", "") or "")
        name = (getattr(n, "name", "") or "").strip()
        # Only MSAA trees reach here. Its nav loop re-emits the SAME named chrome
        # at slightly-varying bounds, so collapse labelled nodes by (role, name)
        # — an exact-bounds key leaves ~400 near-dup phantoms. Unnamed nodes keep
        # a bounds key (distinct positions are distinct structural containers).
        if name:
            return (role, name)
        return (role, "", getattr(n, "x", 0), getattr(n, "y", 0),
                getattr(n, "width", 0), getattr(n, "height", 0))

    seen = {sig(root)}

    def prune(n):
        kept = []
        for c in (getattr(n, "children", None) or []):
            s = sig(c)
            # only a labelled / sized node counts as a loop-duplicate — this
            # avoids collapsing many legitimately-blank structural containers
            if s in seen and (s[1] or s[4] or s[5]):
                continue
            seen.add(s)
            prune(c)
            kept.append(c)
        n.children = kept

    prune(root)
    return root


def _web_render_bounds(hwnd):
    """Screen rect (x, y, w, h) of the embedded Chromium render surface under
    ``hwnd`` (WebView2/CEF ``Chrome_RenderWidgetHostHWND``), or None.

    CDP ``getBoundingClientRect`` coords are relative to the web VIEWPORT, whose
    screen origin is this render widget's top-left — NOT the app window's. Using
    the window origin misplaces the whole page (it floats over the native chrome).
    """
    if not hwnd:
        return None
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        best = [None, 0]
        buf = ctypes.create_unicode_buffer(128)

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def _cb(h, _l):
            user32.GetClassNameW(h, buf, 128)
            if "Chrome_RenderWidgetHostHWND" in (buf.value or ""):
                r = wintypes.RECT()
                user32.GetWindowRect(h, ctypes.byref(r))
                area = (r.right - r.left) * (r.bottom - r.top)
                if area > best[1]:
                    best[0] = (r.left, r.top, r.right - r.left, r.bottom - r.top)
                    best[1] = area
            return True

        user32.EnumChildWindows(wintypes.HWND(int(hwnd)), _cb, 0)
        return best[0]
    except Exception:
        return None


def _graft_cdp(root_tree, cdp_elements):
    """Tag CDP web elements and nest them under the browser control's node."""
    return _graft_web_under_control(
        root_tree, [_tag_source(el, "cdp") for el in cdp_elements])


def _graft_web_under_control(root_tree, tagged):
    """Nest already-tagged web nodes UNDER the browser control's UIA node (not flat
    at the window root — the page lives inside the embedded browser). Find the
    smallest UIA node containing the web content (the WebView2/Chrome host pane),
    mark it the interactive web surface, and graft there; fall back to the root.
    """
    boxed = [t for t in tagged if (t.width or 0) > 0 and (t.height or 0) > 0]
    host = None
    if boxed and root_tree is not None and (root_tree.children is not None):
        bx = min(t.x for t in boxed)
        by = min(t.y for t in boxed)
        bw = max(t.x + t.width for t in boxed) - bx
        bh = max(t.y + t.height for t in boxed) - by
        target_area = max(bw * bh, 1)
        best_key = None

        def _walk(node, depth):
            nonlocal host, best_key
            nx, ny = node.x, node.y
            nw, nh = node.width, node.height
            contains = (nx <= bx + 8 and ny <= by + 8
                        and nx + nw >= bx + bw - 8 and ny + nh >= by + bh - 8)
            if contains and node is not root_tree:
                # Smallest containing node, then shallowest — that is the browser
                # CONTROL (e.g. the WebView2 host pane), not the whole window and
                # not a deep redundant Chromium pane. The control is legitimately
                # bigger than the page content, so don't gate on content size.
                key = (max(nw * nh, 1), depth)
                if best_key is None or key < best_key:
                    host, best_key = node, key
            for c in (node.children or []):
                _walk(c, depth + 1)

        _walk(root_tree, 0)

    target = host if host is not None else root_tree
    if target is not None:
        if target is not root_tree:
            props = target.properties if isinstance(target.properties, dict) else {}
            props["web_host"] = True
            target.properties = props
            if not (getattr(target, "name", "") or "").strip():
                target.name = "Web content"
        target.children.extend(tagged)
    return tagged


def _web_content_roots(tree):
    """The content subtree(s) inside a render-widget UIA tree — the Document
    node(s) (which carry the page), skipping the 'Chrome Legacy Window' wrapper.
    """
    found = []

    def _walk(n):
        if (getattr(n, "role", "") or "").lower() == "document":
            found.append(n)
            return
        for c in (getattr(n, "children", None) or []):
            _walk(c)

    _walk(tree)
    return found or list(getattr(tree, "children", None) or [])


def _webview_uia_content(backend, hwnd, depth):
    """No-CDP fallback for embedded browsers: read each Chromium render widget's
    OWN UIA tree and return the page content, tagged 'uia'.

    Chromium (WebView2/CEF/Electron) exposes its DOM as UIA accessible objects,
    but naturo's window-level read stops at empty WebView panes — reading the
    render-widget hwnd directly recovers the real content. Works with NO debug
    port, so Tauri/WebView2 apps (Clash Verge, etc.) that don't expose CDP are
    still readable.
    """
    if not hwnd:
        return []
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return []
    user32 = ctypes.windll.user32
    widgets = []
    buf = ctypes.create_unicode_buffer(128)

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _cb(h, _l):
        try:
            user32.GetClassNameW(h, buf, 128)
            if "Chrome_RenderWidgetHostHWND" in (buf.value or ""):
                widgets.append(h)
        except Exception:
            pass
        return True

    try:
        user32.EnumChildWindows(wintypes.HWND(int(hwnd)), _cb, 0)
    except Exception:
        return []

    nodes = []
    for wh in widgets:
        try:
            tree = backend.get_element_tree(hwnd=wh, depth=depth, backend="uia")
        except Exception:
            continue
        if tree is None:
            continue
        for root in _web_content_roots(tree):
            nodes.append(_tag_source(root, "uia"))
    return nodes


def run_cascade(
    backend,
    *,
    app: Optional[str] = None,
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    pid: Optional[int] = None,
    depth: int = 3,
    backend_name: str = "uia",
    coverage_target: float = 0.0,
    fill_gaps_ai: bool = False,
    ai_provider: str = "auto",
    ai_model: Optional[str] = None,
    ai_api_key: Optional[str] = None,
    screenshot_path: Optional[str] = None,
    screenshot_scale_factor: float = 1.0,
    run_ocr: bool = False,
) -> CascadeResult:
    """Run progressive recognition and return a merged element tree.

    Parameters
    ----------
    backend:
        Platform backend instance (:class:`naturo.backends.base.Backend`).
    app:
        Target application name (passed to ``backend.get_element_tree``).
    window_title:
        Window title filter.
    hwnd:
        Window handle (Windows only).
    pid:
        Process ID.
    depth:
        Maximum tree depth for UIA/MSAA probes.
    backend_name:
        Base accessibility backend: ``"uia"`` | ``"msaa"`` | ``"ia2"`` | ``"jab"`` |
        ``"cdp"`` | ``"auto"`` | ``"hybrid"``.
        When ``"auto"``, each provider is tried in cascade order.
        When ``"cdp"``, uses Chrome DevTools Protocol directly (browser must
        have ``--remote-debugging-port`` enabled).
    coverage_target:
        When >0, also run CDP if UIA coverage < this threshold (0.0–1.0).
        Ignored when ``backend_name`` is ``"auto"`` (always cascades).
    fill_gaps_ai:
        When True, add AI vision as the final fallback provider.
    ai_provider:
        AI provider name (``"auto"`` | ``"anthropic"`` | ``"openai"`` | ``"ollama"``).
    ai_model:
        AI model override (e.g. ``"claude-opus-4-6"``, ``"gpt-4o"``).
        When ``None``, uses the provider's default model.
    ai_api_key:
        API key override.  When ``None``, uses the provider's default
        credentials (env var or credentials file).
    screenshot_path:
        Path to existing screenshot for AI vision (avoids re-capture).
    screenshot_scale_factor:
        DPI scale factor of the screenshot's monitor (e.g. 1.5 for 150%).
        Used to convert AI pixel coordinates to UIA screen coordinates.

    Returns
    -------
    CascadeResult
        Merged element tree with source-tagged elements and statistics.
    """
    # ── Hybrid mode: per-node backend selection ────────────────────────────
    if backend_name == "hybrid":
        resolved_hwnd = hwnd
        if resolved_hwnd is None:
            # Resolve app/window_title to hwnd first
            try:
                resolved_hwnd = backend._resolve_hwnd(
                    app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                )
            except Exception as exc:
                logger.debug("Hybrid: HWND resolution failed: %s", exc)
                return CascadeResult(
                    tree=None,
                    stats=CascadeStats(providers=[
                        ProviderStat(name="hybrid", status="error"),
                    ]),
                    primary_provider="hybrid",
                )

        tree, stats = _get_cascade_pkg().build_hybrid_tree(
            backend, hwnd=resolved_hwnd, depth=depth, pid=pid,
        )
        return CascadeResult(
            tree=tree,
            stats=stats,
            primary_provider="hybrid",
        )

    # ── CDP-only mode: explicit --backend cdp ────────────────────────────
    if backend_name == "cdp":
        return _run_cdp_only(
            backend, app=app, window_title=window_title,
            hwnd=hwnd, pid=pid, depth=depth,
        )

    stats = CascadeStats()
    merged_elements: List[ElementInfo] = []
    root_tree: Optional[ElementInfo] = None
    window_area = 0

    # ── Provider 1: pick the RICHEST accessibility tree (UIA/MSAA/JAB/IA2) ──
    # "first non-empty wins" was wrong: custom-drawn / legacy apps (Creo, the
    # charmap character grid, old MFC/Delphi) return a THIN opaque frame via UIA
    # (a few chrome nodes — non-empty but useless), so MSAA/JAB — which actually
    # see the controls — were never tried.  Now: try UIA first and short-circuit
    # only if it is already rich; otherwise also probe the others and keep the
    # tree with the most nodes (the one that truly matches what's on screen).
    _best_size = -1
    _best_flat: List[ElementInfo] = []
    _uia_size = -1  # baseline; a heavier backend only wins if it DWARFS UIA

    # Class-authoritative routing: a window whose class maps to a known provider
    # (SunAwt→JAB, Mozilla→IA2) is opaque to UIA *by construction*, so trust the
    # class over any node-count heuristic. Unknown classes (charmap, Creo, …) get
    # the "MSAA dwarfs UIA" fallback below instead.
    _class_pref: Optional[str] = None
    if backend_name == "auto" and hwnd is not None:
        try:
            from ._build import _detect_backend_for_class
            from ._com_excel import _win32_class_name
            _p = _detect_backend_for_class(_win32_class_name(hwnd) or "")
            if _p in ("jab", "ia2"):
                _class_pref = _p
        except Exception as exc:
            logger.debug("class-pref detection skipped: %s", exc)

    # For auto, compete only UIA + MSAA generically; add JAB/IA2 ONLY when the
    # window class calls for it (real Swing/Mozilla). JAB and COM also have
    # dedicated additive providers (2b/2c) that graft onto whichever base wins —
    # probing them generically here would double-count and, worse, leave a
    # "jab ok" stat that suppresses the 2b fallback merge (losing JAB entirely
    # when class detection misses).
    if backend_name == "auto":
        providers_to_try = ["uia", "msaa"]
        if _class_pref:
            providers_to_try.append(_class_pref)
    else:
        providers_to_try = [backend_name]

    for pname in providers_to_try:
        t0 = time.monotonic()
        try:
            tree = backend.get_element_tree(
                app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                depth=depth, backend=pname,
            )
            elapsed = (time.monotonic() - t0) * 1000

            if tree is None:
                stats.providers.append(ProviderStat(
                    name=pname, elapsed_ms=elapsed, status="skipped"))
                continue

            tagged = _tag_source(tree, pname)
            flat = _flatten(tagged)
            elements_count = len(flat)

            # MSAA navigation loops and re-emits the same chrome many times. Dedup
            # it here (before it competes with UIA) and remember whether it was
            # MOSTLY a loop: a high collapse ratio means the raw richness was
            # phantom duplication (taskmgr 1221→38, all chrome — the real process
            # list is custom-drawn, opaque to MSAA too), NOT real content, so it
            # must not be trusted to displace a real UIA tree. A low collapse ratio
            # is genuine content (charmap 922→415) and is allowed to win.
            _msaa_loopy = False
            if pname == "msaa":
                _raw_n = elements_count
                tree = _dedup_tree(tree)
                tagged = _tag_source(tree, pname)
                flat = _flatten(tagged)
                elements_count = len(flat)
                _msaa_loopy = _raw_n > 3 * max(elements_count, 1)

            # (#394) A root-only tree (0 children) is not useful — keep trying.
            if not tree.children:
                stats.providers.append(ProviderStat(
                    name=pname, elements=elements_count,
                    elapsed_ms=elapsed, status="empty_tree"))
                if root_tree is None:
                    root_tree = tagged
                    window_area = _window_area(tree)
                continue

            stats.providers.append(ProviderStat(
                name=pname, elements=elements_count, elapsed_ms=elapsed, status="ok"))

            if pname == "uia":
                _uia_size = elements_count

            if pname == _class_pref:
                # Class says this backend is the correct one (e.g. Java→JAB) and
                # it returned real content → adopt it authoritatively and stop.
                _best_size, _best_flat = elements_count, flat
                root_tree = tagged
                window_area = _window_area(tree)
                break

            # Otherwise keep the richest tree — but a heavier backend DISPLACES UIA
            # only when it DWARFS it (opaque UIA: charmap 27→msaa 922 = 34×), never
            # when merely larger (complete-UIA app where MSAA just adds container
            # noise: notepad uia 34 vs msaa 300 → keep UIA).
            if elements_count > _best_size and (
                pname == "uia" or _uia_size <= 0
                or (elements_count > 10 * _uia_size and not _msaa_loopy)
            ):
                _best_size = elements_count
                _best_flat = flat
                root_tree = tagged
                window_area = _window_area(tree)

            # UIA already rich enough → don't pay for the heavier backends.
            if pname == "uia" and elements_count >= 60:
                break
        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000
            logger.debug("Provider %s failed: %s", pname, exc)
            stats.providers.append(ProviderStat(
                name=pname, elapsed_ms=elapsed, status="error"))

    if _best_flat:
        merged_elements.extend(_best_flat[1:])  # skip root (merged below)

    # ── Provider 2: CDP (Electron/CEF apps) ─────────────────────────────────
    should_try_cdp = (
        coverage_target > 0
        or backend_name == "auto"
        or backend_name in ("cdp",)
    )

    if should_try_cdp and root_tree is not None:
        current_coverage = _estimate_coverage(merged_elements, window_area) if window_area > 0 else 0.0

        # Only try CDP if coverage is below target (or always when backend_name=auto)
        if backend_name == "auto" or current_coverage < coverage_target:
            t0 = time.monotonic()
            cdp_elements: List[ElementInfo] = []
            debug_port: Optional[int] = None

            try:
                # Try Electron-specific detection first, then generic CDP
                try:
                    from naturo.electron import get_debug_port as _electron_port
                    if app:
                        debug_port = _electron_port(app)
                except Exception as exc:
                    logger.debug("Electron port detection failed for '%s': %s", app, exc)

                # Fall back to generic CDP port discovery (Chrome, Edge, etc.)
                if debug_port is None:
                    # Resolve the target window's PID so find_cdp_port can read
                    # the browser's command line (its Phase 1) and pick up a
                    # non-default --remote-debugging-port — not only the common
                    # ports it blind-probes. Windows-only, best-effort.
                    cdp_pid = pid
                    if cdp_pid is None and hwnd is not None:
                        try:
                            import ctypes
                            import ctypes.wintypes
                            _pid = ctypes.wintypes.DWORD()
                            ctypes.windll.user32.GetWindowThreadProcessId(
                                int(hwnd), ctypes.byref(_pid)
                            )
                            cdp_pid = _pid.value or None
                        except Exception:
                            cdp_pid = None
                    debug_port = _get_cascade_pkg().find_cdp_port(cdp_pid)
            except Exception as exc:
                logger.debug("CDP port detection failed: %s", exc)

            if debug_port:
                # Offset CDP viewport coords by the embedded browser's render
                # surface (not the app window), so the page lands inside the
                # browser control; fall back to the window origin if not found.
                bounds = _web_render_bounds(hwnd) or (
                    root_tree.x, root_tree.y, root_tree.width, root_tree.height)
                cdp_elements = _get_cascade_pkg()._fetch_cdp_elements(
                    pid or 0, debug_port, bounds
                )

            elapsed = (time.monotonic() - t0) * 1000
            if cdp_elements:
                # Graft CDP web elements UNDER the browser control's UIA node (not
                # flat at the window root) so the tree reflects that the page lives
                # inside the embedded browser. Also feed coverage math.
                merged_elements.extend(_graft_cdp(root_tree, cdp_elements))

                stats.providers.append(ProviderStat(
                    name="cdp", elements=len(cdp_elements), elapsed_ms=elapsed, status="ok"
                ))
            else:
                stats.providers.append(ProviderStat(
                    name="cdp", elapsed_ms=elapsed,
                    status="skipped" if debug_port is None else "no_elements"
                ))
                # No CDP (no debug port owned by this app) — recover the embedded
                # web content from the render widget's UIA tree instead. Chromium
                # exposes its DOM as UIA accessible objects, so Tauri/WebView2/
                # Electron apps that don't open a debug port (e.g. Clash Verge) are
                # still readable, structurally, with zero debug port.
                _t0w = time.monotonic()
                _web_nodes = _webview_uia_content(backend, hwnd, max(depth, 12))
                if _web_nodes:
                    _graft_web_under_control(root_tree, _web_nodes)
                    for _n in _web_nodes:
                        merged_elements.extend(_flatten(_n))
                    stats.providers.append(ProviderStat(
                        name="webview_uia", elements=len(_web_nodes),
                        elapsed_ms=(time.monotonic() - _t0w) * 1000, status="ok"))

    # ── Provider 2b: Java Access Bridge (Swing/AWT apps) ─────────────────────
    # The primary provider loop above stops at the first non-empty accessibility
    # tree.  For a Java window that tree is the UIA *window chrome* (title bar,
    # system buttons) — the actual Swing controls live below a SunAwtFrame that
    # UIA collapses into one opaque node, so the loop never reaches the "jab"
    # provider and the moat is silently lost on the default ``auto`` path (it
    # only worked via an explicit ``--backend jab``).  Detect a Java window and
    # merge its JAB elements here, mirroring the additive CDP provider above, so
    # ``naturo see --backend auto`` actually delivers Java recognition (#932).
    already_have_jab = any(
        p.name == "jab" and p.status == "ok" for p in stats.providers
    )
    if backend_name == "auto" and root_tree is not None and not already_have_jab:
        resolved_hwnd = hwnd
        if resolved_hwnd is None:
            try:
                resolved_hwnd = backend._resolve_hwnd(
                    app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                )
            except Exception as exc:
                logger.debug("Auto cascade: HWND resolution for JAB failed: %s", exc)
                resolved_hwnd = None

        if resolved_hwnd is not None and _get_cascade_pkg()._is_java_window(
            resolved_hwnd
        ):
            t0 = time.monotonic()
            jab_tree: Optional[ElementInfo] = None
            try:
                jab_tree = backend.get_element_tree(
                    hwnd=resolved_hwnd, depth=depth, backend="jab",
                )
            except Exception as exc:
                logger.debug("Auto cascade: JAB probe failed: %s", exc)
            elapsed = (time.monotonic() - t0) * 1000

            # Attach the JAB controls (the children below the JAB window root)
            # to the UIA root so callers actually receive them, and count them
            # the same way the primary/CDP providers are counted.
            jab_added: List[ElementInfo] = []
            if jab_tree is not None:
                tagged_jab = _tag_source(jab_tree, "jab")
                for child in tagged_jab.children:
                    root_tree.children.append(child)
                    jab_added.extend(_flatten(child))

            if jab_added:
                merged_elements.extend(jab_added)
                stats.providers.append(ProviderStat(
                    name="jab", elements=len(jab_added),
                    elapsed_ms=elapsed, status="ok",
                ))
            else:
                stats.providers.append(ProviderStat(
                    name="jab", elapsed_ms=elapsed, status="no_elements",
                ))

    # Provider 2c: COM/Excel (spreadsheet cells UIA collapses into one node).
    # Excel exposes its grid only via COM, so ``see --cascade`` on an Excel
    # window otherwise shows just the ribbon/chrome.  Bind the running Excel
    # instance and graft its cells onto the root, mirroring the additive
    # CDP/JAB providers above, so ``see --backend auto`` delivers spreadsheet
    # recognition (M2).
    already_have_com = any(
        p.name == "com" and p.status == "ok" for p in stats.providers
    )
    if backend_name == "auto" and root_tree is not None and not already_have_com:
        com_hwnd = hwnd
        if com_hwnd is None:
            try:
                com_hwnd = backend._resolve_hwnd(
                    app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                )
            except Exception as exc:
                logger.debug(
                    "Auto cascade: HWND resolution for COM/Excel failed: %s", exc,
                )
                com_hwnd = None

        if com_hwnd is not None and _get_cascade_pkg()._is_excel_window(com_hwnd):
            t0 = time.monotonic()
            com_cells: List[ElementInfo] = []
            try:
                com_cells = _get_cascade_pkg()._fetch_excel_cells(com_hwnd)
            except Exception as exc:
                logger.debug("Auto cascade: COM/Excel probe failed: %s", exc)
            elapsed = (time.monotonic() - t0) * 1000

            if com_cells:
                for cell in com_cells:
                    tagged_cell = _tag_source(cell, "com")
                    root_tree.children.append(tagged_cell)
                    merged_elements.append(tagged_cell)
                stats.providers.append(ProviderStat(
                    name="com", elements=len(com_cells),
                    elapsed_ms=elapsed, status="ok",
                ))
            else:
                stats.providers.append(ProviderStat(
                    name="com", elapsed_ms=elapsed, status="no_elements",
                ))

    # ── Shallow tree detection (issue #275) ────────────────────────────────
    # When the UIA tree is too shallow (few elements, mostly invalid bounds),
    # automatically enable AI vision fallback even without --fill-gaps.
    shallow_fallback = False
    if root_tree is not None and not fill_gaps_ai:
        flat_all = _flatten(root_tree)
        is_shallow, total_count, invalid_count = _is_shallow_tree(flat_all)
        if is_shallow and screenshot_path:
            shallow_fallback = True
            logger.info(
                "UIA tree too shallow (%d elements, %d with invalid bounds), "
                "falling back to AI vision...",
                total_count, invalid_count,
            )

    # ── Provider 3: AI vision fallback ──────────────────────────────────────
    should_run_ai = (fill_gaps_ai or shallow_fallback) and root_tree is not None and screenshot_path
    if should_run_ai:
        current_coverage = _estimate_coverage(merged_elements, window_area) if window_area > 0 else 0.0

        if current_coverage < coverage_target or coverage_target == 0.0 or shallow_fallback:
            t0 = time.monotonic()
            bounds = (root_tree.x, root_tree.y, root_tree.width, root_tree.height)
            ai_elements = _get_cascade_pkg()._fetch_ai_elements(
                screenshot_path, bounds, ai_provider,
                scale_factor=screenshot_scale_factor,
                model=ai_model,
                api_key=ai_api_key,
            )
            elapsed = (time.monotonic() - t0) * 1000

            trigger = "shallow_tree" if shallow_fallback else "fill_gaps"
            if ai_elements:
                # (#694) Merge AI elements into the UIA tree with IoU dedup
                # instead of flat append — skip duplicates, attach novel
                # elements to the deepest matching parent node.
                novel, added_count, skipped_count = _get_cascade_pkg()._merge_ai_into_tree(
                    root_tree, ai_elements,
                )
                merged_elements.extend(novel)
                stats.providers.append(ProviderStat(
                    name="vision", elements=added_count, elapsed_ms=elapsed,
                    status="ok",
                ))
                logger.info(
                    "AI vision: %d added, %d duplicates skipped (trigger: %s)",
                    added_count, skipped_count, trigger,
                )
            else:
                stats.providers.append(ProviderStat(
                    name="vision", elapsed_ms=elapsed, status="skipped"
                ))

    # Provider 4: local OCR fallback (text baked into images/canvas that
    # accessibility APIs cannot see).  UNCERTAIN by construction — merged with
    # the same IoU/text dedup as AI vision, so OCR that overlaps a deterministic
    # node corroborates it (deterministic stays preferred) and only genuinely
    # image-only text is added as an uncertain, warned node (M2).
    if run_ocr and root_tree is not None and screenshot_path:
        t0 = time.monotonic()
        bounds = (root_tree.x, root_tree.y, root_tree.width, root_tree.height)
        ocr_elements: List[ElementInfo] = []
        try:
            ocr_elements = _get_cascade_pkg()._fetch_ocr_elements(
                screenshot_path, bounds,
            )
        except Exception as exc:
            logger.debug("OCR provider failed: %s", exc)
        elapsed = (time.monotonic() - t0) * 1000
        if ocr_elements:
            novel, added_count, skipped_count = _get_cascade_pkg()._merge_ai_into_tree(
                root_tree, ocr_elements,
            )
            merged_elements.extend(novel)
            stats.providers.append(ProviderStat(
                name="ocr", elements=added_count, elapsed_ms=elapsed, status="ok",
            ))
            logger.info(
                "OCR: %d added, %d duplicates skipped", added_count, skipped_count,
            )
        else:
            stats.providers.append(ProviderStat(
                name="ocr", elapsed_ms=elapsed, status="no_elements",
            ))

    # ── De-loop the tree (MSAA navigation loops and re-emits chrome) ─────────
    # Scoped to MSAA only: UIA/JAB/CDP/COM trees are clean and an exact
    # (role,name,bounds) collision there is a legitimate node, not a loop.
    _root_src = (getattr(root_tree, "properties", None) or {}).get("source") if root_tree else None
    if _root_src == "msaa":
        root_tree = _dedup_tree(root_tree)

    # ── Assemble final stats ─────────────────────────────────────────────────
    stats.total_elements = len(merged_elements)
    if window_area > 0 and merged_elements:
        stats.coverage_estimate = _estimate_coverage(merged_elements, window_area)

    return CascadeResult(
        tree=root_tree,
        stats=stats,
        primary_provider=providers_to_try[0] if providers_to_try else "uia",
    )
