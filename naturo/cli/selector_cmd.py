"""Selector management CLI commands — save, load, list, delete, export, import.

Provides `naturo selector save/list/show/delete/export/import/test` commands
for persisting and managing UI element selectors.
"""
from __future__ import annotations

import json
from naturo.cli._jsonio import json_dumps
import sys
from pathlib import Path
from typing import Optional

import click

from naturo.cli.core._common import _ensure_output_dir
from naturo.cli.error_helpers import collection_read, json_error, success_envelope
from naturo.cli.fuzzy_group import FuzzyGroup
from naturo.errors import ErrorCode


# Default storage locations
SELECTORS_DIR = Path.home() / ".naturo" / "selectors"
BUILTIN_DIR = Path(__file__).parent.parent / "selectors_builtin"


class SelectorNotFoundError(KeyError):
    """Raised when an ``@app/name`` selector reference cannot be resolved.

    Subclasses :class:`KeyError` so existing callers that catch ``KeyError`` to
    distinguish the not-found case from a malformed reference (a ``ValueError``)
    keep working unchanged. It overrides ``__str__`` because ``KeyError`` is the
    one builtin whose ``__str__`` wraps its argument in ``repr`` quotes
    (``str(KeyError("msg")) == "'msg'"``): consumers that build a user-facing
    error message via ``str(exc)`` — ``find``/``click``/``type`` — would
    otherwise leak stray single quotes into the JSON envelope's ``message``
    (#1172), inconsistent with the clean ``ValueError`` malformed-format path.
    """

    def __str__(self) -> str:
        """Return the message verbatim, without ``KeyError``'s repr quoting."""
        return self.args[0] if self.args else super().__str__()


def _ensure_dir(d: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    return d


def _user_selectors_path(app_name: Optional[str] = None) -> Path:
    """Get path to user selectors file."""
    d = _ensure_dir(SELECTORS_DIR)
    if app_name:
        return d / f"{app_name}.json"
    return d


def _load_selectors(app_name: str) -> dict:
    """Load selectors for an app from disk."""
    path = _user_selectors_path(app_name)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_selectors(app_name: str, selectors: dict) -> Path:
    """Save selectors for an app to disk."""
    path = _user_selectors_path(app_name)
    _ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(selectors, f, indent=2, ensure_ascii=False)
    return path


def _list_all_user_selectors() -> dict[str, dict]:
    """Load all user selectors across all apps."""
    result = {}
    d = _user_selectors_path()
    if d.exists():
        for f in sorted(d.glob("*.json")):
            app_name = f.stem
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    result[app_name] = json.load(fh)
            except (json.JSONDecodeError, OSError):
                continue
    return result


def _list_builtin_selectors() -> dict[str, dict]:
    """Load all built-in selector templates."""
    result = {}
    if BUILTIN_DIR.exists():
        for f in sorted(BUILTIN_DIR.glob("*.json")):
            app_name = f.stem
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    result[app_name] = json.load(fh)
            except (json.JSONDecodeError, OSError):
                continue
    return result


def resolve_named_selector(reference: str) -> str:
    """Resolve an ``@app/name`` reference to its selector string.

    Searches user selectors first, then built-in templates.

    Args:
        reference: An ``@app/name`` reference (the leading ``@`` is optional).

    Returns:
        The selector string stored under that name.

    Raises:
        SelectorNotFoundError: If the reference cannot be found in user or
            built-in selectors. This is a :class:`KeyError` subclass with a
            clean ``__str__`` (no repr quotes), so ``except KeyError`` callers
            are unaffected while ``str(exc)`` yields a clean message (#1172).
        ValueError: If the reference format is invalid.
    """
    ref = reference.lstrip("@")
    if "/" not in ref:
        raise ValueError(
            f"Invalid selector reference '{reference}': expected @app/name format"
        )
    app_name, name = ref.split("/", 1)
    if not app_name or not name:
        raise ValueError(
            f"Invalid selector reference '{reference}': app and name must be non-empty"
        )

    # User selectors take priority over built-in templates
    user_sels = _load_selectors(app_name)
    if name in user_sels:
        info = user_sels[name]
        return info.get("selector", info) if isinstance(info, dict) else info

    builtin_sels = _list_builtin_selectors().get(app_name, {})
    if name in builtin_sels:
        info = builtin_sels[name]
        return info.get("selector", info) if isinstance(info, dict) else info

    raise SelectorNotFoundError(f"Selector not found: @{app_name}/{name}")


@click.group("selector", cls=FuzzyGroup)
def selector():
    """Manage saved selectors for UI elements.

    \b
    Examples:
        naturo selector save notepad save-btn 'app://notepad.exe/Button[@name="Save"]'
        naturo selector load notepad save-btn
        naturo selector list
        naturo selector list --app notepad
        naturo selector show notepad
        naturo selector test notepad save-btn
        naturo selector delete notepad save-btn
        naturo selector export notepad -o selectors.json
        naturo selector import selectors.json
    """


@click.command("save")
@click.argument("app_name")
@click.argument("name")
@click.argument("selector_value")
@click.option("--description", "-d", default="", help="Description of the selector.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def selector_save(app_name: str, name: str, selector_value: str,
                  description: str, json_output: bool):
    """Save a selector with a friendly name.

    \b
    Examples:
        naturo selector save notepad save-btn 'app://notepad.exe/Button[@name="Save"]'
        naturo selector save chrome address-bar '//Edit[@name="Address and search bar"]' -d "Chrome address bar"
    """
    selectors = _load_selectors(app_name)
    is_update = name in selectors
    selectors[name] = {
        "selector": selector_value,
        "description": description,
    }
    path = _save_selectors(app_name, selectors)

    if json_output:
        click.echo(json_dumps({
            "success": True,
            "app": app_name,
            "name": name,
            "selector": selector_value,
            "updated": is_update,
            "path": str(path),
        }))
    else:
        action = "Updated" if is_update else "Saved"
        click.echo(f"{action}: @{app_name}/{name}")
        click.echo(f"Selector: {selector_value}")


@click.command("load")
@click.argument("app_name")
@click.argument("name")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def selector_load(app_name: str, name: str, json_output: bool):
    """Load a saved selector by name.

    Searches user selectors first, then built-in templates.
    Use with interaction commands: naturo click --selector @app/name

    \b
    Examples:
        naturo selector load notepad save-btn
        naturo selector load chrome address-bar --json
    """
    try:
        sel_str = resolve_named_selector(f"{app_name}/{name}")
    except KeyError:
        msg = f"Selector not found: @{app_name}/{name}"
        if json_output:
            click.echo(json_error(ErrorCode.SELECTOR_NOT_FOUND, msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    # Get full info for description
    user_sels = _load_selectors(app_name)
    builtin_sels = _list_builtin_selectors().get(app_name, {})
    merged = {**builtin_sels, **user_sels}
    info = merged.get(name, {})
    desc = info.get("description", "") if isinstance(info, dict) else ""
    source = "user" if name in user_sels else "builtin"

    if json_output:
        click.echo(json_dumps({
            "success": True,
            "app": app_name,
            "name": name,
            "selector": sel_str,
            "description": desc,
            "source": source,
        }))
    else:
        click.echo(sel_str)


@collection_read("selectors")
@click.command("list")
@click.option("--app", "app_name", default=None, help="Filter by app name.")
@click.option("--builtin", is_flag=True, help="Show built-in templates.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def selector_list(app_name: Optional[str], builtin: bool, json_output: bool):
    """List saved selectors.

    \b
    Examples:
        naturo selector list                # All user selectors
        naturo selector list --app notepad  # Filter by app
        naturo selector list --builtin      # Show built-in templates
    """
    if builtin:
        all_selectors = _list_builtin_selectors()
    else:
        all_selectors = _list_all_user_selectors()

    if app_name:
        if app_name in all_selectors:
            all_selectors = {app_name: all_selectors[app_name]}
        else:
            all_selectors = {}

    if json_output:
        selectors = []
        for app, sels in all_selectors.items():
            for name, info in sels.items():
                if isinstance(info, dict):
                    selector_value = info.get("selector", "")
                    description = info.get("description", "")
                else:
                    selector_value = info
                    description = ""
                selectors.append({
                    "app": app,
                    "name": name,
                    "selector": selector_value,
                    "description": description,
                })
        click.echo(json_dumps(success_envelope("selectors", selectors)))
        return

    if not all_selectors:
        source = "built-in" if builtin else "saved"
        if app_name:
            click.echo(f"No {source} selectors for '{app_name}'.")
        else:
            click.echo(f"No {source} selectors.")
        return

    total = 0
    for app, sels in all_selectors.items():
        click.echo(f"\n  {app} ({len(sels)} selectors)")
        click.echo(f"  {'─' * 50}")
        for name, info in sels.items():
            sel = info.get("selector", info) if isinstance(info, dict) else info
            desc = info.get("description", "") if isinstance(info, dict) else ""
            desc_str = f"  — {desc}" if desc else ""
            click.echo(f"    @{app}/{name}{desc_str}")
            click.echo(f"      {sel}")
            total += 1
    click.echo(f"\n  Total: {total} selectors")


@click.command("show")
@click.argument("app_name")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def selector_show(app_name: str, json_output: bool):
    """Show all selectors for an app.

    \b
    Examples:
        naturo selector show notepad
    """
    selectors = _load_selectors(app_name)
    builtin = _list_builtin_selectors().get(app_name, {})

    if json_output:
        if not selectors and not builtin:
            # A nonexistent app (no user and no built-in selectors) must fail
            # loudly so scripters can distinguish it from an existing app that
            # simply has zero selectors. Mirrors `record show <nonexistent> -j`.
            click.echo(json_error(
                ErrorCode.SELECTOR_NOT_FOUND,
                f"No selectors saved for app '{app_name}'",
            ))
            sys.exit(1)
        click.echo(json_dumps({
            "success": True,
            "app": app_name,
            "selectors": selectors,
            "builtin": builtin,
            "count": len(selectors) + len(builtin),
        }))
        return

    if not selectors and not builtin:
        click.echo(f"No selectors for '{app_name}'.")
        return

    if builtin:
        click.echo(f"\n  Built-in selectors for {app_name}:")
        for name, info in builtin.items():
            sel = info.get("selector", info) if isinstance(info, dict) else info
            click.echo(f"    @{app_name}/{name} = {sel}")

    if selectors:
        click.echo(f"\n  User selectors for {app_name}:")
        for name, info in selectors.items():
            sel = info.get("selector", info) if isinstance(info, dict) else info
            click.echo(f"    @{app_name}/{name} = {sel}")


@click.command("delete")
@click.argument("app_name")
@click.argument("name")
@click.option("--force", is_flag=True, help="Skip confirmation.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def selector_delete(app_name: str, name: str, force: bool, json_output: bool):
    """Delete a saved selector.

    \b
    Examples:
        naturo selector delete notepad save-btn
        naturo selector delete notepad save-btn --force
    """
    selectors = _load_selectors(app_name)
    if name not in selectors:
        msg = f"Selector not found: @{app_name}/{name}"
        if json_output:
            click.echo(json_error(ErrorCode.SELECTOR_NOT_FOUND, msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    if not force and not json_output:
        click.confirm(f"Delete @{app_name}/{name}?", abort=True)

    del selectors[name]
    if selectors:
        _save_selectors(app_name, selectors)
    else:
        path = _user_selectors_path(app_name)
        if path.exists():
            path.unlink()

    if json_output:
        click.echo(json_dumps({"success": True, "deleted": f"@{app_name}/{name}"}))
    else:
        click.echo(f"Deleted: @{app_name}/{name}")


@click.command("clear")
@click.argument("app_name")
@click.option("--force", is_flag=True, help="Skip confirmation.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def selector_clear(app_name: str, force: bool, json_output: bool):
    """Delete all user selectors for an app.

    \b
    Examples:
        naturo selector clear notepad
    """
    selectors = _load_selectors(app_name)
    if not selectors:
        msg = f"No selectors for '{app_name}'."
        if json_output:
            click.echo(json_error(ErrorCode.SELECTOR_NOT_FOUND, msg))
            sys.exit(1)
        else:
            click.echo(msg)
        sys.exit(1)

    if not force and not json_output:
        click.confirm(f"Delete all {len(selectors)} selectors for '{app_name}'?", abort=True)

    path = _user_selectors_path(app_name)
    if path.exists():
        path.unlink()

    if json_output:
        click.echo(json_dumps({"success": True, "app": app_name, "deleted_count": len(selectors)}))
    else:
        click.echo(f"Cleared {len(selectors)} selectors for '{app_name}'.")


@click.command("export")
@click.argument("app_name")
@click.option("--output", "-o", "output_path", type=click.Path(), help="Output file.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def selector_export(app_name: str, output_path: str | None, json_output: bool):
    """Export selectors for an app to a JSON file.

    \b
    Examples:
        naturo selector export notepad
        naturo selector export notepad -o notepad-selectors.json
    """
    selectors = _load_selectors(app_name)
    builtin = _list_builtin_selectors().get(app_name, {})
    merged = {**builtin, **selectors}

    if not merged:
        msg = f"No selectors for '{app_name}'."
        if json_output:
            click.echo(json_error(ErrorCode.SELECTOR_NOT_FOUND, msg))
            sys.exit(1)
        else:
            click.echo(msg)
        sys.exit(1)

    export_data = {"app": app_name, "selectors": merged}
    content = json_dumps(export_data, indent=2, ensure_ascii=False)

    if output_path:
        _ensure_output_dir(output_path, json_output)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        if json_output:
            click.echo(json_dumps({"success": True, "path": output_path, "count": len(merged)}))
        else:
            click.echo(f"Exported {len(merged)} selectors to {output_path}")
    else:
        click.echo(content)


@click.command("import")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--merge/--replace", default=True,
              help="Merge with existing (default) or replace all.")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def selector_import(file_path: str, merge: bool, json_output: bool):
    """Import selectors from a JSON file.

    \b
    Examples:
        naturo selector import team-selectors.json
        naturo selector import team-selectors.json --replace
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    app_name = data.get("app", Path(file_path).stem)
    imported = data.get("selectors", data)

    if not isinstance(imported, dict):
        msg = "Invalid selector file format."
        if json_output:
            click.echo(json_error(ErrorCode.INVALID_INPUT, msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    if merge:
        existing = _load_selectors(app_name)
        existing.update(imported)
        _save_selectors(app_name, existing)
        count = len(imported)
    else:
        _save_selectors(app_name, imported)
        count = len(imported)

    if json_output:
        click.echo(json_dumps({
            "success": True, "app": app_name,
            "imported": count, "mode": "merge" if merge else "replace",
        }))
    else:
        mode = "merged into" if merge else "replaced"
        click.echo(f"Imported {count} selectors, {mode} '{app_name}'.")


@click.command("test")
@click.argument("app_name")
@click.argument("name")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output JSON.")
def selector_test(app_name: str, name: str, json_output: bool):
    """Test a saved selector against the live UI.

    Resolves the selector and reports whether the element was found.

    \b
    Examples:
        naturo selector test notepad save-btn
    """
    selectors = _load_selectors(app_name)
    builtin = _list_builtin_selectors().get(app_name, {})
    merged = {**builtin, **selectors}

    if name not in merged:
        msg = f"Selector not found: @{app_name}/{name}"
        if json_output:
            click.echo(json_error(ErrorCode.SELECTOR_NOT_FOUND, msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    info = merged[name]
    sel_str = info.get("selector", info) if isinstance(info, dict) else info

    try:
        from naturo.selector import parse
        ast = parse(sel_str)
    except Exception as e:
        if json_output:
            click.echo(json_error(
                ErrorCode.INVALID_INPUT, f"Parse error: {e}",
                extra={"selector": sel_str},
            ))
        else:
            click.echo(f"Parse error: {e}")
        sys.exit(1)

    if json_output:
        click.echo(json_dumps({
            "success": True,
            "name": f"@{app_name}/{name}",
            "selector": sel_str,
            "parsed": True,
            "app": ast.app,
            "nodes": len(ast.nodes),
        }))
    else:
        click.echo(f"@{app_name}/{name}")
        click.echo(f"  Selector: {sel_str}")
        click.echo(f"  Parsed: OK (app={ast.app}, {len(ast.nodes)} nodes)")
        click.echo("  Note: live UI resolution requires a running Windows desktop.")


# Register subcommands
selector.add_command(selector_save, "save")
selector.add_command(selector_load, "load")
selector.add_command(selector_list, "list")
selector.add_command(selector_show, "show")
selector.add_command(selector_delete, "delete")
selector.add_command(selector_clear, "clear")
selector.add_command(selector_export, "export")
selector.add_command(selector_import, "import")
selector.add_command(selector_test, "test")
