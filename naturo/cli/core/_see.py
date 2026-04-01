"""See command — capture screenshot and analyze UI elements."""
from __future__ import annotations

import json as json_module
import re as _re_mod
from typing import Any

import click

import naturo.cli.core._common as _common


@click.command()
@click.option("--app", help="Target application (name or partial match)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--pid", type=int, help="Process ID")
@click.option(
    "--mode",
    type=click.Choice(["full", "interactive", "fast"]),
    default="full",
    help="Analysis mode: full (all elements), interactive (clickable only), fast (quick scan)",
)
@click.option("--depth", "-d", type=int, default=7, help="Maximum tree depth (1-50)")
@click.option("--path", "-p", help="Save screenshot to path")
@click.option("--annotate", is_flag=True, help="Annotate screenshot with element labels")
@click.option("--snapshot/--no-snapshot", "store_snapshot", default=True, help="Store result in snapshot (default: on)")
@click.option("--session", default=None, envvar="NATURO_SESSION",
              help="Snapshot session name for isolation (default: NATURO_SESSION env or 'default')")
@click.option("--cascade", is_flag=True,
              help="Progressive recognition: try UIA, then CDP (Electron/CEF), then AI vision")
@click.option("--fill-gaps", "fill_gaps", is_flag=True,
              help="Use AI vision to fill uncovered UI regions (requires AI provider)")
@click.option("--stats", "show_stats", is_flag=True,
              help="Show per-provider recognition statistics after output")
@click.option("--coverage", "coverage_target", type=float, default=0.0,
              help="Coverage target (0.0\u20131.0) before trying next provider (default: 0 = UIA only)")
@click.option("--visible-only", is_flag=True, help="Hide offscreen/zero-bounds elements")
@click.option("--selectors", "show_selectors", is_flag=True,
              help="Show unified selectors alongside eN refs (always included in JSON mode)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.option(
    "--backend", "--method", "-b", "-m",
    type=click.Choice(["uia", "msaa", "ia2", "jab", "cdp", "win32", "win32hybrid", "auto", "hybrid"]),
    default="auto",
    help="Accessibility backend / interaction method: auto (default: tries all), uia, msaa (legacy apps), ia2 (Firefox/Thunderbird), jab (Java/Swing), cdp (Chrome/Electron web content via DevTools), win32 (VB6/ActiveX), hybrid (per-node backend selection)",
)
@click.option("--app-id", "app_id", default=None,
              help='Stable app/window ID from "naturo app list" output (e.g. a1)')
@click.option("--provider", "ai_provider",
              type=click.Choice(["auto", "anthropic", "openai", "google", "ollama"]),
              default="auto", help="AI provider for --cascade/--fill-gaps mode")
@click.option("--model", "ai_model", default=None, envvar="NATURO_AI_MODEL",
              help="AI model name (e.g. claude-opus-4-6, gpt-4o, gemini-2.5-pro)")
@click.option("--api-key", "ai_api_key", default=None,
              help="AI provider API key (overrides env var / credentials file)")
def see(app: str | None, window_title: str | None, hwnd: int | None, pid: int | None,
        mode: str, depth: int, path: str | None, annotate: bool, store_snapshot: bool,
        session: str | None, cascade: bool, fill_gaps: bool, show_stats: bool,
        coverage_target: float, visible_only: bool, show_selectors: bool,
        json_output: bool, backend: str, app_id: str | None,
        ai_provider: str, ai_model: str | None, ai_api_key: str | None) -> None:
    """Capture screenshot and analyze UI elements.

    Inspects the UI element tree of the foreground window (or a specific
    window identified by --hwnd). Shows the element hierarchy with roles,
    names, and bounding rectangles.  Results are stored in a snapshot so
    subsequent commands can reference elements by ID.

    Use --backend msaa for legacy applications (MFC, VB6, Delphi) that
    don't expose UIAutomation elements. Use --backend ia2 for IA2-enabled
    applications (Firefox, Thunderbird, LibreOffice). Use --backend auto to
    try UIA first, then IA2, then MSAA automatically.

    Use --backend cdp for Chrome/Electron apps with DevTools Protocol enabled.
    The browser must be started with --remote-debugging-port=9222.

    Use --backend hybrid for per-node backend selection \u2014 each node in the
    tree picks the optimal backend based on its Win32 class (Electron\u2192CDP,
    Java\u2192JAB, Mozilla\u2192IA2, default\u2192UIA).

    Use --cascade to progressively try multiple providers (UIA \u2192 CDP \u2192 AI vision).
    This maximizes coverage for Electron apps (Feishu, Slack, VS Code, etc.)
    that render content in a WebView.

    \b
    Examples:
        naturo see --app feishu --cascade      # UIA + CDP for Electron content
        naturo see --app feishu --cascade --fill-gaps  # Also use AI vision
        naturo see --app feishu --cascade --stats      # Show provider breakdown
        naturo see --app feishu --backend auto         # Try all A11y backends
        naturo see --app feishu --backend hybrid       # Per-node backend selection
    """
    # (#361) Resolve --app-id to app/hwnd/pid before any other logic
    if app_id is not None:
        from naturo.app_ids import get_app_id_map
        id_map = get_app_id_map()
        entry = id_map.resolve(app_id)
        if entry is None:
            msg = f'App ID "{app_id}" not found or expired. Run "naturo app list" to refresh.'
            if json_output:
                click.echo(_common._json_error_str("APP_ID_NOT_FOUND", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)
        # (#573) Use hwnd + pid for precise targeting.  Do NOT set app
        # to process_name — it may be a full path that breaks fuzzy matching.
        hwnd = entry.handle
        pid = entry.pid

    # BUG-028: Validate --depth range (before platform check — input validation first)
    if depth < 1 or depth > 50:
        msg = f"--depth must be between 1 and 50, got {depth}"
        if json_output:
            click.echo(_common._json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    if not _common._platform_supports_gui():
        msg = _common._platform_error_msg("UI inspection")
        if json_output:
            click.echo(_common._json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    try:
        be = _common._get_backend(json_output)

        # ── Cascade mode: progressive multi-provider recognition (issue #140) ──
        cascade_stats = None
        if cascade or backend == "auto" or backend == "hybrid":
            # (#275) Auto-capture screenshot for cascade mode so AI vision
            # fallback can trigger when UIA tree is too shallow.
            # (#694) Use capture_window with resolved hwnd so the screenshot
            # captures the target app, not the foreground terminal window.
            cascade_screenshot = path
            _cascade_tmp_screenshot = None
            cascade_capture_result = None
            if not cascade_screenshot and cascade:
                import tempfile as _tmpfile
                _cascade_tmp_screenshot = _tmpfile.NamedTemporaryFile(
                    suffix=".png", prefix="naturo_cascade_", delete=False,
                )
                _cascade_tmp_screenshot.close()
                try:
                    # (#694) Capture the TARGET window, not the foreground
                    # window (which is often the terminal running naturo).
                    _cascade_hwnd = hwnd
                    if not _cascade_hwnd and hasattr(be, "_resolve_hwnd"):
                        try:
                            _cascade_hwnd = be._resolve_hwnd(
                                app=app, window_title=window_title, pid=pid,
                            )
                        except Exception:
                            _cascade_hwnd = None
                    if _cascade_hwnd:
                        cascade_capture_result = be.capture_window(
                            hwnd=_cascade_hwnd,
                            output_path=_cascade_tmp_screenshot.name,
                        )
                    else:
                        cascade_capture_result = be.capture_screen(
                            output_path=_cascade_tmp_screenshot.name,
                        )
                    cascade_screenshot = cascade_capture_result.path
                except Exception:
                    cascade_screenshot = None

            from naturo.cascade import run_cascade
            cascade_result = run_cascade(
                be,
                app=app,
                window_title=window_title,
                hwnd=hwnd,
                pid=pid,
                depth=depth,
                backend_name=backend,
                coverage_target=coverage_target,
                fill_gaps_ai=fill_gaps,
                ai_provider=ai_provider,
                ai_model=ai_model,
                ai_api_key=ai_api_key,
                screenshot_path=cascade_screenshot,
                screenshot_scale_factor=(
                    cascade_capture_result.scale_factor
                    if cascade_capture_result else 1.0
                ),
            )
            tree = cascade_result.tree
            cascade_stats = cascade_result.stats
        else:
            # (#304) When --app is used without --hwnd, enumerate ALL windows
            # of the application and merge their UI trees.
            if app and not hwnd and hasattr(be, "_resolve_hwnds"):
                hwnds = be._resolve_hwnds(app=app)
                if not hwnds:
                    msg = f"No windows found for app '{app}'."
                    if json_output:
                        click.echo(_common._json_error_str("WINDOW_NOT_FOUND", msg))
                    else:
                        click.echo(f"Error: {msg}", err=True)
                    raise SystemExit(1)

                # Get element tree for each window
                from naturo.backends.base import ElementInfo as BaseElementInfo
                window_trees = []
                for h in hwnds:
                    subtree = be.get_element_tree(
                        hwnd=h, depth=depth, backend=backend,
                    )
                    if subtree:
                        window_trees.append((h, subtree))

                if not window_trees:
                    msg = "All windows have empty UI trees."
                    if json_output:
                        click.echo(_common._json_error_str("WINDOW_NOT_FOUND", msg))
                    else:
                        click.echo(f"Error: {msg}", err=True)
                    raise SystemExit(1)

                # Merge into a single root: create a virtual root node
                # with each window's tree as a child
                tree = BaseElementInfo(
                    id="app_root",
                    role="Application",
                    name=app,
                    value=None,
                    x=0, y=0, width=0, height=0,
                    children=[],
                    properties={},
                )
                for h, subtree in window_trees:
                    # Wrap each window tree with a "Window" group node
                    # to preserve window identity in output
                    window_node = BaseElementInfo(
                        id=f"window_{h}",
                        role="WindowGroup",
                        name=f"{subtree.name} (HWND:{h})",
                        value=None,
                        x=subtree.x,
                        y=subtree.y,
                        width=subtree.width,
                        height=subtree.height,
                        children=[subtree],
                        properties={},
                    )
                    tree.children.append(window_node)
            else:
                tree = be.get_element_tree(
                    app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                    depth=depth, backend=backend,
                )

        if tree is None:
            msg = "No window found or UI tree is empty."
            if json_output:
                click.echo(_common._json_error_str("WINDOW_NOT_FOUND", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)

        snapshot_id = None
        ref_map: dict[str, str] = {}  # Maps "eN" → backend element id
        if store_snapshot:
            from naturo.snapshot import get_snapshot_manager
            from naturo.models.snapshot import UIElement

            mgr = get_snapshot_manager(session=session)
            snapshot_id = mgr.create_snapshot()

            # Flatten element tree into ui_map and build ref→element mapping.
            # (#456) eN refs are now hash-based (stable across snapshots) instead
            # of sequential.  The same element gets the same eN even if the tree
            # changes between snapshots (e.g. Calculator display update after Clear).
            from naturo.refs import assign_stable_refs

            _element_obj_to_ref: dict[int, str] = {}
            ui_map, ref_map = assign_stable_refs(
                tree, UIElement, element_obj_to_ref=_element_obj_to_ref,
            )
            mgr.store_detection_result(snapshot_id, ui_map)
            # Persist ref mapping so click/type can resolve e<N> refs
            mgr.store_ref_map(snapshot_id, ref_map)

            # Store window bounds in the snapshot metadata for coordinate
            # offset calculations (e.g. capture --element crop).
            _win_bounds = None
            if tree:
                _win_bounds = (tree.x, tree.y, tree.width, tree.height)
            snap_obj = mgr.get_snapshot(snapshot_id)
            snap_obj.window_bounds = _win_bounds
            snap_obj.window_handle = hwnd
            snap_obj.application_name = app
            snap_obj.window_title = window_title
            mgr._write_json_atomic(
                mgr._snap_dir(snapshot_id) / "snapshot.json",
                snap_obj.to_dict(),
            )

            # Optionally capture screenshot into snapshot
            if path:
                result = be.capture_screen(output_path=path)
                metadata = {
                    "window_handle": hwnd,
                    "application_name": app,
                    "window_title": window_title,
                    "window_bounds": _win_bounds,
                }
                mgr.store_screenshot(snapshot_id, result.path, metadata)

        # (#502) Build mapping from sequential display refs (e1, e2, …) to
        # stable hash-based refs (e1876, e2473, …) so that ``click eN`` can
        # resolve the refs shown in ``see`` output.
        _display_ref_map: dict[str, str] = {}

        # (#102) Selector builder for generating unified selectors alongside
        # eN refs.  Always active in JSON mode; opt-in via --selectors in text.
        from naturo.selector import SelectorBuilder
        _sel_builder = SelectorBuilder()
        _selector_app = app or "*"

        def _el_to_selector_dict(el: Any) -> dict[str, str]:
            """Convert an ElementInfo to a dict suitable for SelectorBuilder."""
            raw_id = str(el.id) if el.id else ""
            aid = raw_id if raw_id and not _re_mod.fullmatch(r"e\d+", raw_id) else ""
            return {
                "role": el.role or "*",
                "name": el.name or "",
                "automationid": aid,
            }

        def _build_selector(el: Any, ancestors_dicts: list[dict[str, str]]) -> str:
            """Build a URI selector for an element given its ancestor dicts."""
            el_dict = _el_to_selector_dict(el)
            return _sel_builder.build_uri(el_dict, ancestors_dicts, app=_selector_app)

        if json_output:
            # (#237) Use a sequential counter matching _flatten() DFS order
            # to assign unique display IDs.  The previous reverse-map approach
            # was lossy: when multiple elements share the same backend
            # AutomationId, the dict comprehension kept only the last ref,
            # causing duplicate display IDs in JSON output.
            _json_ref_seq = [0]

            def to_dict(el: Any, parent_ref: str | None = None, ancestors_dicts: list[dict[str, str]] | None = None) -> dict[str, Any] | None:
                """Convert ElementInfo tree to a JSON-serializable dict.

                Args:
                    el: Backend ElementInfo node.
                    parent_ref: The naturo ref (eN) of the parent element,
                        ensuring parent references are always in the same
                        ID space as element refs (#295).
                    ancestors_dicts: List of ancestor selector dicts (root-first)
                        for building unified selectors (#102).
                """
                if ancestors_dicts is None:
                    ancestors_dicts = []

                _json_ref_seq[0] += 1
                display_id = f"e{_json_ref_seq[0]}"

                # (#502) Map display ref → stable ref for click resolution
                if store_snapshot:
                    stable_ref = _element_obj_to_ref.get(id(el))
                    if stable_ref:
                        _display_ref_map[display_id] = stable_ref

                # (#295) Expose AutomationId separately.  The raw
                # el.id from the bridge may be an AutomationId or a
                # tree-assigned "eN" placeholder.  Filter placeholders.
                raw_id = str(el.id) if el.id else ""
                automation_id = raw_id if raw_id and not _re_mod.fullmatch(r"e\d+", raw_id) else ""

                # (#365) Zero-bounds elements are offscreen
                _is_offscreen = (el.x == 0 and el.y == 0 and el.width == 0 and el.height == 0)

                # (#365) --visible-only: skip offscreen elements entirely
                if visible_only and _is_offscreen:
                    return None

                # (#102) Build selector and track ancestors for children
                el_dict = _el_to_selector_dict(el)
                selector_uri = _build_selector(el, ancestors_dicts)
                child_ancestors = ancestors_dicts + [el_dict]

                children_raw = [to_dict(c, parent_ref=display_id,
                                        ancestors_dicts=child_ancestors)
                                for c in el.children]
                children = [c for c in children_raw if c is not None]

                d = {
                    "id": display_id,
                    "automation_id": automation_id,
                    "role": el.role,
                    "name": el.name,
                    "value": el.value,
                    "selector": selector_uri,
                    "x": el.x,
                    "y": el.y,
                    "width": el.width,
                    "height": el.height,
                    "children": children,
                }

                # (#365) Mark offscreen elements
                if _is_offscreen:
                    d["offscreen"] = True

                # (#372) Value preview for Document/Edit/Text elements
                if el.role and el.role.lower() in ("document", "edit", "text") and el.value:
                    d["value_preview"] = el.value[:100]
                    d["value_length"] = len(el.value)

                # (#295) Always use naturo ref for parent, never raw
                # AutomationId — keeps a single consistent ID space.
                if parent_ref:
                    d["parent_ref"] = parent_ref
                # Keep deprecated "parent_id" as alias for backward compat
                if parent_ref:
                    d["parent_id"] = parent_ref
                props = getattr(el, "properties", {})
                if props.get("keyboard_shortcut"):
                    d["keyboard_shortcut"] = props["keyboard_shortcut"]
                if props.get("source"):
                    d["source"] = props["source"]
                return d
            out = to_dict(tree)
            assert out is not None, "Root element should never be filtered"
            if snapshot_id:
                out["snapshot_id"] = snapshot_id
            if cascade_stats:
                out["cascade_stats"] = cascade_stats.to_dict()

            # Add DPI context so AI agents know coordinate scaling
            try:
                dpi_scale = be.get_dpi_scale(0) if hasattr(be, "get_dpi_scale") else 1.0
                monitors = be.list_monitors()
                primary = monitors[0] if monitors else None
                out["dpi_context"] = {
                    "scale_factor": primary.scale_factor if primary else dpi_scale,
                    "dpi": primary.dpi if primary else 96,
                    "note": "Element coordinates are in physical (pixel) space.",
                }
            except Exception:
                out["dpi_context"] = {"scale_factor": 1.0, "dpi": 96, "note": "Element coordinates are in physical (pixel) space."}



            click.echo(json_module.dumps(out, indent=2))
        else:
            # BUG-071: include short element IDs (e1, e2, ...) that can be
            # passed to ``naturo click e3`` for quick interaction.
            _ref_counter = [0]

            def print_tree(el, indent=0, ancestors_dicts=None) -> None:
                """Print element tree with short element refs."""
                if ancestors_dicts is None:
                    ancestors_dicts = []

                _ref_counter[0] += 1
                ref = f"e{_ref_counter[0]}"

                # (#502) Map display ref → stable ref for click resolution
                if store_snapshot:
                    stable_ref = _element_obj_to_ref.get(id(el))
                    if stable_ref:
                        _display_ref_map[ref] = stable_ref

                # (#365) Zero-bounds = offscreen
                _is_offscreen = (el.x == 0 and el.y == 0 and el.width == 0 and el.height == 0)

                # (#102) Track ancestors for selector building
                el_dict = _el_to_selector_dict(el)
                child_ancestors = ancestors_dicts + [el_dict]

                # (#365) --visible-only: skip offscreen elements
                if visible_only and _is_offscreen:
                    for child in el.children:
                        print_tree(child, indent, child_ancestors)
                    return

                prefix = "  " * indent
                name_str = f' "{el.name}"' if el.name else ""
                pos_str = f" ({el.x},{el.y} {el.width}x{el.height})"
                props = getattr(el, "properties", {})
                source_str = f" [{props['source']}]" if props.get("source") else ""
                offscreen_str = " [offscreen]" if _is_offscreen else ""
                # (#102) Show selector when --selectors is requested
                selector_str = ""
                if show_selectors:
                    selector_uri = _build_selector(el, ancestors_dicts)
                    selector_str = f"  {selector_uri}"
                click.echo(f"{prefix}[{el.role}]{name_str}{pos_str} {ref}{source_str}{offscreen_str}{selector_str}")

                # (#372) Show text preview for Document/Edit elements
                _vp = props.get("value_preview")
                if _vp:
                    click.echo(f"{prefix}  \u00bb {_vp}")
                elif el.role and el.role.lower() in ("document", "edit", "text") and el.value:
                    preview = el.value[:100].replace("\n", "\\n").replace("\r", "")
                    suffix = "\u2026" if len(el.value) > 100 else ""
                    click.echo(f"{prefix}  \u00bb {preview}{suffix}")

                for child in el.children:
                    print_tree(child, indent + 1, child_ancestors)

            print_tree(tree)
            if snapshot_id:
                click.echo(f"\nSnapshot: {snapshot_id}")
                if show_selectors:
                    click.echo("Tip: use 'naturo click --selector \"<selector>\"' for stable targeting across sessions.")
                else:
                    click.echo("Tip: use 'naturo click e<N>' to click an element by its ref.")

            # Print cascade stats when --stats is requested
            if show_stats and cascade_stats:
                click.echo("\nRecognition Stats:")
                click.echo(f"  Total elements: {cascade_stats.total_elements}")
                click.echo(f"  Coverage:       {cascade_stats.coverage_estimate:.1%}")
                click.echo("  Providers:")
                for p in cascade_stats.providers:
                    click.echo(f"    {p.name:<12} {p.elements:>4} elements  {p.elapsed_ms:>6.0f}ms  [{p.status}]")

        # (#502) Persist display ref → stable ref mapping so that
        # ``click eN`` can resolve the sequential refs shown in ``see``.
        if store_snapshot and snapshot_id and _display_ref_map:
            mgr.store_display_ref_map(snapshot_id, _display_ref_map)

        # Generate annotated screenshot
        if annotate and store_snapshot and snapshot_id:
            try:
                from naturo.annotate import annotate_screenshot
                snap = mgr.get_snapshot(snapshot_id)
                if snap.screenshot_path:
                    elements = list(snap.ui_map.values())
                    annotated_path = annotate_screenshot(
                        snap.screenshot_path,
                        elements,
                    )
                    mgr.store_annotated(snapshot_id, annotated_path)
                    if not json_output:
                        click.echo(f"Annotated: {annotated_path}")
                else:
                    if not json_output:
                        click.echo("Warning: --annotate requires a screenshot (use --path)")
            except ImportError:
                click.echo("Warning: Pillow required for --annotate. Install: pip install naturo[annotate]", err=True)

        # Capture screenshot (when not already done above)
        if path and not store_snapshot:
            result = be.capture_screen(output_path=path)
            click.echo(f"\nScreenshot saved: {result.path}")

    except _common.WindowNotFoundError as e:
        if json_output:
            click.echo(_common._json_error_str("WINDOW_NOT_FOUND", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        if json_output:
            click.echo(_common._json_error_str("UNKNOWN_ERROR", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
