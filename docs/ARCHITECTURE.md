# Naturo Architecture

## Vision

Naturo is a **cross-platform desktop automation engine** built for AI agents.
One unified API, multiple native backends.

## System Architecture

```
                         User Code / AI Agent
                               │
                    ┌──────────┴──────────┐
                    │   naturo Python API  │   pip install naturo
                    │   + CLI + MCP        │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │  Backend Abstraction │   naturo/backends/base.py
                    │  (Platform-agnostic) │
                    └──┬──────┬───────┬───┘
                       │      │       │
            ┌──────────┴┐ ┌───┴────┐ ┌┴──────────┐
            │  Windows  │ │ macOS  │ │  Linux    │
            │  Backend  │ │Backend │ │ Backend   │
            └──────┬────┘ └───┬────┘ └────┬──────┘
                   │          │            │
            naturo_core.dll  Peekaboo    AT-SPI2
            (C++ engine)     CLI/pyobjc  xdotool/ydotool
```

### Layer Responsibilities

| Layer | Role | Technology |
|-------|------|-----------|
| **CLI** | User-facing commands | Python (click) |
| **Python API** | Programmatic access | Python |
| **MCP Server** | AI agent integration | Python (MCP protocol) |
| **AI Providers** | Vision + language | Anthropic, OpenAI, Ollama |
| **Backend Abstraction** | Platform-agnostic interface | Python ABC |
| **Windows Backend** | Native Windows automation | C++ DLL via ctypes |
| **macOS Backend** | Native macOS automation | Peekaboo CLI / pyobjc |
| **Linux Backend** | Native Linux automation | AT-SPI2 + xdotool |

### Backend Capabilities Matrix

| Capability | Windows | macOS | Linux |
|-----------|---------|-------|-------|
| **Input Modes** | normal, hardware, hook | normal | normal |
| **Accessibility** | UIA, MSAA, IA2 | AX (Accessibility) | AT-SPI2 |
| **Element Caching** | ✅ (C++ optimized) | Via Peekaboo | Basic |
| **Screenshot** | GDI/DXGI | ScreenCaptureKit | Xlib/portal |
| **Java Bridge** | ✅ (JAB) | ❌ | ❌ |
| **SAP** | ✅ (GUI Scripting) | ❌ | ❌ |
| **Excel** | ✅ (COM) | ❌ | ❌ |
| **Hook Injection** | ✅ (MinHook) | ❌ | ❌ |
| **Hardware Keyboard** | ✅ (Phys32) | ❌ | ❌ |
| **Browser** | ✅ (Chrome CDP) | Via Peekaboo | Basic |

### Deep Capabilities (Phase 1/2 Extensions)

#### Annotated Screenshots

`naturo/annotate.py` generates annotated screenshots with red bounding boxes
and numbered labels for AI vision models.  Only actionable elements with
non-trivial bounding rectangles are annotated.

```
annotate_screenshot(screenshot_path, elements, output_path) → str
```

- Requires Pillow: `pip install naturo[annotate]`
- CLI: `naturo see --annotate --path screenshot.png`
- Colour scheme: red boxes + white-background red-text numbered labels

#### Element Search / Query

`naturo/search.py` provides flexible element finding beyond exact `role:name`
matching.

```
search_elements(root, query, role_filter?, actionable_only?, max_results?) → List[SearchResult]
```

Query syntax:
- `"Save"` — fuzzy name match (case-insensitive substring)
- `"role:Button"` — filter by role
- `"role:Button name:Save"` — combined
- `"Button:Save"` — shorthand
- `"Button:*Save*"` — glob wildcard
- CLI: `naturo find "Save"` — returns all matches with breadcrumb paths

#### UI Hierarchy + Keyboard Shortcuts

`bridge.py` `ElementInfo` extended with `parent_id` and `keyboard_shortcut`.
`populate_hierarchy(root)` fills `parent_id` and assigns sequential IDs
(`e0`, `e1`, ...) via depth-first traversal.  Windows backend calls this
automatically after `get_element_tree`.

#### Menu Bar Traversal

`naturo/models/menu.py` provides the `MenuItem` data model.
`WindowsBackend.get_menu_items()` traverses UIA MenuBar → MenuItem hierarchy.

```
MenuItem(name, shortcut?, submenu?, enabled, checked)
```

- CLI: `naturo menu-inspect [--app "Notepad"] [--flat] [--json]`
- `MenuItem.flatten()` produces path-based list (e.g., `"File > Save"`)

---

### CLI ↔ Peekaboo Command Mapping

| Category | Peekaboo (macOS) | Naturo | Notes |
|----------|-----------------|--------|-------|
| **Core** | capture, list, see | capture, list, see, find, menu-inspect | Full parity + extensions |
| **Interaction** | click, type, press, hotkey, scroll, drag, move, swipe | click, type, press, hotkey, scroll, drag, move | swipe N/A; paste merged into type --paste |
| **System** | app, window, menu, menubar, dialog, dock, space | app, window, dialog, taskbar, tray, desktop | Platform equivalents |
| **MCP** | mcp | mcp | Same protocol |
| **Snapshot** | (internal) | snapshot list / snapshot clean | Phase 1.5 |
| **Other** | — | wait, diff, get, config | Naturo extensions |

### Windows-Specific Parameters

These parameters are available on Windows but not other platforms:

- `--input-mode normal|hardware|hook` — Input simulation method
  - `normal`: SendInput API (default, works for most apps)
  - `hardware`: Phys32/Port32 IO (bypasses software hooks, for anti-cheat/protected apps)
  - `hook`: MinHook injection (injects into target process, for apps that block external input)
- `--hwnd` — Direct window handle targeting
- `--process-name` — Target by process name

---

## Phase 1.5 — Snapshot System

Naturo implements a persistent snapshot system aligned with Peekaboo's
`UIAutomationSnapshot` / `SnapshotManager` architecture.

### Purpose

Every `see` or `capture live` call produces a **snapshot** — a directory on disk
containing the raw screenshot, an optional annotated screenshot, and a
`snapshot.json` file with the full UI element map.  Subsequent commands can
reference elements by snapshot ID without re-scanning the UI tree.

### Storage Layout

```
~/.naturo/snapshots/
└── <snapshot_id>/          # e.g. 1742363045123-7321
    ├── snapshot.json       # full Snapshot JSON (atomic write)
    ├── raw.png             # raw screenshot (copied from capture output)
    └── annotated.png       # annotated screenshot (optional)
```

**Snapshot ID format:** `<unix-milliseconds>-<4-digit-random>` — sortable
chronologically, no UUID dependency, compatible with cross-process use.

### Data Model

```
naturo/models/snapshot.py
├── UIElement          — single accessibility element
│     id, element_id, role, title, label, value, description,
│     identifier, frame(x,y,w,h), is_actionable,
│     parent_id, children, keyboard_shortcut
├── Snapshot           — full snapshot (mirrors UIAutomationSnapshot)
│     snapshot_id, version, screenshot_path, annotated_path,
│     ui_map{id→UIElement}, last_update_time,
│     application_name, application_pid,
│     window_title, window_bounds(x,y,w,h), window_handle(HWND)
├── SnapshotInfo       — lightweight list summary
└── SnapshotError / SnapshotNotFoundError / SnapshotVersionError / SnapshotStorageError
```

### SnapshotManager API

```
naturo/snapshot.py — SnapshotManager
├── create_snapshot() → str
├── store_screenshot(id, path, metadata)
├── store_detection_result(id, ui_elements)
├── store_annotated(id, path)
├── get_snapshot(id) → Snapshot
├── get_most_recent_snapshot(app_name?) → str | None
├── list_snapshots() → List[SnapshotInfo]
├── clean_snapshot(id)
├── clean_older_than(days) → int
└── clean_all() → int
```

**Design guarantees:**

| Property | Mechanism |
|----------|-----------|
| Atomic writes | `tempfile` → `os.replace()` |
| Thread safety | `threading.Lock` wraps all mutations |
| Validity window | 10 minutes (configurable), same as Peekaboo |
| Version check | `SnapshotVersionError` on schema mismatch |

### CLI Commands

| Command | Description |
|---------|-------------|
| `naturo see` | Inspect UI tree → auto-stores snapshot, prints snapshot_id |
| `naturo capture live` | Screenshot → auto-stores snapshot, prints snapshot_id |
| `naturo snapshot list` | List all snapshots (id, time, app, size) |
| `naturo snapshot clean --days N` | Delete snapshots older than N days |
| `naturo snapshot clean --all` | Delete all snapshots |

---

### C++ Core Architecture (Windows)

```
naturo_core.dll
├── exports.h          ← Pure C API (stable ABI)
├── auto/              ← Input simulation
│   ├── SendKeys       ← Normal mode (SendInput)
│   ├── Phys32         ← Hardware mode (IO ports)
│   └── AutoInput      ← Unified input dispatcher
├── uia/               ← UIAutomation + element caching
├── msaa/              ← MSAA / IAccessible
├── ia2/               ← IAccessible2 Proxy
├── element/           ← Unified element model
├── selector/          ← CSS-like selector engine
├── window/            ← Window management
├── image/             ← Screenshot + image matching
├── hook/              ← MinHook wrapper
├── java/              ← Java Access Bridge
├── chromium/          ← Chrome CDP + Native Host
├── sap/               ← SAP GUI Scripting
└── excel/             ← Excel COM automation
```

### CI/CD Matrix

```yaml
matrix:
  include:
    - os: windows-latest   # Primary — full build + test
      build-cpp: true
      test-level: full     # C++ + Python + UI (notepad/calc)
    - os: ubuntu-latest    # Python tests (no DLL)
      build-cpp: false
      test-level: python
    - os: macos-latest     # Python tests (no DLL)
      build-cpp: false
      test-level: python
  # Future:
  # - os: ubuntu-latest, xvfb + AT-SPI2 (Linux UI tests)
  # - os: macos-latest, Peekaboo integration tests
```
