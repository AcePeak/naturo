"""CLI diff command — compare UI element trees."""
from __future__ import annotations

from naturo.cli._jsonio import json_dumps

from naturo.cli.error_helpers import json_error as _json_error_str
from naturo.cli.options import app_id_option, resolve_app_id_to_hwnd
from naturo.models.snapshot import SnapshotNotFoundError as _ModelsSnapshotNotFoundError
import sys
import time
import click


@click.command("diff")
@click.option("--snapshot", "snapshots", multiple=True, help="Snapshot ID (specify twice)")
@click.option("--window", "window_title", help="Window to diff (captures before/after)")
@click.option("--interval", type=float, default=2.0, help="Seconds between captures (with --window)")
@click.option("--app", help="Target application (name or partial match)")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--pid", type=int, default=None, help="Process ID")
@app_id_option
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def diff(ctx: click.Context, snapshots: tuple[str, ...], window_title: str | None, interval: float, app: str | None, hwnd: int | None, pid: int | None, app_id: str | None, json_output: bool) -> None:
    """Compare two UI element trees to detect changes.

    Either provide two --snapshot IDs, or use --window to capture before/after
    with an interval.

    \b
    Examples:

      naturo diff --snapshot snap1 --snapshot snap2

      naturo diff --window "Notepad" --interval 2

      naturo diff --app-id a1 --interval 2
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    # (#752) Auto-detect app ID pattern (a1, a2, ...) in --app flag
    from naturo.cli.options import maybe_promote_app_to_app_id
    app, app_id = maybe_promote_app_to_app_id(app, app_id)

    # Resolve --app-id to hwnd (#595)
    resolved_hwnd = resolve_app_id_to_hwnd(app_id, hwnd, json_output)
    if app_id is not None and resolved_hwnd is None:
        sys.exit(1)
        return
    hwnd = resolved_hwnd

    # (#1121) --app resolves by application/process NAME — the same resolver
    # `see`/`capture`/`list windows` use — NOT by window title. The old code
    # aliased `window_title = app`, so `diff --app Calculator` looked for a
    # window whose *title* contained "Calculator" and failed on any app whose
    # title differs from its name (e.g. the localized "计算器"). We now pass
    # `app` straight through to `backend.get_element_tree(app=...)`, which runs
    # `_resolve_hwnd(app=...)`.

    if interval is not None and interval <= 0:
        msg = f"--interval must be > 0, got {interval}"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    if not snapshots and not window_title and not hwnd and not app:
        msg = "Specify two --snapshot IDs, --window, --app, --hwnd, or --app-id"
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

    from naturo.diff import diff_trees
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError, WindowNotFoundError

    try:
        if window_title or hwnd or app:
            backend = get_backend()
            target_label = window_title or app or f"hwnd={hwnd}"
            if not json_output:
                click.echo(f"Capturing UI tree for '{target_label}'...")

            tree_kwargs: dict = {}
            if app:
                tree_kwargs["app"] = app
            if window_title:
                tree_kwargs["window_title"] = window_title
            if hwnd:
                tree_kwargs["hwnd"] = hwnd

            tree_before = backend.get_element_tree(**tree_kwargs)
            if tree_before is None:
                raise WindowNotFoundError(target_label)

            if not json_output:
                click.echo(f"Waiting {interval}s...")
            time.sleep(interval)

            tree_after = backend.get_element_tree(**tree_kwargs)
            if tree_after is None:
                raise WindowNotFoundError(target_label)

            result = diff_trees(tree_before, tree_after)
        else:
            # (#1121) Snapshot-based diff. `see` stores the full element tree in
            # each snapshot's `ui_map` (a flat dict of UIElement keyed by eN ref,
            # with parent_id/children links), so we can rebuild the two trees and
            # feed them to the SAME `diff_trees` routine the live --window path
            # uses. Previously this branch was a hard-coded "not yet implemented"
            # placeholder even though it was the first documented example.
            from naturo.snapshot import get_snapshot_manager
            mgr = get_snapshot_manager()
            snap_before = mgr.get_snapshot(snapshots[0])
            snap_after = mgr.get_snapshot(snapshots[1])

            tree_before = _tree_from_snapshot(snap_before)
            tree_after = _tree_from_snapshot(snap_after)
            if tree_before is None or tree_after is None:
                missing = snapshots[0] if tree_before is None else snapshots[1]
                msg = (
                    f"Snapshot '{missing}' has no stored element tree "
                    f"(ui_map is empty). Re-capture it with 'naturo see' before "
                    f"diffing."
                )
                if json_output:
                    click.echo(_json_error_str("INVALID_INPUT", msg))
                else:
                    click.echo(f"Error: {msg}", err=True)
                sys.exit(1)
                return

            result = diff_trees(tree_before, tree_after)

        _output_diff(result, json_output)

    except NaturoError as exc:
        if json_output:
            click.echo(json_dumps(exc.to_json_response(), indent=2))
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


def _tree_from_snapshot(snapshot):
    """Rebuild an ``ElementInfo`` tree from a snapshot's ``ui_map`` (#1121).

    ``see`` persists the captured element tree flattened into
    ``snapshot.ui_map`` — a ``dict[str, UIElement]`` keyed by ``eN`` ref, where
    each :class:`~naturo.models.snapshot.UIElement` carries ``parent_id`` and a
    ``children`` list of child refs. This reconstructs the nested
    :class:`~naturo.backends.base.ElementInfo` tree that :func:`diff_trees`
    consumes, so a snapshot-to-snapshot diff runs through the exact same
    comparison path as the live ``--window`` diff.

    Returns the root ``ElementInfo``, or ``None`` when the snapshot stored no
    elements (empty ``ui_map``).
    """
    from naturo.backends.base import ElementInfo

    ui_map = snapshot.ui_map or {}
    if not ui_map:
        return None

    # First pass: a childless ElementInfo per element, keyed by ref.
    nodes: dict[str, ElementInfo] = {}
    for ref, el in ui_map.items():
        frame = el.frame or (0, 0, 0, 0)
        x, y, w, h = (list(frame) + [0, 0, 0, 0])[:4]
        nodes[ref] = ElementInfo(
            id=el.id or ref,
            role=el.role or "",
            name=el.title or el.label or "",
            value=el.value,
            x=int(x), y=int(y), width=int(w), height=int(h),
            children=[],
            properties={},
        )

    # Second pass: wire children by ref and note which refs are children.
    referenced: set[str] = set()
    for ref, el in ui_map.items():
        parent = nodes[ref]
        for child_ref in el.children or []:
            child = nodes.get(child_ref)
            if child is not None:
                parent.children.append(child)
                referenced.add(child_ref)

    # Roots: elements with no parent in the map and never linked as a child.
    roots = [
        nodes[ref]
        for ref, el in ui_map.items()
        if ref not in referenced
        and (el.parent_id is None or el.parent_id not in ui_map)
    ]
    if not roots:
        # Degenerate/cyclic map — fall back to anything not referenced.
        roots = [nodes[ref] for ref in ui_map if ref not in referenced]
    if not roots:
        roots = list(nodes.values())

    if len(roots) == 1:
        return roots[0]

    # Multiple top-level windows: wrap them under a synthetic root so the whole
    # forest is compared (mirrors how `see --app` merges multi-window trees).
    return ElementInfo(
        id="snapshot_root",
        role="Snapshot",
        name=(
            snapshot.application_name
            or snapshot.window_title
            or snapshot.snapshot_id
            or "snapshot"
        ),
        value=None,
        x=0, y=0, width=0, height=0,
        children=roots,
        properties={},
    )


def _output_diff(result, json_output: bool) -> None:
    """Format and output a TreeDiff result."""
    if json_output:
        click.echo(json_dumps({
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
