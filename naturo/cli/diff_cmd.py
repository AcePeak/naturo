"""CLI diff command — compare UI element trees."""
import json

from naturo.cli.error_helpers import json_error as _json_error_str
from naturo.models.snapshot import SnapshotNotFoundError as _ModelsSnapshotNotFoundError
import sys
import time
import click


@click.command("diff")
@click.option("--snapshot", "snapshots", multiple=True, help="Snapshot ID (specify twice)")
@click.option("--window", "window_title", help="Window to diff (captures before/after)")
@click.option("--interval", type=float, default=2.0, help="Seconds between captures (with --window)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def diff(ctx, snapshots, window_title, interval, json_output):
    """Compare two UI element trees to detect changes.

    Either provide two --snapshot IDs, or use --window to capture before/after
    with an interval.

    \b
    Examples:

      naturo diff --snapshot snap1 --snapshot snap2

      naturo diff --window "Notepad" --interval 2
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    if interval is not None and interval <= 0:
        msg = f"--interval must be > 0, got {interval}"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    if not snapshots and not window_title:
        msg = "Specify two --snapshot IDs or --window"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    if snapshots and len(snapshots) != 2:
        msg = "Provide exactly two --snapshot IDs"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    from naturo.diff import diff_trees, TreeDiff
    from naturo.backends.base import get_backend, ElementInfo
    from naturo.errors import NaturoError, WindowNotFoundError

    try:
        if window_title:
            backend = get_backend()
            if not json_output:
                click.echo(f"Capturing UI tree for '{window_title}'...")

            tree_before = backend.get_element_tree(window_title=window_title)
            if tree_before is None:
                raise WindowNotFoundError(window_title)

            if not json_output:
                click.echo(f"Waiting {interval}s...")
            time.sleep(interval)

            tree_after = backend.get_element_tree(window_title=window_title)
            if tree_after is None:
                raise WindowNotFoundError(window_title)

            result = diff_trees(tree_before, tree_after)
        else:
            # Snapshot-based diff
            from naturo.snapshot import SnapshotManager
            mgr = SnapshotManager()
            snap1 = mgr.get_snapshot(snapshots[0])
            snap2 = mgr.get_snapshot(snapshots[1])

            # For snapshot diff, we'd need the element trees stored in snapshots
            # This is a placeholder — real impl would extract trees from snapshot data
            msg = "Snapshot-based diff requires element trees stored in snapshots (not yet implemented)"
            if json_output:
                click.echo(_json_error_str("INVALID_INPUT", msg))
            else:
                click.echo(f"Note: {msg}", err=True)
            sys.exit(1)
            return

        _output_diff(result, json_output)

    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response(), indent=2))
        else:
            click.echo(f"Error: {exc.message}", err=True)
        sys.exit(1)
    except _ModelsSnapshotNotFoundError as exc:
        # models.snapshot.SnapshotNotFoundError doesn't inherit NaturoError,
        # so translate it to the proper SNAPSHOT_NOT_FOUND error code.
        if json_output:
            click.echo(_json_error_str("SNAPSHOT_NOT_FOUND", str(exc)))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        if json_output:
            click.echo(_json_error_str("UNKNOWN_ERROR", str(exc)))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


def _output_diff(result, json_output: bool) -> None:
    """Format and output a TreeDiff result."""
    if json_output:
        click.echo(json.dumps({
            "success": True,
            "diff": result.to_dict(),
        }, indent=2))
    else:
        if not result.has_changes:
            click.echo("No changes detected")
            return

        click.echo(f"Changes: {result.summary}\n")

        if result.added:
            click.echo("Added:")
            for c in result.added:
                click.echo(f"  + [{c.element_role}] {c.element_name or '(unnamed)'}")
                if c.path:
                    click.echo(f"    Path: {c.path}")

        if result.removed:
            click.echo("Removed:")
            for c in result.removed:
                click.echo(f"  - [{c.element_role}] {c.element_name or '(unnamed)'}")
                if c.path:
                    click.echo(f"    Path: {c.path}")

        if result.modified:
            click.echo("Modified:")
            for c in result.modified:
                click.echo(f"  ~ [{c.element_role}] {c.element_name or '(unnamed)'}")
                click.echo(f"    {c.old_value!r} → {c.new_value!r}")
                if c.path:
                    click.echo(f"    Path: {c.path}")
