# Naturo — Windows Desktop Automation Engine

> See, click, type, automate. Built for AI agents.

[![Build & Test](https://github.com/AcePeak/naturo/actions/workflows/build.yml/badge.svg)](https://github.com/AcePeak/naturo/actions/workflows/build.yml)

## What You Get

- 🖥️ **Screen Capture** — Screenshot any window or monitor
- 🌳 **UI Tree Inspection** — Walk the accessibility tree (MSAA / UIA)
- 🔍 **Element Finding** — CSS-like selectors for UI elements
- 🖱️ **Click & Type** — Hardware-level input simulation
- ⌨️ **Key Combos** — Send any keystroke or shortcut
- 🤖 **AI-Ready** — JSON output, agent-friendly CLI, MCP server

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
| `find` | Find UI element | 🔜 2 |
| `click` | Click element/coordinates | 🔜 2 |
| `type` | Type text | 🔜 2 |
| `press` | Press key combination | 🔜 2 |

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
