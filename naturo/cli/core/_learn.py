"""Learn command — usage guide and tutorials."""
from __future__ import annotations

import click


@click.command()
@click.argument("topic", required=False)
def learn(topic):
    """Show usage guide and tutorials.

    Without TOPIC, shows an overview. With TOPIC, shows detailed help
    including common commands, examples, and tips.
    """
    topics = {
        "capture": {
            "summary": "Capture screenshots and compare UI snapshots.",
            "guide": """\
  Screenshots
  -----------
    naturo capture live --path screenshot.png   Save a screenshot
    naturo capture live --json                  Screenshot with metadata (JSON)
    naturo capture live --app "Notepad"         Capture a specific app window

  Snapshots (element-annotated screenshots)
  -----------------------------------------
    naturo capture live --path snap.png          Capture + store snapshot
    naturo snapshot list                         List saved snapshots
    naturo snapshot clean                        Remove old snapshots

  Watch for Changes
  -----------------
    naturo diff --snapshot ID1 --snapshot ID2    Compare two snapshots
    naturo diff --window "Notepad"              Capture before/after diff

  Tips
  ----
    \u2022 Add --json to any command for structured output
    \u2022 Use --app or --window-title to capture a specific window
    \u2022 Snapshots annotate UI elements for AI-assisted automation""",
        },
        "interaction": {
            "summary": "Click, type, press, hotkey, scroll, drag, move.",
            "guide": """\
  Mouse
  -----
    naturo click --coords 500 300               Click at coordinates (x, y)
    naturo click --coords 500 300 --right        Right-click
    naturo click --coords 500 300 --double       Double-click
    naturo click "Submit"                        Click element by text
    naturo click e5                              Click element by eN ref
    naturo click e5 --paste                      Click then paste clipboard
    naturo drag --from-coords 100 200 --to-coords 400 500
                                                Drag from (100,200) to (400,500)
    naturo move --coords 500 300                Move mouse cursor
    naturo scroll down                          Scroll down
    naturo scroll up --amount 5                 Scroll up 5 clicks

  Keyboard
  --------
    naturo type "Hello, World!"                 Type text
    naturo type --paste "long text"             Paste via clipboard (fast)
    naturo press enter                          Press a single key
    naturo hotkey ctrl+s                        Key combination (Ctrl+S)
    naturo hotkey alt+f4                        Close active window
    naturo hotkey ctrl+shift+esc                Open Task Manager

  Element Finding
  ---------------
    naturo see                                  Show UI tree with eN refs
    naturo see --app notepad                    UI tree for specific app
    naturo find "Submit button"                 Find element by description

  Tips
  ----
    \u2022 Run naturo see first, then click eN refs by number
    \u2022 Use --app to target a specific application
    \u2022 All commands support --json for automation pipelines""",
        },
        "system": {
            "summary": "App, window, dialog, menu management.",
            "guide": """\
  Applications
  ------------
    naturo app list                             List running applications
    naturo app launch notepad                   Launch an application
    naturo app quit notepad                     Close an application
    naturo app switch "Google Chrome"            Switch to an app
    naturo app inspect notepad                  Detect app framework

  Windows
  -------
    naturo list windows                         List all windows
    naturo window focus --title "Untitled"       Focus a window by title
    naturo window minimize --title "Notepad"     Minimize a window
    naturo window maximize --title "Notepad"     Maximize a window
    naturo window close --title "Notepad"        Close a window
    naturo window move --title "Notepad" --x 100 --y 100
    naturo window resize --title "Notepad" --width 800 --height 600

  Dialogs
  -------
    naturo dialog detect                        Detect open dialogs
    naturo dialog accept                        Accept/OK a dialog
    naturo dialog dismiss                       Cancel/dismiss a dialog

  Menus
  -----
    naturo menu-inspect --app notepad           Extract menu structure

  Tips
  ----
    \u2022 naturo list screens shows monitor info
    \u2022 Use --json on any command for structured output
    \u2022 App names are case-insensitive for most commands""",
        },
        "windows": {
            "summary": "Windows-specific: taskbar, tray, virtual desktops.",
            "guide": """\
  Taskbar & System Tray
  ---------------------
    naturo taskbar list                         List taskbar items
    naturo taskbar click "Chrome"               Click a taskbar icon
    naturo tray list                            List system tray icons
    naturo tray click "Volume"                  Click a tray icon

  Virtual Desktops
  ----------------
    naturo desktop list                         List virtual desktops
    naturo desktop switch 2                     Switch to desktop 2
    (Requires pyvda: pip install pyvda)

  Tips
  ----
    \u2022 Use --json for automation-friendly output
    \u2022 App names are case-insensitive""",
        },
        "mcp": {
            "summary": "MCP server for AI agent integration.",
            "guide": """\
  MCP Server (Model Context Protocol)
  ------------------------------------
    naturo mcp start                            Start MCP server (stdio)
    naturo mcp start --transport sse            Start over SSE (HTTP)
    naturo mcp tools                            List all MCP tools
    naturo mcp tools --json                     Tool list as JSON

  Integration with AI Agents
  ---------------------------
    Use naturo as an MCP server in Claude Desktop, Claude Code,
    Cursor, or any MCP-compatible client:

    {
      "mcpServers": {
        "naturo": {
          "command": "naturo",
          "args": ["mcp", "start"]
        }
      }
    }

  Tips
  ----
    \u2022 MCP server exposes all naturo capabilities as tools
    \u2022 Supports stdio, SSE, and streamable-http transports
    \u2022 Use --json output format for reliable LLM parsing""",
        },
    }
    topic_names = list(topics.keys())
    if topic and topic in topics:
        info = topics[topic]
        click.echo(f"\n  {topic}: {info['summary']}\n")
        click.echo(info["guide"])
        click.echo()
    elif topic and topic not in topics:
        click.echo(f"Error: Unknown topic: {topic}", err=True)
        click.echo(f"Available topics: {', '.join(topic_names)}", err=True)
        raise SystemExit(1)
    else:
        click.echo("\nNaturo \u2014 Windows desktop automation engine\n")
        click.echo("Available topics:")
        for name in topic_names:
            click.echo(f"  {name:15s} {topics[name]['summary']}")
        click.echo("\nRun: naturo learn <topic> for details.")
