"""See command — capture screenshot and analyze UI elements."""
from __future__ import annotations

from naturo.cli._jsonio import json_dumps
import re as _re_mod
from dataclasses import dataclass
from typing import Any

import click

import naturo.cli.core._common as _common
from naturo.value_preview import bounded_value


# ── see recognition helpers ──────────────────────────────────────────────────
# Extracted from the former monolithic `see` so its recognition phases read as
# named steps. Behaviour-identical lifts; each returns the element tree the
# renderer below consumes.


def _recognize_via_cascade(be, *, app, window_title, hwnd, pid, depth, backend,
                           coverage_target, path, tech, cascade,
                           ai_provider, ai_model, ai_api_key,
                           excel_max_cells, excel_max_rows, excel_max_cols):
    """Progressive multi-provider recognition (#140): auto-capture a screenshot
    when a pixel technique (AI/OCR) is active, then fuse the structured + pixel
    providers via ``run_cascade`` (or ``app_content_tree`` for a bare --app that
    resolves to several UWP windows). Returns ``(tree, cascade_stats)``.
    """
    # Auto-capture a screenshot when a pixel technique is active so AI/OCR have an
    # image to read (#275); capture the TARGET window, not the foreground terminal
    # (#694). The temp file is block-local — only its path feeds the cascade.
    cascade_screenshot = path
    cascade_capture_result = None
    if not cascade_screenshot and (cascade or tech.fill_gaps_ai or tech.run_ocr):
        import tempfile as _tmpfile
        _tmp = _tmpfile.NamedTemporaryFile(
            suffix=".png", prefix="naturo_cascade_", delete=False)
        _tmp.close()
        try:
            _cascade_hwnd = hwnd
            if not _cascade_hwnd and hasattr(be, "_resolve_hwnd"):
                try:
                    _cascade_hwnd = be._resolve_hwnd(
                        app=app, window_title=window_title, pid=pid)
                except Exception:
                    _cascade_hwnd = None
            if _cascade_hwnd:
                cascade_capture_result = be.capture_window(
                    hwnd=_cascade_hwnd, output_path=_tmp.name)
            else:
                cascade_capture_result = be.capture_screen(output_path=_tmp.name)
            cascade_screenshot = cascade_capture_result.path
        except Exception:
            cascade_screenshot = None

    from naturo.cascade import run_cascade
    tree = None
    cascade_stats = None

    # (calc-zombie) A bare --app can resolve to several UWP windows at once —
    # empty ApplicationFrameWindow ghosts + the live CoreWindow — and a single
    # _resolve_hwnd may pick a ghost. Gather all the app's windows, cascade each,
    # keep only the content-bearing ones. Shared with MCP see_ui_tree.
    if app and hwnd is None and not window_title and pid is None:
        from naturo.cascade._appwindows import app_content_tree
        tree, cascade_stats = app_content_tree(
            be, app, depth=depth, backend_name=backend,
            coverage_target=coverage_target)

    if tree is None:
        cascade_result = run_cascade(
            be, app=app, window_title=window_title, hwnd=hwnd, pid=pid,
            depth=depth, backend_name=backend, coverage_target=coverage_target,
            fill_gaps_ai=tech.fill_gaps_ai, ai_provider=ai_provider,
            ai_model=ai_model, ai_api_key=ai_api_key,
            screenshot_path=cascade_screenshot,
            screenshot_scale_factor=(
                cascade_capture_result.scale_factor if cascade_capture_result else 1.0),
            run_ocr=tech.run_ocr, excel_max_cells=excel_max_cells,
            excel_max_rows=excel_max_rows, excel_max_cols=excel_max_cols,
            enable_uia=tech.enable_uia, enable_msaa=tech.enable_msaa,
            enable_ia2=tech.enable_ia2, enable_jab=tech.enable_jab,
            enable_cdp=tech.enable_cdp, enable_com=tech.enable_com)
        tree = cascade_result.tree
        cascade_stats = cascade_result.stats
    return tree, cascade_stats


def _merge_app_windows(be, app, depth, backend, json_output):
    """(#304) Enumerate ALL windows of an application and merge their UI trees
    under one virtual ``app_root`` node (used for ``see --app`` without --hwnd on
    the non-cascade path). :func:`_common._fail` if nothing matches / all empty."""
    from naturo.backends.base import ElementInfo as BaseElementInfo
    hwnds = be._resolve_hwnds(app=app)
    if not hwnds:
        _common._fail(json_output, "WINDOW_NOT_FOUND", f"No windows found for app '{app}'.")

    window_trees = []
    for h in hwnds:
        subtree = be.get_element_tree(hwnd=h, depth=depth, backend=backend)
        # Keep every window with a real tree; ghost-frame dropping is the cascade
        # path's job (content_score can't tell a childless window from a ghost).
        if subtree:
            window_trees.append((h, subtree))

    if not window_trees:
        _common._fail(json_output, "WINDOW_NOT_FOUND", "All windows have empty UI trees.")

    tree = BaseElementInfo(
        id="app_root", role="Application", name=app, value=None,
        x=0, y=0, width=0, height=0, children=[], properties={})
    for h, subtree in window_trees:
        # Wrap each window tree in a "Window" group node to preserve identity.
        tree.children.append(BaseElementInfo(
            id=f"window_{h}", role="WindowGroup",
            name=f"{subtree.name} (HWND:{h})", value=None,
            x=subtree.x, y=subtree.y, width=subtree.width, height=subtree.height,
            children=[subtree], properties={}))
    return tree


def _el_to_selector_dict(el: Any) -> dict[str, str]:
    """Convert an ElementInfo to a dict suitable for SelectorBuilder (#102)."""
    raw_id = str(el.id) if el.id else ""
    aid = raw_id if raw_id and not _re_mod.fullmatch(r"e\d+", raw_id) else ""
    return {"role": el.role or "*", "name": el.name or "", "automationid": aid}


def _build_selector(el: Any, ancestors_dicts: list, sel_builder: Any,
                    selector_app: str) -> str:
    """Build a URI selector for *el* given its ancestor dicts (#102)."""
    return sel_builder.build_uri(
        _el_to_selector_dict(el), ancestors_dicts, app=selector_app)


@dataclass
class _JsonRenderCtx:
    """Immutable config + mutable accumulators for :func:`_tree_to_json`."""
    store_snapshot: bool
    element_obj_to_ref: dict          # id(el) -> stable ref (#502)
    display_ref_map: dict             # display "eN" -> stable ref (mutated)
    visible_only: bool
    full_text: bool
    selector_app: str
    sel_builder: Any
    fusion_annotate: Any              # cascade._correctness.annotate
    seq: list                         # DFS display-id counter [0] (mutated)


def _tree_to_json(el: Any, ctx: _JsonRenderCtx, parent_ref: str | None = None,
                  ancestors_dicts: list | None = None) -> dict | None:
    """Serialize an ElementInfo tree to the ``see --json`` node dict (recursive).

    Assigns sequential display refs (e1, e2, … in DFS order, #237), maps them to
    stable refs for click resolution (#502), exposes AutomationId (#295), unified
    selectors (#102), value previews (#372), and correctness-tagged fusion (M1).
    Returns ``None`` for an offscreen node under ``--visible-only`` (#365).
    """
    if ancestors_dicts is None:
        ancestors_dicts = []

    ctx.seq[0] += 1
    display_id = f"e{ctx.seq[0]}"

    if ctx.store_snapshot:
        stable_ref = ctx.element_obj_to_ref.get(id(el))
        if stable_ref:
            ctx.display_ref_map[display_id] = stable_ref

    # (#295) Expose AutomationId separately; filter tree-assigned "eN" placeholders.
    raw_id = str(el.id) if el.id else ""
    automation_id = raw_id if raw_id and not _re_mod.fullmatch(r"e\d+", raw_id) else ""

    _is_offscreen = (el.x == 0 and el.y == 0 and el.width == 0 and el.height == 0)
    if ctx.visible_only and _is_offscreen:  # (#365)
        return None

    el_dict = _el_to_selector_dict(el)
    selector_uri = _build_selector(el, ancestors_dicts, ctx.sel_builder, ctx.selector_app)
    child_ancestors = ancestors_dicts + [el_dict]

    children_raw = [_tree_to_json(c, ctx, parent_ref=display_id,
                                  ancestors_dicts=child_ancestors)
                    for c in el.children]
    children = [c for c in children_raw if c is not None]

    d = {
        "id": display_id, "automation_id": automation_id,
        "role": el.role, "name": el.name, "value": el.value,
        "selector": selector_uri, "x": el.x, "y": el.y,
        "width": el.width, "height": el.height, "children": children,
    }
    if _is_offscreen:
        d["offscreen"] = True

    # (#372) Value preview for Document/Edit/Text (full value already in d["value"]).
    if el.role and el.role.lower() in ("document", "edit", "text") and el.value:
        _pv, _ = bounded_value(el.value, full=ctx.full_text)
        d["value_preview"] = _pv
        d["value_length"] = len(el.value)

    # (#295) Always use the naturo ref for parent, never raw AutomationId.
    if parent_ref:
        d["parent_ref"] = parent_ref
        d["parent_id"] = parent_ref  # deprecated alias, kept for back-compat
    props = getattr(el, "properties", {})
    if props.get("keyboard_shortcut"):
        d["keyboard_shortcut"] = props["keyboard_shortcut"]
    if props.get("source"):
        d["source"] = props["source"]
    # (M1) Correctness-tagged fusion: techniques[]/correctness/confidence.
    _fusion = ctx.fusion_annotate(props)
    if _fusion is not None:
        d["techniques"] = _fusion["techniques"]
        d["correctness"] = _fusion["correctness"]
        d["confidence"] = _fusion["confidence"]
    return d


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
@click.option("--depth", "-d", type=int, default=0,
              help="Maximum tree depth (0 = unlimited, the default; "
                   "pass a positive N to cap traversal at N levels)")
@click.option("--path", "-p", help="Save screenshot to path")
@click.option("--annotate", is_flag=True, help="Annotate screenshot with element labels")
@click.option("--snapshot/--no-snapshot", "store_snapshot", default=True, help="Store result in snapshot (default: on)")
@click.option("--session", default=None, envvar="NATURO_SESSION",
              help="Snapshot session name for isolation (default: NATURO_SESSION env or 'default')")
@click.option("--cascade", is_flag=True, hidden=True,
              help="Deprecated alias for --ai (adds the AI-vision layer).")
@click.option("--fill-gaps", "fill_gaps", is_flag=True, hidden=True,
              help="Deprecated alias for --ai.")
@click.option("--ocr", "run_ocr", is_flag=True,
              help="Recognition technique: local OCR (rapidocr) — recover text baked "
                   "into images/canvas; nodes tagged 'ocr' (uncertain).")
# ── Recognition techniques (composable; the active set is the UNION of every one
# given). Presets --fast/--deep expand to a set and join the union. If NONE is
# given, defaults to --fast. UIA/MSAA/IA2/JAB/CDP/COM are deterministic/structured
# and only run when the window actually exposes them (cheap when they don't); OCR
# and AI are the uncertain pixel layers. ──
@click.option("--fast", "want_fast", is_flag=True,
              help="Preset: all fast structured techniques (uia+msaa+ia2+jab+cdp+com), "
                   "each auto-triggered only where applicable. This is the DEFAULT "
                   "when no technique is given.")
@click.option("--deep", "want_deep", is_flag=True,
              help="Preset: the full stack — every structured technique PLUS ocr + ai.")
@click.option("--uia", "want_uia", is_flag=True, help="Technique: UIAutomation (modern Windows apps).")
@click.option("--msaa", "want_msaa", is_flag=True, help="Technique: MSAA (legacy MFC/VB6/Delphi).")
@click.option("--ia2", "want_ia2", is_flag=True, help="Technique: IAccessible2 (Firefox/Thunderbird/LibreOffice).")
@click.option("--jab", "want_jab", is_flag=True, help="Technique: Java Access Bridge (Swing/AWT).")
@click.option("--cdp", "want_cdp", is_flag=True, help="Technique: Chrome DevTools Protocol web/DOM (Chromium/Electron).")
@click.option("--com", "want_com", is_flag=True, help="Technique: COM object model (Excel/WPS spreadsheet cells).")
@click.option("--ai", "want_ai", is_flag=True,
              help="Technique: AI vision (needs a provider; slower). Recovers structure "
                   "from pixels for windows that expose no accessibility.")
@click.option("--excel-max-cells", "excel_max_cells", type=int, default=None,
              help="Cascade Excel: max non-empty cells to emit (default 500). "
                   "Raise for large sheets; per-invocation, so concurrent runs "
                   "can differ.")
@click.option("--excel-max-rows", "excel_max_rows", type=int, default=None,
              help="Cascade Excel: max rows of the used range to scan (default 400)")
@click.option("--excel-max-cols", "excel_max_cols", type=int, default=None,
              help="Cascade Excel: max cols of the used range to scan (default 100)")
@click.option("--stats", "show_stats", is_flag=True,
              help="Show per-provider recognition statistics after output")
@click.option("--coverage", "coverage_target", type=float, default=0.0,
              help="Coverage target (0.0\u20131.0) before trying next provider (default: 0 = UIA only)")
@click.option("--visible-only", is_flag=True, help="Hide offscreen/zero-bounds elements")
@click.option("--selectors", "show_selectors", is_flag=True,
              help="Show unified selectors alongside eN refs (always included in JSON mode)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.option("--compact", "compact", is_flag=True,
              help='Compact agent-friendly text: one line per element as '
                   '\'eN [role] "name" [=value]\' — no bounds/props/selectors '
                   '(fewest tokens; refs still work with \'naturo click eN\')')
@click.option("--full-text", "full_text", is_flag=True,
              help="Inline the COMPLETE text of each Document/Edit/Text element "
                   "instead of a truncated preview (for dumping + searching all "
                   "visible content in one call)")
@click.option(
    "--backend", "--method", "-b", "-m",
    type=click.Choice(["uia", "msaa", "ia2", "jab", "cdp", "win32", "win32hybrid", "auto", "hybrid"]),
    default="auto", hidden=True,
    help="Superseded by the composable technique flags (--uia/--msaa/--ia2/--jab/"
         "--cdp). Low-level single-backend override; kept for scripts.",
)
@click.option("--app-id", "app_id", default=None,
              help='Stable app/window ID from "naturo app list" output (e.g. a1)')
@click.option("--ai-provider", "ai_provider",
              type=click.Choice(["auto", "anthropic", "openai", "ollama"]),
              default="auto",
              help="AI vision provider for --ai/--deep (default: auto)")
@click.option("--ai-model", "ai_model", default=None, envvar="NATURO_AI_MODEL",
              help="AI model override (e.g. claude-opus-4-6, gpt-4o)")
@click.option("--ai-api-key", "ai_api_key", default=None,
              help="AI provider API key (overrides env var / credentials file)")
def see(app: str | None, window_title: str | None, hwnd: int | None, pid: int | None,
        mode: str, depth: int, path: str | None, annotate: bool, store_snapshot: bool,
        session: str | None, cascade: bool, fill_gaps: bool, run_ocr: bool, show_stats: bool,
        want_fast: bool, want_deep: bool, want_uia: bool, want_msaa: bool,
        want_ia2: bool, want_jab: bool, want_cdp: bool, want_com: bool, want_ai: bool,
        coverage_target: float, visible_only: bool, show_selectors: bool,
        excel_max_cells: int | None, excel_max_rows: int | None, excel_max_cols: int | None,
        json_output: bool, compact: bool, full_text: bool, backend: str, app_id: str | None,
        ai_provider: str, ai_model: str | None, ai_api_key: str | None) -> None:
    """Capture screenshot and analyze UI elements.

    Inspects the UI element tree of the foreground window (or a specific
    window identified by --hwnd). Shows the element hierarchy with roles,
    names, and bounding rectangles.  Results are stored in a snapshot so
    subsequent commands can reference elements by ID.

    Recognition techniques are composable flags; the active set is the UNION of
    every one given. Structured techniques \u2014 --uia --msaa --ia2 --jab --cdp --com
    \u2014 auto-trigger only where the window exposes them (cheap when they don't).
    --ocr and --ai are the pixel-recovery layers (uncertain; --ai needs a provider).

    Presets: --fast = all structured techniques (the DEFAULT when nothing is
    given); --deep = the full stack (structured + ocr + ai). Give nothing and you
    get the fused structured tree, each node tagged with the technique that found
    it. When a window exposes no accessibility, `see` prints a hint to try --ocr/--ai.

    \b
    Examples:
        naturo see --app feishu                # default = --fast: fused structured tree
        naturo see --app feishu --ocr          # add local OCR (on-screen text)
        naturo see --app feishu --ai           # add AI vision (needs a provider)
        naturo see --app feishu --deep         # everything (structured + ocr + ai)
        naturo see --hwnd 12345 --uia          # only UIA (no fusion)
        naturo see --hwnd 12345 --uia --cdp    # only UIA + CDP web content
        naturo see --app feishu --stats        # show which technique found each region
    """
    # (#752) Auto-detect app ID pattern (a1, a2, ...) in --app flag
    from naturo.cli.options import maybe_promote_app_to_app_id
    app, app_id = maybe_promote_app_to_app_id(app, app_id)

    # (#361) Resolve --app-id to hwnd/pid before any other logic. (#573) Use
    # hwnd + pid for precise targeting; never set app to process_name (may be a
    # full path that breaks fuzzy matching).
    if app_id is not None:
        entry = _common._resolve_app_id(app_id, json_output)
        hwnd = entry.handle
        pid = entry.pid

    # BUG-028: Validate --depth (before platform check — input validation first).
    # 0 = unlimited (walk the whole tree); any positive value caps traversal.
    # Negative is the only invalid input now — the native layer bounds the total.
    if depth < 0:
        msg = f"--depth must be 0 (unlimited) or a positive number, got {depth}"
        _common._fail(json_output, "INVALID_INPUT", msg)

    _common._require_gui(json_output, "UI inspection")

    # (#1022) Auto-create the parent directory for --path so a missing folder
    # doesn't surface as a raw [Errno 2] mislabeled as UNKNOWN_ERROR on save.
    if path:
        _common._ensure_output_dir(path, json_output)

    try:
        be = _common._get_backend(json_output)

        # ── Recognition-technique selection (shared resolver; default --fast) ──
        from naturo.cli._techniques import resolve_techniques
        _tech = resolve_techniques(
            fast=want_fast, deep=want_deep, uia=want_uia, msaa=want_msaa,
            ia2=want_ia2, jab=want_jab, cdp=want_cdp, com=want_com,
            ocr=run_ocr, ai=want_ai, cascade=cascade, fill_gaps=fill_gaps,
        )
        # _recognize_via_cascade reads the enable_* flags off _tech directly; only
        # the pixel-technique flags are needed here to pick the recognition path.
        _want_ai = _tech.fill_gaps_ai
        _want_ocr = _tech.run_ocr

        # ── Recognition: cascade fusion, multi-window merge, or single fetch ──
        cascade_stats = None
        if cascade or _want_ai or _want_ocr or backend in ("auto", "hybrid", "cdp"):
            tree, cascade_stats = _recognize_via_cascade(
                be, app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                depth=depth, backend=backend, coverage_target=coverage_target,
                path=path, tech=_tech, cascade=cascade, ai_provider=ai_provider,
                ai_model=ai_model, ai_api_key=ai_api_key,
                excel_max_cells=excel_max_cells, excel_max_rows=excel_max_rows,
                excel_max_cols=excel_max_cols)
        elif app and not hwnd and hasattr(be, "_resolve_hwnds"):
            # (#304) --app without --hwnd on the non-cascade path: merge all windows.
            tree = _merge_app_windows(be, app, depth, backend, json_output)
        else:
            tree = be.get_element_tree(
                app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                depth=depth, backend=backend)

        if tree is None:
            _common._fail(json_output, "WINDOW_NOT_FOUND",
                          "No window found or UI tree is empty.")

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

        # (M1) Unified Auto Element Tree: fusion tags + AI/image warning.
        # recognition_summary only counts cascade-tagged nodes, so a plain
        # (non-cascade) tree yields an empty summary and no false warning.
        from naturo.cascade._correctness import (
            annotate as _fusion_annotate,
            recognition_summary as _fusion_summary,
            uncertain_warning as _fusion_warning,
        )
        _recognition = _fusion_summary(tree)
        _recognition_warning = _fusion_warning(_recognition)

        if json_output:
            # (#237) _tree_to_json assigns display ids from a DFS counter so refs
            # match _flatten() order and stay unique even when elements share a
            # backend AutomationId.
            _json_ctx = _JsonRenderCtx(
                store_snapshot=store_snapshot,
                element_obj_to_ref=_element_obj_to_ref if store_snapshot else {},
                display_ref_map=_display_ref_map, visible_only=visible_only,
                full_text=full_text, selector_app=_selector_app,
                sel_builder=_sel_builder, fusion_annotate=_fusion_annotate, seq=[0])
            out = _tree_to_json(tree, _json_ctx)
            assert out is not None, "Root element should never be filtered"
            if snapshot_id:
                out["snapshot_id"] = snapshot_id
            if cascade_stats:
                out["cascade_stats"] = cascade_stats.to_dict()
            # (M1) Structured recognition summary so agents can branch on
            # correctness without parsing the stderr warning.
            if _recognition["total_nodes"] > 0:
                out["recognition_summary"] = _recognition

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



            click.echo(json_dumps(out, indent=2))
            # (M1) Correctness warning to stderr keeps --json stdout pure.
            if _recognition_warning:
                click.echo(_recognition_warning, err=True)
        else:
            # BUG-071: include short element IDs (e1, e2, ...) that can be
            # passed to ``naturo click e3`` for quick interaction.
            _ref_counter = [0]
            _CLI_ACTIONABLE = {
                "button", "hyperlink", "link", "edit", "text", "checkbox",
                "radiobutton", "combobox", "menuitem", "listitem", "tab",
                "tabitem", "treeitem", "slider", "spinner", "document",
            }

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

                # (goal) --compact: agent-friendly minimal line — eN [role] "name"
                # [=value], no bounds/props/selectors. Refs still assigned for all
                # nodes so `naturo click eN` resolves; only meaningful nodes print.
                # True per-node capabilities: [r]eadable/[a]ctionable/[e]ditable
                _cp = getattr(el, "properties", {}) or {}
                _caps = "".join(c for c, k in (("r", "readable"), ("a", "actionable"),
                                               ("e", "editable")) if _cp.get(k))
                _caps_str = f" [{_caps}]" if _caps else ""

                if compact:
                    _name = f' "{el.name}"' if el.name else ""
                    _val = getattr(el, "value", None)
                    _val_str = ""
                    if _val:
                        _shown, _elided = bounded_value(_val, full=full_text)
                        _val_str = f" ={_shown!r}"
                        if _elided:
                            _val_str += f" …(+{_elided} chars)"
                    if el.name or (el.role or "").lower() in _CLI_ACTIONABLE or _val:
                        click.echo(f"{prefix}{ref} [{el.role}]{_name}{_val_str}{_caps_str}")
                    for child in el.children:
                        print_tree(child, indent + 1, child_ancestors)
                    return

                name_str = f' "{el.name}"' if el.name else ""
                pos_str = f" ({el.x},{el.y} {el.width}x{el.height})"
                props = getattr(el, "properties", {})
                # Fusion tag: show every source that saw this control, e.g.
                # [uia+msaa], so the unified merge is visible — the primary
                # `source` plus any `corroborated_by` sources folded in.
                if props.get("source"):
                    _srcs = [props["source"]] + list(props.get("corroborated_by") or [])
                    source_str = f" [{'+'.join(dict.fromkeys(_srcs))}]"
                else:
                    source_str = ""
                offscreen_str = " [offscreen]" if _is_offscreen else ""
                # (#102) Show selector when --selectors is requested
                selector_str = ""
                if show_selectors:
                    selector_uri = _build_selector(el, ancestors_dicts, _sel_builder, _selector_app)
                    selector_str = f"  {selector_uri}"
                click.echo(f"{prefix}[{el.role}]{name_str}{pos_str} {ref}{source_str}{offscreen_str}{_caps_str}{selector_str}")

                # (#372) Show text content for Document/Edit/Text elements: full
                # when --full-text, otherwise a bounded preview with a marker for
                # how much was elided (read it all with `naturo get eN`).
                if el.role and el.role.lower() in ("document", "edit", "text") and el.value:
                    _shown, _elided = bounded_value(el.value, full=full_text)
                    disp = _shown.replace("\n", "\\n").replace("\r", "")
                    suffix = f" \u2026(+{_elided} chars)" if _elided else ""
                    click.echo(f"{prefix}  \u00bb {disp}{suffix}")

                for child in el.children:
                    print_tree(child, indent + 1, child_ancestors)

            print_tree(tree)
            # (M1) Warn (stderr) when any node is AI/image-only (uncertain).
            if _recognition_warning:
                click.echo(_recognition_warning, err=True)
            if snapshot_id:
                click.echo(f"\nSnapshot: {snapshot_id}")
                if show_selectors:
                    click.echo("Tip: use 'naturo click --selector \"<selector>\"' for stable targeting across sessions.")
                else:
                    click.echo("Tip: use 'naturo click e<N>' to click an element by its ref.")

            # Empty/shallow structured tree + no pixel technique chosen → nudge
            # toward --ocr / --ai (some windows expose no accessibility at all;
            # those are the pixel-recovery paths).
            if not (_want_ocr or _want_ai) and tree is not None:
                try:
                    from naturo.cascade._run import _flatten as _flat
                    from naturo.cascade._run import _is_shallow_tree
                    if _is_shallow_tree(_flat(tree))[0]:
                        click.echo(
                            "Note: this window exposed little/no structured "
                            "content. Try '--ocr' (read on-screen text) or "
                            "'--ai' (AI vision) to recover it.", err=True)
                except Exception:
                    pass

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
        _common._fail(json_output, "WINDOW_NOT_FOUND", str(e))
    except Exception as e:
        _common._fail(json_output, "UNKNOWN_ERROR", str(e))
