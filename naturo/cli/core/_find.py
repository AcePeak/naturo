"""Find command — search for UI elements matching a query."""
from __future__ import annotations

import json as json_module
from typing import Any

import click

import naturo.cli.core._common as _common


@click.command("find")
@click.argument("query", required=False, default=None)
@click.option("--query", "-q", "query_opt", default=None,
              help="Search query (alternative to positional arg; survives shell glob expansion)")
@click.option("--all", "find_all", is_flag=True,
              help="Find all elements (equivalent to query \"*\"). Safe from shell glob expansion.")
@click.option("--role", help="Filter by element role (e.g., Button, Edit)")
@click.option("--actionable", is_flag=True, help="Only show actionable elements")
@click.option("--depth", "-d", type=int, default=20, help="Maximum tree depth (default 20; use lower values for performance)")
@click.option("--limit", type=int, default=50, help="Maximum number of results")
@click.option("--ai", is_flag=True, help="Use AI vision to find element by natural language")
@click.option("--screenshot", type=click.Path(), default=None,
              help="Use existing screenshot (for --ai mode)")
@click.option("--app", default=None, help="Target app window")
@click.option("--app-id", "app_id", default=None,
              help='Stable app/window ID from "naturo app list" output (e.g. a1)')
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.option(
    "--backend", "--method", "-b", "-m",
    type=click.Choice(["uia", "msaa", "ia2", "jab", "cdp", "win32", "win32hybrid", "auto", "hybrid"]),
    default="auto",
    help="Accessibility backend / interaction method: auto (default: tries all), uia, msaa (legacy apps), ia2 (Firefox/Thunderbird), jab (Java/Swing), cdp (Chrome/Electron web content), win32 (VB6/ActiveX), hybrid (per-node backend selection)",
)
@click.option("--provider", "ai_provider",
              type=click.Choice(["auto", "anthropic", "openai", "ollama"]),
              default="auto", help="AI provider for --ai mode (auto, anthropic, openai, ollama)")
@click.option("--model", "ai_model", default=None, envvar="NATURO_AI_MODEL",
              help="AI model name override (e.g. claude-sonnet-4-20250514, gpt-4o)")
@click.option("--api-key", "ai_api_key", default=None,
              help="AI provider API key (overrides env var)")
def find_cmd(query: str | None, query_opt: str | None, find_all: bool, role: str | None,
             actionable: bool, depth: int, limit: int, ai: bool,
             ai_provider: str, ai_model: str | None, ai_api_key: str | None,
             screenshot: str | None, app: str | None, app_id: str | None,
             json_output: bool, backend: str) -> None:
    """Search for UI elements matching a query.

    Supports fuzzy name matching, role filtering, and combined queries.
    Use --ai for natural language element finding powered by AI vision.
    Use --backend msaa for legacy applications that lack UIA support.
    Use --backend ia2 for IA2-enabled apps (Firefox, Thunderbird, LibreOffice).

    \b
    Examples:
        naturo find "Save"                      # fuzzy name search
        naturo find "Button:Save"               # role + name
        naturo find "role:Edit"                  # by role only
        naturo find --all --actionable           # all actionable elements
        naturo find --all --role Button          # all buttons
        naturo find "the save button" --ai       # AI vision search
        naturo find "Save" --app "Notepad"              # search in specific app
        naturo find "search field" --ai --app "Chrome"  # AI + specific app
        naturo find "OK" --backend msaa          # MSAA for legacy apps
    """
    # (#593) Resolve --app-id to hwnd before any other logic
    hwnd = None
    if app_id is not None:
        from naturo.app_ids import get_app_id_map
        id_map = get_app_id_map()
        entry = id_map.resolve(app_id)
        if entry is None:
            msg = f'App ID "{app_id}" not found or expired. Run "naturo app list" to refresh.'
            if json_output:
                click.echo(_common._json_error_str("APP_ID_NOT_FOUND", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)
        hwnd = entry.handle

    # Resolve query: --all flag → wildcard, --query option → override positional
    if find_all:
        query = "*"
    elif query_opt is not None:
        query = query_opt
    # else: query is the positional arg (may be None)

    if query is None:
        # When --actionable or --role is set, treat missing query as wildcard
        if actionable or role:
            query = "*"
        else:
            msg = "Missing argument 'QUERY'. Provide as positional arg or --query/-q option."
            if json_output:
                click.echo(_common._json_error_str("INVALID_INPUT", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)

    # Auto-enable AI mode when --provider or --model is explicitly set (#287)
    if not ai and (ai_provider != "auto" or ai_model is not None or ai_api_key is not None):
        ai = True

    # AI vision mode — natural language element finding
    if ai:
        _find_with_ai(query, ai_provider, screenshot, app, json_output,
                      model=ai_model, api_key=ai_api_key)
        return

    # Validate --depth range (find supports deeper traversal than see)
    if depth < 1 or depth > 50:
        msg = f"--depth must be between 1 and 50, got {depth}"
        if json_output:
            click.echo(_common._json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    if not _common._platform_supports_gui():
        msg = _common._platform_error_msg("UI inspection")
        if json_output:
            click.echo(_common._json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    try:
        be = _common._get_backend(json_output)
        tree = be.get_element_tree(app=app, hwnd=hwnd, depth=depth, backend=backend)
        if tree is None:
            msg = "No window found or UI tree is empty."
            if json_output:
                click.echo(_common._json_error_str("WINDOW_NOT_FOUND", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)

        from naturo.search import search_elements
        # Convert backend ElementInfo tree to bridge ElementInfo for search
        from naturo.bridge import ElementInfo as BridgeElementInfo

        def to_bridge(el: Any) -> BridgeElementInfo:
            """Convert backend ElementInfo to bridge ElementInfo."""
            return BridgeElementInfo(
                id=el.id,
                role=el.role,
                name=el.name,
                value=el.value,
                x=el.x,
                y=el.y,
                width=el.width,
                height=el.height,
                children=[to_bridge(c) for c in el.children],
                parent_id=el.properties.get("parent_id"),
                keyboard_shortcut=el.properties.get("keyboard_shortcut"),
            )

        bridge_tree = to_bridge(tree)
        results = search_elements(
            bridge_tree,
            query,
            role_filter=role,
            actionable_only=actionable,
            max_results=limit,
        )

        # (#369) Store snapshot with refs so users can `naturo click e3` after find
        from naturo.snapshot import get_snapshot_manager
        from naturo.models.snapshot import UIElement

        mgr = get_snapshot_manager()
        snapshot_id = mgr.create_snapshot()

        # (#456) Use stable hash-based refs (same as `see` command)
        from naturo.refs import assign_stable_refs

        _element_id_to_ref: dict[int, str] = {}
        ui_map, ref_map = assign_stable_refs(
            bridge_tree, UIElement, element_obj_to_ref=_element_id_to_ref,
        )
        mgr.store_detection_result(snapshot_id, ui_map)
        mgr.store_ref_map(snapshot_id, ref_map)

        if json_output:
            data = [
                {
                    "ref": _element_id_to_ref.get(id(r.element), r.element.id),
                    "id": r.element.id,
                    "role": r.element.role,
                    "name": r.element.name,
                    "value": r.element.value,
                    "x": r.element.x,
                    "y": r.element.y,
                    "width": r.element.width,
                    "height": r.element.height,
                    "breadcrumb": r.breadcrumb_str,
                    "keyboard_shortcut": r.element.keyboard_shortcut,
                }
                for r in results
            ]
            click.echo(json_module.dumps({
                "success": True,
                "elements": data,
                "count": len(data),
                "snapshot_id": snapshot_id,
            }, indent=2))
        else:
            if not results:
                click.echo(f"No elements found matching: {query}")
                return

            for i, r in enumerate(results):
                el = r.element
                ref = _element_id_to_ref.get(id(el), "?")
                name_str = f' "{el.name}"' if el.name else ""
                pos_str = f"({el.x},{el.y} {el.width}x{el.height})"
                shortcut = f" [{el.keyboard_shortcut}]" if el.keyboard_shortcut else ""
                click.echo(f"  {ref}. [{el.role}]{name_str} {pos_str}{shortcut}")
                click.echo(f"     {r.breadcrumb_str}")

            click.echo(f"\n{len(results)} element(s) found.")
            click.echo(f"Snapshot: {snapshot_id}")
            click.echo("Tip: use 'naturo click e<N>' to interact with a found element.")

    except Exception as e:
        if json_output:
            click.echo(_common._json_error_str("UNKNOWN_ERROR", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


def _find_with_ai(
    query,
    provider_name,
    screenshot,
    app,
    json_output,
    *,
    model: str | None = None,
    api_key: str | None = None,
):
    """AI-powered element finding via naturo find --ai.

    Args:
        query: Natural language description of the element.
        provider_name: AI provider name.
        screenshot: Optional screenshot path.
        app: Optional target application window.
        json_output: Whether to output JSON.
        model: Optional AI model name override (from --model).
        api_key: Optional API key override (from --api-key).
    """
    try:
        from naturo.ai_find import ai_find_element
    except ImportError as e:
        msg = f"AI find dependencies not available: {e}"
        if json_output:
            click.echo(_common._json_error_str("MISSING_DEPENDENCY", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    # Validate screenshot path
    if screenshot and not __import__("os").path.exists(screenshot):
        msg = f"Screenshot file not found: {screenshot}"
        if json_output:
            click.echo(_common._json_error_str("FILE_NOT_FOUND", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    try:
        result = ai_find_element(
            query,
            provider_name=provider_name,
            window_title=app,
            screenshot_path=screenshot,
            model=model,
            api_key=api_key,
        )
    except Exception as e:
        msg = str(e)
        code = "AI_FIND_FAILED"
        if "unavailable" in msg.lower() or "api key" in msg.lower():
            code = "AI_PROVIDER_UNAVAILABLE"
        elif "capture" in msg.lower():
            code = "CAPTURE_FAILED"
        if json_output:
            click.echo(json_module.dumps({"success": False, "error": {"code": code, "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    if json_output:
        output = {
            "success": result.found,
            "description": result.description,
            "confidence": result.confidence,
            "method": result.method,
            "model": result.model,
            "tokens_used": result.tokens_used,
        }
        if result.ai_bounds:
            output["ai_bounds"] = result.ai_bounds
        if result.element:
            output["element"] = result.element
        if not result.found:
            output["error"] = {
                "code": "ELEMENT_NOT_FOUND",
                "message": f"AI could not locate: {query}",
            }
        click.echo(json_module.dumps(output, indent=2))
    else:
        if not result.found:
            click.echo(f"Element not found: {query}")
            if result.description:
                click.echo(f"  AI says: {result.description}")
            raise SystemExit(1)

        click.echo(f"Found: {result.description}")
        click.echo(f"  Confidence: {result.confidence:.0%}")
        click.echo(f"  Method: {result.method}")
        if result.ai_bounds:
            b = result.ai_bounds
            click.echo(f"  AI bounds: ({b.get('x', '?')}, {b.get('y', '?')}) "
                        f"{b.get('width', '?')}x{b.get('height', '?')}")
        if result.element:
            el = result.element
            click.echo(f"  UIA match: [{el.get('role', '')}] \"{el.get('name', '')}\"")
            eb = el.get("bounds", {})
            click.echo(f"  UIA bounds: ({eb.get('x', '?')}, {eb.get('y', '?')}) "
                        f"{eb.get('width', '?')}x{eb.get('height', '?')}")
            click.echo(f"  Match distance: {el.get('match_distance', '?')} px")
        click.echo(f"  [{result.model}, {result.tokens_used} tokens]", err=True)

    if not result.found:
        raise SystemExit(1)
