"""List command group — apps, windows, screens, permissions."""
from __future__ import annotations

from naturo.cli._jsonio import json_dumps
import ntpath
import platform

import click

import naturo.cli.core._common as _common


def _window_state(w) -> str:
    """Reliable OS-level usability label: "min" (minimized), "hidden" (not
    visible), or "live". Kept to hard OS facts on purpose — per-handle content
    probing is unreliable for UWP (the app UI lives in a CoreWindow child and
    which frame handle "sees" it varies run to run), so this does NOT guess
    content; the duplicate-handle collapse below is what removes the noise."""
    if getattr(w, "is_minimized", False):
        return "min"
    if not getattr(w, "is_visible", True):
        return "hidden"
    return "live"


def _dedup_windows(win_list):
    """Collapse duplicate handles of the SAME window to one usable representative.

    A single window often has SEVERAL top-level HWNDs sharing one (pid, title) —
    UWP frames, off-screen helper strips, ghost handles — so a raw list gives the
    caller a pile of interchangeable/unusable handles for one window. Group by
    (pid, title) and keep the most-usable handle in each group (prefer visible,
    non-minimized, largest). Genuinely different windows (different titles, or
    different processes) are never merged.
    """
    def _rank(w):
        return (
            1 if not getattr(w, "is_minimized", False) else 0,
            1 if getattr(w, "is_visible", True) else 0,
            (getattr(w, "width", 0) or 0) * (getattr(w, "height", 0) or 0),
        )
    groups: dict = {}
    order: list = []
    for w in win_list:
        key = (w.pid, w.title)
        if key not in groups:
            groups[key] = w
            order.append(key)
        elif _rank(w) > _rank(groups[key]):
            groups[key] = w
    return [groups[k] for k in order]


@click.group("list", cls=_common.FuzzyGroup)
def list_cmd() -> None:
    """List apps, windows, and screens."""
    pass


@list_cmd.command()
@click.option("--all", "show_all", is_flag=True, help="Show all processes (not just apps with windows)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def apps(ctx, show_all, json_output) -> None:
    """List running applications (delegates to 'app list')."""
    from naturo.cli.app_cmd import app_list
    ctx.invoke(app_list, show_all=show_all, json_output=json_output)


@list_cmd.command()
@click.option("--app", help="Target application: process name or window title (partial match)")
@click.option("--process-name", "app", default=None, hidden=True, help="")
@click.option("--window", "window_title", default=None,
              help="Window title pattern (substring match)")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--app-id", "app_id", default=None,
              help='Stable app/window ID from "naturo app list" output (e.g. a1)')
@click.option("--pid", type=int, help="Process ID")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.option("--all", "-a", "show_all", is_flag=True,
              help="Show every raw HWND. By default, duplicate handles of the "
                   "same window (UWP frames/helper strips sharing one pid+title) "
                   "are collapsed to one usable handle per window.")
def windows(app, window_title, hwnd, app_id, pid, json_output, show_all) -> None:
    """List open windows.

    Shows all visible top-level windows with their handles, titles,
    process names, and dimensions.

    Window-targeting filters (``--window``/``--hwnd``/``--app-id``) mirror the
    flag family used by ``see``/``capture``/``click`` so a window can be
    narrowed the same way everywhere. ``--app`` is broad targeting: it matches
    a window whose process name **or** window title contains the term — the
    same rule ``see``/``capture``/``click`` use, so a window in a multi-window
    process can be picked by title. ``--window`` narrows to the window title
    only. Filters combine with AND.
    """
    if not _common._platform_supports_gui():
        msg = _common._platform_error_msg("Window listing")
        if json_output:
            click.echo(_common._json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    # Resolve --app-id to its window handle up front so an unresolvable ID fails
    # loudly (INVALID_INPUT) instead of silently listing every window. This
    # mirrors the foreground-fallback guard in see/capture (#361/#957).
    app_id_handle: int | None = None
    if app_id is not None:
        from naturo.app_ids import get_app_id_map
        entry = get_app_id_map().resolve(app_id)
        if entry is None:
            msg = (
                f'App ID "{app_id}" not found or expired. '
                'Run "naturo list windows" or "naturo app list" to refresh.'
            )
            if json_output:
                click.echo(_common._json_error_str("INVALID_INPUT", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)
        app_id_handle = entry.handle

    try:
        backend = _common._get_backend(json_output)
        win_list = backend.list_windows()
        # Raw enumeration count, captured before any filtering — this, not the
        # post-filter list, is what tells us whether a desktop session exists.
        raw_window_count = len(win_list)

        # Exclude own process and parent (terminal) to avoid matching
        # the terminal running the command (#358)
        import os
        _own_pid = os.getpid()
        _parent_pid = os.getppid()
        win_list = [w for w in win_list if w.pid not in (_own_pid, _parent_pid)]

        # Apply filters (all combine with AND).
        if app:
            app_lower = app.lower()
            # An agent may feed the full-path `process_name` this command emits
            # (e.g. "C:\\...\\WindowsTerminal.exe") straight back into --app, so
            # basename the query before the process-name comparison to keep the
            # discover→act round-trip working (#1084). This mirrors the
            # gold-standard `_resolve_hwnd`, which compares against
            # basename(process_name) and deliberately avoids full-path matching
            # to prevent over-matching shared directories (#789). A non-path
            # query basenames to itself, so name/substring matching is unchanged.
            app_query = ntpath.basename(app_lower) or app_lower
            win_list = [w for w in win_list
                        if app_lower in w.title.lower()
                        or app_query in ntpath.basename(w.process_name).lower()]
        if window_title:
            title_lower = window_title.lower()
            win_list = [w for w in win_list if title_lower in w.title.lower()]
        if hwnd:
            win_list = [w for w in win_list if w.handle == hwnd]
        if app_id_handle is not None:
            win_list = [w for w in win_list if w.handle == app_id_handle]
        if pid:
            win_list = [w for w in win_list if w.pid == pid]

        # Collapse duplicate handles of the same window (see _dedup_windows) so
        # the list shows one usable handle per real window instead of a pile of
        # UWP frame/helper dupes. --all keeps every handle. An explicit --hwnd/
        # --app-id filter is never collapsed: return exactly the handle asked for.
        if not show_all and hwnd is None and app_id_handle is None:
            win_list = _dedup_windows(win_list)
        _states = {w.handle: _window_state(w) for w in win_list}

        # Warn only when an empty result genuinely indicates no interactive
        # desktop session — i.e. the *raw* enumeration found nothing and the
        # canonical WTS check confirms this process has no desktop (#1010).
        # An empty result produced by a --app/--pid filter on a desktop that
        # did enumerate windows is normal and must not raise this warning.
        if not win_list and raw_window_count == 0 and platform.system() == "Windows":
            from naturo.cli.interaction._common import _is_current_session_interactive
            if not _is_current_session_interactive():
                click.echo(
                    "Warning: no windows found "
                    "(no interactive desktop session detected — running via SSH or service?)",
                    err=True,
                )

        if json_output:
            # Assign stable session-scoped IDs (a1, a2, ...) on the listed
            # windows so each entry is directly targetable with --app-id, matching
            # `list apps` / `app list` (#952). Without this the emitted `id` would
            # be cosmetic and would not resolve.
            from naturo.app_ids import get_app_id_map
            get_app_id_map().assign_ids(win_list)

            data = [
                {
                    # `id` + `handle` mirror the `list apps` schema; `hwnd` is kept
                    # as a back-compatible alias so both names resolve (#952).
                    "id": f"a{i}",
                    "handle": w.handle,
                    "hwnd": w.handle,
                    "title": w.title,
                    "process_name": w.process_name,
                    "pid": w.pid,
                    "x": w.x,
                    "y": w.y,
                    "width": w.width,
                    "height": w.height,
                    "is_visible": w.is_visible,
                    "is_minimized": w.is_minimized,
                }
                for i, w in enumerate(win_list, start=1)
            ]
            click.echo(json_dumps({"success": True, "windows": data, "count": len(data)}, indent=2))
        else:
            if not win_list:
                click.echo("No windows found.")
                return
            # Table-like output
            click.echo(f"{'HWND':<16} {'PID':<8} {'SIZE':<14} {'STATE':<8} {'TITLE'}")
            click.echo("-" * 78)
            for w in win_list:
                size = f"{w.width}x{w.height}"
                state = _states.get(w.handle, "") or "live"
                title = w.title[:40] if len(w.title) > 40 else w.title
                click.echo(f"{w.handle:<16} {w.pid:<8} {size:<14} {state:<8} {title}")
            _hidden = "" if show_all else "  (duplicate handles collapsed; --all to show every handle)"
            click.echo(f"\n{len(win_list)} windows found.{_hidden}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@list_cmd.command()
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def screens(json_output) -> None:
    """List connected screens/monitors.

    Shows monitor index, resolution, position, DPI scale factor, and
    whether the monitor is the primary display.  On Windows, shows the
    human-readable monitor model name when available (#359).
    """
    try:
        backend = _common._get_backend(json_output)
        monitors = backend.list_monitors()

        if json_output:
            items = []
            for m in monitors:
                # (#359) Use model_name as 'name', keep device path separate
                display_name = getattr(m, "model_name", None) or m.name
                item = {
                    "index": m.index,
                    "name": display_name,
                    "device_path": getattr(m, "device_path", None) or m.name,
                    "x": m.x,
                    "y": m.y,
                    "width": m.width,
                    "height": m.height,
                    "is_primary": m.is_primary,
                    "scale_factor": m.scale_factor,
                    "dpi": m.dpi,
                }
                if m.work_area:
                    item["work_area"] = m.work_area
                items.append(item)
            click.echo(json_dumps({"success": True, "monitors": items, "count": len(items)}, indent=2))
        else:
            from naturo.cli.table import print_table

            if not monitors:
                click.echo("No monitors detected.")
                return

            headers = ["Index", "Name", "Resolution", "Position", "Scale", "DPI", "Primary"]
            rows = []
            for m in monitors:
                display_name = getattr(m, "model_name", None) or m.name
                res = f"{m.width}x{m.height}"
                pos = f"({m.x}, {m.y})"
                primary = "\u2713" if m.is_primary else ""
                scale = f"{m.scale_factor}x"
                rows.append([str(m.index), display_name, res, pos, scale, str(m.dpi), primary])

            print_table(
                headers, rows,
                count_label=f"{len(monitors)} monitor(s) found.",
            )
    except NotImplementedError:
        msg = f"Monitor listing is not supported on {platform.system()} yet."
        if json_output:
            click.echo(_common._json_error_str("NOT_IMPLEMENTED", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)
    except Exception as e:
        if json_output:
            click.echo(_common._json_error_str("UNKNOWN_ERROR", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@list_cmd.command(hidden=True)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def permissions(json_output) -> None:
    """List automation permissions status (UIAccess, admin, etc.)."""
    msg = "Permission listing is not implemented yet — coming in a future release."
    if json_output:
        click.echo(_common._json_error_str("NOT_IMPLEMENTED", msg))
    else:
        click.echo(f"Error: {msg}", err=True)
    raise SystemExit(1)
