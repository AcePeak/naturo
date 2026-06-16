"""Browser anti-detection commands (#760): stealth, stealth-flags, stealth-check."""

from __future__ import annotations

import json as json_module

import click

from naturo.cli import browser_cmd
from naturo.cli._browser._group import browser
from naturo.cli.error_helpers import emit_exception_error


@browser.command("stealth")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def stealth_cmd(ctx: click.Context, json_output: bool) -> None:
    """Apply anti-detection patches to the running browser.

    Injects JavaScript patches that mask common bot fingerprints
    (navigator.webdriver, plugins, languages, WebGL vendor, etc.).
    Patches persist across page navigations.

    \\b
    Examples:
        naturo browser stealth
        naturo browser stealth --json
    """
    from naturo.browser._stealth import apply_stealth_patches

    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        count = apply_stealth_patches(page)
        if json_output:
            click.echo(json_module.dumps({
                "success": True,
                "patches_applied": count,
            }))
        else:
            click.echo(f"Applied {count} stealth patches.")
    except Exception as exc:
        emit_exception_error(exc, json_output)
    finally:
        page.close()


@browser.command("stealth-flags")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def stealth_flags_cmd(json_output: bool) -> None:
    """Print Chrome flags for anti-detection.

    These flags should be passed when launching Chrome to reduce
    automation fingerprinting. No running browser required.

    \\b
    Examples:
        naturo browser stealth-flags
        chrome $(naturo browser stealth-flags)
    """
    from naturo.browser._stealth import STEALTH_FLAGS

    if json_output:
        click.echo(json_module.dumps({"flags": STEALTH_FLAGS}))
    else:
        click.echo(" ".join(STEALTH_FLAGS))


@browser.command("stealth-check")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def stealth_check_cmd(ctx: click.Context, json_output: bool) -> None:
    """Verify stealth patches are working in the running browser.

    Runs 6 JavaScript checks against common bot-detection vectors:
    webdriver, plugins, languages, chrome.runtime, WebGL vendor,
    and permissions. Exits non-zero if any check fails.

    \\b
    Examples:
        naturo browser stealth-check
        naturo browser stealth-check --json
    """
    from naturo.browser._stealth import check_stealth

    page = None
    try:
        page = browser_cmd._get_page(ctx, json_output=json_output)
        results = check_stealth(page)
        all_passed = all(results.values())

        if json_output:
            click.echo(json_module.dumps({
                "success": all_passed,
                "checks": results,
            }))
        else:
            for name, passed in results.items():
                status = "PASS" if passed else "FAIL"
                click.echo(f"  {name}: {status}")
            if all_passed:
                click.echo(f"\nAll {len(results)} checks passed.")
            else:
                failed = [k for k, v in results.items() if not v]
                click.echo(f"\n{len(failed)} check(s) failed: {', '.join(failed)}")

        if not all_passed:
            raise SystemExit(1)
    except SystemExit:
        raise
    except Exception as exc:
        emit_exception_error(exc, json_output)
    finally:
        if page is not None:
            page.close()
