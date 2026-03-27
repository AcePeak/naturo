# Changelog

All notable changes to Naturo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-03-27

### Added
- **Framework detection chain** — CDP → UIA → MSAA → JAB → IA2 → Vision auto-detection
- **`naturo app inspect`** — probe app and report available interaction methods (`--all` for all windows)
- **Auto-routing for action commands** — click/type/press/find dispatched through optimal channel
- **`--method` override flag** — explicit channel selection for any action command
- **`--quick` mode** — fast probe that skips slow framework checks
- **Element ref caching system** — temporary eN → coordinates cache with TTL
- **Post-action verification engine** — `--verify/--no-verify` on type/click/press
- **Unified Selector format specification** ([design doc](design/UNIFIED_SELECTOR.md))
- **MCP tools for app inspect**
- **Per-PID detection cache** with TTL

### Tests
- Integration tests across framework types

## [0.2.1] — 2026-03-23

### Added
- **Auto-routing for action commands** — intelligent command dispatch ([#28](https://github.com/user/naturo/issues/28))
- **`naturo get` command** — read element text/value via UIA patterns ([#109](https://github.com/user/naturo/issues/109))
- **Version bump script** — `scripts/bump_version.py` for release automation ([#30](https://github.com/user/naturo/issues/30))

### Fixed
- `find --all` flag for SSH-safe wildcard search ([#112](https://github.com/user/naturo/issues/112))
- `list apps` now correctly delegates to `app list` ([#114](https://github.com/user/naturo/issues/114))
- `find --actionable` works without QUERY; `press --json` returns proper error ([#123](https://github.com/user/naturo/issues/123), [#124](https://github.com/user/naturo/issues/124))
- Standardized `get` command JSON error format ([#121](https://github.com/user/naturo/issues/121))
- `find --query` option and improved SSH desktop detection ([#112](https://github.com/user/naturo/issues/112), [#113](https://github.com/user/naturo/issues/113))
- Missing `--method` override code in interaction.py

### Tests
- Integration test suite for Unified App Model ([#37](https://github.com/user/naturo/issues/37))
- Method override tests ([#34](https://github.com/user/naturo/issues/34) partially)

### Docs
- Enforce PR workflow, no direct push to main

## [0.2.0] — 2026-03-22

### Added
- **App inspect** — probe app frameworks + interaction methods ([#27](https://github.com/user/naturo/issues/27))
- **Detection chain orchestrator** with public API + 35 tests ([#26](https://github.com/user/naturo/issues/26))
- **Unified Selector system** — format spec + roadmap + issues
- **`app_inspect` MCP tool** for framework detection ([#36](https://github.com/user/naturo/issues/36) partial)

### Breaking
- Removed 12 non-core commands — focus on Eyes+Hands

### Fixed
- Unified error handling for headless/SSH environments ([#99](https://github.com/user/naturo/issues/99))
- Filter system processes from app list, show only user apps with windows ([#98](https://github.com/user/naturo/issues/98))
- DPI handling via `SetThreadDpiAwarenessContext` for reliable coordinates ([#16](https://github.com/user/naturo/issues/16))
- `open_uri` uses Popen for URLs to avoid blocking ([#31](https://github.com/user/naturo/issues/31))
- `--json` flag implies `--yes` for snapshot clean
- README corrections: `press→hotkey`, `app quit` accepts positional arg, `scroll` accepts positional direction
- Electron list hang due to per-PID wmic calls
- Taskbar/tray use FindWindowW+get_element_tree
- Learn capture/tutorial reference fixes
- CI stability improvements for desktop-requiring tests

### Docs
- Updated MCP tool count from 76 to 82
- Migrated from bugs.md to GitHub Issues + CONTRIBUTING.md
- Added diff, learn, excel commands to README CLI table

## [0.1.0] — 2026-03-21

### Added
- **Screen Capture** — GDI-based screenshot of any window or full screen
- **UI Tree Inspection** — Walk accessibility tree (UIA / MSAA / IAccessible2 / Java Access Bridge)
- **Element Finding** — CSS-like selectors + fuzzy search for UI elements
- **Mouse Input** — Click, double-click, right-click, drag, scroll, move
- **Keyboard Input** — Type text, press keys, hotkey combos, hardware-level scan codes
- **Annotated Screenshots** — AI-ready screenshots with numbered bounding boxes
- **Menu Traversal** — Extract app menu structures with keyboard shortcuts
- **Window Management** — Focus, close, minimize, maximize, move, resize, set-bounds
- **App Control** — Launch, quit, switch, hide/unhide, relaunch applications
- **Dialog Handling** — Detect and interact with system dialogs (message boxes, file pickers)
- **Taskbar & System Tray** — List and click taskbar items and tray icons
- **Multi-Monitor** — Enumerate monitors, capture specific screens, DPI-aware coordinates
- **Virtual Desktops** — List, switch, create, close desktops and move windows between them
- **Chrome DevTools** — Control Chrome via CDP (navigate, click, type, screenshot, eval JS)
- **Electron/CEF Support** — Detect, list, launch, connect to Electron apps
- **Windows Registry** — Read, write, list, delete, search registry keys/values
- **Windows Services** — List, start, stop, restart, query service status
- **Clipboard** — Get/set clipboard text and files
- **Action Recording** — Record and replay user operation sequences
- **AI Integration** — Vision describe, natural language find, agent command, multi-provider
- **MCP Server** — 82 tools via stdio/SSE/streamable-http transport
- **npm Package** — `npx naturo mcp` for Node.js ecosystem
- **JSON Output** — Every command supports `--json` for structured output
- **macOS Backend** — Full Peekaboo CLI wrapper (40+ methods) for cross-platform support
- **1461 Tests** — Comprehensive test suite with 0 failures
