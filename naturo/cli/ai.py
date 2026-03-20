"""AI commands: agent, mcp."""
import click
import json
import sys

# ── agent ───────────────────────────────────────


@click.command(hidden=True)
@click.argument("instruction")
@click.option("--app", help="Target application")
@click.option("--window-title", help="Target window")
@click.option("--model", help="AI model to use")
@click.option("--max-steps", type=int, default=10, help="Max automation steps")
@click.option("--dry-run", is_flag=True, help="Plan but don't execute")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def agent(instruction, app, window_title, model, max_steps, dry_run, json_output):
    """Execute a natural language automation instruction.

    Uses AI vision + UI automation to complete tasks described in plain language.

    Example: naturo agent "Open Chrome and search for weather"
    """
    click.echo("Not implemented yet — coming in Phase 4", err=True)
    sys.exit(1)


# ── mcp ─────────────────────────────────────────


@click.group()
def mcp():
    """MCP (Model Context Protocol) server for AI agent integration."""
    pass


@mcp.command()
@click.option("--transport", type=click.Choice(["stdio", "sse", "streamable-http"]),
              default="stdio", help="Transport protocol (default: stdio)")
@click.option("--host", default="localhost", help="Bind host (for sse/http)")
@click.option("--port", type=int, default=3100, help="Bind port (for sse/http)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def start(transport, host, port, json_output):
    """Start the MCP server.

    Default transport is stdio (for integration with AI agents like Claude, OpenClaw).

    Examples:
        naturo mcp start                    # stdio transport
        naturo mcp start --transport sse    # SSE transport on port 3100
    """
    try:
        from naturo.mcp_server import run_server
        run_server(transport=transport, host=host, port=port)
    except ImportError as e:
        msg = f"MCP dependencies not installed. Run: pip install naturo[mcp]"
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "MISSING_DEPENDENCY", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "SERVER_ERROR", "message": str(e)}}))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@mcp.command()
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def install(json_output):
    """Install MCP server dependencies.

    Installs the required 'mcp' package for running the MCP server.

    Example: naturo mcp install
    """
    import subprocess
    try:
        click.echo("Installing MCP dependencies...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "mcp>=1.0"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            if json_output:
                click.echo(json.dumps({"success": True, "message": "MCP dependencies installed successfully"}))
            else:
                click.echo("✅ MCP dependencies installed. Run 'naturo mcp start' to launch the server.")
        else:
            msg = result.stderr.strip() or result.stdout.strip() or "pip install failed"
            if json_output:
                click.echo(json.dumps({"success": False, "error": {"code": "INSTALL_FAILED", "message": msg}}))
            else:
                click.echo(f"Error: {msg}", err=True)
            sys.exit(1)
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "INSTALL_FAILED", "message": str(e)}}))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@mcp.command()
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def tools(json_output):
    """List available MCP tools.

    Shows all tools that the MCP server exposes to AI agents.
    """
    try:
        from naturo.mcp_server import create_server
        server = create_server()
        tool_list = []
        for tool_obj in server._tool_manager.list_tools():
            tool_list.append({
                "name": tool_obj.name,
                "description": tool_obj.description or "",
            })

        if json_output:
            click.echo(json.dumps({"success": True, "tools": tool_list}, indent=2))
        else:
            click.echo(f"Naturo MCP Server — {len(tool_list)} tools available:\n")
            for t in tool_list:
                desc = t["description"].split("\n")[0] if t["description"] else ""
                click.echo(f"  {t['name']:20s}  {desc}")
    except ImportError:
        msg = "MCP dependencies not installed. Run: pip install naturo[mcp]"
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "MISSING_DEPENDENCY", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
