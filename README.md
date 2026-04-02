# Naturo — Desktop Automation Engine (Eyes + Hands for AI Agents)

> See, click, type, capture. Desktop automation core only.

[![Build & Test](https://github.com/AcePeak/naturo/actions/workflows/build.yml/badge.svg)](https://github.com/AcePeak/naturo/actions/workflows/build.yml)
[![codecov](https://codecov.io/gh/AcePeak/naturo/graph/badge.svg)](https://codecov.io/gh/AcePeak/naturo)
[![PyPI version](https://img.shields.io/pypi/v/naturo)](https://pypi.org/project/naturo/)
[![Downloads](https://img.shields.io/pypi/dm/naturo)](https://pypi.org/project/naturo/)
[![Python 3.9+](https://img.shields.io/pypi/pyversions/naturo)](https://pypi.org/project/naturo/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue)](https://github.com/AcePeak/naturo#platform-support)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

## What You Get

- 🖥️ **Screen Capture** — Screenshot any window or monitor
- 🌳 **UI Tree Inspection** — Walk the accessibility tree (UIA / MSAA / IAccessible2 / Java Access Bridge)
- 🔍 **Element Finding** — CSS-like selectors + fuzzy search for UI elements
- 🖱️ **Click & Type** — Hardware-level input simulation
- ⌨️ **Key Combos** — Send any keystroke or shortcut
- 🎮 **Hardware Keyboard** — Scan-code input bypasses virtual-key detection (games, anti-cheat)
- 📸 **Annotated Screenshots** — AI-ready screenshots with numbered bounding boxes
- 📋 **Menu Traversal** — Extract app menu structures with shortcuts
- 🪟 **Window Management** — Focus, close, minimize, maximize, move, resize windows
- 📦 **App Control** — Launch, quit, switch, hide/unhide applications
- 💬 **Dialog Handling** — Detect and interact with system dialogs (message boxes, file pickers)
- 📌 **Taskbar & Tray** — List and click taskbar items and system tray icons
- 🖥️ **Multi-Monitor** — Enumerate monitors, capture specific screens, DPI-aware coordinates
- 🗂️ **Virtual Desktops** — List, switch, create, close desktops and move windows between them
- 🍎 **macOS Support** — Coming soon (native implementation in development)
- 🎬 **Recording & Playback** — Record user actions, replay them, export to Python/Bash scripts
- 🏷️ **Selector Management** — Save, share, and reuse UI element selectors across sessions
- 🔬 **Cascade Recognition** — UIA + CDP + AI Vision multi-source fusion for Electron/CEF apps where single-source fails
- 🤖 **AI-Ready** — JSON output, agent-friendly CLI, MCP server

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| **Windows 10/11** | ✅ Full support | Primary platform. All features available. |
| **Windows 7 SP1+** | ⚠️ Best-effort | Basic features only, no UIAutomation v3. |
| **macOS 13+** | 🚧 Coming soon | Native support is under active development. |
| **Linux** | 🚧 Coming soon | Backend is a placeholder. Not usable yet. |
| **Python** | 3.9+ | Required for all platforms. |

> **Why Windows 10+?** UIAutomation v2/v3 APIs (caching, virtualized controls) require Windows 8+. Windows 7 has been out of support since January 2020. Most enterprise customers have migrated to Windows 10/11.

## Install

```bash
pip install naturo
```

## MCP Server Setup

Naturo includes a built-in [MCP](https://modelcontextprotocol.io/) server with 60+ tools for AI agent integration.

### Claude Desktop / Claude Code

Add to your Claude configuration file (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "naturo": {
      "command": "naturo",
      "args": ["mcp", "start"]
    }
  }
}
```

> **Config file location:**
> - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
> - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

### Other AI Agents (SSE / HTTP)

For agents that connect over HTTP instead of stdio:

```bash
# SSE transport (Server-Sent Events)
naturo mcp start --transport sse --port 3100

# Streamable HTTP transport
naturo mcp start --transport streamable-http --port 3100
```

### Verify Setup

```bash
# List all 60+ MCP tools
naturo mcp tools

# Install MCP dependencies if needed
naturo mcp install
```

## Quick Start

```bash
# Check version
naturo --version

# Capture a screenshot
naturo capture --path screen.png

# List open windows
naturo list windows

# Inspect UI tree
naturo see --window "Notepad" --depth 5

# Click an element
naturo click "Button:Save"

# Type text
naturo type "Hello, World!"

# Type with hardware scan codes (bypass anti-cheat detection)
naturo type "Hello" --input-mode hardware

# Press key combo
naturo press ctrl+s

# Find element
naturo find "Edit:filename"

# App management
naturo app launch "notepad"
naturo app focus "notepad"
naturo app quit "chrome" --force
naturo app minimize "notepad"
naturo app restore "notepad"
naturo app inspect "notepad"             # Probe frameworks (UIA, CDP, MSAA...)
naturo app relaunch "notepad"

# Dialog handling
naturo dialog detect                       # Detect active dialogs
naturo dialog accept                       # Click OK/Yes
naturo dialog dismiss                      # Click Cancel/No
naturo dialog type "hello.txt" --accept    # Type filename then OK

# Taskbar & tray
naturo taskbar list                        # List taskbar items
naturo taskbar click "Chrome"              # Click taskbar button
naturo tray list                           # List tray icons
naturo tray click "Volume"                 # Left-click tray icon
naturo tray click "Wi-Fi" --right          # Right-click for menu

# Virtual desktops (Windows 10/11)
naturo desktop list                        # List virtual desktops
naturo desktop switch 1                    # Switch to desktop 1
naturo desktop create --name "Work"        # Create named desktop
naturo desktop close                       # Close current desktop
naturo desktop move-window 1 --app "Notepad"  # Move window to desktop 1

# Type Windows paths literally (--raw disables escape interpretation)
naturo type "C:\Users\test\report.txt" --raw --app notepad

# Paste text via clipboard (fast for large content)
naturo type "large content" --paste        # Set clipboard → Ctrl+V → restore
naturo type --paste --file data.txt        # Read file → paste

# Read element values
naturo get e47                             # Read text/value by element ref
naturo get --aid txtSearch                 # Read by AutomationId
naturo get --role Edit --name Search       # Read by role + name
naturo get --role Button --app notepad --all -j  # All buttons (JSON)

# Write element values
naturo set e47 "hello world"               # Set text field value
naturo set --aid txtSearch "query"          # Set by AutomationId
naturo set e12 --toggle                    # Toggle a checkbox
naturo set e8 --select                     # Select a list/radio item
naturo set e5 --expand                     # Expand a combo box

# Highlight UI elements
naturo highlight --app notepad             # Show actionable elements
naturo highlight --app notepad --all       # Show all elements
naturo highlight e11 --app notepad         # Highlight specific ref
naturo highlight --app notepad -A out.png  # Save annotated screenshot
```

## Cascade Recognition

Most desktop automation tools rely on a single accessibility API (UIA) — when
it fails (Electron apps, custom-rendered UI), you're stuck. Naturo cascades
through multiple recognition sources automatically:

```
UIA → CDP → AI Vision
 ↓      ↓       ↓
Win32  Chrome   Claude/GPT
native DevTools  screenshot
```

```bash
# Progressive multi-source recognition
naturo see --app feishu --cascade --fill-gaps --stats

# Result: UIA finds 700+ elements, AI Vision adds 130+ that UIA missed
#   uia      705 elements    6s   [ok]
#   cdp        0 elements   15s   [skipped]
#   vision   133 elements   72s   [ok]

# Click an AI-discovered element by ref
naturo click e805 --app feishu    # "视频会议" (Video Meeting) found by AI Vision
```

**How it works:**
- **UIA/MSAA** finds native Win32/WPF/UWP controls (fastest, most accurate)
- **CDP** reaches into Electron/Chrome web content via DevTools Protocol
- **AI Vision** screenshots the window and asks Claude/GPT to enumerate every visible element — catches anything the other sources miss
- **IoU dedup** prevents duplicates: if UIA already found an element, AI Vision skips it
- **Tree merge** attaches AI-discovered elements to the correct UIA parent container

Requires `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` for AI Vision. Set `NATURO_AI_MODEL` to choose the model (default: `claude-sonnet-4-20250514`).

## CLI Commands

### See (observe the desktop)

| Command | Description | Since |
|---------|-------------|-------|
| `capture` | Screenshot screen/window | 0.1.0 |
| `see` | Inspect UI element tree | 0.1.0 |
| `find` | Search UI elements (fuzzy match) | 0.1.0 |
| `get` | Read element properties (text, value, state) | 0.2.1 |
| `highlight` | Visual overlay showing all actionable elements | 0.3.0 |
| `list windows` | List open windows | 0.1.0 |
| `list apps` | List running applications | 0.1.0 |
| `list screens` | List monitors and resolutions | 0.1.0 |
| `diff` | Compare two UI snapshots | 0.1.1 |
| `menu-inspect` | List app menu structure with shortcuts | 0.1.0 |

### Act (interact with the desktop)

| Command | Description | Since |
|---------|-------------|-------|
| `click` | Click element/coordinates (`--paste`, `--copy`, `--cut` modifiers) | 0.1.0 |
| `type` | Type text (supports `--paste` for clipboard) | 0.1.0 |
| `set` | Set element value/state (toggle, select, expand) | 0.3.0 |
| `press` | Press key combination (e.g., `ctrl+s`) | 0.1.0 |
| `scroll` | Scroll mouse wheel | 0.1.0 |
| `drag` | Drag from/to coordinates | 0.1.0 |
| `move` | Move mouse cursor | 0.1.0 |
| `wait` | Wait for element/window to appear | 0.1.0 |

### App management

| Command | Description | Since |
|---------|-------------|-------|
| `app launch` | Launch application by name or path | 0.1.0 |
| `app quit` | Quit application (supports `--force`) | 0.1.0 |
| `app focus` | Focus an application window (alias: `app switch`) | 0.1.0 |
| `app close` | Close an application window (graceful or forced) | 0.1.0 |
| `app minimize` | Minimize an application window (alias: `app hide`) | 0.1.0 |
| `app maximize` | Maximize an application window | 0.1.0 |
| `app restore` | Restore a minimized/maximized window (alias: `app unhide`) | 0.1.0 |
| `app move` | Move and/or resize an application window | 0.1.0 |
| `app list` | List running applications with visible windows | 0.1.0 |
| `app windows` | List open windows (filter by app/PID) | 0.1.0 |
| `app find` | Find application by name or PID | 0.1.0 |
| `app inspect` | Probe app frameworks (UIA, CDP, MSAA...) | 0.3.0 |
| `app relaunch` | Quit and relaunch an application | 0.3.0 |

### System

| Command | Description | Since |
|---------|-------------|-------|
| `clipboard get` | Read clipboard text content | 0.3.1 |
| `clipboard set` | Write text to clipboard | 0.3.1 |
| `clipboard clear` | Clear clipboard contents | 0.3.1 |
| `clipboard info` | Show clipboard format and size | 0.3.1 |
| `dialog detect` | Detect active system dialogs | 0.1.0 |
| `dialog accept` | Accept (OK/Yes) a dialog | 0.1.0 |
| `dialog dismiss` | Dismiss (Cancel/No) a dialog | 0.1.0 |
| `dialog click-button` | Click specific dialog button | 0.1.0 |
| `dialog type` | Type in dialog input field | 0.1.0 |
| `taskbar list` | List taskbar items | 0.1.0 |
| `taskbar click` | Click taskbar item | 0.1.0 |
| `tray list` | List system tray icons | 0.1.0 |
| `tray click` | Click tray icon (left/right/double) | 0.1.0 |
| `desktop list` | List virtual desktops | 0.1.0 |
| `desktop switch` | Switch to a virtual desktop | 0.1.0 |
| `desktop create` | Create a new virtual desktop | 0.1.0 |
| `desktop close` | Close a virtual desktop | 0.1.0 |
| `desktop move-window` | Move window to another desktop | 0.1.0 |

### Tools

| Command | Description | Since |
|---------|-------------|-------|
| `snapshot list` | List stored snapshots | 0.1.0 |
| `snapshot sessions` | List all snapshot sessions | 0.1.0 |
| `snapshot clean` | Remove old snapshots | 0.1.0 |
| `mcp start` | Start MCP server | 0.1.0 |
| `mcp install` | Install MCP server configuration | 0.3.0 |
| `mcp tools` | List available MCP tools | 0.3.0 |
| `record start` | Start recording user actions | 0.3.2 |
| `record stop` | Stop recording and save | 0.3.2 |
| `record play` | Replay a saved recording | 0.3.2 |
| `record list` | List saved recordings | 0.3.2 |
| `record show` | Show recording steps | 0.3.2 |
| `record delete` | Delete a recording | 0.3.2 |
| `record export` | Export recording to Python/Bash/JSON | 0.3.2 |
| `selector save` | Save a UI selector with a friendly name | 0.3.2 |
| `selector list` | List saved/built-in selectors | 0.3.2 |
| `selector delete` | Delete a saved selector | 0.3.2 |
| `selector export` | Export selectors to JSON | 0.3.2 |
| `selector import` | Import selectors from JSON | 0.3.2 |
| `selector test` | Validate a selector against the parser | 0.3.2 |
| `config` | View/set naturo configuration | 0.3.0 |
| `excel open` | Open Excel workbook (Windows only) | 0.1.1 |
| `excel read` | Read cells from worksheet | 0.1.1 |
| `excel write` | Write values to cells | 0.1.1 |
| `excel list-sheets` | List worksheets in workbook | 0.1.1 |
| `excel run-macro` | Execute VBA macro | 0.1.1 |
| `excel info` | Show workbook metadata | 0.1.1 |

> **Deprecated:** `window *` commands still work but print a deprecation warning. Use `app *` equivalents instead. `hotkey` is deprecated in favor of `press`.

## Snapshot System

Every `see` and `capture` call automatically persists a **snapshot** — a
directory under `~/.naturo/snapshots/` containing the screenshot and full UI
element map.

```bash
# List all snapshots
naturo snapshot list

# Remove snapshots older than 7 days
naturo snapshot clean --days 7

# Remove all snapshots
naturo snapshot clean --all --yes
```

Snapshots expire after **10 minutes** when queried via `get_most_recent_snapshot`,
mirroring Peekaboo's validity window.

## Recording & Playback

Record user actions and replay them — the fastest way to create automation scripts.

```bash
# Start recording — all subsequent naturo commands are captured
naturo record start "Login flow"

# ... perform actions ...
naturo click 500 300
naturo type "username"
naturo press tab
naturo type "password"
naturo press enter

# Stop and save
naturo record stop

# List saved recordings
naturo record list
# ID                        Name                           Steps  Created
# rec_20260401_120000       Login flow                         5  2026-04-01T12:00

# Replay at 2x speed
naturo record play rec_20260401_120000 --speed 2.0

# Preview without executing
naturo record play rec_20260401_120000 --dry-run

# Export to a standalone Python script
naturo record export rec_20260401_120000 --format python -o login.py

# Export to Bash
naturo record export rec_20260401_120000 --format bash -o login.sh

# Show step details
naturo record show rec_20260401_120000
```

Recordings are stored in `~/.naturo/recordings/` as JSON files.
Export to Python or Bash generates standalone scripts with proper timing between steps.

## Selector Management

Save, reuse, and share UI element selectors — no more re-discovering selectors for common apps.

```bash
# Save a selector with a friendly name
naturo selector save notepad save-btn 'app://notepad.exe/Button[@name="Save"]'
naturo selector save chrome address-bar '//Edit[@name="Address and search bar"]' \
  -d "Chrome address bar"

# List all saved selectors
naturo selector list
#   notepad (1 selectors)
#   ──────────────────────────────────────────────────
#     @notepad/save-btn
#       app://notepad.exe/Button[@name="Save"]

# List built-in templates (shipped with naturo)
naturo selector list --builtin

# Use a saved selector (@ prefix in click/type/find commands)
naturo click --selector @notepad/save-btn

# Test that a selector parses correctly
naturo selector test notepad save-btn

# Export for sharing with your team
naturo selector export notepad -o notepad-selectors.json

# Import selectors from a teammate
naturo selector import team-selectors.json

# Clean up
naturo selector delete notepad save-btn
naturo selector clear notepad  # delete all selectors for an app
```

Selectors are stored in `~/.naturo/selectors/<app>.json`.
Built-in templates live in `naturo/selectors_builtin/` and are read-only.

## Architecture

```
┌─────────────┐
│  AI Agent    │  Python SDK / MCP Server
├─────────────┤
│  CLI (click) │  naturo CLI
├─────────────┤
│  Snapshot    │  naturo/snapshot.py + naturo/models/snapshot.py
├─────────────┤
│  Python      │  ctypes bridge
├─────────────┤
│  C API       │  exports.h
├─────────────┤
│  C++ Core    │  UIA, MSAA, IA2, JAB, Win32, DirectX
└─────────────┘
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Comparison

| Feature | naturo | PyAutoGUI | pywinauto | AutoIt | WinAppDriver |
|---------|--------|-----------|-----------|--------|--------------|
| **MCP Server** | ✅ Built-in | ❌ | ❌ | ❌ | ❌ |
| **AI Agent Ready** | ✅ JSON output, agent CLI | ❌ | ❌ | ❌ | ❌ |
| **UI Frameworks** | UIA + MSAA + IA2 + JAB + CDP + AI Vision | None (image only) | UIA, Win32 | Win32 messages | UIA only |
| **Cascade Recognition** | ✅ Multi-source fusion with auto-dedup | ❌ | ❌ | ❌ | ❌ |
| **Auto-Detection** | ✅ Picks best framework per app | N/A | Manual backend choice | N/A | N/A |
| **Element Tree** | ✅ Full hierarchy | ❌ | ✅ | ❌ | ✅ |
| **Post-Action Verify** | ✅ Confirms actions took effect | ❌ | ❌ | ❌ | ❌ |
| **Hardware Keyboard** | ✅ Scan codes (anti-cheat safe) | ❌ | ❌ | ✅ | ❌ |
| **Image Matching** | Via AI vision | ✅ Built-in | ❌ | ✅ | ❌ |
| **Screen Capture** | ✅ DirectX / GDI | ✅ | ❌ | ✅ | ❌ |
| **Cross-Platform** | Windows + macOS | Win / Mac / Linux | Windows (+ Linux partial) | Windows only | Windows only |
| **Language** | Python + C++ core | Python | Python | Custom script | C# / WebDriver |
| **Maintained** | ✅ Active | ✅ Active | ⚠️ Slow | ⚠️ Slow | ❌ Deprecated |

### vs Peekaboo (macOS)

Naturo aims to provide cross-platform desktop automation. On macOS, native support is coming soon.

| | Peekaboo (macOS) | Naturo (Windows) | Naturo (macOS - planned) |
|--|-----------------|-----------------|--------------------------|
| UI Framework | Accessibility API | UIA + MSAA + IA2 + JAB | Accessibility API |
| Screen Capture | ScreenCaptureKit | DirectX / GDI | ScreenCaptureKit |
| Input | CGEvent | SendInput + Phys32 scan codes | CGEvent |
| Language | Swift | C++ | C++ / Python bridge |
| Status | Available | Available | Coming soon |

## Contributing

We welcome bug reports and testing help!

- 🐛 **Report bugs**: [GitHub Issues](https://github.com/AcePeak/naturo/issues)
- 🧪 **Testing guide**: See [External Tester Guide](agents/external-tester/SOUL.md)
- 📖 **Contributing guide**: See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT — see [LICENSE](LICENSE)
