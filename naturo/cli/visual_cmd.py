"""Visual regression testing CLI commands.

Provides `naturo visual baseline/compare/list/delete/report` commands
for screenshot-based regression testing.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from naturo.cli.fuzzy_group import FuzzyGroup
from naturo.visual import (
    save_baseline,
    update_baseline,
    list_baselines,
    delete_baseline,
    compare_with_baseline,
    compare_images,
    generate_html_report,
    load_suite,
    run_suite,
    VisualReport,
)


@click.group("visual", cls=FuzzyGroup)
def visual():
    """Visual regression testing — compare screenshots across runs.

    \b
    Examples:
        naturo visual baseline login_screen --from screenshot.png
        naturo visual compare login_screen --current screenshot2.png
        naturo visual list
        naturo visual report --name "Sprint 42" --output report.html
    """


@click.command("baseline")
@click.argument("name")
@click.option("--from", "from_path", required=True, type=click.Path(exists=True),
              help="Path to screenshot to use as baseline.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def visual_baseline(name: str, from_path: str, json_output: bool):
    """Save a screenshot as a visual baseline.

    \b
    Examples:
        naturo visual baseline login_screen --from screenshot.png
        naturo visual baseline dashboard --from ~/captures/dash.png
    """
    try:
        path = save_baseline(from_path, name)
    except ImportError as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if json_output:
        click.echo(json.dumps({"success": True, "name": name, "path": str(path)}))
    else:
        click.echo(f"Baseline saved: {name}")
        click.echo(f"Path: {path}")


def _parse_region(value: str) -> tuple[int, int, int, int]:
    """Parse 'x,y,w,h' into a tuple of ints."""
    parts = value.split(",")
    if len(parts) != 4:
        raise click.BadParameter(f"Expected x,y,w,h but got: {value}")
    try:
        return tuple(int(p.strip()) for p in parts)  # type: ignore[return-value]
    except ValueError:
        raise click.BadParameter(f"Non-integer in region: {value}")


@click.command("compare")
@click.argument("name")
@click.option("--current", required=True, type=click.Path(exists=True),
              help="Path to current screenshot to compare.")
@click.option("--threshold", type=float, default=0.95,
              help="Similarity threshold (0.0-1.0, default 0.95).")
@click.option("--ignore-region", multiple=True,
              help="Region to mask (x,y,w,h). Repeatable.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def visual_compare(name: str, current: str, threshold: float,
                   ignore_region: tuple, json_output: bool):
    """Compare a screenshot against its saved baseline.

    \b
    Examples:
        naturo visual compare login_screen --current new_screenshot.png
        naturo visual compare login_screen --current new.png --threshold 0.90
        naturo visual compare dashboard --current new.png --ignore-region 10,5,200,30
    """
    regions = [_parse_region(r) for r in ignore_region] if ignore_region else None
    try:
        result = compare_with_baseline(current, name, threshold=threshold,
                                       ignore_regions=regions)
    except FileNotFoundError as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ImportError as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if json_output:
        click.echo(json.dumps(result.to_dict()))
    else:
        status = "PASS" if result.match else "FAIL"
        color = "" if result.match else "! "
        click.echo(f"{color}[{status}] {result.name}")
        click.echo(f"  Similarity: {result.similarity:.1%} (threshold: {result.threshold:.1%})")
        click.echo(f"  Diff pixels: {result.diff_pixels:,} / {result.total_pixels:,} "
                    f"({result.to_dict()['diff_percentage']:.2f}%)")
        if not result.dimensions_match:
            click.echo(f"  Warning: dimensions differ — "
                        f"baseline {result.baseline_size} vs current {result.current_size}")
        if result.diff_path:
            click.echo(f"  Diff image: {result.diff_path}")

    if not result.match:
        sys.exit(1)


@click.command("diff")
@click.argument("image1", type=click.Path(exists=True))
@click.argument("image2", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Save diff image to path.")
@click.option("--threshold", type=float, default=0.95, help="Similarity threshold.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def visual_diff(image1: str, image2: str, output: Optional[str],
                threshold: float, json_output: bool):
    """Compare any two images directly (without baseline).

    \b
    Examples:
        naturo visual diff before.png after.png
        naturo visual diff before.png after.png -o diff.png
    """
    try:
        result = compare_images(
            image1, image2, name="diff",
            threshold=threshold, diff_output=output,
        )
    except ImportError as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if json_output:
        click.echo(json.dumps(result.to_dict()))
    else:
        status = "MATCH" if result.match else "DIFFER"
        click.echo(f"[{status}] Similarity: {result.similarity:.1%}")
        click.echo(f"  Diff pixels: {result.diff_pixels:,} / {result.total_pixels:,}")
        if output:
            click.echo(f"  Diff image: {output}")


@click.command("list")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def visual_list(json_output: bool):
    """List all saved baselines.

    \b
    Examples:
        naturo visual list
    """
    baselines = list_baselines()

    if json_output:
        click.echo(json.dumps({"baselines": baselines}))
        return

    if not baselines:
        click.echo("No baselines saved.")
        click.echo("Use 'naturo visual baseline <name> --from <image>' to create one.")
        return

    click.echo(f"{'Name':<25} {'Size':>12}  {'Created'}")
    click.echo("-" * 60)
    for b in baselines:
        size = f"{b.get('size', [0, 0])[0]}x{b.get('size', [0, 0])[1]}"
        created = b.get("created_at", "")[:19]
        exists = "" if b.get("exists", True) else " [MISSING]"
        click.echo(f"{b['name']:<25} {size:>12}  {created}{exists}")


@click.command("delete")
@click.argument("name")
@click.option("--force", is_flag=True, help="Skip confirmation.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def visual_delete(name: str, force: bool, json_output: bool):
    """Delete a saved baseline.

    \b
    Examples:
        naturo visual delete login_screen
        naturo visual delete login_screen --force
    """
    if not force and not json_output:
        click.confirm(f"Delete baseline '{name}'?", abort=True)

    deleted = delete_baseline(name)
    if json_output:
        click.echo(json.dumps({"success": deleted, "name": name}))
    else:
        if deleted:
            click.echo(f"Deleted baseline: {name}")
        else:
            click.echo(f"Baseline not found: {name}")


@click.command("report")
@click.argument("names", nargs=-1)
@click.option("--current-dir", type=click.Path(exists=True),
              help="Directory containing current screenshots (name.png).")
@click.option("--threshold", type=float, default=0.95, help="Similarity threshold.")
@click.option("--ignore-region", multiple=True,
              help="Region to mask globally (x,y,w,h). Repeatable.")
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Output HTML report path.")
@click.option("--name", "report_name", default=None, help="Report name.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def visual_report(names: tuple, current_dir: Optional[str], threshold: float,
                  ignore_region: tuple, output: Optional[str],
                  report_name: Optional[str], json_output: bool):
    """Run visual regression tests and generate a report.

    Compare multiple baselines against current screenshots at once.
    If no names given, compares all baselines against screenshots in --current-dir.

    \b
    Examples:
        naturo visual report login dashboard --current-dir ./screenshots/
        naturo visual report --current-dir ./screenshots/ -o report.html
        naturo visual report --current-dir ./current/ --ignore-region 0,0,200,30
    """
    regions = [_parse_region(r) for r in ignore_region] if ignore_region else None

    if not current_dir:
        click.echo("Error: --current-dir is required.", err=True)
        sys.exit(1)

    current_path = Path(current_dir)
    rname = report_name or f"Visual Regression {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    report = VisualReport(name=rname, created_at=datetime.now().isoformat())

    # If no names given, compare all baselines
    if not names:
        baselines = list_baselines()
        names = tuple(b["name"] for b in baselines)

    if not names:
        msg = "No baselines to compare."
        if json_output:
            click.echo(json.dumps({"success": False, "error": msg}))
        else:
            click.echo(msg)
        sys.exit(1)

    for name in names:
        current_img = current_path / f"{name}.png"
        if not current_img.exists():
            if not json_output:
                click.echo(f"  [SKIP] {name} — no current screenshot at {current_img}")
            continue

        try:
            result = compare_with_baseline(str(current_img), name, threshold=threshold,
                                           ignore_regions=regions)
            report.add_result(result)
            if not json_output:
                status = "PASS" if result.match else "FAIL"
                click.echo(f"  [{status}] {name} — {result.similarity:.1%}")
        except (FileNotFoundError, ImportError) as e:
            if not json_output:
                click.echo(f"  [ERROR] {name} — {e}")

    # Generate HTML report
    if output:
        try:
            html_path = generate_html_report(report, output)
            if not json_output:
                click.echo(f"\nReport saved: {html_path}")
        except Exception as e:
            if not json_output:
                click.echo(f"Error generating report: {e}", err=True)

    if json_output:
        click.echo(json.dumps(report.to_dict()))
    else:
        click.echo(f"\nResults: {report.passed} passed, {report.failed} failed")

    if not report.all_passed:
        sys.exit(1)


@click.command("update")
@click.argument("name")
@click.option("--from", "from_path", required=True, type=click.Path(exists=True),
              help="Path to new screenshot to replace the baseline.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def visual_update(name: str, from_path: str, json_output: bool):
    """Update an existing baseline with a new screenshot.

    \b
    Examples:
        naturo visual update login_screen --from new_screenshot.png
        naturo visual update dashboard --from ~/captures/dash_v2.png
    """
    try:
        path = update_baseline(from_path, name)
    except FileNotFoundError as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ImportError as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if json_output:
        click.echo(json.dumps({"success": True, "name": name, "path": str(path)}))
    else:
        click.echo(f"Baseline updated: {name}")
        click.echo(f"Path: {path}")


@click.command("update-all")
@click.option("--from-dir", required=True, type=click.Path(exists=True),
              help="Directory containing new screenshots (name.png).")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def visual_update_all(from_dir: str, json_output: bool):
    """Update all baselines from a directory of screenshots.

    Each file in the directory is matched by name to an existing baseline.
    Only existing baselines are updated; new files are skipped.

    \b
    Examples:
        naturo visual update-all --from-dir ./new_screenshots/
    """
    from_path = Path(from_dir)
    baselines = list_baselines()
    baseline_names = {b["name"] for b in baselines}

    updated = []
    skipped = []
    for img_file in sorted(from_path.glob("*.png")):
        name = img_file.stem
        if name in baseline_names:
            try:
                update_baseline(str(img_file), name)
                updated.append(name)
            except (FileNotFoundError, ImportError):
                skipped.append(name)
        else:
            skipped.append(name)

    if json_output:
        click.echo(json.dumps({
            "success": True,
            "updated": updated,
            "skipped": skipped,
            "updated_count": len(updated),
            "skipped_count": len(skipped),
        }))
    else:
        for name in updated:
            click.echo(f"  Updated: {name}")
        for name in skipped:
            click.echo(f"  Skipped: {name}")
        click.echo(f"\n{len(updated)} updated, {len(skipped)} skipped")


@click.command("suite")
@click.argument("suite_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Output HTML report path.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def visual_suite(suite_path: str, output: Optional[str], json_output: bool):
    """Run a visual regression test suite from a JSON definition.

    The suite JSON format:

    \b
        {
          "name": "Login Flow",
          "threshold": 0.95,
          "tests": [
            {"name": "login_screen", "current": "screenshots/login.png"},
            {"name": "dashboard", "current": "screenshots/dash.png",
             "threshold": 0.98, "ignore_regions": [[10, 5, 200, 30]]}
          ]
        }

    \b
    Examples:
        naturo visual suite regression.json
        naturo visual suite regression.json -o report.html
        naturo visual suite regression.json --json
    """
    try:
        suite = load_suite(suite_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(f"Error loading suite: {e}", err=True)
        sys.exit(1)

    try:
        report = run_suite(suite)
    except ImportError as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if not json_output:
        click.echo(f"Suite: {suite.name}")
        for r in report.results:
            status = "PASS" if r.match else "FAIL"
            click.echo(f"  [{status}] {r.name} — {r.similarity:.1%}")

    if output:
        try:
            html_path = generate_html_report(report, output)
            if not json_output:
                click.echo(f"\nReport saved: {html_path}")
        except Exception as e:
            if not json_output:
                click.echo(f"Error generating report: {e}", err=True)

    if json_output:
        click.echo(json.dumps(report.to_dict()))
    else:
        click.echo(f"\nResults: {report.passed} passed, {report.failed} failed")

    if not report.all_passed:
        sys.exit(1)


# Register subcommands
visual.add_command(visual_baseline, "baseline")
visual.add_command(visual_compare, "compare")
visual.add_command(visual_diff, "diff")
visual.add_command(visual_list, "list")
visual.add_command(visual_delete, "delete")
visual.add_command(visual_report, "report")
visual.add_command(visual_update, "update")
visual.add_command(visual_update_all, "update-all")
visual.add_command(visual_suite, "suite")
