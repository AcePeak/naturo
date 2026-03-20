"""AI commands: agent, describe, mcp."""
import click
import json
import sys
from typing import Optional

# ── agent ───────────────────────────────────────


@click.command()
@click.argument("instruction")
@click.option("--app", help="Target application window")
@click.option("--window-title", help="Target window title pattern")
@click.option("--provider", type=click.Choice(["anthropic", "openai"]),
              default="anthropic", help="AI provider (default: anthropic)")
@click.option("--model", default=None, help="Model override (e.g., claude-sonnet-4-20250514, gpt-4o)")
@click.option("--max-steps", type=int, default=10, help="Max automation steps (default: 10)")
@click.option("--dry-run", is_flag=True, help="Plan actions but don't execute them")
@click.option("--verbose", "-v", is_flag=True, help="Show step-by-step reasoning")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def agent(instruction, app, window_title, provider, model, max_steps, dry_run, verbose, json_output):
    """Execute a natural language automation instruction.

    Uses AI vision + UI automation to complete multi-step tasks described
    in plain language. The agent captures screenshots, reasons about the
    UI, and executes actions in a loop until the task is complete.

    Requires an AI provider API key (ANTHROPIC_API_KEY or OPENAI_API_KEY).

    \b
    Examples:
        naturo agent "Open Notepad and type Hello World"
        naturo agent "Take a screenshot of the calculator" --app calc
        naturo agent "Save the current document" --max-steps 5
        naturo agent "Close all Notepad windows" --verbose
        naturo agent "List all open windows" --dry-run
    """
    # Validate max_steps
    if max_steps < 1:
        msg = f"--max-steps must be >= 1, got {max_steps}"
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "INVALID_INPUT", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    if max_steps > 50:
        msg = f"--max-steps must be <= 50, got {max_steps}"
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "INVALID_INPUT", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    # Get agent provider
    try:
        agent_provider = _get_agent_provider(provider, model)
    except Exception as e:
        msg = str(e)
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "AI_PROVIDER_UNAVAILABLE", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    # Run the agent
    try:
        from naturo.agent import run_agent

        result = run_agent(
            instruction=instruction,
            provider=agent_provider,
            max_steps=max_steps,
            window_title=window_title or app,
            dry_run=dry_run,
        )
    except Exception as e:
        msg = str(e)
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "AGENT_ERROR", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    # Output results
    if json_output:
        output = {
            "success": result.success,
            "instruction": result.instruction,
            "steps": result.step_count,
            "total_time": round(result.total_time, 2),
            "summary": result.summary,
        }
        if result.error:
            output["error"] = {"code": "AGENT_INCOMPLETE", "message": result.error}
        if verbose:
            output["step_details"] = [
                {
                    "step": s.step_number,
                    "reasoning": s.reasoning,
                    "tools": [{"name": tc.name, "args": tc.arguments} for tc in s.tool_calls],
                    "results": [
                        {"name": tr.name, "success": tr.success, "result": tr.result}
                        for tr in s.tool_results
                    ],
                }
                for s in result.steps
            ]
        click.echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        if verbose:
            for s in result.steps:
                click.echo(f"\n── Step {s.step_number} ──")
                if s.reasoning:
                    click.echo(f"Reasoning: {s.reasoning}")
                for tc in s.tool_calls:
                    args_str = ", ".join(f"{k}={v!r}" for k, v in tc.arguments.items())
                    click.echo(f"  → {tc.name}({args_str})")
                for tr in s.tool_results:
                    status = "✅" if tr.success else "❌"
                    click.echo(f"  {status} {tr.name}: {tr.result}")
            click.echo("")

        if result.success:
            click.echo(f"✅ {result.summary}")
        else:
            click.echo(f"❌ {result.error or 'Agent failed'}", err=True)

        click.echo(f"[{result.step_count} steps, {result.total_time:.1f}s]", err=True)

    if not result.success:
        sys.exit(1)


def _get_agent_provider(provider_name: str, model: Optional[str] = None):
    """Get an agent provider instance.

    Args:
        provider_name: Provider name ('anthropic' or 'openai').
        model: Optional model override.

    Returns:
        Agent provider instance implementing AIProvider protocol.

    Raises:
        AIProviderUnavailableError: Provider not available.
    """
    from naturo.errors import AIProviderUnavailableError

    _AGENT_PROVIDERS = {
        "anthropic": {
            "class_path": "naturo.providers.anthropic_agent",
            "class_name": "AnthropicAgentProvider",
            "env_key": "ANTHROPIC_API_KEY",
        },
        "openai": {
            "class_path": "naturo.providers.openai_agent",
            "class_name": "OpenAIAgentProvider",
            "env_key": "OPENAI_API_KEY",
        },
    }

    info = _AGENT_PROVIDERS.get(provider_name)
    if info is None:
        available = ", ".join(sorted(_AGENT_PROVIDERS.keys()))
        raise AIProviderUnavailableError(
            provider=provider_name,
            suggested_action=f"Available agent providers: {available}",
        )

    import importlib
    mod = importlib.import_module(info["class_path"])
    cls = getattr(mod, info["class_name"])

    kwargs = {}
    if model:
        kwargs["model"] = model
    prov = cls(**kwargs)

    if not prov.is_available:
        raise AIProviderUnavailableError(
            provider=provider_name,
            suggested_action=f"Set {info['env_key']} environment variable",
        )
    return prov


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
    # Validate max_tokens boundary
    if max_tokens < 1:
        msg = f"--max-tokens must be >= 1, got {max_tokens}"
        if json_output:
            click.echo(json.dumps({"success": False, "error": {"code": "INVALID_INPUT", "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

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
