"""Browser captcha commands: captcha-detect, captcha-solve."""

from __future__ import annotations

import json as json_module
from typing import Optional

import click

from naturo.cli import browser_cmd
from naturo.cli._browser._group import browser
from naturo.cli.error_helpers import emit_error, emit_exception_error


@browser.command("captcha-detect")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def captcha_detect(ctx: click.Context, json_output: bool) -> None:
    """Detect captchas on the current page.

    Scans for reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile,
    and generic captcha iframes.

    \b
    Examples:
        naturo browser captcha-detect
        naturo browser captcha-detect --json
    """
    page = browser_cmd._get_page(ctx, json_output=json_output)
    from naturo.browser._captcha import CaptchaManager

    manager = CaptchaManager(page)
    captchas = manager.detect()

    if json_output:
        click.echo(json_module.dumps({"captchas": captchas, "count": len(captchas)}))
    elif not captchas:
        click.echo("No captchas detected on this page.")
    else:
        click.echo(f"Detected {len(captchas)} captcha(s):")
        for i, c in enumerate(captchas, 1):
            visible = "visible" if c.get("visible") else "hidden"
            sitekey = c.get("sitekey", "")
            key_display = f" (sitekey: {sitekey[:20]}...)" if sitekey else ""
            click.echo(f"  {i}. {c['type']} [{visible}]{key_display}")


@browser.command("captcha-solve")
@click.option("--solver", type=click.Choice(["manual", "token"]), default="manual",
              help="Solver strategy (default: manual)")
@click.option("--token", default=None,
              help="Pre-obtained captcha token (required for 'token' solver)")
@click.option("--timeout", type=float, default=120.0,
              help="Timeout for manual solving (default: 120s)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def captcha_solve(ctx: click.Context, solver: str, token: Optional[str],
                  timeout: float, json_output: bool) -> None:
    """Solve a captcha on the current page.

    \b
    Solver strategies:
      manual   — Wait for user to solve captcha in browser (default)
      token    — Inject a pre-obtained token (e.g. from 2Captcha)

    \b
    Examples:
        naturo browser captcha-solve --solver manual --timeout 60
        naturo browser captcha-solve --solver token --token "03AGdBq24..."
    """
    page = browser_cmd._get_page(ctx, json_output=json_output)
    from naturo.browser._captcha import (
        CaptchaManager,
        CaptchaError,
        CaptchaSolver,
        ManualSolver,
        TokenInjectionSolver,
    )

    manager = CaptchaManager(page)

    solver_instance: CaptchaSolver
    if solver == "token":
        if not token:
            emit_error(
                "INVALID_INPUT",
                "--token is required when using 'token' solver",
                json_output,
            )
        solver_instance = TokenInjectionSolver(token=token)
    else:
        solver_instance = ManualSolver(timeout=timeout)

    try:
        result_token = manager.solve(solver=solver_instance)
        if json_output:
            click.echo(json_module.dumps({
                "success": True,
                "solver": solver,
                "token_length": len(result_token),
            }))
        else:
            click.echo(f"Captcha solved ({len(result_token)} chars)")
    except CaptchaError as exc:
        emit_exception_error(exc, json_output)
