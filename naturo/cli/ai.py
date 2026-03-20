"""AI commands: agent, describe, mcp."""
import click
import json
import sys

# ── agent ───────────────────────────────────────


@click.command(hidden=True)
@click.argument("instruction")
@click.option("--app", help="Target application")
@click.option("--window-title", help="Target window")
@click.option("--model", default="anthropic", help="AI provider (anthropic/openai)")
@click.option("--max-steps", type=int, default=10, help="Max automation steps")
@click.option("--dry-run", is_flag=True, help="Plan but don't execute")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def agent(instruction, app, window_title, model, max_steps, dry_run, json_output):
    """Execute a natural language automation instruction.

    Uses AI vision + UI automation to complete tasks described in plain language.
    Requires an AI provider API key (ANTHROPIC_API_KEY or OPENAI_API_KEY).

    Example: naturo agent "Open Notepad and type hello world"
    """
    try:
        from naturo.agent import run_agent
    except ImportError as e:
        msg = f"Agent dependencies not available: {e}"
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "MISSING_DEPENDENCY", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    # For now, agent command requires AI provider integration (Phase 4 ongoing)
    # The framework is ready, provider implementations are next
    msg = "Agent command requires AI provider integration (coming soon). Use 'naturo mcp start' for MCP-based AI integration."
    if json_output:
        click.echo(json.dumps({"success": False, "error": {"code": "NOT_READY", "message": msg}}))
    else:
        click.echo(f"Error: {msg}", err=True)
    sys.exit(1)


# ── describe ────────────────────────────────────


@click.command()
@click.option("--app", help="Target application window")
@click.option("--window-title", help="Target window title pattern")
@click.option("--screenshot", type=click.Path(), default=None,
              help="Use an existing screenshot instead of capturing")
@click.option("--provider", type=click.Choice(["auto", "anthropic", "openai", "ollama"]),
              default="auto", help="AI provider (default: auto-detect)")
@click.option("--model", default=None, help="Model override (e.g., gpt-4o, claude-sonnet-4-20250514)")
@click.option("--prompt", default=None, help="Custom analysis prompt")
@click.option("--max-tokens", type=int, default=1024, help="Max response tokens")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def describe(app, window_title, screenshot, provider, model, prompt, max_tokens, json_output):
    """Describe the screen or a window using AI vision.

    Captures a screenshot and sends it to an AI model for analysis.
    Returns a natural language description of what's visible.

    Requires an AI provider API key:
      - Anthropic: ANTHROPIC_API_KEY
      - OpenAI: OPENAI_API_KEY
      - Ollama: local server (no key needed)

    Examples:
        naturo describe                           # Describe full screen
        naturo describe --app "Notepad"           # Describe Notepad window
        naturo describe --screenshot capture.png  # Analyze existing image
        naturo describe --provider openai         # Use OpenAI specifically
    """
    try:
        from naturo.vision import describe_screen
        from naturo.providers.base import get_vision_provider
    except ImportError as e:
        msg = f"Vision dependencies not available: {e}"
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "MISSING_DEPENDENCY", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    # Validate screenshot path before provider init (avoid misleading errors)
    if screenshot and not __import__("os").path.exists(screenshot):
        msg = f"Screenshot file not found: {screenshot}"
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "FILE_NOT_FOUND", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    # Build provider kwargs
    provider_kwargs = {}
    if model:
        provider_kwargs["model"] = model

    try:
        vision_provider = get_vision_provider(provider, **provider_kwargs)
    except Exception as e:
        msg = str(e)
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "AI_PROVIDER_UNAVAILABLE", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    try:
        result = describe_screen(
            provider=vision_provider,
            window_title=window_title or app,
            screenshot_path=screenshot,
            prompt=prompt,
            max_tokens=max_tokens,
        )
    except Exception as e:
        msg = str(e)
        code = "AI_ANALYSIS_FAILED"
        if "unavailable" in msg.lower() or "api key" in msg.lower():
            code = "AI_PROVIDER_UNAVAILABLE"
        elif "capture" in msg.lower():
            code = "CAPTURE_FAILED"
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": code, "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    if json_output:
        output = {
            "success": True,
            "description": result.description,
            "model": result.model,
            "tokens_used": result.tokens_used,
        }
        if result.elements:
            output["elements"] = result.elements
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(result.description)
        if result.model:
            click.echo(f"\n[Model: {result.model}, Tokens: {result.tokens_used}]", err=True)


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
    except ImportError:
        msg = "MCP dependencies not installed. Run: pip install naturo[mcp]"
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "MISSING_DEPENDENCY", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    try:
        # Suppress uvicorn/server logs in JSON mode to keep stdout clean
        if json_output:
            import logging as _logging
            for _logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "mcp"):
                _logging.getLogger(_logger_name).setLevel(_logging.CRITICAL)
        run_server(transport=transport, host=host, port=port)
    except OSError as e:
        # Port already in use or bind failure
        msg = str(e)
        if "already in use" in msg.lower() or "address already in use" in msg.lower() or getattr(e, 'errno', 0) in (10048, 98):
            msg = f"Port {port} already in use"
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "SERVER_ERROR", "message": msg}}))
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
        if not json_output:
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
