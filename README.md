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
- 🍎 **macOS Support** — Peekaboo CLI wrapper (requires [Peekaboo](https://github.com/steipete/Peekaboo) installed)
- 🤖 **AI-Ready** — JSON output, agent-friendly CLI, MCP server

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| **Windows 10/11** | ✅ Full support | Primary platform. All features available. |
| **Windows 7 SP1+** | ⚠️ Best-effort | Basic features only, no UIAutomation v3. |
| **macOS 13+** | ⚠️ Partial | Requires [Peekaboo](https://github.com/steipete/Peekaboo) installed. Wraps Peekaboo CLI for capture, click, type, window management. |
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
| **UI Frameworks** | UIA + MSAA + IA2 + JAB + CDP | None (image only) | UIA, Win32 | Win32 messages | UIA only |
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

Naturo is the Windows counterpart to [Peekaboo](https://github.com/steipete/Peekaboo) (macOS).
On macOS, Naturo wraps Peekaboo's CLI so you get one unified API across platforms.

| | Peekaboo (macOS) | Naturo (Windows) |
|--|-----------------|-----------------|
| UI Framework | Accessibility API | UIA + MSAA + IA2 + JAB |
| Screen Capture | ScreenCaptureKit | DirectX / GDI |
| Input | CGEvent | SendInput + Phys32 scan codes |
| Language | Swift | C++ |
| Python Bridge | Swift subprocess | ctypes DLL |

## Contributing

We welcome bug reports and testing help!

- 🐛 **Report bugs**: [GitHub Issues](https://github.com/AcePeak/naturo/issues)
- 🧪 **Testing guide**: See [External Tester Guide](agents/external-tester/SOUL.md)
- 📖 **Contributing guide**: See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT — see [LICENSE](LICENSE)
