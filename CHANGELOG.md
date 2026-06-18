# Changelog

All notable changes to Naturo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Worktree-integrity import guard (opt-in)** — when `NATURO_EXPECTED_ROOT` is set, importing `naturo` (or running `python -m naturo`) fails loudly with a `WORKTREE_MISMATCH` error if the resolved package is not under that root. This catches a stale editable install (egg-link/`.pth`) silently shadowing the checkout under test with a sibling worktree's code, which would otherwise let runtime verification validate the wrong source and emit confident false verdicts. The guard is a no-op for ordinary installs (the variable is unset), so it only affects the multi-worktree agent harness that sets it. The fix for the install itself is environment-only and tracked separately ([#969](https://github.com/AcePeak/naturo/issues/969)); this is the code-only loud-failure companion ([#971](https://github.com/AcePeak/naturo/issues/971))

### Fixed
- **`get`/`set` stale-ref error envelope is now dispatchable** — `naturo -j get eN` / `set eN value` against an element ref absent from the snapshot cache previously returned `{code: "UNKNOWN_ERROR"}` with no `suggested_action`, so machine consumers could not branch on `error.code` nor read a recovery hint. Both raise sites now emit a dedicated `STALE_SNAPSHOT_CACHE` code plus `suggested_action: "Run 'naturo see' to capture a fresh element snapshot, then retry."` and `recoverable: true`. The human message and exit code are unchanged. Continues the error-envelope normalization of [#993](https://github.com/AcePeak/naturo/issues/993) ([#877](https://github.com/AcePeak/naturo/issues/877))
- **Optional-dependency install prompt no longer leaks into `-j` JSON output** — when a feature's optional package is missing (e.g. `pyvda` for `naturo desktop`), `naturo -j desktop list` previously printed the human prompt `Install it now? [Y/n]:` to stdout *before* the JSON envelope, so `json.loads` failed. `ensure_package` now takes a `json_output` flag and, in JSON mode, never prompts and never writes prose to stdout — emitting only the `{success: false, error: {code: "MISSING_DEPENDENCY", ...}}` envelope (exit 1). Gating is on the explicit flag rather than `sys.stdin.isatty()` because on Windows a DEVNULL-redirected child still reports a TTY, so a TTY check alone leaked for correctly-behaved agents too. The `@requires_package` decorator forwards the command's `json_output` automatically, so future optional-dep paths inherit the fix. Non-JSON behaviour is unchanged ([#869](https://github.com/AcePeak/naturo/issues/869))
- **Global `-j/--json` honoured on Click eager paths** — `naturo -j --version` now emits `{success: true, version: "..."}`, `naturo -j --help` emits `{success: true, help: {usage, commands, options}}`, and `naturo -j <unknown-command>` emits `{success: false, error: {code: "UNKNOWN_COMMAND", ...}}` with exit code 1 (runtime-error contract) instead of Click's plain-text banner and exit 2. Click resolves `--version`/`--help` and unknown commands before any naturo command runs, so the console-script entry point now wraps the group to close that gap; all other invocations are byte-for-byte unchanged. Top-level twin of the subcommand-level [#872](https://github.com/AcePeak/naturo/issues/872) ([#874](https://github.com/AcePeak/naturo/issues/874))
- **Top-level `count` in `list windows` and `list screens` JSON** — `naturo -j list windows` now emits `{success, windows, count}` and `naturo -j list screens` now emits `{success, monitors, count}` (both previously omitted `count`), matching their `window list` / `app windows` counterparts. Scripted wrappers no longer need to special-case these two endpoints. Text output is unchanged. Continues the read-command envelope normalization of [#876](https://github.com/AcePeak/naturo/issues/876) / [#977](https://github.com/AcePeak/naturo/issues/977) ([#980](https://github.com/AcePeak/naturo/issues/980))
- **Consistent JSON success envelope for `visual list` and `selector show`** — `naturo -j visual list` now emits `{success, baselines, count}` (was a bare `{baselines: [...]}`), and `naturo -j selector show <app>` now emits `{success, app, selectors, builtin, count}`; a nonexistent app fails loudly with `{success: false, error}` and exit 1 instead of being indistinguishable from an existing app with zero selectors. Completes the read-command envelope normalization started in [#876](https://github.com/AcePeak/naturo/issues/876) ([#977](https://github.com/AcePeak/naturo/issues/977))
- **Unicode capture paths regardless of native build** — `capture_screen` / `capture_window` again write to output paths containing non-ASCII characters (e.g. a Chinese/Japanese Windows username or folder in `%TEMP%`). The native core's Unicode fix ([#693](https://github.com/AcePeak/naturo/pull/693)) lives in source but the shipped DLL can lag a rebuild; the Python bridge now stages such captures through an ASCII-only temp file and moves the result to the requested path, so Unicode paths work independent of the native build ([#777](https://github.com/AcePeak/naturo/issues/777))
- **NO_DESKTOP_SESSION silent-failure cluster** — `app windows`, `dialog detect`, `taskbar list`, `tray list`, `wait --gone` (CLI) and `capture_screen`, `list_windows`, `list_apps`, `app_inspect`, `capture_window`, `list_monitors` (MCP) no longer return fabricated success (empty arrays, all-black PNGs, stale window lists) without a desktop session. The session guard is now enforced structurally at the shared entrypoint and these surfaces fail loudly with `NO_DESKTOP_SESSION` (exit 1 / `isError:true`) ([#885](https://github.com/AcePeak/naturo/issues/885), [#868](https://github.com/AcePeak/naturo/issues/868), [#875](https://github.com/AcePeak/naturo/issues/875), [#878](https://github.com/AcePeak/naturo/issues/878), [#883](https://github.com/AcePeak/naturo/issues/883), [#893](https://github.com/AcePeak/naturo/issues/893))

## [0.3.1] — 2026-03-31

### Added
- AI vision cascade: window capture, coordinate scaling, tree merge ([#694](https://github.com/AcePeak/naturo/pull/694), [#701](https://github.com/AcePeak/naturo/pull/701))
- Input strategy refactor ([#412](https://github.com/AcePeak/naturo/issues/412), [#692](https://github.com/AcePeak/naturo/pull/692))
- MCP click resolves eN refs ([#682](https://github.com/AcePeak/naturo/issues/682), [#688](https://github.com/AcePeak/naturo/pull/688))

### Fixed
- Highlight DPI positioning fix ([#662](https://github.com/AcePeak/naturo/issues/662), [#687](https://github.com/AcePeak/naturo/pull/687))
- Click snapshot alignment ([#687](https://github.com/AcePeak/naturo/pull/687))
- AI vision JSON parsing — code fence regex, tuple bounds ([#691](https://github.com/AcePeak/naturo/pull/691))
- Unicode file paths in capture ([#693](https://github.com/AcePeak/naturo/pull/693))
- CI UIA detection regression fix ([#683](https://github.com/AcePeak/naturo/issues/683), [#690](https://github.com/AcePeak/naturo/pull/690))

### Removed
- Remove dead _learn.py ([#686](https://github.com/AcePeak/naturo/issues/686), [#689](https://github.com/AcePeak/naturo/pull/689))

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
- **Auto-routing for action commands** — intelligent command dispatch ([#28](https://github.com/AcePeak/naturo/issues/28))
- **`naturo get` command** — read element text/value via UIA patterns ([#109](https://github.com/AcePeak/naturo/issues/109))
- **Version bump script** — `scripts/bump_version.py` for release automation ([#30](https://github.com/AcePeak/naturo/issues/30))

### Fixed
- `find --all` flag for SSH-safe wildcard search ([#112](https://github.com/AcePeak/naturo/issues/112))
- `list apps` now correctly delegates to `app list` ([#114](https://github.com/AcePeak/naturo/issues/114))
- `find --actionable` works without QUERY; `press --json` returns proper error ([#123](https://github.com/AcePeak/naturo/issues/123), [#124](https://github.com/AcePeak/naturo/issues/124))
- Standardized `get` command JSON error format ([#121](https://github.com/AcePeak/naturo/issues/121))
- `find --query` option and improved SSH desktop detection ([#112](https://github.com/AcePeak/naturo/issues/112), [#113](https://github.com/AcePeak/naturo/issues/113))
- Missing `--method` override code in interaction.py

### Tests
- Integration test suite for Unified App Model ([#37](https://github.com/AcePeak/naturo/issues/37))
- Method override tests ([#34](https://github.com/AcePeak/naturo/issues/34) partially)

### Docs
- Enforce PR workflow, no direct push to main

## [0.2.0] — 2026-03-22

### Added
- **App inspect** — probe app frameworks + interaction methods ([#27](https://github.com/AcePeak/naturo/issues/27))
- **Detection chain orchestrator** with public API + 35 tests ([#26](https://github.com/AcePeak/naturo/issues/26))
- **Unified Selector system** — format spec + roadmap + issues
- **`app_inspect` MCP tool** for framework detection ([#36](https://github.com/AcePeak/naturo/issues/36) partial)

### Breaking
- Removed 12 non-core commands — focus on Eyes+Hands

### Fixed
- Unified error handling for headless/SSH environments ([#99](https://github.com/AcePeak/naturo/issues/99))
- Filter system processes from app list, show only user apps with windows ([#98](https://github.com/AcePeak/naturo/issues/98))
- DPI handling via `SetThreadDpiAwarenessContext` for reliable coordinates ([#16](https://github.com/AcePeak/naturo/issues/16))
- `open_uri` uses Popen for URLs to avoid blocking ([#31](https://github.com/AcePeak/naturo/issues/31))
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
