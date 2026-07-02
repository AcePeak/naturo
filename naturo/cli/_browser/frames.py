"""Browser iframe commands (#764): frames, frame-eval, frame-find."""

from __future__ import annotations

from naturo.cli._jsonio import json_dumps

import click

from naturo.cli import browser_cmd
from naturo.cli._browser._group import browser
from naturo.cli.error_helpers import emit_exception_error


@browser.command("frames")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def frames_cmd(ctx: click.Context, json_output: bool) -> None:
    """List all frames (main frame and iframes) on the page.

    \b
    Examples:
        naturo browser frames
        naturo browser frames --json
    """
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        frame_list = page.frames()
        if json_output:
            click.echo(json_dumps({
                "frames": frame_list,
                "count": len(frame_list),
            }, indent=2))
        else:
            if not frame_list:
                click.echo("No frames found.")
            else:
                for f in frame_list:
                    indent = "  " * f.get("depth", 0)
                    name_display = f" name={f['name']!r}" if f.get("name") else ""
                    click.echo(f"  {indent}[{f['id'][:12]}]{name_display}  {f['url'][:80]}")
                click.echo(f"\n{len(frame_list)} frame(s) total")
    finally:
        page.close()


@browser.command("frame-eval")
@click.argument("frame_ref")
@click.argument("expression")
@click.option("--by-name", is_flag=True,
              help="Treat FRAME_REF as frame name (default: CSS selector)")
@click.option("--by-url", is_flag=True,
              help="Treat FRAME_REF as URL substring")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def frame_eval_cmd(ctx: click.Context, frame_ref: str, expression: str,
                   by_name: bool, by_url: bool, json_output: bool) -> None:
    """Evaluate JavaScript inside a specific iframe.

    FRAME_REF identifies the iframe by CSS selector (default),
    frame name (--by-name), or URL substring (--by-url).

    \b
    Examples:
        naturo browser frame-eval "iframe#payment" "document.title"
        naturo browser frame-eval "checkout" "document.title" --by-name
        naturo browser frame-eval "payment.example.com" "document.title" --by-url
    """
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        if by_name:
            frame = page.frame(name=frame_ref)
        elif by_url:
            frame = page.frame(url=frame_ref)
        else:
            frame = page.frame(selector=frame_ref)

        result = frame.evaluate(expression)
        if json_output:
            click.echo(json_dumps({"result": result, "frame": frame_ref}))
        else:
            click.echo(result)
    except RuntimeError as exc:
        emit_exception_error(exc, json_output, fallback_code="ELEMENT_NOT_FOUND")
    finally:
        page.close()


@browser.command("frame-find")
@click.argument("frame_ref")
@click.argument("selector")
@click.option("--by-name", is_flag=True,
              help="Treat FRAME_REF as frame name")
@click.option("--by-url", is_flag=True,
              help="Treat FRAME_REF as URL substring")
@click.option("--all", "find_all", is_flag=True, help="Find all matching elements")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def frame_find_cmd(ctx: click.Context, frame_ref: str, selector: str,
                   by_name: bool, by_url: bool, find_all: bool,
                   json_output: bool) -> None:
    """Find elements inside a specific iframe.

    FRAME_REF identifies the iframe. SELECTOR is a CSS selector for
    elements within that frame.

    \b
    Examples:
        naturo browser frame-find "iframe#payment" "#card-number"
        naturo browser frame-find "checkout" "input" --by-name --all
    """
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        if by_name:
            frame = page.frame(name=frame_ref)
        elif by_url:
            frame = page.frame(url=frame_ref)
        else:
            frame = page.frame(selector=frame_ref)

        if find_all:
            elements = frame.find_all(selector)
            if json_output:
                items = [{"ref": f"e{i+1}", "tag": el.tag_name, "text": el.text[:200]}
                         for i, el in enumerate(elements)]
                click.echo(json_dumps({"elements": items, "count": len(items)}, indent=2))
            else:
                if not elements:
                    click.echo("No elements found in frame.")
                else:
                    for i, el in enumerate(elements):
                        text = el.text[:80].replace("\n", "\\n")
                        click.echo(f"  e{i+1}  [{el.tag_name}] {text}")
                    click.echo(f"\n{len(elements)} element(s) found.")
        else:
            el = frame.find(selector)
            if json_output:
                click.echo(json_dumps({
                    "ref": "e1", "tag": el.tag_name,
                    "text": el.text[:200], "value": el.value,
                }, indent=2))
            else:
                text = el.text[:80].replace("\n", "\\n")
                click.echo(f"  e1  [{el.tag_name}] {text}")
    except RuntimeError as exc:
        emit_exception_error(exc, json_output, fallback_code="ELEMENT_NOT_FOUND")
    finally:
        page.close()
