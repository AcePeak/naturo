"""Highlight command — highlight UI elements on screen."""
from __future__ import annotations

from naturo.cli._jsonio import json_dumps
import logging

import click

import naturo.cli.core._common as _common
from naturo.cli import _techniques

logger = logging.getLogger(__name__)


@click.command()
@click.argument("positional_refs", nargs=-1)
@click.option("--on", "--id", "on_ref", help="Target element ref (eN) to highlight")
@click.option("--ref", "-r", "ref_option", multiple=True, help="Specific refs to highlight (e.g. -r e5 -r e10). Omit for all.")
@click.option("--app", "-a", help="Application name (partial match)")
@click.option("--window", "window_title", default=None,
              help="Window title pattern (substring match)")
@click.option("--hwnd", type=int, help="Direct window handle")
@click.option("--app-id", "app_id", default=None,
              help='Stable app/window ID from "naturo app list" output (e.g. a1)')
@click.option("--depth", "-d", type=int, default=30, help="Tree depth for element discovery")
@click.option("--duration", type=float, default=5.0, help="Highlight duration in seconds")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.option(
    "--backend", "-b",
    type=click.Choice(["uia", "win32", "win32hybrid", "msaa", "ia2", "jab", "auto", "hybrid"]),
    default="uia", hidden=True,
    help="Low-level rendering/backend override (e.g. win32 for VB6/ActiveX). "
         "Recognition is selected with the technique flags (--uia/--cdp/…).",
)
@click.option("--all", "show_all", is_flag=True, help="Show all elements, not just actionable ones")
@click.option("--annotate", "-A", "annotate_path", type=click.Path(), default=None,
              help="Save annotated screenshot to file instead of live overlay (requires Pillow)")
@click.option("--filter", "role_filter", default=None,
              help="Filter elements by role (e.g. --filter Button)")
@click.option("--visible-only", is_flag=True,
              help="Only highlight visible (non-zero-bounds) elements")
@_techniques.technique_options
@click.option("--pid", type=int, default=None, help="Process ID")
def highlight(positional_refs, on_ref, ref_option, app, window_title, hwnd, app_id,
              depth, duration, json_output, backend, show_all, annotate_path,
              role_filter, visible_only, pid,
              want_fast, want_deep, want_uia, want_msaa, want_ia2, want_jab,
              want_cdp, want_com, run_ocr, want_ai, cascade, fill_gaps,
              ai_provider, ai_model, ai_api_key) -> None:
    """Highlight UI elements on screen with colored borders and labels.

    By default highlights only actionable elements (Button, Edit, ComboBox,
    etc.) using the UIA element tree from the most recent snapshot. Use --all
    to show every element. Use --filter to show only specific roles.

    Elements at the same tree depth share a color for visual grouping.
    Labels are positioned to avoid overlapping each other.

    Uses the same recognition techniques as 'naturo see' — the composable flags
    --uia/--msaa/--ia2/--jab/--cdp/--com/--ocr/--ai and the --fast/--deep presets
    (default --fast). --visible-only and --filter refine what's drawn.

    Use --annotate to save an annotated screenshot instead of live overlay.

    \b
    Examples:
      naturo highlight --app notepad             # Actionable only
      naturo highlight --app notepad --all       # All elements
      naturo highlight e11 --app notepad         # Specific ref
      naturo highlight --id e11 --app notepad    # --id is an alias for the eN ref
      naturo highlight --app notepad --filter Button
      naturo highlight --app notepad --visible-only
      naturo highlight --app feishu --deep -d 10
      naturo highlight --app notepad -A out.png  # Annotated screenshot
      naturo highlight --hwnd 10697004 -r e69 -r e77
      naturo highlight --app notepad --duration 10
      naturo highlight --app feishu --cdp        # web content only
    """
    # (#752) Auto-detect app ID pattern (a1, a2, ...) in --app flag
    from naturo.cli.options import maybe_promote_app_to_app_id
    app, app_id = maybe_promote_app_to_app_id(app, app_id)

    # (#593) Resolve --app-id to hwnd before any other logic
    if app_id is not None:
        from naturo.app_ids import get_app_id_map
        id_map = get_app_id_map()
        entry = id_map.resolve(app_id)
        if entry is None:
            msg = f'App ID "{app_id}" not found or expired. Run "naturo app list" to refresh.'
            _common._fail(json_output, "APP_ID_NOT_FOUND", msg)
        hwnd = entry.handle

    be = _common._get_backend(json_output)
    try:
        handle = be._resolve_hwnd(app=app, window_title=window_title, hwnd=hwnd, pid=pid)
    except Exception as exc:
        if json_output:
            click.echo(_common._json_error_str("WINDOW_NOT_FOUND", str(exc)))
            raise SystemExit(1)
        raise

    # Merge positional refs, --on ref, and --ref option refs
    all_refs = list(positional_refs) + list(ref_option)
    if on_ref:
        all_refs.append(on_ref)
    refs_list = all_refs if all_refs else None

    # Recognition uses the same technique vocabulary as `see` (shared resolver).
    _tech = _techniques.resolve_techniques(
        fast=want_fast, deep=want_deep, uia=want_uia, msaa=want_msaa,
        ia2=want_ia2, jab=want_jab, cdp=want_cdp, com=want_com,
        ocr=run_ocr, ai=want_ai, cascade=cascade, fill_gaps=fill_gaps,
    )
    try:
        # (#662) Fetch the element tree so highlight has DPI-correct coordinates.
        element_tree = None
        try:
            if backend in ("win32", "win32hybrid"):
                # Legacy Win32/VB6 rendering path — its own tree source.
                element_tree = be.get_element_tree(
                    hwnd=handle, depth=depth, backend=backend,
                )
            else:
                from naturo.cascade import run_cascade
                _shot = None
                if _tech.needs_screenshot:
                    import tempfile as _tf
                    _t = _tf.NamedTemporaryFile(suffix=".png", prefix="naturo_hl_",
                                                delete=False)
                    _t.close()
                    try:
                        _shot = be.capture_window(hwnd=handle, output_path=_t.name).path
                    except Exception:
                        _shot = None
                cascade_result = run_cascade(
                    be, app=app, hwnd=handle, depth=depth, backend_name="auto",
                    fill_gaps_ai=_tech.fill_gaps_ai, ai_provider=ai_provider,
                    ai_model=ai_model, ai_api_key=ai_api_key,
                    screenshot_path=_shot, run_ocr=_tech.run_ocr,
                    enable_uia=_tech.enable_uia, enable_msaa=_tech.enable_msaa,
                    enable_ia2=_tech.enable_ia2, enable_jab=_tech.enable_jab,
                    enable_cdp=_tech.enable_cdp, enable_com=_tech.enable_com,
                )
                element_tree = cascade_result.tree
        except Exception:
            logger.debug("Pre-fetch element tree failed, highlight will fallback", exc_info=True)

        # (#662) Filter out zero-bounds (offscreen) elements when --visible-only
        if visible_only and element_tree is not None:
            _filter_zero_bounds(element_tree)

        if backend in ("win32",):
            from naturo.bridge import highlight_elements
            if not json_output:
                click.echo(f"Highlighting elements (win32) for {duration}s... (switch to the target window)")
            import time
            time.sleep(1.5)
            highlight_elements(hwnd=handle, depth=depth, duration=duration,
                               refs=refs_list, show_all=show_all,
                               element_tree=element_tree)
        else:
            # UIA mode: use snapshot element tree (#364)
            from naturo.bridge import highlight_elements_uia
            if annotate_path:
                if not json_output:
                    click.echo("Generating annotated screenshot...")
                result_path = highlight_elements_uia(
                    backend=be, app=app, hwnd=handle, depth=depth,
                    duration=duration, refs=refs_list, show_all=show_all,
                    annotate_path=annotate_path, role_filter=role_filter,
                )
                if result_path:
                    if json_output:
                        click.echo(json_dumps({
                            "success": True,
                            "backend": backend,
                            "annotate_path": result_path,
                            "refs": refs_list,
                        }))
                    else:
                        click.echo(f"Annotated screenshot saved: {result_path}")
                    return
                else:
                    msg = (
                        "No snapshot with a stored screenshot is available for "
                        "--annotate. Run 'naturo see --path <file>' first: a "
                        "screenshot is only persisted into the snapshot when "
                        "'see' is given --path."
                    )
                    if json_output:
                        click.echo(_common._json_error_str("NO_SNAPSHOT", msg))
                        raise SystemExit(1)
                    click.echo(f"Error: {msg}", err=True)
                    raise SystemExit(1)
            else:
                if not json_output:
                    click.echo(f"Highlighting elements ({backend}) for {duration}s... (switch to the target window)")
                import time
                time.sleep(1.5)
                highlight_elements_uia(
                    backend=be, app=app, hwnd=handle, depth=depth,
                    duration=duration, refs=refs_list, show_all=show_all,
                    role_filter=role_filter,
                    element_tree=element_tree,
                )
    except SystemExit:
        raise
    except Exception as exc:
        if json_output:
            click.echo(_common._json_error_str("HIGHLIGHT_ERROR", str(exc)))
            raise SystemExit(1)
        raise

    if json_output:
        result = {
            "success": True,
            "backend": backend,
            "duration": duration,
            "hwnd": handle,
            "refs": refs_list,
            "show_all": show_all,
        }
        click.echo(json_dumps(result))
    else:
        click.echo("Done.")


def _filter_zero_bounds(el) -> None:
    """Recursively remove zero-bounds children from element tree (in-place)."""
    el.children = [
        c for c in el.children
        if not (c.x == 0 and c.y == 0 and c.width == 0 and c.height == 0)
    ]
    for c in el.children:
        _filter_zero_bounds(c)
