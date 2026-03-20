# Naturo — Windows Desktop Automation Engine

> See, click, type, automate. Built for AI agents.

[![Build & Test](https://github.com/AcePeak/naturo/actions/workflows/build.yml/badge.svg)](https://github.com/AcePeak/naturo/actions/workflows/build.yml)

## What You Get

- 🖥️ **Screen Capture** — Screenshot any window or monitor
- 🌳 **UI Tree Inspection** — Walk the accessibility tree (MSAA / UIA)
- 🔍 **Element Finding** — CSS-like selectors + fuzzy search for UI elements
- 🖱️ **Click & Type** — Hardware-level input simulation
- ⌨️ **Key Combos** — Send any keystroke or shortcut
- 📸 **Annotated Screenshots** — AI-ready screenshots with numbered bounding boxes
- 📋 **Menu Traversal** — Extract app menu structures with shortcuts
- 🪟 **Window Management** — Focus, close, minimize, maximize, move, resize windows
- 📦 **App Control** — Launch, quit, switch, hide/unhide applications
- 🤖 **AI-Ready** — JSON output, agent-friendly CLI, MCP server (29 tools)

## System Requirements

| Platform | Requirement |
|----------|-------------|
| **Windows** | Windows 10+ (officially supported) |
| | Windows 7 SP1+ (best-effort, basic features only) |
| **Python** | 3.9+ |
| **macOS / Linux** | Python CLI wrapper only (no C++ automation) |

> **Why Windows 10+?** UIAutomation v2/v3 APIs (caching, virtualized controls) require Windows 8+. Windows 7 has been out of support since January 2020. Most enterprise customers have migrated to Windows 10/11.

## Install

```bash
pip install naturo
```

## Quick Start

```bash
# Check version
naturo version

# Capture a screenshot
naturo capture --output screen.png

# List open windows
naturo list --type windows

# Inspect UI tree
naturo see --window "Notepad" --depth 5

# Click an element
naturo click "Button:Save"

# Type text
naturo type "Hello, World!"

# Press key combo
naturo press "ctrl+s"

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
naturo app switch "chrome"
naturo app hide "notepad"
naturo app unhide "notepad"
```

## CLI Commands

| Command | Description | Phase |
|---------|-------------|-------|
| `version` | Show version info | ✅ 0 |
| `capture` | Screenshot screen/window | ✅ 1 |
| `list` | List windows/processes | ✅ 1 |
| `see` | Inspect UI element tree | ✅ 1 |
| `snapshot list` | List stored snapshots | ✅ 1.5 |
| `snapshot clean` | Remove old snapshots | ✅ 1.5 |
| `find` | Search UI elements (fuzzy) | ✅ 2 |
| `menu-inspect` | List app menu structure | ✅ 2 |
| `click` | Click element/coordinates | ✅ 2 |
| `type` | Type text | ✅ 2 |
| `press` | Press key combination | ✅ 2 |
| `hotkey` | Press keyboard shortcut | ✅ 2 |
| `scroll` | Scroll mouse wheel | ✅ 2 |
| `drag` | Drag from/to coordinates | ✅ 2 |
| `move` | Move mouse cursor | ✅ 2 |
| `paste` | Paste from clipboard | ✅ 2 |
| `wait` | Wait for element/window | ✅ 3 |
| `app launch` | Launch application | ✅ 3 |
| `app quit` | Quit application | ✅ 3 |
| `app list` | List running applications | ✅ 3 |
| `app find` | Find application by name | ✅ 3 |
| `app hide` | Minimize all app windows | ✅ 3.5 |
| `app unhide` | Restore all app windows | ✅ 3.5 |
| `app switch` | Switch to application | ✅ 3.5 |
| `window focus` | Focus a window | ✅ 3.5 |
| `window close` | Close a window | ✅ 3.5 |
| `window minimize` | Minimize a window | ✅ 3.5 |
| `window maximize` | Maximize a window | ✅ 3.5 |
| `window restore` | Restore a window | ✅ 3.5 |
| `window move` | Move a window | ✅ 3.5 |
| `window resize` | Resize a window | ✅ 3.5 |
| `window set-bounds` | Set position + size | ✅ 3.5 |
| `window list` | List windows with filters | ✅ 3.5 |
| `open` | Open URL/file with default app | ✅ 4 |
| `mcp start` | Start MCP server | ✅ 4 |

## Snapshot System

Every `see` and `capture live` call automatically persists a **snapshot** — a
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
│  C++ Core    │  MSAA, UIA, Win32, DirectX
└─────────────┘
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## vs Peekaboo

Naturo is the Windows counterpart to [Peekaboo](https://github.com/AcePeak/peekaboo) (macOS).

| Feature | Peekaboo (macOS) | Naturo (Windows) |
|---------|-----------------|-----------------|
| UI Framework | Accessibility API | MSAA + UIA |
| Screen Capture | ScreenCaptureKit | DirectX / GDI |
| Input | CGEvent | SendInput |
| Language | Swift | C++ |
| Python Bridge | Swift subprocess | ctypes DLL |

## Contributing

1. Fork the repo
2. Create a feature branch
3. Write tests first (TDD)
4. Implement the feature
5. Submit a PR

## License

MIT — see [LICENSE](LICENSE)
