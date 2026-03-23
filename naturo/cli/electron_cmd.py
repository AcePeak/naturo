"""CLI commands for Electron/CEF app detection and Chrome DevTools Protocol.

Provides ``naturo electron`` and ``naturo chrome`` command groups for
discovering Electron apps, connecting via CDP, and listing browser tabs.

These commands require Windows and delegate to :mod:`naturo.electron`
and :mod:`naturo.cdp`.
"""

from __future__ import annotations

import json
import sys
from typing import Optional

import click


def _json_out(data: dict) -> None:
    """Print a JSON-encoded dict to stdout."""
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def _json_err(message: str, code: str = "ERROR") -> None:
    """Print a JSON error to stdout and exit with code 1."""
    click.echo(json.dumps({"error": message, "code": code}, ensure_ascii=False))
    raise SystemExit(1)


# ── electron group ───────────────────────────────────────────────────────────


@click.group("electron")
def electron() -> None:
    """Detect and automate Electron/CEF applications via CDP.

    Electron apps (VS Code, Slack, Discord, etc.) can be controlled
    through the Chrome DevTools Protocol when launched with a debug port.

    Examples:

      naturo electron detect slack
      naturo electron list
      naturo electron connect slack
      naturo electron launch "C:\\\\Program Files\\\\App\\\\app.exe"
    """


@electron.command("detect")
@click.argument("app_name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def electron_detect(app_name: str, json_output: bool) -> None:
    """Detect if a running application is Electron-based.

    Checks whether APP_NAME is an Electron/CEF app and reports its
    debug port if available.

    Examples:

      naturo electron detect slack
      naturo electron detect "Visual Studio Code"
    """
    from naturo.electron import detect_electron_app

    try:
        result = detect_electron_app(app_name)
    except Exception as exc:
        if json_output:
            _json_err(str(exc), "DETECT_FAILED")
        else:
            click.echo(f"Error: {exc}", err=True)
            raise SystemExit(1) from exc
        return

    if json_output:
        _json_out(result)
    else:
        name = result.get("app_name", app_name)
        is_electron = result.get("is_electron", False)
        port = result.get("debug_port")
        pid = result.get("main_pid")
        proc_count = len(result.get("processes", []))

        if is_electron:
            click.echo(f"✅ {name} is an Electron app")
            click.echo(f"   Processes: {proc_count}")
            if pid:
                click.echo(f"   Main PID:  {pid}")
            if port:
                click.echo(f"   Debug port: {port} (CDP available)")
            else:
                click.echo(
                    "   Debug port: not active\n"
                    f"   Tip: relaunch with --remote-debugging-port=9229"
                )
        else:
            click.echo(f"❌ {name} is not detected as Electron")
            if proc_count == 0:
                click.echo("   (app may not be running)")


@electron.command("list")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def electron_list(json_output: bool) -> None:
    """List all running Electron/CEF applications.

    Scans running processes for Electron characteristics and reports
    detected apps with their debug port status.

    Examples:

      naturo electron list
      naturo electron list --json
    """
    from naturo.electron import list_electron_apps

    try:
        result = list_electron_apps()
    except Exception as exc:
        if json_output:
            _json_err(str(exc), "LIST_FAILED")
        else:
            click.echo(f"Error: {exc}", err=True)
            raise SystemExit(1) from exc
        return

    if json_output:
        _json_out(result)
    else:
        apps = result.get("apps", [])
        count = result.get("count", 0)
        if count == 0:
            click.echo("No Electron apps detected.")
        else:
            click.echo(f"Found {count} Electron app(s):\n")
            for app in apps:
                name = app.get("app_name", "Unknown")
                pid = app.get("pid", "?")
                port = app.get("debug_port")
                port_str = f"port {port}" if port else "no debug port"
                click.echo(f"  • {name}  (PID {pid}, {port_str})")


@electron.command("connect")
@click.argument("app_name")
@click.option("--port", "-p", type=int, default=None, help="Specific debug port")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def electron_connect(app_name: str, port: Optional[int], json_output: bool) -> None:
    """Connect to a running Electron app via CDP.

    Auto-detects the debug port or uses --port if specified.
    Returns connection info and available tabs.

    Examples:

      naturo electron connect slack
      naturo electron connect vscode --port 9229
    """
    from naturo.electron import connect_to_electron

    try:
        result = connect_to_electron(app_name, port=port)
    except Exception as exc:
        if json_output:
            _json_err(str(exc), "CONNECT_FAILED")
        else:
            click.echo(f"Error: {exc}", err=True)
            raise SystemExit(1) from exc
        return

    if json_output:
        _json_out(result)
    else:
        success = result.get("success", False)
        actual_port = result.get("port")
        tabs = result.get("tabs", [])
        if success:
            click.echo(f"✅ Connected to {app_name} (port {actual_port})")
            click.echo(f"   Tabs: {len(tabs)}")
            for i, tab in enumerate(tabs):
                title = tab.get("title", "Untitled")
                url = tab.get("url", "")
                click.echo(f"   [{i}] {title}")
                if url:
                    click.echo(f"       {url}")
        else:
            click.echo(f"❌ Could not connect to {app_name}")


@electron.command("launch")
@click.argument("app_path")
@click.option("--port", "-p", type=int, default=9229, help="Debug port (default: 9229)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def electron_launch(app_path: str, port: int, json_output: bool) -> None:
    """Launch an Electron app with remote debugging enabled.

    Starts the application with --remote-debugging-port so it can
    be controlled via CDP.

    Examples:

      naturo electron launch "C:\\\\Program Files\\\\Slack\\\\Slack.exe"
      naturo electron launch "C:\\\\App.exe" --port 9229
    """
    from naturo.electron import launch_with_debug

    try:
        result = launch_with_debug(app_path, port=port)
    except Exception as exc:
        if json_output:
            _json_err(str(exc), "LAUNCH_FAILED")
        else:
            click.echo(f"Error: {exc}", err=True)
            raise SystemExit(1) from exc
        return

    if json_output:
        _json_out(result)
    else:
        pid = result.get("pid")
        click.echo(f"✅ Launched with debug port {port}")
        click.echo(f"   PID: {pid}")
        click.echo(f"   Path: {app_path}")
        click.echo(f"\n   Connect: naturo electron connect --port {port}")


# ── chrome group ─────────────────────────────────────────────────────────────


@click.group("chrome")
def chrome() -> None:
    """Chrome DevTools Protocol commands.

    Interact with Chrome/Chromium/Edge browsers via CDP.
    Requires the browser to be started with --remote-debugging-port.

    Examples:

      naturo chrome tabs
      naturo chrome tabs --port 9229
    """


@chrome.command("tabs")
@click.option("--port", "-p", type=int, default=9222, help="Debug port (default: 9222)")
@click.option("--host", default="127.0.0.1", help="Debug host (default: 127.0.0.1)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def chrome_tabs(port: int, host: str, json_output: bool) -> None:
    """List open tabs in a Chrome/Chromium browser.

    Connects to the browser's CDP endpoint and lists all page targets.

    Examples:

      naturo chrome tabs
      naturo chrome tabs --port 9229
      naturo chrome tabs --host 192.168.1.5 --port 9222
    """
    from naturo.cdp import CDPClient, CDPConnectionError

    try:
        client = CDPClient(port=port, host=host)
        tabs = client.list_tabs()
    except CDPConnectionError as exc:
        if json_output:
            _json_err(str(exc), "CDP_CONNECTION_ERROR")
        else:
            click.echo(
                f"Error: Cannot connect to Chrome at {host}:{port}\n"
                "Make sure the browser was started with:\n"
                f"  --remote-debugging-port={port}",
                err=True,
            )
            raise SystemExit(1) from exc
        return
    except Exception as exc:
        if json_output:
            _json_err(str(exc), "CDP_ERROR")
        else:
            click.echo(f"Error: {exc}", err=True)
            raise SystemExit(1) from exc
        return

    if json_output:
        _json_out({"tabs": tabs, "count": len(tabs)})
    else:
        if not tabs:
            click.echo("No tabs found.")
        else:
            click.echo(f"Found {len(tabs)} tab(s):\n")
            for i, tab in enumerate(tabs):
                title = tab.get("title", "Untitled")
                url = tab.get("url", "")
                tab_type = tab.get("type", "page")
                tab_id = tab.get("id", "")
                click.echo(f"  [{i}] {title}")
                if url:
                    click.echo(f"      {url}")
                click.echo(f"      type={tab_type}  id={tab_id}")
