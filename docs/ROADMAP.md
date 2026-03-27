# Roadmap

## 0.1.0 ✅ — Core Automation + MCP + macOS (Eyes + Hands)

First release. Full Windows automation with AI integration and cross-platform foundation.

### Core
- [x] Project structure (C++ core + Python wrapper)
- [x] CI/CD pipeline (GitHub Actions)
- [x] Cross-platform backend abstraction layer
- [x] TDD infrastructure, 700+ tests
- [x] Error handling framework (Peekaboo-aligned error codes)
- [x] Wait/retry strategies (polling, exponential backoff)
- [x] Element cache (TTL-based, auto-invalidation)

### See
- [x] Screen capture (GDI → Pillow PNG)
- [x] Window enumeration
- [x] UI tree inspection (UIA)
- [x] Element attributes (name, role, bounds, state)
- [x] Annotated screenshots (numbered bounding boxes)
- [x] Element search/query (fuzzy match, role filter)
- [x] UI hierarchy (parent_id, children linkage)
- [x] Snapshot system (screenshot + UI tree bundling)

### Act
- [x] Mouse input (click, double-click, right-click, drag, scroll)
- [x] Keyboard input (type, press, hotkey, paste)
- [x] Element finding by selector
- [x] Coordinate-based and element-based actions
- [x] Menu bar traversal
- [x] Keyboard shortcut discovery

### Window Management
- [x] Window focus / close / minimize / maximize / restore
- [x] Window move / resize / set-bounds
- [x] App hide / unhide / switch
- [x] Window list with filters (--app / --pid / --process-name)
- [x] 105 window management tests

### MCP Server
- [x] MCP Server — stdio/sse/streamable-http transport
- [x] Agent-friendly error messages with recovery suggestions

> Note: AI vision (`describe`), agent command, and recording CLI removed in v0.2.0.
> These features are handled by the orchestrating AI agent (e.g., OpenClaw).
> Backend modules (vision.py, agent.py, recording.py) kept for internal use.

### Dialog & System
- [x] Dialog detection and interaction (accept/dismiss/fill)
- [x] Taskbar interaction (list/click)
- [x] System tray (list/click)

> Note: `clipboard` and `open` CLI commands removed in v0.2.0.
> These are handled directly by the orchestrating AI agent.

### Deep Capabilities
- [x] Multi-monitor capture
- [x] DPI/scaling awareness (125%/150%/200%)
- [x] Virtual desktop support
- [x] MSAA / IAccessible
- [x] IAccessible2 (Firefox, Thunderbird, LibreOffice)
- [x] Java Access Bridge (Swing/AWT)
- [x] Hardware-level keyboard (Phys32)
- [x] UIA cache optimization (CacheRequest, batch properties)
> Note: Chrome CDP, Electron, Registry, and Service CLI commands removed in v0.2.0.
> Backend modules kept for Unified App Model internal use.
> Use PowerShell for registry/service ops, Playwright for browser automation.
- [x] Process management (launch/quit/relaunch/find)
- [x] UI tree diff

### macOS Backend
- [x] Peekaboo CLI detection + subprocess wrapper
- [x] capture/list/see via Peekaboo
- [x] click/type/press/hotkey via Peekaboo
- [x] app/window/menu via Peekaboo
- [x] dock/space mapping
- [x] CI: macOS runner integration tests
- [x] Fallback: pyobjc for Peekaboo-free environments

## 0.2.0 ✅ — Eyes + Hands Focus (Breaking)

Refocused on core "Eyes + Hands" for AI agents. Removed 12 non-core CLI commands.

### Removed Commands
- `describe` — AI vision analysis (agent does this)
- `agent` — Natural language automation (OpenClaw handles this)
- `learn` — Tutorial content (moved to docs)
- `record` — High-level orchestration (agent composes commands)
- `chrome` — Browser automation (use Playwright/browser tools)
- `registry` — Windows registry ops (use PowerShell)
- `service` — Windows service ops (use PowerShell)
- `clipboard` — Agent can do this directly
- `open` — Agent can do this directly
- `electron` — Folded into Unified App Model auto-detection
- `structure` — Unclear function
- `paste` — Merged into `type --paste` flag

### Kept Commands (Core Eyes + Hands)
see, find, capture, list, wait, diff, menu-inspect, click, type, press, hotkey, scroll, drag, move, window, app, dialog, taskbar, tray, desktop, mcp, snapshot

### Migration
- `naturo paste "text"` → `naturo type --paste "text"`
- `naturo clipboard get` → Use agent's native clipboard access
- `naturo open <url>` → Use agent's browser tool or system commands
- `naturo chrome ...` → Use Playwright or browser automation skill

## 0.3.0 ✅ — Unified App Model + Selector Foundation

Auto-detect application frameworks and route interactions through the optimal channel. Users don't need to know if it's Electron, Java, or WPF.

See [design doc](design/UNIFIED_APP_MODEL.md).

- [x] Framework detection chain (CDP → UIA → MSAA → JAB → IA2 → Vision)
- [x] `naturo app inspect` — probe app and report available interaction methods
- [x] `naturo app inspect --all` — scan all visible windows
- [x] Per-PID detection cache with TTL
- [x] Auto-routing for action commands (click/type/press/find)
- [x] `--method` override flag for explicit channel selection
- [x] `--quick` mode for fast probe (skip slow checks)
- [x] MCP tools for app inspect
- [x] Integration tests across framework types
- [x] Element ref caching system (temporary eN → coordinates cache with TTL)
- [x] Unified Selector format specification ([design doc](design/UNIFIED_SELECTOR.md))
- [x] Post-action verification engine (`--verify/--no-verify` on type/click/press, #231)

## 0.4.0 — Unified Selector Engine + Enterprise Features + Open Source Polish

Unified Selector system, deep enterprise automation capabilities from Naturobot engine, and continued open source launch efforts.

See [Unified Selector design doc](design/UNIFIED_SELECTOR.md).

### Unified Selectors
- [ ] Unified Selector engine (SelectorBuilder + SelectorResolver)
- [ ] `see` outputs selectors alongside eN IDs
- [ ] `click --selector` accepts unified selector format
- [ ] Built-in selector templates for Top 20 Windows apps
- [ ] User selector management (`naturo selector save/load/list/export`)

### Enterprise
- [ ] Excel COM automation (read/write cells, run macros, create charts)
- [ ] SAP GUI Scripting
- [ ] MinHook injection (function hooks, intercept/modify Win32 API calls)
- [ ] Embedded Python 3.12 runtime (~40MB bundled)
- [ ] `naturo run my_script.py` — execute user scripts with bundled Python
- [ ] Standalone executable (Nuitka/PyInstaller -> naturo.exe)

### Open Source Polish
- [ ] Branch protection (require PR + CI)
- [x] CONTRIBUTING.md + CODE_OF_CONDUCT.md
- [x] Issue/PR templates
- [ ] README hero GIF (Notepad E2E demo)
- [ ] README badges
- [ ] Code signing certificate + CI integration
- [x] First PyPI release (`pip install naturo`)
- [ ] npm package (`npx naturo mcp`)
- [ ] OpenClaw skill published to ClawHub
- [x] Flip repo to public
- [ ] Announcements: LinkedIn / Reddit / Twitter / HN / Discord
- [ ] "How Naturo Works" blog post
- [ ] Submit to awesome-python, awesome-automation
- [ ] Demo videos (YouTube + Bilibili)

## 0.5.0 — Linux Backend

X11 + Wayland support.

- [ ] X11: xdotool + python-xlib
- [ ] AT-SPI2 element inspection
- [ ] Screenshot via Xlib / dbus portal
- [ ] Wayland: ydotool + wlr protocols
- [ ] CI: Ubuntu + xvfb UI tests
- [ ] GNOME + KDE compatibility

## 0.6.0 — National OS + Enterprise Recording

UOS, Kylin, openEuler support and production recording engine.

- [ ] DDE (Deepin Desktop) compatibility
- [ ] Kylin adapters
- [ ] Self-hosted CI runner
- [ ] Enterprise recording/playback engine
- [ ] Enterprise visual regression testing

## 1.0.0 — Stable Release

API freeze, ecosystem partnerships, community selector registry.

- [ ] Community selector registry (npm-like service for sharing verified selectors)
- [ ] API stability guarantee (semver contract)
- [ ] Peekaboo collaboration — official Windows counterpart
- [ ] OpenClaw recommended Windows tool
- [ ] Conference talk (PyCon / EuroPython)
- [ ] RPA/testing community partnerships
