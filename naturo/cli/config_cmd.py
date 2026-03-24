"""Config commands: manage credentials and provider settings.

Commands
--------
``naturo config setup anthropic``
    Interactive setup for the Anthropic provider.  Stores the chosen
    auth token in ``~/.config/naturo/credentials.json``.

``naturo config show``
    Display the current credentials configuration (redacted).

``naturo config clear``
    Remove a provider's stored credentials.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import click

from naturo.cli.fuzzy_group import FuzzyGroup

_CREDENTIALS_PATH: Path = Path.home() / ".config" / "naturo" / "credentials.json"


def _load_credentials() -> dict:
    try:
        if _CREDENTIALS_PATH.exists():
            return json.loads(_CREDENTIALS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _save_credentials(data: dict) -> None:
    import tempfile
    _CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=_CREDENTIALS_PATH.parent,
        prefix=".tmp_",
        suffix=".json",
        delete=False,
    ) as tmp:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp_path = tmp.name
    try:
        os.replace(tmp_path, _CREDENTIALS_PATH)
    except OSError:
        os.unlink(tmp_path)
        raise


@click.group(cls=FuzzyGroup)
def config_cmd() -> None:
    """Manage Naturo configuration and provider credentials."""
    pass


@config_cmd.group("setup", cls=FuzzyGroup)
def config_setup() -> None:
    """Interactive setup for AI provider credentials."""
    pass


@config_setup.command("anthropic")
@click.option(
    "--mode",
    type=click.Choice(["api_key", "oauth"]),
    default=None,
    help="Auth mode: api_key (pay-per-use) or oauth (subscription/session token)",
)
@click.option("--token", default=None, help="API key or session token (skip interactive prompt)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def setup_anthropic(mode: Optional[str], token: Optional[str], json_output: bool) -> None:
    """Configure Anthropic (Claude) credentials.

    Supports two authentication modes:

    \b
    - api_key  : Standard pay-per-use API key (ANTHROPIC_API_KEY)
    - oauth    : Subscription/session token for Pro/Max users (ANTHROPIC_AUTH_TOKEN)

    Credentials are saved to ~/.config/naturo/credentials.json.

    \b
    Examples:
        naturo config setup anthropic                   # interactive
        naturo config setup anthropic --mode api_key    # API key mode
        naturo config setup anthropic --mode oauth      # OAuth mode
        naturo config setup anthropic --token sk-ant-xxx --mode api_key
    """
    if not json_output and token is None:
        click.echo("Naturo — Anthropic credential setup")
        click.echo("─" * 40)

    # Choose auth mode
    if mode is None and not json_output:
        click.echo("\nAuth modes:")
        click.echo("  1. api_key  — Standard API key (ANTHROPIC_API_KEY)")
        click.echo("  2. oauth    — Subscription/session token (Pro/Max users)")
        choice = click.prompt("\nChoose mode", type=click.Choice(["1", "2", "api_key", "oauth"]), default="1")
        mode_map = {"1": "api_key", "2": "oauth", "api_key": "api_key", "oauth": "oauth"}
        mode = mode_map[choice]
    elif mode is None:
        mode = "api_key"

    # Get the token
    if token is None:
        if json_output:
            msg = "Token required when using --json. Pass --token <value>."
            click.echo(json.dumps({"success": False, "error": {"code": "INVALID_INPUT", "message": msg}}))
            raise SystemExit(1)

        if mode == "api_key":
            click.echo("\nFind your API key at: https://console.anthropic.com/settings/keys")
            token = click.prompt("Anthropic API key (sk-ant-...)", hide_input=True)
        else:
            click.echo("\nGet your session token from:")
            click.echo("  1. Sign in at https://claude.ai/")
            click.echo("  2. Open DevTools → Application → Cookies → sessionKey value")
            click.echo("  (Or use ANTHROPIC_AUTH_TOKEN env var directly)")
            token = click.prompt("Session token", hide_input=True)

    token = token.strip()
    if not token:
        msg = "Token cannot be empty."
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "INVALID_INPUT", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    # Persist
    creds = _load_credentials()
    creds.setdefault("anthropic", {})
    creds["anthropic"]["auth_mode"] = mode
    creds["anthropic"]["token"] = token
    _save_credentials(creds)

    if json_output:
        click.echo(json.dumps({
            "success": True,
            "provider": "anthropic",
            "auth_mode": mode,
            "credentials_path": str(_CREDENTIALS_PATH),
        }))
    else:
        click.echo(f"\n✅ Saved {mode} credentials for Anthropic.")
        click.echo(f"   Path: {_CREDENTIALS_PATH}")
        click.echo("\nVerify with: naturo config show")


@config_cmd.command("show")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def config_show(json_output: bool) -> None:
    """Show current credential configuration (tokens are redacted).

    \b
    Example:
        naturo config show
        naturo config show --json
    """
    creds = _load_credentials()
    env_vars = {
        "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "ANTHROPIC_AUTH_TOKEN": bool(os.environ.get("ANTHROPIC_AUTH_TOKEN")),
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        "NATURO_AI_MODEL": os.environ.get("NATURO_AI_MODEL", ""),
    }

    def _redact(value: str) -> str:
        if not value:
            return ""
        return value[:6] + "..." + value[-4:] if len(value) > 12 else "***"

    if json_output:
        result: dict = {"success": True, "credentials_path": str(_CREDENTIALS_PATH), "providers": {}, "env": {}}
        for provider, data in creds.items():
            result["providers"][provider] = {
                "auth_mode": data.get("auth_mode", "api_key"),
                "token": _redact(data.get("token", "")),
            }
        for var, val in env_vars.items():
            result["env"][var] = "set" if val else "not set"
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"Credentials: {_CREDENTIALS_PATH}")
        click.echo("")

        if not creds:
            click.echo("No credentials stored in file.")
        else:
            for provider, data in creds.items():
                mode = data.get("auth_mode", "api_key")
                token = _redact(data.get("token", ""))
                click.echo(f"  {provider}: mode={mode}, token={token}")

        click.echo("\nEnvironment variables:")
        for var, is_set in env_vars.items():
            val = os.environ.get(var, "")
            display = f"set ({_redact(val)})" if val else "not set"
            click.echo(f"  {var}: {display}")


@config_cmd.command("clear")
@click.argument("provider", default="all")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def config_clear(provider: str, yes: bool, json_output: bool) -> None:
    """Remove stored credentials for a provider (or all providers).

    \b
    Examples:
        naturo config clear anthropic
        naturo config clear all --yes
    """
    creds = _load_credentials()

    if provider == "all":
        targets = list(creds.keys())
    else:
        targets = [provider] if provider in creds else []

    if not targets:
        msg = f"No stored credentials for '{provider}'."
        if json_output:
            click.echo(json.dumps({"success": True, "cleared": [], "message": msg}))
        else:
            click.echo(msg)
        return

    if not yes and not json_output:
        if not click.confirm(f"Remove credentials for: {', '.join(targets)}?"):
            click.echo("Aborted.")
            raise SystemExit(0)

    for t in targets:
        creds.pop(t, None)
    _save_credentials(creds)

    if json_output:
        click.echo(json.dumps({"success": True, "cleared": targets}))
    else:
        click.echo(f"Cleared credentials: {', '.join(targets)}")
