"""CLI app command extensions — launch, quit, relaunch, list, find.

Replaces the stub implementations in system.py with working process management.
These are registered as subcommands of the existing ``app`` group.
"""
import json
import sys
import click


def _safe_echo(text: str, **kwargs) -> None:
    """Echo text safely, replacing unencodable characters on Windows GBK terminals."""
    try:
        click.echo(text, **kwargs)
    except UnicodeEncodeError:
        # Fallback: encode with replace for terminals that can't handle the chars
        encoded = text.encode(sys.stdout.encoding or "utf-8", errors="replace")
        click.echo(encoded.decode(sys.stdout.encoding or "utf-8", errors="replace"), **kwargs)


@click.command("launch")
@click.argument("name")
@click.option("--path", help="Explicit executable path")
@click.option("--wait-until-ready", is_flag=True, help="Wait for app to create a window")
@click.option("--timeout", type=float, default=30.0, help="Timeout for wait-until-ready")
@click.option("--no-focus", is_flag=True, help="Launch without focusing")
@click.option("--args", multiple=True, help="Arguments to pass to the application")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_launch(ctx, name, path, wait_until_ready, timeout, no_focus, args, json_output):
    """Launch an application by name or path."""
    json_output = json_output or (ctx.obj or {}).get("json", False)

    from naturo.process import launch_app
    from naturo.errors import NaturoError

    try:
        info = launch_app(
            name=name,
            path=path,
            wait_until_ready=wait_until_ready,
            timeout=timeout,
            args=list(args) if args else None,
            no_focus=no_focus,
        )
        if json_output:
            click.echo(json.dumps({
                "success": True,
                "process": {
                    "pid": info.pid,
                    "name": info.name,
                    "path": info.path,
                    "is_running": info.is_running,
                    "window_count": info.window_count,
                },
            }, indent=2))
        else:
            _safe_echo(f"Launched {info.name} (PID: {info.pid})")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response(), indent=2))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        ctx.exit(1)


@click.command("quit")
@click.option("--name", help="Application name")
@click.option("--pid", type=int, help="Process ID")
@click.option("--force", is_flag=True, help="Force kill immediately")
@click.option("--timeout", type=float, default=10.0, help="Graceful shutdown timeout")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_quit(ctx, name, pid, force, timeout, json_output):
    """Quit an application gracefully (or force kill)."""
    json_output = json_output or (ctx.obj or {}).get("json", False)

    if not name and pid is None:
        msg = "Specify --name or --pid"
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "INVALID_INPUT", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        ctx.exit(1)
        return

    from naturo.process import quit_app
    from naturo.errors import NaturoError

    try:
        quit_app(name=name, pid=pid, force=force, timeout=timeout)
        if json_output:
            click.echo(json.dumps({"success": True, "message": f"Quit {name or pid}"}))
        else:
            _safe_echo(f"Quit {name or pid}")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response(), indent=2))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        ctx.exit(1)


@click.command("relaunch")
@click.argument("name")
@click.option("--wait-until-ready", is_flag=True, default=True, help="Wait for app (default: on)")
@click.option("--timeout", type=float, default=30.0, help="Timeout in seconds")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_relaunch(ctx, name, wait_until_ready, timeout, json_output):
    """Quit and relaunch an application."""
    json_output = json_output or (ctx.obj or {}).get("json", False)

    from naturo.process import relaunch_app
    from naturo.errors import NaturoError

    try:
        info = relaunch_app(name=name, wait_until_ready=wait_until_ready, timeout=timeout)
        if json_output:
            click.echo(json.dumps({
                "success": True,
                "process": {
                    "pid": info.pid,
                    "name": info.name,
                    "path": info.path,
                    "is_running": info.is_running,
                    "window_count": info.window_count,
                },
            }, indent=2))
        else:
            _safe_echo(f"Relaunched {info.name} (PID: {info.pid})")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response(), indent=2))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        ctx.exit(1)


@click.command("list")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_list(ctx, json_output):
    """List running applications."""
    json_output = json_output or (ctx.obj or {}).get("json", False)

    from naturo.process import list_apps

    apps = list_apps()
    if json_output:
        click.echo(json.dumps({
            "success": True,
            "apps": [
                {"pid": a.pid, "name": a.name, "path": a.path, "is_running": a.is_running}
                for a in apps
            ],
            "count": len(apps),
        }, indent=2))
    else:
        if not apps:
            click.echo("No running applications found")
        else:
            for a in apps:
                _safe_echo(f"  {a.pid:>8}  {a.name}")
            click.echo(f"\n{len(apps)} applications")


@click.command("find")
@click.argument("name")
@click.option("--pid", type=int, help="Search by PID instead of name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_find(ctx, name, pid, json_output):
    """Find a running application by name or PID."""
    json_output = json_output or (ctx.obj or {}).get("json", False)

    # Validate empty name
    if not name or not name.strip():
        msg = "Name cannot be empty"
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "INVALID_INPUT", "message": msg}}))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        ctx.exit(1)
        return

    from naturo.process import find_process

    proc = find_process(name=name, pid=pid)
    if proc:
        if json_output:
            click.echo(json.dumps({
                "success": True,
                "process": {
                    "pid": proc.pid,
                    "name": proc.name,
                    "path": proc.path,
                    "is_running": proc.is_running,
                    "window_count": proc.window_count,
                },
            }, indent=2))
        else:
            _safe_echo(f"Found: {proc.name} (PID: {proc.pid})")
    else:
        if json_output:
            click.echo(json.dumps({
                "success": False,
                "process": None,
                "error": {
                    "code": "PROCESS_NOT_FOUND",
                    "message": f"No process found matching '{name}'",
                },
            }, indent=2))
        else:
            _safe_echo(f"Not found: {name}")
        ctx.exit(1)
