#!/usr/bin/env python3
"""AI agent integration patterns for naturo.

Shows three ways to integrate naturo with an AI agent:
1. CLI subprocess loop — simplest, works with any language
2. MCP server — structured tool calls for Claude/OpenClaw
3. AI vision — use see --cascade for visual understanding

Requirements:
    - Windows 10/11 with a desktop session
    - pip install naturo

Usage:
    python agent_demo.py cli      # CLI subprocess demo
    python agent_demo.py mcp      # MCP server usage info
    python agent_demo.py vision   # AI vision demo (requires API key)
"""

import argparse
import json
import subprocess


def run_json(cmd: str) -> dict:
    """Run a naturo CLI command with --json and parse the output."""
    result = subprocess.run(
        ["naturo"] + cmd.split() + ["--json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"success": False, "error": result.stderr.strip()}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"success": False, "raw": result.stdout}


def demo_cli_loop() -> None:
    """Demonstrate the CLI subprocess integration pattern.

    This is the simplest way for an AI agent to use naturo:
    run commands, parse JSON output, decide next action.
    """
    print("=== CLI Subprocess Loop ===\n")

    # Step 1: Observe — what apps are running?
    print("1. Listing running applications...")
    apps = run_json("app list")
    if apps.get("success"):
        app_list = apps.get("apps", [])
        print(f"   Found {len(app_list)} app(s)")
        for app in app_list[:5]:
            print(f"   - {app.get('process_name')}: {app.get('title', '')[:40]}")
    else:
        print("   No apps found (expected on headless systems)")

    # Step 2: See — capture the screen state
    print("\n2. Capturing screen state...")
    screen = run_json("capture --path agent_screen.png")
    if screen.get("success"):
        print("   Screenshot saved: agent_screen.png")
    else:
        print("   Capture failed (expected without a desktop)")

    # Step 3: Act — the agent would decide what to do based on observations
    print("\n3. Agent decision loop:")
    print("   In a real agent, you would:")
    print("   a) Send the screenshot to an LLM for analysis")
    print("   b) Parse the LLM's response for the next action")
    print("   c) Execute the action via naturo CLI")
    print("   d) Repeat until the task is complete")

    print("\nExample agent loop (pseudocode):")
    print("""
    while not task_complete:
        # Observe
        screen = naturo capture --json
        elements = naturo see --app target --json

        # Think (send to LLM)
        action = llm.decide(screen, elements, task)

        # Act
        if action.type == "click":
            naturo click --on {action.target} --app {action.app}
        elif action.type == "type":
            naturo type {action.text}
        elif action.type == "press":
            naturo press {action.key}
    """)


def demo_mcp() -> None:
    """Show MCP server configuration for AI agents."""
    print("=== MCP Server Integration ===\n")
    print("Start the naturo MCP server:\n")
    print("  naturo mcp --transport stdio     # For Claude Desktop / local agents")
    print("  naturo mcp --transport sse        # For remote agents (SSE)")
    print("  naturo mcp --transport http       # For HTTP-based agents\n")

    print("Claude Desktop configuration (claude_desktop_config.json):\n")
    config = {
        "mcpServers": {
            "naturo": {
                "command": "naturo",
                "args": ["mcp", "--transport", "stdio"],
            }
        }
    }
    print(json.dumps(config, indent=2))

    print("\nThe MCP server exposes 50+ tools for:")
    print("  - Screen capture and UI inspection")
    print("  - Mouse clicks, keyboard input")
    print("  - Window and app management")
    print("  - Dialog handling")
    print("  - Wait conditions\n")

    print("See docs/MCP_REFERENCE.md for the full tool reference.")


def demo_vision() -> None:
    """Show AI vision integration with see --cascade."""
    print("=== AI Vision Integration ===\n")
    print("naturo can send screenshots to vision LLMs for analysis:\n")
    print("  # Use Claude for visual understanding")
    print("  naturo see --cascade --ai-provider anthropic --ai-model opus\n")
    print("  # Use OpenAI")
    print("  naturo see --cascade --ai-provider openai --ai-model 4o\n")
    print("  # Use Gemini")
    print("  naturo see --cascade --ai-provider google --ai-model gemini-2.5-pro\n")

    print("Configure API keys:")
    print("  naturo config set-credentials anthropic YOUR_API_KEY")
    print("  naturo config set-credentials openai YOUR_API_KEY")
    print("  naturo config set-credentials google YOUR_API_KEY\n")

    print("The --cascade flag captures a screenshot, sends it to the vision")
    print("model, and returns both the UI element tree and the AI's analysis.")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI agent integration demos")
    parser.add_argument("mode", choices=["cli", "mcp", "vision"],
                        help="Demo mode: cli, mcp, or vision")
    args = parser.parse_args()

    if args.mode == "cli":
        demo_cli_loop()
    elif args.mode == "mcp":
        demo_mcp()
    elif args.mode == "vision":
        demo_vision()


if __name__ == "__main__":
    main()
