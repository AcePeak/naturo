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
- 🍎 **macOS Support** — Full Peekaboo CLI wrapper (capture, click, type, window management, and more)
- 🤖 **AI-Ready** — JSON output, agent-friendly CLI, MCP server

## System Requirements

| Platform | Requirement |
|----------|-------------|
| **Windows** | Windows 10+ (officially supported) |
| | Windows 7 SP1+ (best-effort, basic features only) |
| **Python** | 3.9+ |
| **macOS** | macOS 13+ with [Peekaboo](https://github.com/steipete/Peekaboo) installed |
| **Linux** | Not yet supported |

> **Why Windows 10+?** UIAutomation v2/v3 APIs (caching, virtualized controls) require Windows 8+. Windows 7 has been out of support since January 2020. Most enterprise customers have migrated to Windows 10/11.

## Install

```bash
pip install naturo
```

Or via npm (MCP server shortcut):

```bash
npx naturo mcp start
```

## Quick Start

```bash
# Check version
naturo --version

# Capture a screenshot
naturo capture -o screen.png

# List open windows
naturo list windows

# Inspect UI tree
naturo see --window-title "Notepad" --depth 5

# Click an element
naturo click "Button:Save"

# Type text
naturo type "Hello, World!"

# Type with hardware scan codes (bypass anti-cheat detection)
naturo type "Hello" --input-mode hardware

# Press key combo
naturo hotkey ctrl+s

# Find element
naturo find "Edit:filename"

# Window management
naturo window focus --app "Notepad"
naturo window close --app "Chrome" --force
naturo window minimize --hwnd 12345
naturo window move --app "Notepad" --x 0 --y 0
naturo window resize --app "Notepad" --width 1920 --height 1080
naturo window set-bounds --app "Chrome" --x 0 --y 0 --width 960 --height 1080

# App control
naturo app launch "notepad"
naturo app quit "notepad"
naturo app quit "chrome" --force
naturo app switch "chrome"
naturo app hide "notepad"
naturo app unhide "notepad"

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

| Command | Description | Since |
|---------|-------------|-------|
| `--version` | Show version info | 0.1.0 |
| `capture` | Screenshot screen/window | 0.1.0 |
| `list` | List windows/processes | 0.1.0 |
| `see` | Inspect UI element tree | 0.1.0 |
| `snapshot list` | List stored snapshots | 0.1.0 |
| `snapshot clean` | Remove old snapshots | 0.1.0 |
| `find` | Search UI elements (fuzzy) | 0.1.0 |
| `menu-inspect` | List app menu structure | 0.1.0 |
| `click` | Click element/coordinates | 0.1.0 |
| `type` | Type text | 0.1.0 |
| `press` | Press key combination | 0.1.0 |
| `hotkey` | Press keyboard shortcut | 0.1.0 |
| `scroll` | Scroll mouse wheel | 0.1.0 |
| `drag` | Drag from/to coordinates | 0.1.0 |
| `move` | Move mouse cursor | 0.1.0 |
| `type --paste` | Paste text via clipboard (Ctrl+V) | 0.2.0 |
| `wait` | Wait for element/window | 0.1.0 |
| `app launch` | Launch application | 0.1.0 |
| `app quit` | Quit application | 0.1.0 |
| `app list` | List running applications | 0.1.0 |
| `app find` | Find application by name | 0.1.0 |
| `app hide` | Minimize all app windows | 0.1.0 |
| `app unhide` | Restore all app windows | 0.1.0 |
| `app switch` | Switch to application | 0.1.0 |
| `window focus` | Focus a window | 0.1.0 |
| `window close` | Close a window | 0.1.0 |
| `window minimize` | Minimize a window | 0.1.0 |
| `window maximize` | Maximize a window | 0.1.0 |
| `window restore` | Restore a window | 0.1.0 |
| `window move` | Move a window | 0.1.0 |
| `window resize` | Resize a window | 0.1.0 |
| `window set-bounds` | Set position + size | 0.1.0 |
| `window list` | List windows with filters | 0.1.0 |
| `mcp start` | Start MCP server | 0.1.0 |
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

| `chrome title` | Get page title | 0.1.0 |
| `chrome html` | Get page/element HTML | 0.1.0 |
| `chrome version` | Show Chrome version info | 0.1.0 |
| `registry get` | Read registry value | 0.1.0 |
| `registry set` | Write registry value | 0.1.0 |
| `registry list` | List subkeys/values | 0.1.0 |
| `registry delete` | Delete key/value | 0.1.0 |
| `registry search` | Search registry | 0.1.0 |
| `service list` | List Windows services | 0.1.0 |
| `service start` | Start a service | 0.1.0 |
| `service stop` | Stop a service | 0.1.0 |
| `service restart` | Restart a service | 0.1.0 |
| `service status` | Query service status | 0.1.0 |
| `diff` | Compare two UI snapshots or window states | 0.1.1 |
| `learn` | Show usage guides and tutorials | 0.1.0 |
| `excel open` | Open Excel workbook | 0.1.1 |
| `excel read` | Read cells from worksheet | 0.1.1 |
| `excel write` | Write values to cells | 0.1.1 |
| `excel list-sheets` | List worksheets in workbook | 0.1.1 |
| `excel run-macro` | Execute VBA macro | 0.1.1 |
| `excel info` | Show workbook metadata | 0.1.1 |


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
