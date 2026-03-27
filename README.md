# Naturo — Desktop Automation Engine (Eyes + Hands for AI Agents)

> See, click, type, capture. Desktop automation core only.

[![Build & Test](https://github.com/AcePeak/naturo/actions/workflows/build.yml/badge.svg)](https://github.com/AcePeak/naturo/actions/workflows/build.yml)
[![PyPI version](https://img.shields.io/pypi/v/naturo)](https://pypi.org/project/naturo/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
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

Or start the MCP server directly:

```bash
naturo mcp start
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
naturo app switch "notepad"
naturo app quit "chrome" --force
naturo app hide "notepad"
naturo app unhide "notepad"
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
| `click` | Click element/coordinates | 0.1.0 |
| `type` | Type text (supports `--paste` for clipboard) | 0.1.0 |
| `press` | Press key combination (e.g., `ctrl+s`) | 0.1.0 |
| `scroll` | Scroll mouse wheel | 0.1.0 |
| `drag` | Drag from/to coordinates | 0.1.0 |
| `move` | Move mouse cursor | 0.1.0 |
| `wait` | Wait for element/window to appear | 0.1.0 |

### App management

| Command | Description | Since |
|---------|-------------|-------|
| `app launch` | Launch application | 0.1.0 |
| `app quit` | Quit application (supports `--force`) | 0.1.0 |
| `app switch` | Switch to application | 0.1.0 |
| `app list` | List running applications | 0.1.0 |
| `app find` | Find application by name | 0.1.0 |
| `app hide` | Minimize all app windows | 0.1.0 |
| `app unhide` | Restore all app windows | 0.1.0 |
| `app inspect` | Probe app frameworks (UIA, CDP, MSAA...) | 0.3.0 |
| `app relaunch` | Restart an application | 0.3.0 |

### System

| Command | Description | Since |
|---------|-------------|-------|
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

## vs Peekaboo

Naturo is the Windows counterpart to [Peekaboo](https://github.com/steipete/Peekaboo) (macOS).
On macOS, Naturo wraps Peekaboo's CLI so you get one unified API across platforms.

| Feature | Peekaboo (macOS) | Naturo (Windows) |
|---------|-----------------|-----------------|
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
