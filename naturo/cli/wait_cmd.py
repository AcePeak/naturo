"""CLI wait command — wait for elements or windows to appear/disappear."""
import json

from naturo.cli.error_helpers import json_error as _json_error_str
import sys
import click


@click.command("wait")
@click.option("--element", help="Element selector to wait for")
@click.option("--window", "window_title", help="Window title to wait for")
@click.option("--gone", help="Element selector to wait to disappear")
@click.option("--timeout", type=float, default=10.0, help="Timeout in seconds (default: 10)")
@click.option("--interval", type=float, default=0.1, help="Poll interval in seconds (default: 0.1)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def wait(ctx, element, window_title, gone, timeout, interval, json_output):
    """Wait for a UI element or window to appear or disappear.

    Examples:

      naturo wait --element "Button:Save" --timeout 10

      naturo wait --window "Notepad" --timeout 5

      naturo wait --gone "Dialog:Loading" --timeout 30
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    if not element and not window_title and not gone:
        msg = "Specify --element, --window, or --gone"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    if timeout < 0:
        msg = f"--timeout must be >= 0, got {timeout}"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    if interval <= 0:
        msg = f"--interval must be > 0, got {interval}"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    # Import here to avoid import-time side effects
    from naturo.wait import wait_for_element, wait_until_gone, wait_for_window

    from naturo.errors import NaturoError

    try:
        if element:
            result = wait_for_element(selector=element, timeout=timeout, poll_interval=interval)
        elif gone:
            result = wait_until_gone(selector=gone, timeout=timeout, poll_interval=interval)
        elif window_title:
            result = wait_for_window(title=window_title, timeout=timeout, poll_interval=interval)
        else:
            return  # unreachable
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response(), indent=2))
        else:
            click.echo(f"Error: {exc.message}", err=True)
        sys.exit(1)
        return
    except Exception as exc:
        if json_output:
            click.echo(_json_error_str("UNKNOWN_ERROR", str(exc)))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
        return

    if json_output:
        output = {
            "success": result.found,
            "found": result.found,
            "wait_time": round(result.wait_time, 3),
            "warnings": result.warnings,
        }
        if result.element:
            output["element"] = {
                "id": result.element.id,
                "role": result.element.role,
                "name": result.element.name,
                "value": result.element.value,
                "x": result.element.x,
                "y": result.element.y,
                "width": result.element.width,
                "height": result.element.height,
            }
        click.echo(json.dumps(output, indent=2))
        if not result.found:
            sys.exit(1)
    else:
        if result.found:
            if element:
                click.echo(f"Found element '{element}' after {result.wait_time:.1f}s")
            elif gone:
                click.echo(f"Element '{gone}' disappeared after {result.wait_time:.1f}s")
            elif window_title:
                click.echo(f"Window '{window_title}' appeared after {result.wait_time:.1f}s")
        else:
            target = element or gone or window_title
            click.echo(f"Timeout after {result.wait_time:.1f}s waiting for '{target}'", err=True)
            sys.exit(1)

        for w in result.warnings:
            click.echo(f"  Warning: {w}", err=True)
