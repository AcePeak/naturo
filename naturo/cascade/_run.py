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
            for el in cdp_elements:
                root_tree.children.append(_tag_source(el, "cdp"))
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

    # ── Provider 1: UIA/MSAA/JAB/IA2 (primary accessibility) ────────────────
    providers_to_try = (
        ["uia", "msaa", "jab", "ia2"] if backend_name == "auto" else [backend_name]
    )

    for pname in providers_to_try:
        t0 = time.monotonic()
        try:
            tree = backend.get_element_tree(
                app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                depth=depth, backend=pname,
            )
            elapsed = (time.monotonic() - t0) * 1000

            if tree is not None:
                tagged = _tag_source(tree, pname)
                flat = _flatten(tagged)
                elements_count = len(flat)

                # (#394) A tree with only a root node and zero children is
                # not useful — likely a UWP/WinUI app where the backend
                # could not reach the real UI.  Record it but keep trying
                # the next provider instead of accepting it immediately.
                if not tree.children:
                    logger.info(
                        "Provider %s returned root-only tree (0 children), "
                        "trying next provider...", pname,
                    )
                    stats.providers.append(ProviderStat(
                        name=pname, elements=elements_count,
                        elapsed_ms=elapsed, status="empty_tree",
                    ))
                    # Keep as fallback in case no provider does better
                    if root_tree is None:
                        root_tree = tagged
                        window_area = _window_area(tree)
                    continue

                stats.providers.append(ProviderStat(
                    name=pname, elements=elements_count, elapsed_ms=elapsed, status="ok"
                ))
                merged_elements.extend(flat[1:])  # skip root itself (merged below)
                root_tree = tagged
                window_area = _window_area(tree)
                break  # Got a valid tree; stop trying other base providers
            else:
                stats.providers.append(ProviderStat(
                    name=pname, elapsed_ms=elapsed, status="skipped"
                ))
        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000
            logger.debug("Provider %s failed: %s", pname, exc)
            stats.providers.append(ProviderStat(
                name=pname, elapsed_ms=elapsed, status="error"
            ))

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
                    debug_port = _get_cascade_pkg().find_cdp_port(pid)
            except Exception as exc:
                logger.debug("CDP port detection failed: %s", exc)

            if debug_port:
                bounds = (root_tree.x, root_tree.y, root_tree.width, root_tree.height)
                cdp_elements = _get_cascade_pkg()._fetch_cdp_elements(
                    pid or 0, debug_port, bounds
                )

            elapsed = (time.monotonic() - t0) * 1000
            if cdp_elements:
                # Tag and add CDP elements as children of root
                for el in cdp_elements:
                    tagged_el = _tag_source(el, "cdp")
                    merged_elements.append(tagged_el)

                stats.providers.append(ProviderStat(
                    name="cdp", elements=len(cdp_elements), elapsed_ms=elapsed, status="ok"
                ))
            else:
                stats.providers.append(ProviderStat(
                    name="cdp", elapsed_ms=elapsed,
                    status="skipped" if debug_port is None else "no_elements"
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

    # ── Assemble final stats ─────────────────────────────────────────────────
    stats.total_elements = len(merged_elements)
    if window_area > 0 and merged_elements:
        stats.coverage_estimate = _estimate_coverage(merged_elements, window_area)

    return CascadeResult(
        tree=root_tree,
        stats=stats,
        primary_provider=providers_to_try[0] if providers_to_try else "uia",
    )
