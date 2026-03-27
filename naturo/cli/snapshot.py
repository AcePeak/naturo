"""CLI commands for snapshot management.

Commands
--------
``naturo snapshot list``
    List all stored snapshots with creation time, size, and app name.

``naturo snapshot clean``
    Remove snapshots by age or remove all.

``naturo snapshot sessions``
    List all active snapshot sessions.
"""

from __future__ import annotations

import json as json_module

import click

from naturo.snapshot import SnapshotManager, get_snapshot_manager, DEFAULT_STORAGE_ROOT
from naturo.cli.fuzzy_group import FuzzyGroup


def _get_manager(session: str | None = None) -> SnapshotManager:
    return get_snapshot_manager(session=session)


@click.group(cls=FuzzyGroup, hidden=True)
def snapshot() -> None:
    """Manage UI automation snapshots (internal/debug command)."""
    pass


@snapshot.command("list")
@click.option("--session", "-s", default=None, envvar="NATURO_SESSION",
              help="Session name (default: NATURO_SESSION env var or 'default')")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def snapshot_list(session: str | None, json_output: bool) -> None:
    """List all stored snapshots in the active session.

    Shows snapshot ID, creation time, last update, size, screenshot count,
    and the captured application name.

    \b
    Examples:
        naturo snapshot list
        naturo snapshot list --session workflow-a
        NATURO_SESSION=workflow-a naturo snapshot list
    """
    mgr = _get_manager(session=session)
    infos = mgr.list_snapshots()

    if json_output:
        data = [
            {
                "id": s.id,
                "created_at": s.created_at.isoformat(),
                "last_accessed_at": s.last_accessed_at.isoformat(),
                "size_bytes": s.size_in_bytes,
                "screenshot_count": s.screenshot_count,
                "application_name": s.application_name,
            }
            for s in infos
        ]
        click.echo(json_module.dumps({
            "success": True,
            "session": mgr.session,
            "snapshots": data,
        }, indent=2))
    else:
        if not infos:
            click.echo(f"No snapshots found in session '{mgr.session}'.")
            click.echo(f"Storage: {mgr.storage_path}")
            return

        click.echo(f"Session: {mgr.session}")
        click.echo(f"{'ID':<28} {'CREATED':<24} {'APP':<24} {'SIZE':>10}  {'IMGS':>4}")
        click.echo("-" * 94)
        for s in infos:
            app = (s.application_name or "-")[:24]
            size = _human_size(s.size_in_bytes)
            click.echo(
                f"{s.id:<28} {s.created_at.strftime('%Y-%m-%d %H:%M:%S'):<24} "
                f"{app:<24} {size:>10}  {s.screenshot_count:>4}"
            )
        click.echo(f"\n{len(infos)} snapshot(s) found.  Storage: {mgr.storage_path}")


@snapshot.command("sessions")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def snapshot_sessions(json_output: bool) -> None:
    """List all snapshot sessions.

    Shows each session name and snapshot count.

    \b
    Example:
        naturo snapshot sessions
    """
    base = DEFAULT_STORAGE_ROOT
    sessions = []
    if base.exists():
        for entry in sorted(base.iterdir()):
            if entry.is_dir():
                count = sum(1 for d in entry.iterdir() if d.is_dir() and (d / "snapshot.json").exists())
                sessions.append({"name": entry.name, "snapshot_count": count})

    if json_output:
        click.echo(json_module.dumps({"success": True, "sessions": sessions}, indent=2))
    else:
        if not sessions:
            click.echo("No sessions found.")
            click.echo(f"Storage: {base}")
            return
        click.echo(f"{'SESSION':<32}  {'SNAPSHOTS':>9}")
        click.echo("-" * 44)
        for s in sessions:
            click.echo(f"{s['name']:<32}  {s['snapshot_count']:>9}")
        click.echo(f"\n{len(sessions)} session(s).  Storage: {base}")


@snapshot.command("clean")
@click.option("--session", "-s", default=None, envvar="NATURO_SESSION",
              help="Session to clean (default: NATURO_SESSION or 'default'). Use 'all' to clean all sessions.")
@click.option("--days", "-d", type=int, default=None, help="Delete snapshots older than N days")
@click.option("--all", "clean_all", is_flag=True, help="Delete all snapshots in the session")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def snapshot_clean(session: str | None, days: int | None, clean_all: bool, yes: bool, json_output: bool) -> None:
    """Clean up stored snapshots.

    Use ``--days N`` to remove snapshots older than N days, or ``--all``
    to wipe everything.  Without either flag the command shows a help message.

    Pass ``--session all`` to clean every session.
    """
    if not clean_all and days is None:
        msg = "Specify --days N or --all.  Run with --help for usage."
        if json_output:
            click.echo(json_module.dumps({"success": False, "error": {"code": "INVALID_INPUT", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    if days is not None and days < 0:
        msg = f"--days must be >= 0, got {days}"
        if json_output:
            click.echo(json_module.dumps({"success": False, "error": {"code": "INVALID_INPUT", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    # Determine which sessions to clean
    if session == "all":
        # Clean every session
        base = DEFAULT_STORAGE_ROOT
        if not base.exists():
            if json_output:
                click.echo(json_module.dumps({"success": True, "deleted": 0}))
            else:
                click.echo("No snapshots found.")
            return

        if not yes and not json_output:
            confirmed = click.prompt("Delete ALL snapshots in ALL sessions? [y/N] ", default="n")
            if confirmed.lower() not in ("y", "yes"):
                click.echo("Aborted.")
                raise SystemExit(0)

        total = 0
        for sess_dir in base.iterdir():
            if not sess_dir.is_dir():
                continue
            mgr = SnapshotManager(storage_root=base, session=sess_dir.name)
            if clean_all:
                total += mgr.clean_all()
            else:
                total += mgr.clean_older_than(days)  # type: ignore[arg-type]

        if json_output:
            click.echo(json_module.dumps({"success": True, "deleted": total, "sessions": "all"}))
        else:
            click.echo(f"Deleted {total} snapshot(s) across all sessions.")
        return

    mgr = _get_manager(session=session)

    if not yes and not json_output:
        scope = f"session '{mgr.session}'"
        if clean_all:
            msg = f"Delete ALL snapshots in {scope}? [y/N] "
        else:
            msg = f"Delete snapshots older than {days} day(s) in {scope}? [y/N] "
        confirmed = click.prompt(msg, default="n")
        if confirmed.lower() not in ("y", "yes"):
            click.echo("Aborted.")
            raise SystemExit(0)

    if clean_all:
        count = mgr.clean_all()
    else:
        count = mgr.clean_older_than(days)  # type: ignore[arg-type]

    if json_output:
        click.echo(json_module.dumps({"success": True, "deleted": count, "session": mgr.session}))
    else:
        click.echo(f"Deleted {count} snapshot(s) from session '{mgr.session}'.")


# ── helpers ──────────────────────────────────────────────────────────────────


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n //= 1024
    return f"{n:.0f} TB"
