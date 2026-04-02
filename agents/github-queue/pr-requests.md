# PR Requests Queue

Dev-Sirius writes PR requests here when GitHub tools are unavailable.
Orc-Mycelium processes them and creates the actual PRs.

Format:
```
## PR Request: <branch-name>
- **Base**: develop
- **Title**: <type>: <description> (fixes #N)
- **Body**: <what changed, how tested>
- **Auto-merge**: yes
- **Date**: YYYY-MM-DD
- **Status**: pending | created (PR #X) | conflict
```

---

## PR Request: fix/issue-776-app-id-promotion
- **Base**: develop
- **Title**: fix: promote --app aN to --app-id in window/dialog/desktop commands (fixes #776)
- **Body**: The #752 fix added app ID pattern detection (`--app a1` → `--app-id a1`) to core and interaction commands but missed window_cmd (8 commands), dialog_cmd (5 commands), and desktop_cmd (1 command). Users passing `--app a1` to these commands got silent failure because fuzzy process-name matching was used instead of app ID resolution. Added `maybe_promote_app_to_app_id` call before `resolve_app_id_to_hwnd` in all 14 affected call sites. Tests: 2 new tests verify promotion in window focus and dialog detect. Full suite: 3804 passed, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: merged into develop (commit 30c9d53)

## PR Request: docs/issue-774-roadmap-browser-scope
- **Base**: develop
- **Title**: docs: update ROADMAP.md with v0.3.1 shipped features and v0.3.2 browser scope (fixes #774)
- **Body**: Added v0.3.1 section documenting the quality sprint (15+ bug fixes), AI vision improvements (model registry, provider CLI params), and input enhancements (mouse trajectories, strategy pattern). Added v0.3.2 section with browser automation scope (9 issues from #758-#766). No code changes.
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: merged into develop (commit 8c80357)

## PR Request: fix/trajectory-and-registry-quality
- **Base**: develop
- **Title**: fix: consistent rounding in trajectory + model registry edge cases
- **Body**: Fixes rounding inconsistencies in trajectory point generation and adds edge case handling to the model registry. Changes: trajectory rounding made consistent (4 lines in _trajectory.py), model registry edge cases handled (8 lines in model_registry.py). Tests: 40 new lines in test_model_registry.py, 46 new lines in test_trajectory.py. All tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: merged into develop (commit f678381)

## PR Request: refactor/config-cmd-deduplicate-credentials
- **Base**: develop
- **Title**: refactor: deduplicate credential functions in config_cmd.py
- **Body**: config_cmd.py had private _load_credentials(), _save_credentials(), and _CREDENTIALS_PATH that duplicated the public API in naturo.config. Replaced with imports from naturo.config to ensure consistent behavior (e.g. debug logging on read failure) and reduce maintenance burden. Removed 31 lines of duplicate code. Tests updated to use naturo.config directly. All 25 config_cmd tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: pending (branch recreated and force-pushed 2026-04-01)

## PR Request: docs/issue-721-example-scripts
- **Base**: develop
- **Title**: docs: create working example scripts (fixes #721)
- **Body**: Five working example scripts covering core naturo automation patterns: notepad_hello.py (app lifecycle + typing + dialog), window_capture.py (bulk screenshots with JSON parsing), ui_inspector.py (interactive UI tree exploration), form_filler.py (form field filling with Calculator demo), agent_demo.py (AI agent integration via CLI loop, MCP, and AI vision). Updated examples/README.md with usage instructions and common patterns. All scripts are ruff-clean and mypy-clean, Python 3.9+ compatible.
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: merged into develop (PR #790, commit a05a2cb)

## PR Request: docs/issue-721-example-scripts (round 2)
- **Base**: develop
- **Title**: docs: create working example scripts (fixes #721)
- **Body**: (superseded by round 1 merge)
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: superseded — already merged as PR #790

## PR Request: docs/issue-722-mcp-server-reference
- **Base**: develop
- **Title**: docs: create dedicated MCP server reference (fixes #722)
- **Body**: Comprehensive reference for all 58 MCP tools across 11 modules (capture, window, UI inspection, input, app control, wait, snapshot, clipboard, dialog, system, Excel). Includes setup instructions for stdio/SSE/HTTP transports, parameter details, common patterns, error handling, and a worked Notepad automation example.
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: merged into develop (PR #791, commit 6b01b95)

## PR Request: refactor/issue-719-cli-by-domain
- **Base**: develop
- **Title**: refactor: reorganize CLI commands by domain (fixes #719)
- **Body**: Moved system commands (clipboard, dialog, desktop, taskbar, tray) into `cli/system/` subdirectory and value commands (get, set) into `cli/values/`, following the existing pattern established by `cli/core/` and `cli/interaction/`. Renamed `system.py` to `_app_group.py` (it only defines the app Click group stub) and removed 100+ lines of dead code (unused menu, taskbar, tray stubs superseded by dedicated cmd files). All test mock patch paths updated. 4166 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: pending

## PR Request: feat/issue-762-browser-wait-mechanisms
- **Base**: develop
- **Title**: feat: add browser wait mechanisms — navigation, URL, function, network idle (fixes #762)
- **Body**: Four new BrowserPage methods: wait_for_navigation (URL change + load), wait_for_url (substring/regex match), wait_for_function (JS expression polling), wait_for_network_idle (resource count stabilisation). Four corresponding CLI commands: wait-navigation, wait-url, wait-function, wait-network-idle. Public wait_for_network_idle replaces the private _wait_for_network_idle with a proper implementation using performance.getEntriesByType polling. 11 unit tests covering success and timeout paths. All 4184 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: pending

## PR Request: feat/issue-758-chrome-profiles
- **Base**: develop
- **Title**: feat: add Chrome profile management — launch, list, delete (fixes #758)
- **Body**: New `_launcher.py` module with Chrome/Chromium auto-discovery across Windows/Mac/Linux, profile-based user-data directories (`~/.config/naturo/browser-profiles/<name>/`), and CDP startup health check. ChromeProcess wrapper for graceful termination. Three new CLI commands: `browser launch` (--profile, --headless, --chrome-path, --extra-args), `browser profiles` (list with size/date), `browser profile-delete` (with --force). 37 new tests, all mocked (no desktop needed). Ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending (branch re-created and force-pushed 2026-04-02)

## PR Request: feat/issue-760-anti-detection
- **Base**: develop
- **Title**: feat: add anti-detection defaults — stealth flags and JS patches (fixes #760)
- **Body**: New `_stealth.py` module with Chrome launch flags (disable AutomationControlled, infobars, extensions, realistic window size) and 6 runtime JS patches (navigator.webdriver, plugins, languages, permissions, chrome.runtime, WebGL vendor). Patches registered via `Page.addScriptToEvaluateOnNewDocument` for persistence across navigations. Two CLI commands: `browser stealth` (apply to running browser), `browser stealth-flags` (print flags for manual launch). 18 new tests, all mocked. Ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: merged into develop (PR #794, commit 22d0234)

## PR Request: feat/issue-764-iframe-support
- **Base**: develop
- **Title**: feat: add iframe support — frame listing, context switching (fixes #764)
- **Body**: BrowserPage gains `frames()` and `frame(selector)` methods for navigating iframe hierarchies. Frame context uses `Page.createIsolatedWorld` so `evaluate`/`find`/`find_all` execute inside the target iframe. Supports nested frames with URL matching. One CLI command: `browser frames` (list all frames). 17 new tests, all mocked. Ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending (branch re-created and force-pushed 2026-04-02)

## PR Request: feat/issue-765-network-interception
- **Base**: develop
- **Title**: feat: add network request interception — monitor, intercept, mock (fixes #765)
- **Body**: New `_network.py` module with `NetworkMonitor` class wrapping CDP Network domain. Features: `capture_snapshot` (performance API), `find_requests` (glob filtering), `intercept` (abort/fulfill), `abort_pattern`/`mock_response` shorthands, JS-based injection. `BrowserPage.network` property for lazy access. Two CLI commands: `browser requests` (list with filters) and `browser intercept` (add rules). 20 unit tests, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: merged into develop (PR #798, commit bbb6795)

## PR Request: feat/issue-761-captcha-handling
- **Base**: develop
- **Title**: feat: add captcha handling architecture — detect, solve, inject (fixes #761)
- **Body**: Pluggable captcha solver pattern with `CaptchaManager`, `CaptchaSolver` ABC, and two built-in solvers: `ManualSolver` (polls for user solution) and `TokenInjectionSolver` (injects pre-obtained tokens from external services). Detection via JS covers reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile, and generic iframe captchas. Two CLI commands: `browser captcha-detect` and `browser captcha-solve` (--solver manual|token:TOKEN). 37 unit tests, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending (branch re-created and force-pushed 2026-04-02)

## PR Request: fix/issue-785-uwp-launch-pid
- **Base**: develop
- **Title**: fix: resolve real app PID after Windows cmd /c start launch (fixes #785)
- **Body**: (see round 2 below)
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: merged into develop (PR #801, commit 7c19b68)

## PR Request: fix/issue-784-type-newline-drop
- **Base**: develop
- **Title**: fix: send Enter/Tab for control chars in keystroke simulation (fixes #784)
- **Body**: (merged)
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: merged into develop (PR #800, commit b032097)

## PR Request: feat/issue-723-cost-guardrails
- **Base**: develop
- **Title**: ops: add cost guardrails for scheduled agents (fixes #723)
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: superseded by round 3

## PR Request: test/browser-cmd-coverage
- **Base**: develop
- **Title**: test: add 56 tests for browser CLI subcommands
- **Body**: Covers all 16 browser commands (navigate, find, click, type, text, attr, html, screenshot, eval, url, title, wait, tabs, tab, scroll, hover, close) plus group options and connection error handling. All tests use mocked BrowserPage — no Chrome required. 4222 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: pending

## PR Request: fix/issue-776-app-id-promotion (round 2)
- **Base**: develop
- **Title**: fix: resolve app IDs (a1, a2, …) in all app subcommands (fixes #776)
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: superseded — merged as PR #799 (round 4)

## PR Request: feat/issue-762-browser-wait
- **Base**: develop
- **Title**: feat: add browser wait mechanisms — navigation, URL, function, network idle (fixes #762)
- **Body**: Four new BrowserPage methods: wait_for_navigation (URL change + load), wait_for_url (substring/regex match), wait_for_function (JS expression polling), wait_for_network_idle (resource count stabilisation using performance.getEntriesByType). Four corresponding CLI commands: wait-navigation, wait-url, wait-function, wait-network-idle. 13 unit tests covering success and timeout paths. Ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-776-app-subcommands
- **Base**: develop
- **Title**: fix: resolve app IDs (a1, a2, …) in all app subcommands (fixes #776)
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: superseded — merged as PR #799 (round 4)

## PR Request: test/browser-page-element-coverage
- **Base**: develop
- **Title**: test: add 76 tests for BrowserPage and BrowserElement (CDP mocked)
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: merged into develop (PR #803, commit dddff8d)

## PR Request: fix/issue-776-app-subcommands (round 3)
- **Base**: develop
- **Title**: fix: resolve app IDs (a1, a2, …) in all app subcommands (fixes #776)
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: superseded — merged as PR #799 (round 4)

## PR Request: fix/issue-785-uwp-launch-pid (round 2)
- **Base**: develop
- **Title**: fix: resolve real app PID after cmd /c start launch (fixes #785)
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: superseded — merged as PR #801 (round 1)

## PR Request: feat/issue-723-cost-guardrails (round 2)
- **Base**: develop
- **Title**: ops: add cost guardrails for scheduled agents (fixes #723)
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: superseded by round 3

## PR Request: fix/issue-776-app-subcommands (round 4)
- **Base**: develop
- **Title**: fix: resolve app IDs (a1, a2, …) in all app subcommands (fixes #776)
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: merged into develop (PR #799, commit f7f2ca8)

## PR Request: feat/issue-723-cost-guardrails (round 3)
- **Base**: develop
- **Title**: ops: add cost guardrails for scheduled agents (fixes #723)
- **Body**: Daily run limit (default 20/day) per agent, consecutive failure auto-pause (default 3), global pause_all emergency switch, and notification thresholds. Config in agents/config/cost-guardrails.yaml with per-agent budgets for Dev-Sirius and QA-Mariana. 11 tests validate config structure and value constraints.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: docs/issue-721-example-scripts (round 2)
- **Base**: develop
- **Title**: docs: create working example scripts (fixes #721)
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: superseded — merged as PR #790 (round 1)

## PR Request: fix/issue-788-stale-pid-hwnd
- **Base**: develop
- **Title**: fix: detect stale PID/HWND after app restart, fall back to process name (fixes #788)
- **Body**: After an app restarts, cached app-ID entries (HWND + PID) become stale. Returning them caused focus_window/SendInput to silently drop keystrokes. Two-layer fix: (1) _resolve_app_id validates PID liveness via OpenProcess/kill(0); when dead, extracts process-name basename for live window enumeration. (2) _resolve_hwnd validates HWND with IsWindow(); raises WindowNotFoundError or falls through to PID/name resolution. 6 new tests (PID alive/dead, path stripping, HWND validation). Existing tests updated to mock _is_pid_alive. 4334 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-789-app-filter-basename
- **Base**: develop
- **Title**: fix: extract process basename before --app matching (fixes #789)
- **Body**: process_name from the C++ bridge includes the full executable path (e.g. C:\Windows\System32\notepad.exe). The --app filter did substring matching against the full path, so `--app system` would incorrectly match any process in System32. Now uses ntpath.basename() to extract just the filename before matching in _resolve_hwnd, _resolve_hwnds, and _afh_has_content_window. 6 new tests covering path components, basename exact/substring, and _resolve_hwnds. 4334 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-781-json-exit-code
- **Base**: develop
- **Title**: fix: exit non-zero when JSON mode reports failure (fixes #781)
- **Body**: selector clear, selector export, and visual report emitted {"success": false} JSON but exited with code 0. Automation scripts relying on exit codes could not detect failure. Changed `return` to `sys.exit(1)` in all three affected locations, matching the pattern used by every other error path in the CLI. 6 new tests. 4334 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-787-coords-bounds
- **Base**: develop
- **Title**: fix: reject out-of-bounds click coordinates with clear error (fixes #787)
- **Body**: click --coords silently accepted coordinates outside the virtual screen, resulting in no-op clicks. Now validates against GetSystemMetrics (Windows) or a 65535 generic bound (non-Windows). Out-of-bounds coordinates produce a COORDS_OUT_OF_BOUNDS error in both JSON and text modes. 6 new tests. 4334 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-786-uwp-menu-click
- **Base**: develop
- **Title**: fix: detect WinUI 3 apps for UIA click path (fixes #786)
- **Body**: WinUI 3 apps (Win11 Notepad, Paint) run as standalone processes, not under ApplicationFrameHost. The UIA click path was only triggered for AFH-hosted apps, so menu items in WinUI 3 apps were clicked via SendInput which doesn't reliably reach XAML content. Added `_is_winui_window()` that detects DesktopWindowXamlSource child windows. When detected, click uses UIA ExpandCollapsePattern/InvokePattern instead of SendInput. 4 new tests, 3 existing tests updated. 4215 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-783-json-duplicate-stderr
- **Base**: develop
- **Title**: fix: suppress stderr output in JSON mode (fixes #783)
- **Body**: Python's logging lastResort handler emits WARNING+ to stderr when no handlers are configured. In JSON mode, this caused human-readable error text to mix with JSON stdout, breaking piping workflows. Three-part fix: (1) add NullHandler to root logger when --json is active, (2) downgrade routing.py app-not-found from WARNING to DEBUG (caller handles the condition), (3) downgrade press focus-failure from WARNING to DEBUG. 4 new tests. 4215 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: feat/issue-760-stealth-check
- **Base**: develop
- **Title**: feat: add browser stealth-check verification command (fixes #760)
- **Body**: New `check_stealth()` function runs 6 JS checks (webdriver, plugins, languages, chrome.runtime, WebGL vendor, permissions) against the browser and reports pass/fail for each. CLI command `naturo browser stealth-check` supports text and JSON output, exits non-zero when any check fails. 11 new tests. Ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: feat/issue-759-browser-download
- **Base**: develop
- **Title**: feat: add browser download --dir/--wait for file downloads (fixes #759)
- **Body**: New `_download.py` module with `set_download_dir()` (CDP Browser.setDownloadBehavior) and `wait_for_download()` (polls directory for new files, detects .crdownload partials). CLI command: `naturo browser download --dir <path> [--wait] [--timeout N]`. Creates download directory if missing. Supports text and JSON output. 23 new tests. Ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: feat/issue-761-drag-from-element
- **Base**: develop
- **Title**: feat: add drag --from-element/--to-element for UI tree name search (fixes #761)
- **Body**: New `--from-element` and `--to-element` options on the drag command that find elements by name/text in the UI tree using `_find_element_by_text_fallback()`. Returns center coordinates as drag source/destination. Simpler alternative to `--from-selector` for common cases like slider captcha handles. 8 new tests. Ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: feat/issue-90-recording-playback-cli
- **Base**: develop
- **Title**: feat: add recording/playback CLI commands and wire interaction hooks (fixes #90)
- **Body**: Seven CLI commands under `naturo record`: start, stop, status, list, show, delete, play (with --speed, --dry-run, --json). Wires the existing no-op _record_action stub in _common.py to naturo.recording.append_step_to_active so click, type, press, hotkey, scroll, drag, and move are captured during active recordings. Adds missing type command recording hook. 31 new tests. 4083 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending
