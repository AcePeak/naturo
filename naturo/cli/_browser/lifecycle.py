"""Browser process lifecycle commands (#758, #759): launch, profiles, download."""

from __future__ import annotations

from naturo.cli._jsonio import json_dumps
from typing import Optional

import click

from naturo.cli import browser_cmd
from naturo.cli._browser._group import browser
from naturo.cli.error_helpers import emit_exception_error


# ── Launch / Profiles (#758) ────────────────────────────────────────────────


@browser.command("launch")
@click.option("--profile", default=None,
              help="Chrome profile name or directory (e.g. 'Work', 'Profile 1')")
@click.option("--user-data-dir", default=None,
              help="Custom Chrome user data directory path")
@click.option("--headless", is_flag=True, help="Run in headless mode")
@click.option("--stealth", is_flag=True,
              help="Apply stealth flags to reduce bot fingerprinting")
@click.option("--url", default=None, help="Initial URL to open (default: about:blank)")
@click.option("--chrome-path", default=None,
              help="Explicit path to Chrome/Chromium/Edge binary")
@click.option("--timeout", type=float, default=15.0,
              help="Seconds to wait for CDP readiness (default: 15)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def launch_cmd(ctx: click.Context, profile: Optional[str],
               user_data_dir: Optional[str], headless: bool,
               stealth: bool, url: Optional[str],
               chrome_path: Optional[str], timeout: float,
               json_output: bool) -> None:
    """Launch Chrome with remote debugging enabled.

    Starts a new Chrome instance with --remote-debugging-port so naturo
    can connect to it. Optionally selects a Chrome profile.

    \b
    Examples:
        naturo browser launch
        naturo browser launch --profile Work
        naturo browser launch --profile "Profile 1" --headless
        naturo browser launch --user-data-dir /tmp/test-profile
        naturo browser launch --stealth --url https://example.com
    """
    from naturo.browser._launcher import launch_chrome as _launch_chrome
    from naturo.browser._stealth import STEALTH_FLAGS

    port = ctx.obj["cdp_port"]
    extra_args = list(STEALTH_FLAGS) if stealth else None

    try:
        proc = _launch_chrome(
            port=port,
            headless=headless,
            profile=profile,
            user_data_dir=user_data_dir,
            extra_args=extra_args,
            url=url,
            chrome_path=chrome_path,
            timeout=timeout,
        )
        if json_output:
            click.echo(json_dumps({
                "success": True,
                "action": "browser_launch",
                "pid": proc.pid,
                "port": proc.port,
                "profile": profile,
            }))
        else:
            click.echo(f"Chrome launched (pid={proc.pid}, port={proc.port})")
            if profile:
                click.echo(f"Profile: {profile}")
    except FileNotFoundError as exc:
        emit_exception_error(exc, json_output, fallback_code="APP_NOT_FOUND")
    except RuntimeError as exc:
        emit_exception_error(exc, json_output)


@browser.command("profiles")
@click.option("--user-data-dir", default=None,
              help="Custom Chrome user data directory path")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def profiles_cmd(user_data_dir: Optional[str], json_output: bool) -> None:
    """List available Chrome profiles.

    Reads the Chrome 'Local State' file to discover profiles.
    No running browser required.

    \b
    Examples:
        naturo browser profiles
        naturo browser profiles --json
        naturo browser profiles --user-data-dir /custom/path
    """
    from naturo.browser._launcher import list_profiles as _list_profiles

    profiles = _list_profiles(user_data_dir=user_data_dir)

    if json_output:
        click.echo(json_dumps({"profiles": profiles, "count": len(profiles)}, indent=2))
    elif not profiles:
        click.echo("No Chrome profiles found.")
        click.echo("Hint: profiles are read from Chrome's 'Local State' file.")
    else:
        click.echo(f"Found {len(profiles)} profile(s):")
        for p in profiles:
            click.echo(f"  {p['name']:<20} [{p['directory']}]  {p['path']}")


# ── Download management (#759) ───────────────────────────────────────────────


@browser.command("download")
@click.option("--dir", "directory", required=True,
              help="Directory to save downloaded files to")
@click.option("--wait", "wait", is_flag=True,
              help="Wait for a download to complete after setting the directory")
@click.option("--timeout", type=float, default=60.0,
              help="Seconds to wait for download completion (default: 60)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def download_cmd(
    ctx: click.Context,
    directory: str,
    wait: bool,
    timeout: float,
    json_output: bool,
) -> None:
    """Configure file downloads and optionally wait for completion.

    Sets the browser download directory so files are saved without
    prompts. With ``--wait``, blocks until a new file finishes
    downloading (partial files like .crdownload are detected).

    \b
    Examples:
        naturo browser download --dir /tmp/downloads
        naturo browser download --dir /tmp/downloads --wait
        naturo browser download --dir ./out --wait --timeout 120 --json
    """
    import os

    from naturo.browser._download import set_download_dir, wait_for_download

    # Ensure directory exists
    abs_dir = os.path.abspath(directory)
    os.makedirs(abs_dir, exist_ok=True)

    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        set_download_dir(page, abs_dir)

        if not wait:
            if json_output:
                click.echo(json_dumps({
                    "success": True,
                    "download_dir": abs_dir,
                }))
            else:
                click.echo(f"Download directory set to: {abs_dir}")
            return

        # Wait mode: block until a download completes
        if not json_output:
            click.echo(f"Waiting for download in {abs_dir} (timeout: {timeout}s)...")

        try:
            path = wait_for_download(abs_dir, timeout=timeout)
        except TimeoutError as exc:
            emit_exception_error(exc, json_output, fallback_code="TIMEOUT")

        if json_output:
            click.echo(json_dumps({
                "success": True,
                "download_dir": abs_dir,
                "file": path,
                "filename": os.path.basename(path),
            }))
        else:
            click.echo(f"Downloaded: {path}")
    except SystemExit:
        raise
    except Exception as exc:
        emit_exception_error(exc, json_output)
    finally:
        page.close()
