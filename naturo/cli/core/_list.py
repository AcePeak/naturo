"""List command group — apps, windows, screens, permissions."""
from __future__ import annotations

import json as json_module
import platform

import click

import naturo.cli.core._common as _common


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
@click.option("--app", help="Target application (name or partial match)")
@click.option("--process-name", "app", default=None, hidden=True, help="")
@click.option("--pid", type=int, help="Process ID")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def windows(app, pid, json_output) -> None:
    """List open windows.

    Shows all visible top-level windows with their handles, titles,
    process names, and dimensions.
    """
    if not _common._platform_supports_gui():
        msg = _common._platform_error_msg("Window listing")
        if json_output:
            click.echo(_common._json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    try:
        backend = _common._get_backend(json_output)
        win_list = backend.list_windows()

        # Exclude own process and parent (terminal) to avoid matching
        # the terminal running the command (#358)
        import os
        _own_pid = os.getpid()
        _parent_pid = os.getppid()
        win_list = [w for w in win_list if w.pid not in (_own_pid, _parent_pid)]

        # Apply filters
        if app:
            app_lower = app.lower()
            win_list = [w for w in win_list
                        if app_lower in w.title.lower()
                        or app_lower in w.process_name.lower()]
        if pid:
            win_list = [w for w in win_list if w.pid == pid]

        # Warn if empty result on Windows (may indicate no desktop session)
        if not win_list and platform.system() == "Windows":
            session_warning = ""
            session_id = os.environ.get("SESSIONNAME", "")
            if not session_id or session_id.lower() == "services":
                session_warning = " (Warning: no interactive desktop session detected — running via SSH or service?)"
            click.echo(
                f"Warning: no windows found{session_warning}",
                err=True,
            )

        if json_output:
            data = [
                {
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
                for w in win_list
            ]
            click.echo(json_module.dumps({"success": True, "windows": data}, indent=2))
        else:
            if not win_list:
                click.echo("No windows found.")
                return
            # Table-like output
            click.echo(f"{'HWND':<16} {'PID':<8} {'SIZE':<14} {'TITLE'}")
            click.echo("-" * 70)
            for w in win_list:
                size = f"{w.width}x{w.height}"
                title = w.title[:40] if len(w.title) > 40 else w.title
                click.echo(f"{w.handle:<16} {w.pid:<8} {size:<14} {title}")
            click.echo(f"\n{len(win_list)} windows found.")
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
            click.echo(json_module.dumps({"success": True, "monitors": items}, indent=2))
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
