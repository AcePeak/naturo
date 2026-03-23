"""CLI commands for snapshot management.

Commands
--------
``naturo snapshot list``
    List all stored snapshots with creation time, size, and app name.

``naturo snapshot clean``
    Remove snapshots by age or remove all.
"""

from __future__ import annotations

import json as json_module

import click

from naturo.snapshot import SnapshotManager
from naturo.cli.fuzzy_group import FuzzyGroup


def _get_manager() -> SnapshotManager:
    return SnapshotManager()


@click.group(cls=FuzzyGroup)
def snapshot() -> None:
    """Manage UI automation snapshots."""
    pass


@snapshot.command("list")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def snapshot_list(json_output: bool) -> None:
    """List all stored snapshots.

    Shows snapshot ID, creation time, last update, size, screenshot count,
    and the captured application name.
    """
    mgr = _get_manager()
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
        click.echo(json_module.dumps({"success": True, "snapshots": data}, indent=2))
    else:
        if not infos:
            click.echo("No snapshots found.")
            click.echo(f"Storage: {mgr.storage_path}")
            return

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


@snapshot.command("clean")
@click.option("--days", "-d", type=int, default=None, help="Delete snapshots older than N days")
@click.option("--all", "clean_all", is_flag=True, help="Delete all snapshots")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def snapshot_clean(days: int | None, clean_all: bool, yes: bool, json_output: bool) -> None:
    """Clean up stored snapshots.

    Use ``--days N`` to remove snapshots older than N days, or ``--all``
    to wipe everything.  Without either flag the command shows a help message.
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

    mgr = _get_manager()

    if not yes and not json_output:
        if clean_all:
            msg = "Delete ALL snapshots? [y/N] "
        else:
            msg = f"Delete snapshots older than {days} day(s)? [y/N] "
        confirmed = click.prompt(msg, default="n")
        if confirmed.lower() not in ("y", "yes"):
            click.echo("Aborted.")
            raise SystemExit(0)

    if clean_all:
        count = mgr.clean_all()
    else:
        count = mgr.clean_older_than(days)  # type: ignore[arg-type]

    if json_output:
        click.echo(json_module.dumps({"success": True, "deleted": count}))
    else:
        click.echo(f"Deleted {count} snapshot(s).")


# ── helpers ──────────────────────────────────────────────────────────────────


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n //= 1024
    return f"{n:.0f} TB"
