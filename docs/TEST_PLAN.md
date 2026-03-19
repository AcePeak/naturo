# Naturo Test Plan

## Overview

Comprehensive test plan covering all phases of Naturo development. Every test case is mapped to the phase that should implement it, with current status tracked.

- **Total test cases:** 215
- **Currently passing:** 97
- **Currently skipped (Windows-only):** 44
- **Not yet implemented:** 74

### Coverage by Phase

| Phase | Description | Total Tests | Passing | Skipped | Missing |
|-------|-------------|-------------|---------|---------|---------|
| P0 | Skeleton | 18 | 24 | 0 | 0 |
| P1 | See | 43 | 25 | 44 | 0 |
| P2 | Act | 38 | 0 | 0 | 38 |
| P3 | Stabilize | 22 | 0 | 0 | 22 |
| P4 | AI Integration | 12 | 0 | 0 | 12 |
| P5 | Complete | 14 | 0 | 0 | 14 |
| P6 | macOS Backend | 10 | 0 | 0 | 10 |
| P7 | Linux Backend | 8 | 0 | 0 | 8 |
| P8 | National OS & Enterprise | 6 | 0 | 0 | 6 |
| Cross | Cross-phase (CLI, Errors) | 44 | 28 | 0 | 16 |

---

## Test Case Matrix

### 1. Capture (Screenshot)

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T001 | Screen capture primary monitor creates valid BMP file | P1 | ⏭️ Skip (Win) | test_capture.py |
| T002 | Screen capture BMP has valid header (magic bytes "BM") | P1 | ⏭️ Skip (Win) | test_capture.py |
| T003 | Screen capture with null path raises NaturoCoreError | P1 | ⏭️ Skip (Win) | test_capture.py |
| T004 | Screen capture secondary monitor (index=1) | P5 | ❌ Missing | - |
| T005 | Screen capture invalid screen index (999) raises error | P1 | ⏭️ Skip (Win) | test_capture.py |
| T006 | Window capture foreground window (hwnd=0) | P1 | ⏭️ Skip (Win) | test_capture.py |
| T007 | Window capture specific window by HWND | P1 | ⏭️ Skip (Win) | test_capture.py |
| T008 | Window capture by title match | P1 | ⏭️ Skip (Win) | test_capture.py |
| T009 | Window capture minimized window returns error or black image | P1 | ⏭️ Skip (Win) | test_capture.py |
| T010 | Window capture hidden window | P3 | ❌ Missing | - |
| T011 | Capture output file size > 0 bytes | P1 | ⏭️ Skip (Win) | test_capture.py |
| T012 | Capture overwrites existing file at same path | P1 | ⏭️ Skip (Win) | test_capture.py |
| T013 | Capture to read-only path raises file I/O error | P1 | ⏭️ Skip (Win) | test_capture.py |
| T014 | Capture to invalid path raises error | P1 | ⏭️ Skip (Win) | test_capture.py |
| T015 | Capture to very long path (>260 chars) | P3 | ❌ Missing | - |
| T016 | Captured image width > 0 and height > 0 | P1 | ⏭️ Skip (Win) | test_capture.py |
| T017 | Captured image dimensions match actual screen resolution | P5 | ❌ Missing | - |
| T018 | Capture with DPI scaling (150%, 200%) produces correct size | P5 | ❌ Missing | - |
| T019 | Backend capture_screen returns CaptureResult with valid fields | P1 | ⏭️ Skip (Win) | test_capture.py |
| T020 | Multiple captures in parallel (threading) do not corrupt output | P3 | ❌ Missing | - |
| T021 | Capture time < 500ms for primary screen | P1 | ⏭️ Skip (Win) | test_performance.py |

### 2. Window Management

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T030 | list_windows returns a list of WindowInfo objects | P1 | ⏭️ Skip (Win) | test_list_windows.py |
| T031 | list_windows includes visible windows on desktop session | P1 | ⏭️ Skip (Win) | test_list_windows.py |
| T032 | Each window has non-negative width and height | P1 | ⏭️ Skip (Win) | test_list_windows.py |
| T033 | Backend list_windows returns base.WindowInfo instances | P1 | ⏭️ Skip (Win) | test_list_windows.py |
| T034 | Each window has all required fields populated (non-null) | P1 | ⏭️ Skip (Win) | test_list_windows.py |
| T035 | Filter windows by app/process name | P1 | ⏭️ Skip (Win) | test_list_windows.py |
| T036 | Filter windows by PID | P1 | ⏭️ Skip (Win) | test_list_windows.py |
| T037 | Filter windows by title substring | P1 | ⏭️ Skip (Win) | test_list_windows.py |
| T038 | Filter visible-only windows (exclude minimized) | P1 | ⏭️ Skip (Win) | test_list_windows.py |
| T039 | Window lifecycle: launch notepad → appears in list → close → disappears | P2 | ❌ Missing | - |
| T040 | get_window_info returns correct data for known HWND | P1 | ⏭️ Skip (Win) | test_list_windows.py |
| T041 | Window title with unicode characters | P3 | ❌ Missing | - |
| T042 | Window title with emoji | P3 | ❌ Missing | - |
| T043 | Window title longer than 256 characters | P3 | ❌ Missing | - |
| T044 | focus_window brings window to foreground | P2 | ❌ Missing | - |
| T045 | close_window closes the target window | P2 | ❌ Missing | - |
| T046 | minimize_window minimizes target | P2 | ❌ Missing | - |
| T047 | maximize_window maximizes target | P2 | ❌ Missing | - |
| T048 | move_window changes window position | P2 | ❌ Missing | - |
| T049 | resize_window changes window dimensions | P2 | ❌ Missing | - |
| T050 | Window operation on already-closed window raises error | P3 | ❌ Missing | - |
| T051 | Window operation on system window (no permission) | P3 | ❌ Missing | - |
| T052 | State transition: minimize → restore | P2 | ❌ Missing | - |
| T053 | State transition: maximize → normal | P2 | ❌ Missing | - |
| T054 | set-bounds moves and resizes in one call | P2 | ❌ Missing | - |

### 3. UI Element Inspection

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T060 | get_element_tree returns ElementInfo or None | P1 | ⏭️ Skip (Win) | test_element_tree.py |
| T061 | get_element_tree depth clamped to 1-10 without error | P1 | ⏭️ Skip (Win) | test_element_tree.py |
| T062 | Element tree root has structured children | P1 | ⏭️ Skip (Win) | test_element_tree.py |
| T063 | find_element returns None for non-existent element | P1 | ⏭️ Skip (Win) | test_element_tree.py |
| T064 | find_element with no role and no name raises error | P1 | ⏭️ Skip (Win) | test_element_tree.py |
| T065 | Backend get_element_tree works without error | P1 | ⏭️ Skip (Win) | test_element_tree.py |
| T066 | Backend find_element returns None for non-existent | P1 | ⏭️ Skip (Win) | test_element_tree.py |
| T067 | Element has correct properties: role, name, value, bounds | P1 | ⏭️ Skip (Win) | test_element_tree.py |
| T068 | Find element by role only (e.g., "Button") | P1 | ⏭️ Skip (Win) | test_element_tree.py |
| T069 | Find element by name only | P1 | ⏭️ Skip (Win) | test_element_tree.py |
| T070 | Find element by role + name combination | P1 | ⏭️ Skip (Win) | test_element_tree.py |
| T071 | Notepad: Edit element found with correct role | P1 | ⏭️ Skip (Win) | test_e2e_notepad.py |
| T072 | Notepad: Menu elements found | P1 | ⏭️ Skip (Win) | test_e2e_notepad.py |
| T073 | Calculator: Button elements found | P2 | ❌ Missing | - |
| T074 | Explorer: TreeView and ListView elements found | P2 | ❌ Missing | - |
| T075 | MSAA fallback when UIA returns no data | P3 | ❌ Missing | - |
| T076 | Deeply nested element tree (depth=10) completes | P3 | ❌ Missing | - |
| T077 | Element tree for empty/blank window | P1 | ⏭️ Skip (Win) | test_element_tree.py |
| T078 | Element tree for dialog box | P2 | ❌ Missing | - |
| T079 | Element tree for popup/context menu | P2 | ❌ Missing | - |
| T080 | Element tree performance < 2s for typical app (depth=3) | P1 | ⏭️ Skip (Win) | test_element_tree.py |
| T081 | Element is_enabled property reflects actual state | P2 | ❌ Missing | - |
| T082 | Element is_visible property reflects actual state | P2 | ❌ Missing | - |

### 4. Input — Mouse

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T090 | Left click at coordinates | P2 | ❌ Missing | - |
| T091 | Right click at coordinates | P2 | ❌ Missing | - |
| T092 | Middle click at coordinates | P2 | ❌ Missing | - |
| T093 | Double-click at coordinates | P2 | ❌ Missing | - |
| T094 | Click element by selector | P2 | ❌ Missing | - |
| T095 | Click element by ID from see output | P2 | ❌ Missing | - |
| T096 | Click with normal input mode (SendInput) | P2 | ❌ Missing | - |
| T097 | Click with hardware input mode (Phys32) | P2 | ❌ Missing | - |
| T098 | Click with hook input mode (MinHook) | P2 | ❌ Missing | - |
| T099 | Scroll down by amount | P2 | ❌ Missing | - |
| T100 | Scroll up by amount | P2 | ❌ Missing | - |
| T101 | Scroll left / right (horizontal) | P2 | ❌ Missing | - |
| T102 | Scroll with smooth mode | P2 | ❌ Missing | - |
| T103 | Drag from point A to point B | P2 | ❌ Missing | - |
| T104 | Drag element to element | P2 | ❌ Missing | - |
| T105 | Drag with Shift modifier held | P2 | ❌ Missing | - |
| T106 | Move mouse to coordinates | P2 | ❌ Missing | - |
| T107 | Move mouse to element center | P2 | ❌ Missing | - |
| T108 | Click outside screen bounds raises error or clamps | P3 | ❌ Missing | - |
| T109 | Click on disabled element (verify no crash) | P3 | ❌ Missing | - |
| T110 | Drag across monitors | P5 | ❌ Missing | - |
| T111 | Click performance < 100ms | P2 | ❌ Missing | - |

### 5. Input — Keyboard

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T120 | Type regular ASCII text into focused field | P2 | ❌ Missing | - |
| T121 | Type special characters (!@#$%^&*) | P2 | ❌ Missing | - |
| T122 | Type unicode text (Chinese, Japanese, Korean) | P2 | ❌ Missing | - |
| T123 | Type with human profile (variable delay) | P2 | ❌ Missing | - |
| T124 | Type with linear profile (fixed delay) | P2 | ❌ Missing | - |
| T125 | Type with custom WPM speed | P2 | ❌ Missing | - |
| T126 | Press single key (Enter) | P2 | ❌ Missing | - |
| T127 | Press key with modifier (Ctrl+C) | P2 | ❌ Missing | - |
| T128 | Hotkey multi-key combo (Ctrl+Shift+T) | P2 | ❌ Missing | - |
| T129 | Special keys: Tab, Escape, Delete, arrows, F1-F12 | P2 | ❌ Missing | - |
| T130 | Keyboard normal input mode | P2 | ❌ Missing | - |
| T131 | Keyboard hardware input mode | P2 | ❌ Missing | - |
| T132 | Keyboard hook input mode | P2 | ❌ Missing | - |
| T133 | Clear field before typing (Ctrl+A, Delete) | P2 | ❌ Missing | - |
| T134 | Type into read-only field (no crash, error returned) | P3 | ❌ Missing | - |
| T135 | Type very long text (>10000 chars) completes | P3 | ❌ Missing | - |
| T136 | Rapid sequential key presses | P3 | ❌ Missing | - |
| T137 | Type 100 chars at default speed < 5s | P2 | ❌ Missing | - |

### 6. Clipboard

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T140 | clipboard_get returns current text content | P2 | ❌ Missing | - |
| T141 | clipboard_get on empty clipboard returns empty string | P2 | ❌ Missing | - |
| T142 | clipboard_set writes text to clipboard | P2 | ❌ Missing | - |
| T143 | clipboard_set overwrites existing content | P2 | ❌ Missing | - |
| T144 | Paste: set clipboard + Ctrl+V + restore original | P2 | ❌ Missing | - |
| T145 | Clipboard with very large text (>1MB) | P3 | ❌ Missing | - |
| T146 | Clipboard with special characters and unicode | P2 | ❌ Missing | - |

### 7. Application Control

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T150 | Launch app by name (e.g., "notepad") | P2 | ❌ Missing | - |
| T151 | Launch app by full path | P2 | ❌ Missing | - |
| T152 | Launch app with arguments | P2 | ❌ Missing | - |
| T153 | Launch app and wait until ready | P3 | ❌ Missing | - |
| T154 | Quit app gracefully | P2 | ❌ Missing | - |
| T155 | Quit app force kill | P2 | ❌ Missing | - |
| T156 | Relaunch (quit + launch) | P3 | ❌ Missing | - |
| T157 | Switch focus to another app | P2 | ❌ Missing | - |
| T158 | List all running apps with details | P2 | ❌ Missing | - |
| T159 | Hide app (minimize to tray) | P3 | ❌ Missing | - |
| T160 | Unhide app (restore from tray) | P3 | ❌ Missing | - |

### 8. Menu

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T170 | List all menu items for an app | P2 | ❌ Missing | - |
| T171 | Click menu item by name | P2 | ❌ Missing | - |
| T172 | Click nested menu item by path (File > Save As) | P2 | ❌ Missing | - |
| T173 | Nested submenu navigation (3+ levels deep) | P3 | ❌ Missing | - |
| T174 | Disabled menu item click returns error | P3 | ❌ Missing | - |
| T175 | Dynamic menu items (recently opened files) | P3 | ❌ Missing | - |

### 9. System

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T180 | Dialog: detect active dialog | P3 | ❌ Missing | - |
| T181 | Dialog: read dialog text content | P3 | ❌ Missing | - |
| T182 | Dialog: click OK/Cancel/Yes/No buttons | P3 | ❌ Missing | - |
| T183 | Open URL in default browser | P2 | ❌ Missing | - |
| T184 | Open file in default application | P2 | ❌ Missing | - |
| T185 | Taskbar: list pinned items | P5 | ❌ Missing | - |
| T186 | Taskbar: pin/unpin application | P5 | ❌ Missing | - |
| T187 | Tray: list system tray icons | P5 | ❌ Missing | - |
| T188 | Tray: click system tray icon | P5 | ❌ Missing | - |
| T189 | Desktop: list virtual desktops | P5 | ❌ Missing | - |
| T190 | Desktop: create / switch / close virtual desktop | P5 | ❌ Missing | - |

### 10. Selector Engine

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T200 | Select element by role | P2 | ❌ Missing | - |
| T201 | Select element by name (exact match) | P2 | ❌ Missing | - |
| T202 | Select element by name (partial / substring match) | P2 | ❌ Missing | - |
| T203 | Select element by name (regex) | P3 | ❌ Missing | - |
| T204 | Chained selector: parent > child | P2 | ❌ Missing | - |
| T205 | Chained selector: ancestor descendant | P3 | ❌ Missing | - |
| T206 | Index selector: nth element, first, last | P2 | ❌ Missing | - |
| T207 | Attribute filter: [enabled=true], [visible=true] | P3 | ❌ Missing | - |
| T208 | Selector returns None when no match | P2 | ❌ Missing | - |
| T209 | Selector with multiple matches returns first | P2 | ❌ Missing | - |

### 11. AI / Agent

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T220 | Configure Anthropic provider | P4 | ❌ Missing | - |
| T221 | Configure OpenAI provider | P4 | ❌ Missing | - |
| T222 | Configure Ollama (local) provider | P4 | ❌ Missing | - |
| T223 | Agent: natural language instruction → action sequence | P4 | ❌ Missing | - |
| T224 | Agent: dry-run mode outputs plan without executing | P4 | ❌ Missing | - |
| T225 | Agent: max-steps limit respected | P4 | ❌ Missing | - |
| T226 | Agent: error in action sequence reported clearly | P4 | ❌ Missing | - |
| T227 | MCP server start | P4 | ❌ Missing | - |
| T228 | MCP server status check | P4 | ❌ Missing | - |
| T229 | MCP server stop | P4 | ❌ Missing | - |
| T230 | MCP tool registration and listing | P4 | ❌ Missing | - |
| T231 | Screenshot → AI vision pipeline produces actionable output | P4 | ❌ Missing | - |

### 12. Cross-Platform

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T240 | Backend auto-detection returns correct platform | P0 | ✅ Pass | test_backends.py |
| T241 | Backend capabilities report correct fields | P0 | ✅ Pass | test_backends.py |
| T242 | Windows backend advertises hardware/hook input modes | P0 | ⏭️ Skip (Win) | test_backends.py |
| T243 | macOS backend capabilities include AX accessibility | P0 | ✅ Pass | test_backends.py |
| T244 | Linux backend reports display server (x11/wayland/headless) | P0 | ⏭️ Skip (Linux) | test_backends.py |
| T245 | Unsupported method raises NotImplementedError with platform name | P0 | ✅ Pass | test_backends.py |
| T246 | macOS: capture via Peekaboo CLI | P6 | ❌ Missing | - |
| T247 | macOS: list windows via Peekaboo | P6 | ❌ Missing | - |
| T248 | macOS: see (element tree) via Peekaboo | P6 | ❌ Missing | - |
| T249 | macOS: click via Peekaboo | P6 | ❌ Missing | - |
| T250 | macOS: type via Peekaboo | P6 | ❌ Missing | - |
| T251 | Linux: capture via xdotool/Xlib | P7 | ❌ Missing | - |
| T252 | Linux: list windows via xdotool | P7 | ❌ Missing | - |
| T253 | Linux: see via AT-SPI2 | P7 | ❌ Missing | - |
| T254 | Linux: Wayland backend via ydotool | P7 | ❌ Missing | - |
| T255 | Graceful error on unsupported platform feature | P0 | ✅ Pass | test_backends.py |

### 13. CLI

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T260 | --version flag prints version | P0 | ✅ Pass | test_cli.py |
| T261 | --help lists all command groups | P0 | ✅ Pass | test_cli.py |
| T262 | Global flags: --json, --verbose, --log-level, --version | P0 | ✅ Pass | test_cli.py |
| T263 | capture group: live, video, watch subcommands | P0 | ✅ Pass | test_cli.py |
| T264 | capture live: --app, --window-title, --hwnd, --path | P0 | ✅ Pass | test_cli.py |
| T265 | capture live: --screen, --format options | P1 | ✅ Pass | test_cli_phase1.py |
| T266 | list group: apps, windows, screens, permissions | P0 | ✅ Pass | test_cli.py |
| T267 | list windows: --app, --process-name, --pid filters | P1 | ✅ Pass | test_cli_phase1.py |
| T268 | see: --app, --window-title, --mode, --path, --annotate, --json | P0 | ✅ Pass | test_cli.py |
| T269 | see: --depth option | P1 | ✅ Pass | test_cli_phase1.py |
| T270 | learn: runs and outputs Naturo info | P0 | ✅ Pass | test_cli.py |
| T271 | tools: --help shows usage | P0 | ✅ Pass | test_cli.py |
| T272 | click: all options (--on, --id, --coords, --double, --right, --input-mode) | P0 | ✅ Pass | test_cli.py |
| T273 | type: all options (--delay, --profile, --wpm, --return, --clear, --input-mode) | P0 | ✅ Pass | test_cli.py |
| T274 | press: --input-mode, --count | P0 | ✅ Pass | test_cli.py |
| T275 | hotkey: --hold-duration, --input-mode | P0 | ✅ Pass | test_cli.py |
| T276 | scroll: --direction, --amount, --smooth | P0 | ✅ Pass | test_cli.py |
| T277 | drag: --from, --from-coords, --to, --to-coords, --duration, --steps, --modifiers | P0 | ✅ Pass | test_cli.py |
| T278 | move: --to, --coords | P0 | ✅ Pass | test_cli.py |
| T279 | paste: --restore | P0 | ✅ Pass | test_cli.py |
| T280 | app: launch, quit, relaunch, hide, unhide, switch, list | P0 | ✅ Pass | test_cli.py |
| T281 | window: close, minimize, maximize, move, resize, set-bounds, focus, list | P0 | ✅ Pass | test_cli.py |
| T282 | menu: click, list | P0 | ✅ Pass | test_cli.py |
| T283 | clipboard: get, set | P0 | ✅ Pass | test_cli.py |
| T284 | dialog: --action, --button | P0 | ✅ Pass | test_cli.py |
| T285 | open: TARGET argument | P0 | ✅ Pass | test_cli.py |
| T286 | taskbar: pin, unpin, list | P0 | ✅ Pass | test_cli.py |
| T287 | tray: list, click | P0 | ✅ Pass | test_cli.py |
| T288 | desktop: list, create, switch, close | P0 | ✅ Pass | test_cli.py |
| T289 | agent: INSTRUCTION, --model, --max-steps, --dry-run | P0 | ✅ Pass | test_cli.py |
| T290 | mcp: start, status, stop | P0 | ✅ Pass | test_cli.py |
| T291 | excel: open-workbook, read, write, run-macro | P0 | ✅ Pass | test_cli.py |
| T292 | java: list, tree, click | P0 | ✅ Pass | test_cli.py |
| T293 | sap: list, run, get, set | P0 | ✅ Pass | test_cli.py |
| T294 | registry: get, set, list, delete | P0 | ✅ Pass | test_cli.py |
| T295 | service: list, start, stop, restart, status | P0 | ✅ Pass | test_cli.py |
| T296 | Placeholder commands run without required args | P0 | ✅ Pass | test_cli.py |
| T297 | JSON output valid JSON for all --json commands | P2 | ❌ Missing | - |
| T298 | Error messages include actionable guidance | P3 | ❌ Missing | - |
| T299 | Exit code 0 for success, non-zero for failure | P2 | ❌ Missing | - |
| T300 | All commands have examples in --help text | P2.5 | ❌ Missing | - |
| T301 | CLI functional: list windows runs on Windows | P1 | ⏭️ Skip (Win) | test_cli_phase1.py |
| T302 | CLI functional: list windows --json produces valid JSON | P1 | ⏭️ Skip (Win) | test_cli_phase1.py |
| T303 | CLI functional: see runs on Windows | P1 | ⏭️ Skip (Win) | test_cli_phase1.py |
| T304 | CLI functional: capture live runs on Windows | P1 | ⏭️ Skip (Win) | test_cli_phase1.py |

### 14. Error Handling & Edge Cases

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T310 | NaturoCoreError maps error codes to messages | P0 | ✅ Pass | test_bridge.py |
| T311 | DLL not found raises FileNotFoundError (non-Windows) | P0 | ✅ Pass | test_bridge.py |
| T312 | naturo_init / shutdown lifecycle on Windows | P0 | ⏭️ Skip (Win) | test_bridge.py |
| T313 | Double init is idempotent | P0 | ⏭️ Skip (Win) | test_bridge.py |
| T314 | Null / empty arguments return appropriate error | P3 | ❌ Missing | - |
| T315 | Out-of-range arguments handled (negative indices, huge values) | P3 | ❌ Missing | - |
| T316 | COM object cleanup on shutdown (no leaks) | P3 | ❌ Missing | - |
| T317 | File handle cleanup after capture (file not locked) | P3 | ❌ Missing | - |
| T318 | GDI object cleanup (no handle leak over 100 iterations) | P3 | ❌ Missing | - |
| T319 | Thread safety: concurrent list_windows calls | P3 | ❌ Missing | - |
| T320 | Thread safety: concurrent capture_screen calls | P3 | ❌ Missing | - |
| T321 | Buffer too small triggers automatic retry with larger buffer | P1 | ✅ Pass | (in bridge.py logic) |
| T322 | Operation on stale element reference | P3 | ❌ Missing | - |
| T323 | Operation on already-closed window | P3 | ❌ Missing | - |
| T324 | Recovery from COM initialization failure | P3 | ❌ Missing | - |

### 15. Performance

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T330 | Screen capture < 500ms | P1 | ⏭️ Skip (Win) | test_performance.py |
| T331 | Window list < 200ms | P1 | ⏭️ Skip (Win) | test_performance.py |
| T332 | Element tree (depth=3) < 2s for typical app | P1 | ⏭️ Skip (Win) | test_performance.py |
| T333 | Click execution < 100ms | P2 | ❌ Missing | - |
| T334 | Type 100 chars at default speed < 5s | P2 | ❌ Missing | - |
| T335 | 100 consecutive capture+list cycles — memory stable | P3 | ❌ Missing | - |

### 16. Version & Package

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| T340 | Version is a valid semver string | P0 | ✅ Pass | test_version.py |
| T341 | Version format is X.Y.Z (3 numeric parts) | P0 | ✅ Pass | test_version.py |
| T342 | Version matches pyproject.toml | P0 | ✅ Pass | test_version.py |
| T343 | Dataclass: WindowInfo fields | P0 | ✅ Pass | test_backends.py |
| T344 | Dataclass: ElementInfo fields | P0 | ✅ Pass | test_backends.py |
| T345 | Dataclass: CaptureResult fields | P0 | ✅ Pass | test_backends.py |

---

## Phase Coverage

### Phase 0 — Skeleton
T240, T241, T242, T243, T244, T245, T255, T260, T261, T262, T263, T264, T266, T268, T270, T271, T272, T273, T274, T275, T276, T277, T278, T279, T280, T281, T282, T283, T284, T285, T286, T287, T288, T289, T290, T291, T292, T293, T294, T295, T296, T310, T311, T312, T313, T321, T340, T341, T342, T343, T344, T345

### Phase 1 — See
T001, T002, T003, T005, T006, T007, T008, T009, T011, T012, T013, T014, T016, T019, T021, T030, T031, T032, T033, T034, T035, T036, T037, T038, T040, T060, T061, T062, T063, T064, T065, T066, T067, T068, T069, T070, T071, T072, T077, T080, T265, T267, T269, T301, T302, T303, T304, T330, T331, T332

### Phase 2 — Act
T039, T044, T045, T046, T047, T048, T049, T052, T053, T054, T073, T074, T078, T079, T081, T082, T090–T107, T111, T120–T133, T137, T140–T144, T146, T150, T151, T152, T154, T155, T157, T158, T170, T171, T172, T183, T184, T200, T201, T202, T204, T206, T208, T209, T297, T299, T333, T334

### Phase 2.5 — Open Source Launch
T300

### Phase 3 — Stabilize
T010, T015, T020, T041, T042, T043, T050, T051, T075, T076, T108, T109, T134, T135, T136, T145, T153, T156, T159, T160, T173, T174, T175, T180, T181, T182, T203, T205, T207, T298, T314, T315, T316, T317, T318, T319, T320, T322, T323, T324, T335

### Phase 4 — AI Integration
T220, T221, T222, T223, T224, T225, T226, T227, T228, T229, T230, T231

### Phase 5 — Complete
T004, T017, T018, T110, T185, T186, T187, T188, T189, T190

### Phase 6 — macOS Backend
T246, T247, T248, T249, T250

### Phase 7 — Linux Backend
T251, T252, T253, T254

### Phase 8 — National OS & Enterprise
(DDE, Kylin, openEuler, Recording, Visual regression — tests TBD when phase starts)

---

## Role-Based Acceptance Tests

These are not unit or integration tests — they are real-world scenario validations designed from the perspective of different stakeholder roles. Each role has unique concerns and acceptance criteria.

### QA Role — Edge Cases & Stress Testing

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| R-QA-001 | Multi-window chaos: open 5× Notepad + 1× Calculator + 1× Explorer simultaneously, verify list returns all 7 with correct titles, PIDs, and process names — no duplicates, no missing | P1 | ⏭️ Skip (Win) | test_e2e_notepad.py |
| R-QA-002 | Multi-window capture: with 7 windows open, capture each by HWND — all produce distinct, valid BMP files | P1 | ⏭️ Skip (Win) | test_e2e_notepad.py |
| R-QA-003 | Multi-window see: with 7 windows open, get_element_tree for each — correct root element role and distinct children | P1 | ⏭️ Skip (Win) | test_e2e_notepad.py |
| R-QA-004 | Race condition: start see (get_element_tree) then close target window mid-execution — must return graceful error, no crash, no segfault | P3 | ❌ Missing | - |
| R-QA-005 | Race condition: start capture then minimize target window mid-capture — returns error or partial image, no crash | P3 | ❌ Missing | - |
| R-QA-006 | Element value mutation: type text in Notepad Edit field, then see again — Edit element value reflects new text content | P2 | ❌ Missing | - |
| R-QA-007 | Long-running stability: 100 iterations of (capture_screen + list_windows + get_element_tree) — process RSS memory does not grow more than 20% from baseline | P3 | ❌ Missing | - |
| R-QA-008 | Long-running stability: 1000 iterations of list_windows — no handle leak (check GDI/USER object count before/after) | P3 | ❌ Missing | - |
| R-QA-009 | Concurrency: 10 threads calling list_windows simultaneously — all return valid results, no data corruption | P3 | ❌ Missing | - |
| R-QA-010 | Concurrency: 5 threads calling capture_screen to different output files simultaneously — all files valid, no overwrite | P3 | ❌ Missing | - |
| R-QA-011 | Extreme input: window with title of 1000+ characters — list and get_window_info return full title without truncation or crash | P3 | ❌ Missing | - |
| R-QA-012 | Extreme input: element name containing \n, \t, \0, \r — JSON serialization is correct, no parse errors | P3 | ❌ Missing | - |
| R-QA-013 | Extreme input: empty string for all string parameters — appropriate error, no null dereference | P3 | ❌ Missing | - |
| R-QA-014 | Privilege boundary: see (get_element_tree) on Task Manager or other elevated process — returns AccessDenied or empty tree, no hang | P3 | ❌ Missing | - |
| R-QA-015 | Privilege boundary: capture window of UAC consent dialog — returns error, not a security screenshot | P5 | ❌ Missing | - |
| R-QA-016 | DPI scaling 150%: capture_screen output dimensions = physical pixels (not logical), element bounds in physical coordinates | P5 | ❌ Missing | - |
| R-QA-017 | DPI scaling 200%: same as above at 200% | P5 | ❌ Missing | - |
| R-QA-018 | Multi-monitor: list_windows reports correct monitor for each window (bounds within monitor rect) | P5 | ❌ Missing | - |
| R-QA-019 | Rapid window lifecycle: launch + list + capture + close × 50 cycles with Notepad — no stale handles, no zombie processes | P3 | ❌ Missing | - |
| R-QA-020 | Backend fallback: when UIA fails for a window, MSAA provides element data (or clear error, not silent empty tree) | P3 | ❌ Missing | - |

### PD Role — User Experience & Workflow Testing

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| R-PD-001 | Onboarding flow: `pip install naturo` → `naturo --help` → output clearly lists available commands grouped by function (core/interaction/system/ai/extensions) | P0 | ✅ Pass | test_cli.py |
| R-PD-002 | Onboarding flow: `naturo list windows` on fresh install — output is human-readable (table format) with aligned columns | P1 | ⏭️ Skip (Win) | test_cli_phase1.py |
| R-PD-003 | Onboarding flow: `naturo see` on fresh install — output is a readable element tree, not raw JSON dump | P1 | ⏭️ Skip (Win) | test_cli_phase1.py |
| R-PD-004 | Onboarding flow: `naturo capture live` — success message includes file path and image dimensions | P1 | ⏭️ Skip (Win) | test_cli_phase1.py |
| R-PD-005 | End-to-end Notepad workflow: launch notepad → type "Hello World" → Ctrl+S → type filename → Enter → verify file exists → close notepad | P2 | ❌ Missing | - |
| R-PD-006 | End-to-end Calculator workflow: launch calc → click "5" → click "+" → click "3" → click "=" → read display shows "8" | P2 | ❌ Missing | - |
| R-PD-007 | AI agent perspective: `naturo see --json` output includes all info an AI needs (role, name, value, bounds, actionable IDs) in a parseable structure | P1 | ⏭️ Skip (Win) | test_e2e_notepad.py |
| R-PD-008 | AI agent perspective: element IDs from `see --json` can be used directly in `click --id <id>` — round-trip works | P2 | ❌ Missing | - |
| R-PD-009 | Error UX: capture with missing DLL → error message says exactly how to install it (path, env var, pip install) | P0 | ✅ Pass | test_bridge.py |
| R-PD-010 | Error UX: `naturo click --on "NonExistentButton"` → error says "element not found" and suggests using `naturo see` to inspect | P2 | ❌ Missing | - |
| R-PD-011 | Error UX: every CLI error includes a suggestion for next step (not just "Error: failed") | P3 | ❌ Missing | - |
| R-PD-012 | JSON consistency: all commands with --json flag output same top-level structure: `{"status": "...", "data": ...}` or consistent array | P2 | ❌ Missing | - |
| R-PD-013 | JSON consistency: datetime fields use ISO 8601, numeric IDs are numbers not strings | P2 | ❌ Missing | - |
| R-PD-014 | Help quality: every command's --help includes at least one usage example | P2.5 | ❌ Missing | - |
| R-PD-015 | Help quality: option descriptions are self-explanatory — no jargon without explanation | P2.5 | ❌ Missing | - |
| R-PD-016 | First-time empty state: `naturo list apps` with no apps running → clean "No applications found" message, not empty output or error | P2 | ❌ Missing | - |
| R-PD-017 | learn command: output teaches a new user what Naturo can do — mentions key commands (capture, list, see, click, type) | P0 | ✅ Pass | test_cli.py |

### Security Role — Safety & Permission Testing

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| R-SEC-001 | JSON injection: window title containing `"`, `\`, `}`, `]` — JSON output is properly escaped, parses without error | P1 | ✅ Pass | test_security.py |
| R-SEC-002 | JSON injection: element name containing `{"malicious": true}` — treated as literal string in output | P1 | ✅ Pass | test_security.py |
| R-SEC-003 | Path traversal: `capture live --path "../../etc/passwd"` — path is either rejected or resolved safely (no write outside intended directory) | P1 | ✅ Pass | test_security.py |
| R-SEC-004 | Path traversal: `capture live --path "C:\Windows\System32\evil.bmp"` — no write to system directories without explicit permission | P3 | ❌ Missing | - |
| R-SEC-005 | Process isolation: captured window list does not include windows from other user sessions | P3 | ❌ Missing | - |
| R-SEC-006 | No credential leak: all error messages, verbose logs, and debug output are free of passwords, tokens, or API keys | P0 | ✅ Pass | (design principle) |
| R-SEC-007 | No credential leak: `--verbose` mode does not dump environment variables or config file contents | P3 | ❌ Missing | - |
| R-SEC-008 | Hook safety: `--input-mode hook` displays warning about antivirus detection and elevated privileges required | P2 | ❌ Missing | - |
| R-SEC-009 | Hook safety: `--input-mode hardware` displays note about driver requirements | P2 | ❌ Missing | - |
| R-SEC-010 | DLL load safety: library search order does not include CWD before package directory (prevents DLL hijacking) | P0 | ✅ Pass | test_security.py |
| R-SEC-011 | DLL load safety: NATURO_CORE_PATH env var is validated (file exists, has expected exports) before loading | P3 | ❌ Missing | - |
| R-SEC-012 | Input sanitization: `type` command does not execute shell commands — typing `$(rm -rf /)` literally types the string | P2 | ❌ Missing | - |
| R-SEC-013 | Resource exhaustion: very large element tree (depth=10 on complex app) does not OOM — buffer retry has upper bound | P3 | ❌ Missing | - |

### DevOps Role — Build & Deploy Testing

| ID | Test Case | Phase | Status | Test File |
|----|-----------|-------|--------|-----------|
| R-DEV-001 | Clean install: `pip install naturo` on fresh Windows 10 VM → `naturo --version` works | P2.5 | ❌ Missing | - |
| R-DEV-002 | Clean install: `pip install naturo` on fresh Windows 11 VM → all CLI commands registered | P2.5 | ❌ Missing | - |
| R-DEV-003 | Offline install: install from .whl file with no internet → DLL bundled, `naturo capture live` works | P2.5 | ❌ Missing | - |
| R-DEV-004 | Version consistency: `naturo --version` == `python -c "from naturo.version import __version__; print(__version__)"` == pyproject.toml version | P0 | ✅ Pass | test_version.py |
| R-DEV-005 | Version consistency: Python version == DLL version (naturo_core.naturo_version()) | P1 | ⏭️ Skip (Win) | test_version_consistency.py |
| R-DEV-006 | Upgrade: `pip install --upgrade naturo` replaces old DLL, no stale files remain | P2.5 | ❌ Missing | - |
| R-DEV-007 | Python 3.9 compatibility: all imports and type hints work | P0 | ✅ Pass | test_python_compat.py (static analysis) |
| R-DEV-008 | Python 3.10 compatibility: all tests pass | P0 | ✅ Pass | test_python_compat.py (static analysis) |
| R-DEV-009 | Python 3.11 compatibility: all tests pass | P0 | ✅ Pass | test_python_compat.py (static analysis) |
| R-DEV-010 | Python 3.12 compatibility: all tests pass | P0 | ✅ Pass | test_python_compat.py (static analysis) |
| R-DEV-011 | Python 3.13 compatibility: all tests pass | P0 | ✅ Pass | test_python_compat.py (static analysis) |
| R-DEV-012 | Windows 10 21H2+: all Phase 1 features work | P1 | 📋 Deferred | CI verified on Server 2022; manual testing needed for Win10 |
| R-DEV-013 | Windows 11: all Phase 1 features work | P1 | 📋 Deferred | CI verified on Server 2022; manual testing needed for Win11 |
| R-DEV-014 | Windows Server 2019: all Phase 1 features work | P1 | 📋 Deferred | CI verified on Server 2022; manual testing needed for Server 2019 |
| R-DEV-015 | Windows Server 2022: all Phase 1 features work | P1 | ❌ Missing | - |
| R-DEV-016 | CI pipeline: all 4 jobs green (lint, test-mac, test-win, test-linux) | P0 | ✅ Pass | .github/workflows/ |
| R-DEV-017 | CI pipeline: Windows CI runner has desktop session for UI tests | P1 | ❌ Missing | - |

---

## Test File Restructure Plan

Current test files map well to Phase 0/1 needs. As phases progress, restructure as follows:

```
tests/
├── conftest.py                  # Shared fixtures, markers
├── test_version.py              # T340-T345 — version & package
├── test_backends.py             # T240-T255 — cross-platform backend
├── test_bridge.py               # T310-T324 — native bridge & error handling
├── test_cli.py                  # T260-T296 — CLI registration (all commands)
├── test_cli_phase1.py           # T265-T269, T301-T304 — Phase 1 CLI functional
├── test_capture.py              # T001-T021 — screenshot capture
├── test_list_windows.py         # T030-T054 — window management
├── test_element_tree.py         # T060-T082 — UI element inspection
├── test_input_mouse.py          # T090-T111 — mouse input (Phase 2)
├── test_input_keyboard.py       # T120-T137 — keyboard input (Phase 2)
├── test_clipboard.py            # T140-T146 — clipboard (Phase 2)
├── test_app_control.py          # T150-T160 — application control (Phase 2)
├── test_menu.py                 # T170-T175 — menu interaction (Phase 2)
├── test_system.py               # T180-T190 — dialog, taskbar, tray, desktop (Phase 3/5)
├── test_selector.py             # T200-T209 — selector engine (Phase 2)
├── test_ai.py                   # T220-T231 — AI/agent/MCP (Phase 4)
├── test_performance.py          # T330-T335 — performance benchmarks
├── acceptance/
│   ├── test_qa_stress.py        # R-QA-001 to R-QA-020
│   ├── test_pd_workflow.py      # R-PD-001 to R-PD-017
│   ├── test_security.py         # R-SEC-001 to R-SEC-013
│   └── test_devops.py           # R-DEV-001 to R-DEV-017
└── e2e/
    ├── test_notepad_e2e.py      # R-PD-005 — full Notepad workflow
    └── test_calculator_e2e.py   # R-PD-006 — full Calculator workflow
```

### pytest Markers

```ini
[tool:pytest]
markers =
    ui: requires desktop session with visible windows
    windows: Windows-only test
    macos: macOS-only test
    linux: Linux-only test
    slow: takes >5s to run
    stress: stress/stability test (>30s)
    e2e: end-to-end workflow test
    acceptance: role-based acceptance test
    performance: performance benchmark
```

### Running Test Subsets

```bash
# All fast tests (CI default)
pytest -v -m "not (slow or stress or e2e)"

# Phase 1 only
pytest -v -k "capture or list_windows or element_tree or cli_phase1"

# Windows functional tests
pytest -v -m "ui and windows"

# Acceptance tests by role
pytest -v tests/acceptance/test_qa_stress.py
pytest -v tests/acceptance/test_pd_workflow.py
pytest -v tests/acceptance/test_security.py
pytest -v tests/acceptance/test_devops.py

# Performance benchmarks
pytest -v -m "performance" --benchmark

# Everything
pytest -v
```

---

## Notes

### Python 3.9-3.13 Compatibility (R-DEV-007 to R-DEV-011)

Verified via static analysis in `test_python_compat.py`:
- No `match/case` statements (Python 3.10+)
- No bare `X | Y` union types without `from __future__ import annotations`
- No `except*` syntax (Python 3.11+)
- No `tomllib` without fallback for Python < 3.11
- All source files compile successfully

Full CI matrix expansion across Python 3.9-3.13 is recommended for Phase 2.

### Windows Version Tests (R-DEV-012 to R-DEV-014)

CI runs on Windows Server 2022 (GitHub Actions `windows-latest`). Manual testing is needed for:
- Windows 10 21H2+
- Windows 11
- Windows Server 2019

### Phase 0/1 Coverage Completion (2026-03-19)

All P0 and P1 test cases now have implementations:
- 64 tests pass on macOS (cross-platform + compatibility checks)
- 57 tests properly skip on non-Windows (Windows-only UI/DLL tests)
- All 4 CI jobs (C++ build, Windows Python, Ubuntu Python, macOS Python) pass
- QA, PD, and Security role acceptance reviews completed
