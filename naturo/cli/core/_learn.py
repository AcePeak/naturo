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
            "summary": "Capture screenshots, video, or watch for changes.",
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

  Recording
  ---------
    naturo record start                         Start screen recording
    naturo record stop                          Stop and save recording
    naturo record list                          List recordings

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
            "summary": "Click, type, press, hotkey, scroll, drag, move, paste.",
            "guide": """\
  Mouse
  -----
    naturo click --coords 500 300               Click at coordinates (x, y)
    naturo click --coords 500 300 --right        Right-click
    naturo click --coords 500 300 --double       Double-click
    naturo click "Submit"                        Click element by text
    naturo drag --from-coords 100 200 --to-coords 400 500
                                                Drag from (100,200) to (400,500)
    naturo move --coords 500 300                Move mouse cursor
    naturo scroll down                          Scroll down
    naturo scroll up --amount 5                 Scroll up 5 clicks

  Keyboard
  --------
    naturo type "Hello, World!"                 Type text
    naturo press enter                          Press a single key
    naturo hotkey ctrl+s                        Key combination (Ctrl+S)
    naturo hotkey alt+f4                        Close active window
    naturo hotkey ctrl+shift+esc                Open Task Manager

  AI-Powered Interaction
  ----------------------
    naturo find "Submit button"                 Find element by description
    naturo see                                  Describe what's on screen

  Tips
  ----
    \u2022 Use naturo find to locate elements without knowing coordinates
    \u2022 Combine with naturo capture to verify actions visually
    \u2022 All commands support --json for automation pipelines""",
        },
        "system": {
            "summary": "App, window, menu, clipboard, dialog, open.",
            "guide": """\
  Applications
  ------------
    naturo app list                             List running applications
    naturo app launch notepad                   Launch an application
    naturo app quit notepad                     Close an application
    naturo app switch "Google Chrome"            Switch to an app
    naturo app find "Visual Studio"             Find apps by name

  Windows
  -------
    naturo list windows                         List all windows
    naturo window focus --title "Untitled"       Focus a window by title
    naturo window minimize --title "Notepad"     Minimize a window
    naturo window maximize --title "Notepad"     Maximize a window
    naturo window close --title "Notepad"        Close a window
    naturo window move --title "Notepad" --x 100 --y 100
    naturo window resize --title "Notepad" --width 800 --height 600

  Clipboard
  ---------
    naturo clipboard get                        Read clipboard content
    naturo clipboard set "copied text"          Write to clipboard

  Dialogs
  -------
    naturo dialog detect                        Detect open dialogs
    naturo dialog accept                        Accept/OK a dialog
    naturo dialog dismiss                       Cancel/dismiss a dialog

  Opening Files & URLs
  --------------------
    naturo open https://example.com             Open URL in browser
    naturo open document.pdf                    Open file with default app

  Tips
  ----
    \u2022 naturo list screens shows monitor info
    \u2022 Use --json on any command for structured output
    \u2022 App names are case-insensitive for most commands""",
        },
        "windows": {
            "summary": "Windows-specific: taskbar, tray, desktop, registry, service.",
            "guide": """\
  Taskbar & System Tray
  ---------------------
    naturo taskbar list                         List taskbar items
    naturo taskbar click "Chrome"               Click a taskbar icon
    naturo tray list                            List system tray icons
    naturo tray click "Volume"                  Click a tray icon

  Registry
  --------
    naturo registry list HKCU\\Software          List registry subkeys
    naturo registry get HKCU\\Software\\MyApp -v Setting
    naturo registry set HKCU\\Software\\MyApp -v Key -d "value"
    naturo registry search HKCU\\Software "keyword"

  Services
  --------
    naturo service list                         List all services
    naturo service list --state running         Only running services
    naturo service status Spooler               Get service details
    naturo service start Spooler                Start a service
    naturo service stop Spooler                 Stop a service
    naturo service restart Spooler              Restart a service

  Virtual Desktops
  ----------------
    naturo desktop list                         List virtual desktops
    naturo desktop switch 2                     Switch to desktop 2
    (Requires pyvda: pip install pyvda)

  Tips
  ----
    \u2022 Registry operations support HKCU, HKLM, HKCR, HKU, HKCC
    \u2022 Service commands require appropriate permissions
    \u2022 Use --json for automation-friendly output""",
        },
        "extensions": {
            "summary": "Enterprise: excel, java, sap automation.",
            "guide": """\
  Excel (COM Automation)
  ----------------------
    naturo excel open report.xlsx               Open a workbook
    naturo excel read report.xlsx A1             Read a cell
    naturo excel read report.xlsx "A1:D10"       Read a range
    naturo excel write report.xlsx B2 "Hello"    Write to a cell
    naturo excel list-sheets report.xlsx         List sheets
    naturo excel run-macro data.xlsm "MyMacro"   Run a VBA macro
    naturo excel info report.xlsx                Used range info
    (Requires Microsoft Excel and pywin32)

  Electron/Chrome (Removed in v0.2.0)
  ------------------------------------
    Use Playwright or browser automation tools for Electron/Chrome.
    Backend modules retained for Unified App Model internal use.

  Java Access Bridge (planned)
  ----------------------------
    Java UI automation via JAB is on the roadmap.
    Will enable inspection and control of Swing/AWT applications.

  SAP GUI Scripting (planned)
  ---------------------------
    SAP GUI automation via scripting API is on the roadmap.
    Will enable transaction execution and form interaction.

  Tips
  ----
    \u2022 Electron automation unlocks DOM access for desktop apps
    \u2022 Excel operations preserve formatting and formulas
    \u2022 Use --json for all commands for pipeline integration""",
        },
        "ai": {
            "summary": "AI agent and MCP server integration.",
            "guide": """\
  MCP Server (Model Context Protocol)
  ------------------------------------
    naturo mcp start                            Start MCP server (stdio)
    naturo mcp tools                            List all MCP tools
    naturo mcp tools --json                     Tool list as JSON

  AI Agent
  --------
    naturo agent "Open Notepad and type hello"
    naturo agent --model gpt-4o "Fill in the form"
    (Provides autonomous UI automation via AI vision)

  AI-Powered Commands
  -------------------
    naturo see                                  Describe current screen
    naturo find "Login button"                  Find UI element by description
    naturo describe                             Detailed screen analysis

  Integration with LLM Frameworks
  --------------------------------
    Use naturo as an MCP server in Claude Desktop, Cursor, or any
    MCP-compatible client:

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
    \u2022 82 tools covering capture, interaction, system, and more
    \u2022 Use --json output format for reliable LLM parsing
    \u2022 AI find works best with descriptive element names""",
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
