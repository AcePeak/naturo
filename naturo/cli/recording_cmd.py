"""Recording CLI commands — record, replay, and manage automation recordings.

Provides `naturo record start/stop/play/list/show/delete/export` commands
that wrap the recording engine in naturo/recording.py.
"""
from __future__ import annotations

from naturo.cli._jsonio import json_dumps
import shlex
import sys
from datetime import datetime

import click

from naturo.cli.error_helpers import collection_read, json_error, success_envelope
from naturo.cli.fuzzy_group import FuzzyGroup
from naturo.errors import ErrorCode
from naturo.recording import (
    Recording,
    generate_recording_id,
    get_active_recording,
    set_active_recording,
    save_recording,
    load_recording,
    list_recordings,
    delete_recording,
    replay_recording,
)


@click.group("record", cls=FuzzyGroup)
def record():
    """Record and replay automation actions.

    \b
    Examples:
        naturo record start "Login flow"      # Start recording
        naturo record stop                     # Stop and save
        naturo record list                     # List recordings
        naturo record play rec_20260401_120000 # Replay a recording
        naturo record show rec_20260401_120000 # Show recording details
        naturo record delete rec_20260401_120000
        naturo record export rec_20260401_120000 --format python
    """


@click.command("start")
@click.argument("name", default="")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def record_start(name: str, json_output: bool):
    """Start recording user actions.

    All subsequent naturo commands (click, type, press, etc.) will be
    captured until `naturo record stop` is called.

    \b
    Examples:
        naturo record start                    # Auto-named recording
        naturo record start "Login automation"  # Named recording
    """
    active = get_active_recording()
    if active is not None:
        msg = f"Recording already in progress: {active.recording_id} ({active.name})"
        if json_output:
            click.echo(json_error(
                ErrorCode.INVALID_INPUT, msg,
                suggested_action="Run 'naturo record stop' to finish the current recording first.",
                recoverable=True,
            ))
        else:
            click.echo(f"Error: {msg}", err=True)
            click.echo("Run 'naturo record stop' to finish the current recording first.")
        sys.exit(1)

    rec_id = generate_recording_id()
    rec_name = name or f"Recording {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    rec = Recording(
        name=rec_name,
        recording_id=rec_id,
        created_at=datetime.now().isoformat(),
    )
    set_active_recording(rec)

    if json_output:
        click.echo(json_dumps({
            "success": True,
            "recording_id": rec_id,
            "name": rec_name,
            "message": "Recording started",
        }))
    else:
        click.echo(f"Recording started: {rec_id}")
        click.echo(f"Name: {rec_name}")
        click.echo("All naturo actions will be recorded. Run 'naturo record stop' to finish.")


@click.command("stop")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def record_stop(json_output: bool):
    """Stop recording and save.

    Saves the recorded actions to ~/.naturo/recordings/ as a JSON file.

    \b
    Examples:
        naturo record stop
    """
    active = get_active_recording()
    if active is None:
        msg = "No active recording to stop."
        if json_output:
            click.echo(json_error(
                ErrorCode.INVALID_INPUT, msg,
                suggested_action="Start a recording first with 'naturo record start'.",
            ))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    path = save_recording(active)
    set_active_recording(None)

    if json_output:
        click.echo(json_dumps({
            "success": True,
            "recording_id": active.recording_id,
            "name": active.name,
            "step_count": len(active.steps),
            "path": str(path),
        }))
    else:
        click.echo(f"Recording stopped: {active.recording_id}")
        click.echo(f"Name: {active.name}")
        click.echo(f"Steps: {len(active.steps)}")
        click.echo(f"Saved: {path}")


@click.command("play")
@click.argument("recording_id")
@click.option("--speed", type=float, default=1.0,
              help="Playback speed multiplier (2.0 = twice as fast).")
@click.option("--dry-run", is_flag=True, help="Print actions without executing.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def record_play(recording_id: str, speed: float, dry_run: bool, json_output: bool):
    """Replay a saved recording.

    \b
    Examples:
        naturo record play rec_20260401_120000
        naturo record play rec_20260401_120000 --speed 2.0
        naturo record play rec_20260401_120000 --dry-run
    """
    try:
        rec = load_recording(recording_id)
    except FileNotFoundError:
        msg = f"Recording not found: {recording_id}"
        if json_output:
            click.echo(json_error(ErrorCode.RECORDING_NOT_FOUND, msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    if not json_output and not dry_run:
        click.echo(f"Replaying: {rec.name} ({len(rec.steps)} steps, speed={speed}x)")

    def _on_step(idx, step, result):
        if not json_output:
            status = result.get("status", "unknown")
            symbol = "+" if status == "success" else ("~" if status == "skipped" else "!")
            click.echo(f"  [{symbol}] Step {idx + 1}: {step.command} {step.args}")

    results = replay_recording(rec, speed=speed, dry_run=dry_run, step_callback=_on_step)

    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")
    skipped_count = sum(1 for r in results if r["status"] == "skipped")

    if json_output:
        click.echo(json_dumps({
            "success": error_count == 0,
            "recording_id": recording_id,
            "total_steps": len(results),
            "succeeded": success_count,
            "failed": error_count,
            "skipped": skipped_count,
            "results": results,
        }))
    else:
        click.echo(f"Replay complete: {success_count} succeeded, "
                    f"{error_count} failed, {skipped_count} skipped")


@collection_read("recordings")
@click.command("list")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def record_list(json_output: bool):
    """List all saved recordings.

    \b
    Examples:
        naturo record list
        naturo record list --json
    """
    recordings = list_recordings()

    # Check for active recording
    active = get_active_recording()

    if json_output:
        output: dict = success_envelope("recordings", recordings)
        if active:
            output["active"] = {
                "recording_id": active.recording_id,
                "name": active.name,
                "step_count": len(active.steps),
            }
        click.echo(json_dumps(output))
    else:
        if active:
            click.echo(f"[RECORDING] {active.recording_id} — {active.name} "
                        f"({len(active.steps)} steps so far)")
            click.echo()

        if not recordings:
            click.echo("No saved recordings.")
            return

        click.echo(f"{'ID':<25} {'Name':<30} {'Steps':>6}  {'Created'}")
        click.echo("-" * 80)
        for r in recordings:
            click.echo(
                f"{r['recording_id']:<25} {r['name']:<30} "
                f"{r['step_count']:>6}  {r['created_at'][:19]}"
            )


@click.command("show")
@click.argument("recording_id")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def record_show(recording_id: str, json_output: bool):
    """Show details of a recording including all steps.

    \b
    Examples:
        naturo record show rec_20260401_120000
    """
    try:
        rec = load_recording(recording_id)
    except FileNotFoundError:
        msg = f"Recording not found: {recording_id}"
        if json_output:
            click.echo(json_error(ErrorCode.RECORDING_NOT_FOUND, msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    if json_output:
        click.echo(json_dumps(rec.to_dict()))
    else:
        click.echo(f"Recording: {rec.recording_id}")
        click.echo(f"Name:      {rec.name}")
        click.echo(f"Created:   {rec.created_at[:19]}")
        click.echo(f"Steps:     {len(rec.steps)}")
        duration = rec.total_duration_ms()
        if duration > 0:
            click.echo(f"Duration:  {duration / 1000:.1f}s")
        click.echo()
        if rec.steps:
            click.echo("Steps:")
            for i, step in enumerate(rec.steps, 1):
                args_str = " ".join(f"{k}={v}" for k, v in step.args.items())
                click.echo(f"  {i:3d}. {step.command} {args_str}")


@click.command("delete")
@click.argument("recording_id")
@click.option("--force", is_flag=True, help="Skip confirmation.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def record_delete(recording_id: str, force: bool, json_output: bool):
    """Delete a saved recording.

    \b
    Examples:
        naturo record delete rec_20260401_120000
        naturo record delete rec_20260401_120000 --force
    """
    try:
        rec = load_recording(recording_id)
    except FileNotFoundError:
        msg = f"Recording not found: {recording_id}"
        if json_output:
            click.echo(json_error(ErrorCode.RECORDING_NOT_FOUND, msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    if not force and not json_output:
        click.confirm(
            f"Delete recording '{rec.name}' ({len(rec.steps)} steps)?",
            abort=True,
        )

    deleted = delete_recording(recording_id)
    if json_output:
        click.echo(json_dumps({"success": deleted, "recording_id": recording_id}))
    else:
        click.echo(f"Deleted: {recording_id}")


@click.command("export")
@click.argument("recording_id")
@click.option("--format", "fmt", type=click.Choice(["json", "python", "bash"]),
              default="json", help="Export format.")
@click.option("--output", "-o", "output_path", type=click.Path(),
              help="Output file path. Prints to stdout if omitted.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def record_export(recording_id: str, fmt: str, output_path: str | None,
                  json_output: bool):
    """Export a recording to a script.

    \b
    Formats:
        json    — Raw recording JSON (default)
        python  — Python script using naturo CLI subprocess calls
        bash    — Bash script with naturo commands

    \b
    Examples:
        naturo record export rec_20260401_120000 --format python
        naturo record export rec_20260401_120000 --format bash -o script.sh
    """
    try:
        rec = load_recording(recording_id)
    except FileNotFoundError:
        msg = f"Recording not found: {recording_id}"
        if json_output:
            click.echo(json_error(ErrorCode.RECORDING_NOT_FOUND, msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    content = _export_recording(rec, fmt)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        if json_output:
            click.echo(json_dumps({
                "success": True, "path": output_path, "format": fmt,
            }))
        else:
            click.echo(f"Exported to {output_path} ({fmt})")
    else:
        if json_output:
            click.echo(json_dumps({"success": True, "format": fmt, "content": content}))
        else:
            click.echo(content)


def _export_recording(rec: Recording, fmt: str) -> str:
    """Generate export content for a recording."""
    if fmt == "json":
        return json_dumps(rec.to_dict(), indent=2, ensure_ascii=False)

    if fmt == "python":
        lines = [
            "#!/usr/bin/env python3",
            f'"""Recorded automation: {rec.name}"""',
            "import subprocess",
            "import time",
            "",
            "",
            "def run(cmd: str) -> None:",
            '    subprocess.run(cmd, shell=True, check=True)',
            "",
            "",
            f"# Recording: {rec.name} ({rec.recording_id})",
            f"# Created: {rec.created_at[:19]}",
            f"# Steps: {len(rec.steps)}",
            "",
        ]
        prev_ts = None
        for step in rec.steps:
            if prev_ts is not None:
                delay = step.timestamp - prev_ts
                if delay > 0.1:
                    lines.append(f"time.sleep({delay:.2f})")
            lines.append(f"run({_step_to_naturo_cmd(step)!r})")
            prev_ts = step.timestamp
        return "\n".join(lines) + "\n"

    if fmt == "bash":
        lines = [
            "#!/bin/bash",
            f"# Recording: {rec.name} ({rec.recording_id})",
            f"# Created: {rec.created_at[:19]}",
            f"# Steps: {len(rec.steps)}",
            "set -e",
            "",
        ]
        prev_ts = None
        for step in rec.steps:
            if prev_ts is not None:
                delay = step.timestamp - prev_ts
                if delay > 0.1:
                    lines.append(f"sleep {delay:.2f}")
            lines.append(_step_to_naturo_cmd(step))
            prev_ts = step.timestamp
        return "\n".join(lines) + "\n"

    return ""


def _step_to_naturo_cmd(step) -> str:
    """Convert an ActionStep to a shell-safe naturo CLI command string.

    All user-provided values are escaped with shlex.quote() to prevent
    shell injection in exported bash scripts.
    """
    cmd = step.command
    args = step.args

    if cmd == "click":
        parts = ["naturo", "click"]
        if "x" in args and "y" in args:
            parts.extend([str(args["x"]), str(args["y"])])
        if args.get("button", "left") != "left":
            parts.extend(["--button", shlex.quote(str(args["button"]))])
        if args.get("double_click"):
            parts.append("--double")
        return " ".join(parts)

    if cmd == "type":
        text = args.get("text", "")
        return f"naturo type {shlex.quote(text)}"

    if cmd == "press":
        key = args.get("key", "")
        return f"naturo press {shlex.quote(key)}"

    if cmd == "hotkey":
        keys = args.get("keys", [])
        return f"naturo hotkey {shlex.quote('+'.join(str(k) for k in keys))}"

    if cmd == "scroll":
        direction = args.get("direction", "down")
        amount = args.get("amount", 3)
        return f"naturo scroll {shlex.quote(str(direction))} --amount {amount}"

    if cmd == "drag":
        return (f"naturo drag --from {args.get('from_x', 0)} {args.get('from_y', 0)} "
                f"--to {args.get('to_x', 0)} {args.get('to_y', 0)}")

    if cmd == "move":
        return f"naturo move {args.get('x', 0)} {args.get('y', 0)}"

    if cmd == "wait":
        return f"naturo wait --duration {args.get('seconds', 1)}"

    return f"# Unknown: {cmd} {args}"


# Register subcommands
record.add_command(record_start, "start")
record.add_command(record_stop, "stop")
record.add_command(record_play, "play")
record.add_command(record_list, "list")
record.add_command(record_show, "show")
record.add_command(record_delete, "delete")
record.add_command(record_export, "export")
