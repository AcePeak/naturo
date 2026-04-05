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
- **Status**: superseded by fix/issue-788-stale-pid-app-id

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

## PR Request: feat/issue-104-builtin-selector-templates
- **Base**: develop
- **Title**: feat: add built-in selector templates for Top 20 Windows apps (fixes #104)
- **Body**: 20 JSON template files in naturo/selectors_builtin/ covering Notepad, Chrome, Firefox, Edge, Explorer, VS Code, Word, Excel, PowerPoint, Calculator, Settings, Task Manager, Windows Terminal, Outlook, Teams, CMD, Paint, Snipping Tool, Control Panel, and Registry Editor (119 selectors total). Templates use automationid where available for locale-independence, with wildcard name patterns for cross-version compatibility. 70 new tests. Ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-788-stale-pid-hwnd
- **Base**: develop
- **Title**: fix: detect stale PID/HWND after app restart, fall back to process name (fixes #788)
- **Body**: Two-layer fix: (1) _resolve_app_id validates PID liveness via os.kill(0); when dead, extracts process-name basename for live window enumeration. (2) _resolve_hwnd validates HWND with IsWindow(); raises WindowNotFoundError when the handle is stale. 6 new tests, 3 existing tests updated. 4375 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: superseded by fix/issue-788-stale-pid-app-id

## PR Request: fix/issue-789-app-filter-basename
- **Base**: develop
- **Title**: fix: extract process basename before --app matching (fixes #789)
- **Body**: process_name from the backend may contain a full path (e.g. C:\Windows\System32\notepad.exe). Substring matching against the full path caused --app system to incorrectly match any process in System32. Now uses ntpath.basename() in _resolve_hwnd, _resolve_hwnds, and _is_afh_window. 3 new tests. 4088 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending (branch force-pushed 2026-04-02)

## PR Request: fix/issue-781-json-exit-code
- **Base**: develop
- **Title**: fix: exit non-zero when JSON mode reports failure (fixes #781)
- **Body**: selector clear, selector export, and visual report emitted {"success": false} JSON but exited with code 0. Changed return to sys.exit(1) in all three locations. 3 new tests. 4367 passed, ruff clean. Branch force-pushed with clean implementation.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending (branch force-pushed)

## PR Request: fix/issue-783-json-duplicate-stderr
- **Base**: develop
- **Title**: fix: suppress stderr output in JSON mode (fixes #783)
- **Body**: Three-part fix: (1) add NullHandler to root logger when --json is active, (2) downgrade routing.py app-not-found from WARNING to DEBUG (caller handles condition), (3) downgrade press focus-failure from WARNING to DEBUG. 1 new test. 4366 passed, ruff clean. Branch force-pushed with clean implementation.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending (branch force-pushed)

## PR Request: fix/issue-787-coords-bounds
- **Base**: develop
- **Title**: fix: reject out-of-bounds click coordinates with clear error (fixes #787)
- **Body**: click --coords silently accepted coordinates outside the virtual screen, resulting in no-op clicks. Now validates against GetSystemMetrics (Windows) or 65535 generic bound (non-Windows). 2 new tests. 4367 passed, ruff clean. Branch force-pushed.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending (branch force-pushed)

## PR Request: fix/issue-786-uwp-menu-click
- **Base**: develop
- **Title**: fix: detect WinUI 3 apps for UIA click path (fixes #786)
- **Body**: WinUI 3 apps (Win11 Notepad, Paint) run as standalone processes, not under ApplicationFrameHost. The UIA click path was only triggered for AFH-hosted apps, so menu items in WinUI 3 apps were clicked via SendInput which doesn't reliably reach XAML content. Added _is_winui_window() that detects DesktopWindowXamlSource child windows. When detected, click uses ExpandCollapsePattern/InvokePattern instead of SendInput. 6 new tests, 2 existing tests updated. 4432 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-788-stale-pid-app-id
- **Base**: develop
- **Title**: fix: detect stale PID in app ID resolution, fail loudly (fixes #788)
- **Body**: When an app restarts after `naturo app list`, the cached HWND+PID become stale. Previously, _resolve_app_id returned them without validation, causing focus_window to silently fail and keystrokes to be delivered to the wrong foreground window. Now validates the cached PID is still alive via find_process(pid=) before returning. If the process is gone, exits with a clear error (APP_ID_STALE) telling the user to re-run `naturo app list`. 2 new tests (stale PID exits, alive PID succeeds), 3 existing tests updated to mock find_process. 4091 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: superseded by fix/issue-788-stale-pid-routing

## PR Request: fix/issue-788-stale-pid-routing
- **Base**: develop
- **Title**: fix: validate HWND liveness before routing keystrokes (fixes #788)
- **Body**: After app restart, stale HWNDs from app_ids silently dropped keystrokes because focus_window sent to a dead window. Two-layer fix using IsWindow(): (1) _resolve_app_id validates stored HWND before returning, emits APP_ID_STALE error with clear message. (2) _resolve_hwnd validates any direct HWND param, raises WindowNotFoundError for dead handles. 4 new tests (stale/live HWND at both layers). 4089 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: feat/issue-91-visual-regression-enterprise
- **Base**: develop
- **Title**: feat: add enterprise visual regression features — ignore regions, update, suite (fixes #91)
- **Body**: Three enterprise features for CI/CD visual regression workflows: (1) Ignore regions — mask dynamic UI areas (timestamps, ads, spinners) before pixel comparison via --ignore-region x,y,w,h on compare and report commands; also supported per-test in suite JSON. (2) Baseline update workflow — `naturo visual update` replaces existing baseline, `naturo visual update-all --from-dir` batch-updates all baselines from a directory. (3) Suite runner — `naturo visual suite regression.json` runs batch test definitions from JSON with per-test thresholds, ignore regions, and HTML report output for CI pipelines. 21 new tests. 4447 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: test/visual-cmd-coverage
- **Base**: develop
- **Title**: test: add 22 tests for visual CLI — report command, JSON modes, error paths
- **Body**: Fills the test coverage gap for visual_cmd.py CLI layer. Adds 11 tests for the `report` command (pass/fail/skip/auto-detect/JSON/HTML output/threshold/no-baselines/named report), plus JSON mode tests for baseline, list, delete, compare, and diff commands, and error path tests for missing baselines. All 4445 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: test/cascade-coverage-gaps
- **Base**: develop
- **Title**: test: add 39 tests for cascade coverage and shallow-tree helpers
- **Body**: Fills test coverage gaps in naturo.cascade._coverage and _types modules. Tests _is_actionable_leaf (9 tests including all container roles), _covered_area (4 tests), _has_invalid_bounds (6 tests), _is_shallow_tree (7 tests with threshold edge cases), CascadeStats.to_dict (2 tests), CascadeResult/ProviderStat dataclass fields (4 tests), and _rect_area/_estimate_coverage edge cases (7 tests). All 4404 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: docs/readme-browser-section
- **Base**: develop
- **Title**: docs: add browser automation and visual regression sections to README
- **Body**: README had no documentation for `naturo browser` (23 CDP commands) or `naturo visual` (6 regression testing commands), despite both being on develop. Adds feature bullets, CLI command tables, usage examples section with common patterns, and browser automation row in comparison table.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: test/browser-selectors-coverage
- **Base**: develop
- **Title**: test: add 40 tests for browser selector parsing and CDP expression generation
- **Body**: Fills test coverage gap for naturo.browser._selectors module. Tests parse_selector with explicit css:/xpath:/text: prefixes (7 tests), auto-detection heuristics (16 tests), edge cases (4 tests), to_cdp_expression single-element output (7 tests), and to_cdp_expression_all array output (6 tests). All 4125 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-785-winui3-uia-probe
- **Base**: develop
- **Title**: fix: detect UIA for standalone WinUI 3 apps like Calculator (fixes #785)
- **Body**: Win11 Calculator and Paint are standalone WinUI 3 apps not hosted by ApplicationFrameHost. The UIA probe only checked AFH child windows when the main HWND returned an empty tree, so these apps fell through to vision-only detection. Added _find_winui_content_children() that enumerates DesktopWindowXamlSource children regardless of parent class, used as fallback when AFH child search returns empty. 4 new tests. 4088 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-788-stale-pid-routing
- **Base**: develop
- **Title**: fix: validate HWND liveness before routing keystrokes (fixes #788)
- **Body**: After app restart, stale HWNDs from app_ids silently dropped keystrokes because focus_window sent to a dead window. Two-layer fix using IsWindow(): (1) _resolve_app_id validates stored HWND before returning, emits APP_ID_STALE error with clear message. (2) _resolve_hwnd validates any direct HWND param, raises WindowNotFoundError for dead handles. 4 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-789-app-filter-basename
- **Base**: develop
- **Title**: fix: extract process basename before --app matching (fixes #789)
- **Body**: process_name from the backend may contain a full path (e.g. C:\Windows\System32\notepad.exe). Substring matching against the full path caused --app system to incorrectly match any process in System32. Now uses ntpath.basename() in _resolve_hwnd, _resolve_hwnds, and _is_afh_window. 7 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-781-json-exit-code
- **Base**: develop
- **Title**: fix: exit non-zero when JSON mode reports failure (fixes #781)
- **Body**: selector clear, selector export, and visual report emitted {"success": false} JSON but exited with code 0. Automation scripts relying on exit codes could not detect failure. Changed return to sys.exit(1) in all three affected locations. 3 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-783-json-duplicate-stderr
- **Base**: develop
- **Title**: fix: suppress stderr output in JSON mode (fixes #783)
- **Body**: Python's logging lastResort handler emits WARNING+ to stderr when no handlers are configured. In JSON mode, this caused human-readable error text to mix with JSON stdout, breaking piping workflows. Three-part fix: (1) add NullHandler to root logger when --json is active, (2) downgrade routing.py app-not-found from WARNING to DEBUG, (3) downgrade press focus-failure from WARNING to DEBUG. 2 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-787-coords-bounds
- **Base**: develop
- **Title**: fix: reject out-of-bounds click coordinates with clear error (fixes #787)
- **Body**: click --coords silently accepted coordinates outside the virtual screen, resulting in no-op clicks. Now validates against GetSystemMetrics (Windows) or 65535 generic bound (non-Windows). Out-of-bounds coordinates produce a COORDS_OUT_OF_BOUNDS error in both JSON and text modes. 4 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-786-uwp-menu-click
- **Base**: develop
- **Title**: fix: detect WinUI 3 apps for UIA click path (fixes #786)
- **Body**: WinUI 3 apps (Win11 Notepad, Paint) run as standalone processes, not under ApplicationFrameHost. The UIA click path was only triggered for AFH-hosted apps, so menu items in WinUI 3 apps were clicked via SendInput which doesn't reliably reach XAML content. Added _is_winui_window() that detects DesktopWindowXamlSource child windows. When detected, click uses ExpandCollapsePattern/InvokePattern instead of SendInput. 5 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-788-stale-pid-routing
- **Base**: develop
- **Title**: fix: validate HWND liveness before routing keystrokes (fixes #788)
- **Body**: After app restart, stale HWNDs from app_ids silently dropped keystrokes because focus_window sent to a dead window. Two-layer fix using IsWindow(): (1) _resolve_app_id validates stored HWND before returning, emits APP_ID_STALE error with clear message. (2) _resolve_hwnd validates any direct HWND param, raises WindowNotFoundError for dead handles. 8 new tests. 4093 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-785-winui3-uia-probe
- **Base**: develop
- **Title**: fix: detect UIA for standalone WinUI 3 apps like Calculator (fixes #785)
- **Body**: Win11 Calculator and Paint are standalone WinUI 3 apps not hosted by ApplicationFrameHost. The UIA probe only checked AFH child windows when the main HWND returned an empty tree, so these apps fell through to vision-only detection. Added _find_winui_content_children() that enumerates DesktopWindowXamlSource children regardless of parent class, used as fallback when AFH child search returns empty. 4 new tests. 4088 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-789-app-filter-basename
- **Base**: develop
- **Title**: fix: extract process basename before --app matching (fixes #789)
- **Body**: process_name from the C++ bridge may contain a full path (e.g. C:\Windows\System32\notepad.exe). Substring matching against the full path caused --app system to incorrectly match any process in System32. Now uses ntpath.basename() in _resolve_hwnd, _resolve_hwnds, and _is_afh_window. 7 new tests. 4092 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-786-uwp-menu-click
- **Base**: develop
- **Title**: fix: detect WinUI 3 apps for UIA click path (fixes #786)
- **Body**: WinUI 3 apps (Win11 Notepad, Paint) run as standalone processes, not under ApplicationFrameHost. The UIA click path was only triggered for AFH-hosted apps, so menu items in WinUI 3 apps were clicked via SendInput which doesn't reliably reach XAML content. Added _is_winui_window() that detects DesktopWindowXamlSource child windows. When detected, click uses ExpandCollapsePattern/InvokePattern instead of SendInput. 6 new tests, 2 existing tests updated. 4090 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-781-json-exit-code
- **Base**: develop
- **Title**: fix: exit non-zero when JSON mode reports failure (fixes #781)
- **Body**: selector clear, selector export, and visual report emitted {"success": false} JSON but exited with code 0. Automation scripts relying on exit codes could not detect failure. Changed return to sys.exit(1) in all three affected locations. 5 new tests. 4090 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-783-json-duplicate-stderr
- **Base**: develop
- **Title**: fix: suppress stderr output in JSON mode (fixes #783)
- **Body**: Python's logging lastResort handler emits WARNING+ to stderr when no handlers are configured. In JSON mode, this caused human-readable error text to mix with JSON stdout, breaking piping workflows. Three-part fix: (1) add NullHandler to root logger when --json is active, (2) downgrade routing.py app-not-found from WARNING to DEBUG, (3) downgrade press focus-failure from WARNING to DEBUG. 4 new tests. 4089 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-787-coords-bounds
- **Base**: develop
- **Title**: fix: reject out-of-bounds click coordinates with clear error (fixes #787)
- **Body**: click --coords silently accepted coordinates outside the virtual screen, resulting in no-op clicks. Now validates against GetSystemMetrics (Windows) or 65535 generic bound (non-Windows). Out-of-bounds coordinates produce a COORDS_OUT_OF_BOUNDS error in both JSON and text modes. 5 new tests. 4090 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-02
- **Status**: pending

## PR Request: fix/issue-788-stale-pid-routing
- **Base**: develop
- **Title**: fix: detect stale HWND after app restart, reject with clear error (fixes #788)
- **Body**: After app restart, stale HWNDs from app_ids silently dropped keystrokes because focus_window sent to a dead window. Two-layer fix: (1) _resolve_app_id validates stored HWND via _is_hwnd_alive() helper (calls IsWindow() on Windows); emits APP_ID_STALE error with clear message. (2) _resolve_hwnd validates any direct HWND param, raises WindowNotFoundError for dead handles. 2 new tests. 3995 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-789-app-filter-basename
- **Base**: develop
- **Title**: fix: extract process basename before --app matching (fixes #789)
- **Body**: process_name may contain full paths (e.g. C:\Program Files\...\chrome.exe). Substring matching against the full path caused --app to match directory components like "program" or "files". Now uses ntpath.basename() in both _resolve_hwnd and _resolve_hwnds. 4 new tests. 3997 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-786-uwp-menu-click
- **Base**: develop
- **Title**: fix: detect WinUI 3 apps for UIA click path (fixes #786)
- **Body**: Windows 11 Notepad is a standalone WinUI 3 app (not hosted by ApplicationFrameHost.exe). The click command only checked _is_afh_window for UWP detection, missing WinUI 3 apps. Added _is_winui_window() that checks for DesktopWindowXamlSource child windows, enabling UIA click path for menu items. 4 new tests, 1 existing updated. 3995 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-781-json-exit-code
- **Base**: develop
- **Title**: fix: exit non-zero when JSON mode reports failure (fixes #781)
- **Body**: Three locations output {"success": false} in JSON mode but returned with exit code 0: selector clear (no selectors), selector export (no selectors), visual report (no baselines). All now call sys.exit(1). 6 new tests verify both text and JSON modes exit with code 1. 3997 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-783-json-duplicate-stderr
- **Base**: develop
- **Title**: fix: suppress stderr output in JSON mode (fixes #783)
- **Body**: Python's logging lastResort handler sends WARNING+ messages to stderr even when no handler is configured. In JSON mode, this produces duplicate human-readable errors alongside JSON stdout. Now adds a NullHandler to the naturo logger when -j is active. 2 new tests. 3995 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-787-coords-bounds
- **Base**: develop
- **Title**: fix: reject out-of-bounds click coordinates with clear error (fixes #787)
- **Body**: click --coords silently accepted negative or out-of-bounds coordinates, resulting in no-op clicks. Now validates against negative values and GetSystemMetrics virtual screen bounds on Windows (65535 fallback on other platforms). 5 new tests. 3998 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-788-stale-pid-routing
- **Base**: develop
- **Title**: fix: validate HWND liveness before routing keystrokes (fixes #788)
- **Body**: After app restart, stale HWNDs from app_ids silently dropped keystrokes because focus_window sent to a dead window. Added _is_hwnd_alive() helper that calls IsWindow() on Windows. _resolve_app_id now checks HWND liveness and emits APP_ID_STALE error with clear recovery message. 2 new tests. 41 interaction_common tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-785-calculator-uia-probe
- **Base**: develop
- **Title**: fix: pass exe= and use retry for Calculator UIA detection tests (fixes #785)
- **Body**: Calculator tests called detect_chain without exe= param, so _find_window_by_process_name fallback could not resolve the window when the UWP broker PID differs from the window owner. Also added _detect_with_retry with cache bypass on retries, matching the pattern already used for Notepad tests.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-789-app-filter-basename
- **Base**: develop
- **Title**: fix: extract process basename before --app matching (fixes #789)
- **Body**: process_name from the backend may contain a full path (e.g. C:\Windows\System32\notepad.exe). Substring matching against the full path caused --app system to incorrectly match any process in System32. Now uses ntpath.basename() in _resolve_hwnd, _resolve_hwnds, and _is_afh_window. 4 new tests. 16 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-784-type-newline
- **Base**: develop
- **Title**: fix: convert newline chars to Enter keypresses in type_text (fixes #784)
- **Body**: SendInput with KEYEVENTF_UNICODE sends raw Unicode codepoints, but \n (U+000A) is a control character that most Windows apps silently drop. Now type_text splits text on newline boundaries (\n, \r\n, \r) and inserts Enter keypresses between segments. 4 new tests. 28 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-781-json-exit-code
- **Base**: develop
- **Title**: fix: exit code 1 when JSON mode emits success: false (fixes #781)
- **Body**: Systemic fix: json_error() now sets _json_error_emitted flag. CLI entry point (__main__.py) checks this flag after command returns — if JSON error was emitted but exit code would be 0, corrects to 1. This covers ALL code paths that do click.echo(json_error()); return instead of sys.exit(1), not just the 3 specific locations. 2 new tests for flag behavior. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending (force-pushed systemic version)

## PR Request: fix/issue-786-uwp-menu-click
- **Base**: develop
- **Title**: fix: use UIA click for menu items on all apps, not just UWP (fixes #786)
- **Body**: WinUI 3 apps (Win11 Notepad) aren't hosted by ApplicationFrameHost, so _is_uwp was False and UIA click path was skipped. Menu items need UIA ExpandCollapsePattern to open dropdowns — SendInput coordinate clicks don't trigger menu expansion. Now tries UIA click whenever the element role is MenuItem/Menu/MenuBar regardless of UWP status. Broader fix than WinUI-only detection. 6 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending (force-pushed improved version)

## PR Request: fix/issue-788-stale-pid-routing
- **Base**: develop
- **Title**: fix: reject stale PIDs in AppIdMap.resolve() (fixes #788)
- **Body**: After an app restarts with a new PID, the stored app ID entry becomes stale. resolve() now checks PID liveness via os.kill(pid, 0) before returning an entry, preventing silent keystroke drops. Added _is_pid_alive() helper and 6 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-789-app-filter-basename
- **Base**: develop
- **Title**: fix: extract process basename before --app matching (fixes #789)
- **Body**: process_name can be a full path. Without extracting basename, substring matching matches directory components, picking the wrong process. Uses ntpath.basename in both _resolve_hwnd and _resolve_hwnds. Added 3 tests.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-786-uwp-menu-click
- **Base**: develop
- **Title**: fix: use UIA click for menu items on all apps, not just UWP (fixes #786)
- **Body**: WinUI 3 apps aren't hosted by ApplicationFrameHost, so _is_uwp was False and UIA click path was skipped. Menu items need UIA ExpandCollapsePattern to open. Now triggers UIA click for MenuItem/Menu/MenuBar roles regardless of UWP status. Updated test and added new test.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-781-json-exit-code
- **Base**: develop
- **Title**: fix: exit code 1 when JSON output contains verified:false (fixes #781)
- **Body**: _json_ok() now checks for verified:false in data and emits success:false with exit code 1. Systemic fix covering click, type, press, mouse and all interaction commands. Removed duplicate verification check from type_cmd. Added json_fail() helper. 4 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-787-coords-bounds
- **Base**: develop
- **Title**: fix: reject out-of-bounds click coordinates (fixes #787)
- **Body**: Validates --coords before passing to backend: rejects negative values and values > 65535. Returns INVALID_INPUT error with clear message. 7 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-783-json-duplicate-stderr
- **Base**: develop
- **Title**: fix: suppress logging stderr in JSON mode (fixes #783)
- **Body**: In JSON mode, naturo logger uses NullHandler with CRITICAL+1 level to prevent duplicate human-readable errors on stderr alongside JSON stdout. Also adds verbose mode StreamHandler configuration. 1 new test.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending (branch rebased onto develop 2026-04-03)

## PR Request: feat/issue-105-user-selector-load
- **Base**: develop
- **Title**: feat: add selector load command and @app/name resolution (fixes #105)
- **Body**: New `naturo selector load <app> <name>` command retrieves saved selectors by name. All interaction commands (click, type, press, etc.) now auto-resolve @app/name references in --selector, e.g. `naturo click --selector @notepad/save-btn`. Public `resolve_named_selector()` API searches user selectors first, then built-in templates. 12 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: test/recording-cmd-coverage
- **Base**: develop
- **Title**: test: add 75 tests for recording CLI and engine
- **Body**: Comprehensive test coverage for recording_cmd.py and recording.py — covers all 7 subcommands (start/stop/play/list/show/delete/export), recording persistence, active state management, ActionStep/Recording dataclasses, export formats (json/python/bash), _step_to_naturo_cmd conversion, and help output. All 75 tests pass. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: feat/issue-105-selector-load
- **Base**: develop
- **Title**: feat: add selector load command and @app/name references (fixes #105)
- **Body**: New `naturo selector load <app> <name>` command retrieves a single saved selector by name and prints its value, designed for piping into `--selector` on interaction commands. Named references (`@notepad/save-btn`) are now resolved automatically in `--selector` on all interaction commands (click, type, press, scroll, drag, move). User selectors override built-in templates. `resolve_named_selector()` public function added for programmatic use. 13 new tests covering load command (user/builtin/override/not-found/JSON), resolve_named_selector (valid/invalid refs), and help output. 4122 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: test/detect-probes-coverage
- **Base**: develop
- **Title**: test: add 61 tests for detect/probes.py framework detection and probe logic
- **Body**: Fills test coverage gap for naturo/detect/probes.py (879 lines, previously untested). Tests detect_frameworks_from_dlls with exe-name heuristics (Electron/Chrome/Java/UWP/Win32/Unknown) and DLL-based detection for all 10 framework types (Electron, CEF, Chrome, WPF, WinForms, Qt5/Qt6, Java, GTK, UWP, Win32). Tests probe_ia2 (Firefox/Thunderbird/LibreOffice), probe_vision (always-available fallback), probe_jab (with/without JAB bridge), DLL signature set invariants (non-empty, lowercase), and non-Windows codepaths for all probes. All tests use mocked _get_process_dlls — no Windows APIs required. 4170 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-783-json-stderr-suppress
- **Base**: develop
- **Title**: fix: suppress stderr output in JSON mode (fixes #783)
- **Body**: Python's logging lastResort handler emits WARNING+ to stderr when no handlers are configured. In JSON mode this breaks piping workflows. Three-part fix: (1) add NullHandler to root logger when --json is active, (2) downgrade routing.py app-not-found from WARNING to DEBUG (caller handles the condition), (3) downgrade press focus-failure from WARNING to DEBUG. 3 new tests. 4112 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: feat/issue-760-stealth-check
- **Base**: develop
- **Title**: feat: add browser stealth-check verification command (fixes #760)
- **Body**: New check_stealth() function runs 6 JS checks (webdriver, plugins, languages, chrome.runtime, WebGL vendor, permissions) against the browser and reports pass/fail for each. CLI command `naturo browser stealth-check` supports text and JSON output, exits non-zero when any check fails. 12 new tests. 4121 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending (branch force-pushed with clean version)

## PR Request: fix/issue-788-stale-pid-routing
- **Base**: develop
- **Title**: fix: evict stale PIDs from app ID map on resolve (fixes #788)
- **Body**: AppIdMap.resolve() now checks PID liveness via os.kill(pid, 0) before returning cached entries. Dead PIDs are evicted and the map is persisted to disk, preventing silent routing to nonexistent processes. Added _is_pid_alive() helper, autouse fixture for test isolation, 4 new stale PID tests. All 26 app_ids tests pass.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-789-app-filter-basename
- **Base**: develop
- **Title**: fix: reject window title substring matches in app routing (fixes #789)
- **Body**: _find_pid_by_window_title() used substring matching, causing --app notepad to match Chrome windows titled "help with notepad". Changed to exact title match only. CJK app names are already handled via _LAUNCH_ALIASES in find_process(). 1 new test. 29 routing tests pass.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-781-json-exit-code
- **Base**: develop
- **Title**: fix: exit 1 in JSON mode when verification fails for click/press/find (fixes #781)
- **Body**: click and press commands output success:false with verified:false but returned exit code 0 in JSON mode. Added verification failure checks matching the existing type command pattern. Also fixed find command which returned exit 0 on element-not-found in JSON mode. 2 new tests for click verification exit code. 24 click tests pass.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-783-json-stderr-suppress
- **Base**: develop
- **Title**: fix: suppress stderr logging in JSON mode (fixes #783)
- **Body**: Python's default "last resort" handler writes WARNING+ log messages to stderr, corrupting JSON output when callers redirect stderr (2>&1). When --json is active, installs NullHandler on the naturo logger with propagate=False. 1 new test. All CLI tests pass.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-787-coords-bounds
- **Base**: develop
- **Title**: fix: validate coordinate bounds in click command (fixes #787)
- **Body**: naturo click --coords accepted negative values and values > 65535 silently. Added bounds validation (0–65535) matching Win32 API limits. Invalid coordinates now emit INVALID_INPUT error with exit code 1. 5 new bounds validation tests. 28 click tests pass.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-786-uwp-menu-click
- **Base**: develop
- **Title**: fix: use UIA click for menu-role elements in all app types (fixes #786)
- **Body**: UIA click was only attempted for UWP/ApplicationFrameHost windows. Menu items (MenuItem, Menu, MenuBar roles) in regular Win32/WinUI3 apps also need UIA ExpandCollapsePattern/InvokePattern. Now checks element role from snapshot metadata and triggers UIA click for menu-role elements regardless of app type. 1 new test. 23 click tests pass.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: feat/issue-105-selector-management
- **Base**: develop
- **Title**: feat: add selector load command and @app/name reference resolution (fixes #105)
- **Body**: Adds `naturo selector load <app> <name>` command to retrieve saved selectors by name. Integrates @app/name reference resolution into all interaction commands (click, type, press, scroll, move, drag) via their --selector flag, so users can `naturo click --selector @notepad/save-btn`. User selectors take priority over built-in templates. 35 selector_cmd tests + 25 selector_cli tests pass. Lint and mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: test/config-module-coverage
- **Base**: develop
- **Title**: test: add 16 unit tests for config module (credentials load/save, constants)
- **Body**: Covers load_credentials(), save_credentials(), atomic write behavior, error handling (missing file, invalid JSON, OS errors), unicode preservation, round-trip, and path/env-var constants. All 4138 tests pass, ruff and mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: feat/issue-758-chrome-profiles
- **Base**: develop
- **Title**: feat: add Chrome profile support — launch, profiles CLI commands (fixes #758)
- **Body**: Adds `naturo/browser/_launcher.py` with Chrome binary discovery (Windows/macOS/Linux), profile listing from Chrome's Local State file, profile name resolution, and Chrome launch with `--remote-debugging-port`. CLI gains `naturo browser launch` (with --profile, --user-data-dir, --headless, --stealth, --chrome-path options) and `naturo browser profiles` (list available profiles). ChromeProcess handle provides is_running/terminate/kill/wait. 53 unit tests pass, ruff and mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: feat/issue-764-iframe-support
- **Base**: develop
- **Title**: feat: add iframe support — frames, frame-eval, frame-find CLI commands (fixes #764)
- **Body**: Adds `naturo/browser/_frame.py` with BrowserFrame class using CDP Page.createIsolatedWorld for frame-scoped JavaScript execution. BrowserPage gains `frames()` (list all frames) and `frame(selector/name/url)` (get scoped BrowserFrame). CLI gains `naturo browser frames`, `naturo browser frame-eval`, `naturo browser frame-find` commands. Supports nested iframes. 37 unit tests pass, ruff and mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-788-stale-pid-routing
- **Base**: develop
- **Title**: fix: evict stale PIDs from app ID map on resolve (fixes #788)
- **Body**: AppIdMap.resolve() now checks PID liveness via os.kill(pid, 0) before returning cached entries. Dead PIDs are evicted and the map is persisted to disk, preventing silent routing to nonexistent processes. Added _is_pid_alive() helper, autouse fixture for test isolation, 8 new tests (4 liveness + 4 eviction). All 26 app_ids tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-789-app-filter-basename
- **Base**: develop
- **Title**: fix: reject window title substring matches in app routing (fixes #789)
- **Body**: _find_pid_by_window_title() used substring matching, causing --app notepad to match Chrome windows titled "help with notepad". Changed to exact title match only. 2 new tests. 30 routing tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-781-json-exit-code
- **Base**: develop
- **Title**: fix: exit 1 in JSON mode when verification fails for click/press (fixes #781)
- **Body**: click and press commands output verified:false but returned exit code 0 in JSON mode. Added verification failure check matching the existing type command pattern — exit 1 with VERIFICATION_FAILED error code. 3 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-787-coords-bounds
- **Base**: develop
- **Title**: fix: validate coordinate bounds in click command (fixes #787)
- **Body**: naturo click --coords accepted negative values and values > 65535 silently. Added bounds validation (0-65535) matching Win32 API limits. Invalid coordinates emit INVALID_INPUT error with exit code 1. 6 new tests (4 rejection + 2 boundary acceptance). Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-786-uwp-menu-click
- **Base**: develop
- **Title**: fix: use UIA click for menu-role elements in all app types (fixes #786)
- **Body**: UIA click was only attempted for UWP/ApplicationFrameHost windows. Menu items (MenuItem, Menu, MenuBar) in regular Win32/WinUI3 apps also need UIA ExpandCollapsePattern/InvokePattern. Now checks element role from snapshot metadata and triggers UIA click for menu-role elements regardless of app type. 3 new parametrized tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-783-json-stderr-suppress
- **Base**: develop
- **Title**: fix: suppress stderr logging in JSON mode (fixes #783)
- **Body**: Python's default "last resort" handler writes WARNING+ log messages to stderr, corrupting JSON output when callers redirect stderr (2>&1). When --json is active, installs NullHandler on the naturo logger with propagate=False. 2 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/recording-export-shell-escape
- **Base**: develop
- **Title**: fix: prevent shell injection in recording bash/python export
- **Body**: _step_to_naturo_cmd() was building shell commands via string interpolation, allowing recorded text containing backticks, $(), quotes, or semicolons to execute arbitrary commands when the exported bash script was run. Now uses shlex.quote() for all user-provided values. 8 new tests covering injection vectors. All 4130 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/visual-report-error-handling
- **Base**: develop
- **Title**: fix: surface skips, errors, and HTML failures in visual report JSON mode
- **Body**: visual report silently swallowed three categories of information in JSON mode: skipped items (missing current screenshot), comparison errors (missing baseline), and HTML generation failures. Now tracks skipped/errored items and includes them in JSON output. Narrowed except Exception to except (OSError, ValueError) for HTML generation. Exit non-zero when comparison errors occur. Text mode now shows skip count. 5 new tests. 4188 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: test/detect-probes-coverage-v2
- **Base**: develop
- **Title**: test: add 67 tests for detect/probes.py framework detection and probe logic
- **Body**: Fills test coverage gap for naturo/detect/probes.py (879 lines, previously untested). Tests DLL signature set invariants (10 sets non-empty, all lowercase), detect_frameworks_from_dlls with exe-name heuristics (Electron/Chrome/Java/UWP/Win32/Unknown) and DLL-based detection for all 10 framework types (Electron, CEF, Chrome, WPF, WinForms, Qt5/Qt6, Java, GTK, UWP, Win32). Tests probe_ia2 (Firefox/Thunderbird/LibreOffice), probe_vision (always-available fallback), probe_jab (with/without JAB bridge), platform-gated probes (CDP/UIA/MSAA return None on non-Windows), and helper function non-Windows codepaths. All mocked — no Windows APIs required. 4250 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: test/cascade-build-run-coverage
- **Base**: develop
- **Title**: test: add 35 tests for cascade/_build.py and _run.py orchestration logic
- **Body**: Fills test coverage gap for cascade build and run modules. Tests _detect_backend_for_class (14 tests — all Win32 class→backend mappings), _find_node_by_bounds (7 tests — exact/deep match, zero dims, partial overlap), _get_hwnd_children_with_class non-Windows path, build_hybrid_tree (3 tests — UIA error, UIA-only, CDP enrichment), run_cascade (7 tests — auto/hybrid/cdp modes, null tree, exceptions, empty tree fallback), _run_cdp_only (3 tests — no port, with elements, synthetic root). All tests mock backend and platform calls. 4218 tests pass, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-781-json-exit-code
- **Base**: develop
- **Title**: fix: exit non-zero when JSON mode reports failure (fixes #781)
- **Body**: selector clear, selector export, and visual report emitted {"success": false} JSON but exited with code 0. Changed return to sys.exit(1) in all three locations. 4 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-783-json-stderr-suppress
- **Base**: develop
- **Title**: fix: suppress stderr output in JSON mode (fixes #783)
- **Body**: Three-part fix: (1) add NullHandler to naturo logger when --json is active, (2) downgrade routing.py app-not-found from WARNING to DEBUG, (3) downgrade press focus-failure from WARNING to DEBUG. 1 new test.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-787-coords-bounds
- **Base**: develop
- **Title**: fix: reject out-of-bounds click coordinates with clear error (fixes #787)
- **Body**: click --coords silently accepted coordinates outside the virtual screen. On Windows, validates against GetSystemMetrics virtual screen bounds. On non-Windows, validates 0-65535 range. Emits INVALID_COORDINATES error. 5 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-789-app-filter-basename
- **Base**: develop
- **Title**: fix: extract process basename before --app matching (fixes #789)
- **Body**: process_name from the backend may contain full path. Substring matching against the full path caused --app system to match any System32 process. Now uses ntpath.basename() in _resolve_hwnd, _resolve_hwnds, and _is_afh_window. 5 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-788-stale-pid-routing
- **Base**: develop
- **Title**: fix: detect stale PID in app-ID routing, fall back to process name (fixes #788)
- **Body**: After an app restarts, cached app-ID entries become stale. _resolve_app_id now validates PID liveness via os.kill(0); when dead, extracts process-name basename for live window enumeration. 3 new tests, 1 existing test updated.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-786-uwp-menu-click
- **Base**: develop
- **Title**: fix: detect WinUI 3 apps for UIA click path (fixes #786)
- **Body**: WinUI 3 apps (Win11 Notepad, Paint) run as standalone processes, not under ApplicationFrameHost. Added _is_winui_window() that detects DesktopWindowXamlSource child windows. When detected, click uses UIA patterns instead of SendInput. 3 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: feat/issue-105-selector-management
- **Base**: develop
- **Title**: feat: add selector load command and @app/name resolution (fixes #105)
- **Body**: Adds `naturo selector load <app> <name>` command to retrieve saved selectors by name. Integrates @app/name reference resolution into all interaction commands (click, type, press, scroll, move, drag) via their --selector flag, so users can `naturo click --selector @notepad/save-btn`. Public `resolve_named_selector()` API searches user selectors first, then built-in templates. 13 new tests. 4122 tests pass, ruff and mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-03
- **Status**: pending

## PR Request: fix/issue-781-json-exit-code
- **Base**: develop
- **Title**: fix: exit non-zero when JSON mode reports failure (fixes #781)
- **Body**: selector clear, selector export, visual delete, and visual report emitted {"success": false} JSON but exited with code 0. Changed return to sys.exit(1) in all four locations. 7 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-789-app-filter-basename
- **Base**: develop
- **Title**: fix: extract process basename before --app matching (fixes #789)
- **Body**: process_name from the backend may contain a full path. Substring matching against the full path caused --app system to match any System32 process. Now uses ntpath.basename() in _resolve_hwnd, _resolve_hwnds, and _is_afh_window. 5 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-787-coords-bounds
- **Base**: develop
- **Title**: fix: reject out-of-bounds click coordinates with clear error (fixes #787)
- **Body**: click --coords silently accepted coordinates outside the virtual screen. On Windows, validates against GetSystemMetrics virtual screen bounds. On non-Windows, validates 0-65535 range. Emits INVALID_COORDINATES error. 7 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-783-json-stderr-suppress
- **Base**: develop
- **Title**: fix: suppress stderr output in JSON mode (fixes #783)
- **Body**: Three-part fix: (1) add NullHandler to naturo logger when --json is active, (2) downgrade routing.py app-not-found from WARNING to DEBUG, (3) downgrade press focus-failure from WARNING to DEBUG. 1 new test.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-788-stale-pid-routing
- **Base**: develop
- **Title**: fix: detect stale PID in app-ID routing, fall back to process name (fixes #788)
- **Body**: After an app restarts, cached app-ID entries become stale. _resolve_app_id now validates PID liveness via os.kill(0); when dead, extracts process-name basename for live window enumeration. 3 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-786-uwp-menu-click
- **Base**: develop
- **Title**: fix: detect WinUI 3 apps for UIA click path (fixes #786)
- **Body**: WinUI 3 apps (Win11 Notepad, Paint) run as standalone processes, not under ApplicationFrameHost. Added _is_winui_window() that detects DesktopWindowXamlSource child windows. When detected, click uses UIA patterns instead of SendInput. 4 tests (2 Windows-only).
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-785-winui3-uia-probe
- **Base**: develop
- **Title**: fix: detect UIA for standalone WinUI 3 apps like Calculator (fixes #785)
- **Body**: Win11 Calculator and Paint are standalone WinUI 3 apps not hosted by ApplicationFrameHost. The UIA probe only checked AFH child windows when the main HWND returned an empty tree. Added _find_winui_content_children() that enumerates DesktopWindowXamlSource children regardless of parent class. 3 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-781-json-exit-code
- **Base**: develop
- **Title**: fix: exit non-zero when JSON reports failure (fixes #781)
- **Body**: Three CLI commands output {"success": false} JSON but exited code 0: selector clear, selector export, and visual report (no baselines). Changed return to sys.exit(1) so exit code and JSON agree. 6 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-789-app-filter-basename
- **Base**: develop
- **Title**: fix: extract process basename before --app matching (fixes #789)
- **Body**: process_name may contain a full path. Without basename extraction, --app could match path components. Fixed in _match_windows (app_cmd.py), _resolve_hwnd/_resolve_hwnds (_element.py), and dialog detection (_shell.py). 5 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-787-coords-bounds
- **Base**: develop
- **Title**: fix: reject out-of-bounds click coordinates (fixes #787)
- **Body**: Added _validate_coords() to reject negative coordinates and check Windows virtual screen bounds. Applied to click, scroll, and move commands. 8 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-783-json-stderr-suppress
- **Base**: develop
- **Title**: fix: suppress stderr in JSON mode (fixes #783)
- **Body**: When --json is active, logging.disable(CRITICAL) and warnings.filterwarnings('ignore') prevent stray log/warning lines from contaminating stdout JSON for AI agents. 2 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-788-stale-pid-routing
- **Base**: develop
- **Title**: fix: detect stale PID, fall back to process name (fixes #788)
- **Body**: When find_process(pid=X, name=Y) receives a stale PID (process exited), it now falls back to name-based search. AI agents caching PIDs across sessions can still reach restarted apps. 3 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-786-uwp-menu-click
- **Base**: develop
- **Title**: fix: detect WinUI 3 for UIA click path (fixes #786)
- **Body**: Standalone WinUI 3 apps were using SendInput instead of UIA patterns. Added _is_winui3_window() that detects DesktopWindowXamlSource children. Extended click command to use UIA for both AFH UWP and standalone WinUI 3. 4 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: docs/readme-browser-visual-sections
- **Base**: develop
- **Title**: docs: add browser automation and visual regression sections to README
- **Body**: README was missing documentation for two major v0.3.2 features: browser automation (27 CDP commands) and visual regression testing (6 commands). Added feature list entries, command tables, usage examples, and comparison table row. Also added missing selector show and selector clear to the command table. No code changes.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-781-json-exit-code
- **Base**: develop
- **Title**: fix: exit non-zero when JSON mode reports failure (fixes #781)
- **Body**: selector clear, selector export, and visual report emitted {"success": false} JSON but exited with code 0. Changed return to sys.exit(1) in all three locations. 5 new tests (4 selector, 1 visual). Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-789-app-filter-basename
- **Base**: develop
- **Title**: fix: extract process basename before --app matching (fixes #789)
- **Body**: process_name from the backend may contain a full path (e.g. C:\Windows\System32\notepad.exe). Substring matching against the full path caused --app system to incorrectly match any process in System32. Now uses ntpath.basename() in _resolve_hwnd and _resolve_hwnds. 5 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-787-coords-bounds
- **Base**: develop
- **Title**: fix: reject out-of-bounds click coordinates with clear error (fixes #787)
- **Body**: click --coords silently accepted coordinates outside the virtual screen, resulting in no-op clicks. Now validates against GetSystemMetrics (Windows) or 65535 generic bound (non-Windows). Out-of-bounds coordinates produce a COORDS_OUT_OF_BOUNDS error. 4 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-788-stale-pid-routing
- **Base**: develop
- **Title**: fix: detect stale HWND after app restart, reject with clear error (fixes #788)
- **Body**: After app restart, stale HWNDs from app_ids silently dropped keystrokes. Two-layer fix: (1) _resolve_app_id validates stored HWND via _is_hwnd_alive() (IsWindow() on Windows); emits APP_ID_STALE error. (2) _resolve_hwnd validates direct HWND params, raises WindowNotFoundError. 7 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-783-json-duplicate-stderr
- **Base**: develop
- **Title**: fix: suppress stderr output in JSON mode (fixes #783)
- **Body**: Python's logging lastResort handler emits WARNING+ to stderr when no handlers are configured. In JSON mode, this corrupted piping workflows. Three-part fix: (1) add NullHandler to root logger when --json is active, (2) downgrade routing.py app-not-found from WARNING to DEBUG, (3) downgrade press focus-failure from WARNING to DEBUG. 3 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-785-winui3-uia-probe
- **Base**: develop
- **Title**: fix: detect UIA for standalone WinUI 3 apps like Calculator (fixes #785)
- **Body**: Win11 Calculator and Paint are standalone WinUI 3 apps not hosted by ApplicationFrameHost. The UIA probe only checked AFH child windows when the main HWND returned an empty tree. Added _find_winui_content_children() that enumerates DesktopWindowXamlSource children regardless of parent class, used as fallback when AFH child search returns empty. 4 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-786-uwp-menu-click
- **Base**: develop
- **Title**: fix: detect WinUI 3 apps for UIA click path (fixes #786)
- **Body**: WinUI 3 apps (Win11 Notepad, Paint) run as standalone processes, not under ApplicationFrameHost. Added _is_winui_window() static method that detects DesktopWindowXamlSource child windows. Click command now checks both _is_afh_window and _is_winui_window for UIA click path. 4 new tests. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-810-mcp-stdout-debug
- **Base**: develop
- **Title**: fix: suppress all logging in MCP stdio transport (fixes #810)
- **Body**: The JSON-RPC stdio protocol requires clean stdout/stderr. Python's lastResort logging handler was emitting WARNING+ messages that corrupted the protocol. Now suppress root logger and disable lastResort when transport=stdio or --json is used. 2 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-840-type-newline-drop
- **Base**: develop
- **Title**: fix: handle newlines in type_text by splitting into Enter keypresses (fixes #840)
- **Body**: SendInput's UNICODE path silently drops \n and \r characters. Now split text on line breaks and insert press_key("enter") between segments. Handles \n, \r\n, and \r correctly. 3 new tests covering multi-line, CRLF, and trailing newline.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-807-press-wrong-process
- **Base**: develop
- **Title**: fix: press --app exits with error when window focus fails (fixes #807)
- **Body**: Previously press --app only logged a warning when focus_window() failed, then silently sent keystrokes to whatever window was in the foreground. Now exits non-zero with WINDOW_FOCUS_ERROR, consistent with the type command. 4 new tests.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-834-browser-json-flag
- **Base**: develop
- **Title**: fix: browser subcommand respects -j flag for all error paths (fixes #834)
- **Body**: _get_page() accepts json_output kwarg and emits structured JSON (SERVER_ERROR) on connection failure. All RuntimeError handlers use _emit_browser_error() with ELEMENT_NOT_FOUND code. TimeoutError uses TIMEOUT, FileNotFoundError uses APP_NOT_FOUND, scroll validation uses INVALID_INPUT. 3 new tests: connection error JSON, click error format, scroll no-option JSON. All 59 browser_cmd tests pass, ruff/mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending (branch rebased 2026-04-04)

## PR Request: fix/issue-841-calculator-uia-test
- **Base**: develop
- **Title**: fix: Calculator UIA test passes exe= and retries for WinUI 3 readiness (fixes #841)
- **Body**: Calculator (WinUI 3) has the same UIA detection challenges as UWP Notepad: launcher PID differs from window-owning process, and UIA tree may not be ready immediately. Added exe="CalculatorApp.exe" and _detect_with_retry() matching the Notepad test pattern.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending (branch rebased 2026-04-04)

## PR Request: refactor/issue-832-split-app-cmd
- **Base**: develop
- **Title**: refactor: split app_cmd.py (1,416 lines) into focused modules (fixes #832)
- **Body**: Moved all code from naturo/cli/app_cmd.py into naturo/cli/_app/ package: _common.py (shared helpers), lifecycle.py (launch/quit/relaunch/list/find), diagnostics.py (inspect), window_ops.py (focus/close/min/max/restore/move/windows), legacy.py (hide/unhide/switch). app_cmd.py remains as a thin re-export shim so all existing imports continue to work. All 4652 tests pass, ruff/mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: refactor/issue-833-split-shell
- **Base**: develop
- **Title**: refactor: split _shell.py (1,216 lines) into focused modules (fixes #833)
- **Body**: Split the monolithic ShellMixin (1,216 lines) into a _shell/ package with 6 sub-mixins: _app.py (list/launch/quit apps), _menu.py (Win32 + UIA menu enumeration), _dialog.py (open_uri, dialog detection and interaction), _taskbar.py (taskbar listing/clicking), _tray.py (system tray icons), _desktop.py (virtual desktops via pyvda). ShellMixin in __init__.py composes all sub-mixins via MRO. No public API changes — all 30 methods remain accessible. 4560 tests pass, ruff/mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-834-browser-json-flag
- **Base**: develop
- **Title**: fix: browser subcommand respects -j flag for all error paths (fixes #834)
- **Body**: _get_page() now accepts json_output and emits structured JSON (with error code, suggested_action, recoverable) on connection failure. All 32 call sites pass the flag through. Error handlers use json_error() with proper codes (SERVER_ERROR, ELEMENT_NOT_FOUND, TIMEOUT, INVALID_INPUT). Also fixes scroll no-option and captcha-solve missing-token errors. 3 new tests. All 4658 tests pass, ruff/mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-841-calculator-uia-test
- **Base**: develop
- **Title**: fix: comtypes UIA fallback probes WinUI child windows (fixes #841)
- **Body**: The comtypes fallback (Strategy 2) in probe_uia() only checked the main window handle, which is empty for standalone WinUI 3 apps like Calculator and Paint. Now probes AFH and WinUI child windows, matching the native DLL strategy. Also adds exe= and retry logic to the integration test fixture. 1 new unit test (Windows-only). All tests pass, ruff/mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending (branch rebased 2026-04-04)

## PR Request: fix/issue-810-mcp-stdout-debug
- **Base**: develop
- **Title**: fix: suppress all logging in MCP stdio transport (fixes #810)
- **Body**: Python's logging lastResort handler emits WARNING+ to stderr when no handlers are configured. In MCP stdio mode, this corrupts the JSON-RPC protocol. Now installs NullHandler on root logger, sets level to CRITICAL, and disables lastResort when transport=stdio or --json is active. 2 new tests. Ruff/mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-04
- **Status**: pending

## PR Request: fix/issue-807-press-wrong-process
- **Base**: develop
- **Title**: fix: press --app exits with error when window focus fails (fixes #807)
- **Body**: Previously press --app only logged a debug message when focus_window() failed, then silently sent keystrokes to whatever window was in the foreground. Now exits non-zero with WINDOW_FOCUS_ERROR, consistent with the type command. 2 new tests. Ruff/mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending (branch rebased 2026-04-05)

## PR Request: fix/issue-840-type-newline-drop
- **Base**: develop
- **Title**: fix: handle newlines in type_text by splitting into Enter keypresses (fixes #840)
- **Body**: The DLL's key_type sends raw Unicode but cannot produce Enter keypresses from literal \n/\r\n. Now split on newline boundaries via re.split and press_key("enter") between segments. 3 new tests. Ruff/mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending (branch rebased 2026-04-05)

## PR Request: fix/issue-834-browser-json-flag
- **Base**: develop
- **Title**: fix: browser subcommand emits JSON errors when -j flag is set (fixes #834)
- **Body**: _get_page() now accepts json_output kwarg and emits structured JSON with BACKEND_ERROR code when connection fails in JSON mode. All 30 browser subcommand callers with json_output pass the flag through. 2 new tests (unit + integration via CliRunner). Ruff clean, 4571 tests pass.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending (branch rebased on latest develop)

## PR Request: fix/issue-841-calculator-uia-test
- **Base**: develop
- **Title**: fix: Calculator UIA detection via comtypes probes child windows (fixes #841)
- **Body**: The comtypes fallback (Strategy 2) now mirrors Strategy 1 by probing AFH and DesktopWindowXamlSource child HWNDs. Fixes Calculator detection on Win11 where top-level window doesn't expose useful UIA tree. Integration tests updated with exe="CalculatorApp.exe" and _detect_with_retry matching Notepad pattern. Ruff clean, 4571 tests pass.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending (branch rebased on latest develop)

## PR Request: fix/issue-807-press-wrong-process
- **Base**: develop
- **Title**: fix: press --app exits with error when window focus fails (fixes #807)
- **Body**: Previously press --app silently logged a debug message and sent the hotkey to whatever window was focused. Now matches the type command pattern: exits with WINDOW_FOCUS_ERROR code and non-zero status when focus fails. 2 new tests (JSON + plain text). Ruff clean, 4571 tests pass.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending

## PR Request: fix/issue-840-type-newline-drop
- **Base**: develop
- **Title**: fix: handle newlines in type_text by splitting into Enter keypresses (fixes #840)
- **Body**: SendInput's UNICODE path silently drops \n and \r control characters. Now splits text on line breaks (\r\n, \r, \n) via re.split and inserts press_key("enter") between segments. 5 new tests covering \n, \r\n, trailing newline, no-newline, and CLI end-to-end. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending (branch rebased on latest develop)

## PR Request: fix/issue-810-mcp-stdout-debug
- **Base**: develop
- **Title**: fix: suppress all logging in MCP stdio transport (fixes #810)
- **Body**: When transport is stdio, _suppress_stdout_logging() redirects any stdout StreamHandler to stderr and silences chatty library loggers (uvicorn, mcp, httpx, httpcore) so debug text does not corrupt the JSON-RPC stream. 1 new test. Ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending

## PR Request: fix/issue-834-browser-json-flag
- **Base**: develop
- **Title**: fix: browser subcommand emits structured JSON errors with -j flag (fixes #834)
- **Body**: _get_page() now accepts json_output and uses emit_error() with BROWSER_CONNECTION_ERROR code. All 32 browser commands pass json_output through. All manual error handlers replaced with emit_exception_error() for consistent {success, error: {code, message}} format. 3 new tests. 4686 passed, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending (branch force-pushed clean rebuild 2026-04-05)

## PR Request: fix/issue-841-calculator-uia-test
- **Base**: develop
- **Title**: fix: Calculator UIA detection via comtypes probes child windows (fixes #841)
- **Body**: The comtypes fallback (Strategy 2) in probe_uia() only checked the main window handle, which returns an empty UIA tree for standalone WinUI 3 apps. Now mirrors Strategy 1 by probing AFH and DesktopWindowXamlSource child windows. Integration tests updated with exe="CalculatorApp.exe" and _detect_with_retry matching Notepad pattern. 1 new unit test. 4684 passed, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending (branch force-pushed clean rebuild 2026-04-05)

## PR Request: docs/readme-missing-commands
- **Base**: develop
- **Title**: docs: add 12 missing CLI commands to README tables and examples
- **Body**: README was missing 12 CLI commands added in v0.3.2: browser launch, profiles, select, download, frames, frame-find, frame-eval, stealth-check; visual suite, update, update-all; selector load. Added entries to command reference tables and usage examples section. No code changes.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending

## PR Request: test/shell-mixin-coverage
- **Base**: develop
- **Title**: test: add 42 tests for ShellMixin (app list, dialogs, taskbar, virtual desktops)
- **Body**: The _shell.py module (1,216 lines) had zero test coverage. Added 42 unit tests with full mocking of Windows APIs: list_apps (11 tests covering visibility, PID dedup, system process filtering, UWP resolution), open_uri (5 tests covering URL/file/error/timeout), _flatten_elements (2 tests), _collect_taskbar_buttons (4 tests), dialog_click_button (4 tests), dialog_set_input (3 tests), launch/quit_app (3 tests), virtual_desktop_list/switch/create/close (8 tests), menu_click/list (2 tests). All 4725 passed, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending

## PR Request: fix/issue-843-capture-popup-menus
- **Base**: develop
- **Title**: fix: capture --app composites popup menu windows from same process (fixes #843)
- **Body**: When an app has popup menus/dropdowns/tooltips open, Windows creates separate top-level windows owned by the same process. Previously capture --app selected only the main window (largest area), silently excluding popups. Added capture_app_windows() that finds all visible sibling windows from the same PID, captures each via PrintWindow, and composites them using Pillow. Falls back to single-window capture when no siblings exist. CLI routes --app and --pid through this; direct --hwnd still uses single capture. 7 new tests, all 4187+ passed, ruff+mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending

## PR Request: fix/issue-844-mcp-pydantic-leak
- **Base**: develop
- **Title**: fix: MCP tool validation errors return INVALID_INPUT instead of leaking Pydantic internals (fixes #844)
- **Body**: Pydantic ValidationError was caught by the generic Exception handler in _safe_tool, exposing raw field paths, validator names, and internal type info to MCP clients. Now detected via duck-typing and formatted into clean "Invalid input: field: message" strings with code INVALID_INPUT. Defensive fallback ensures no leak even if errors() fails. 6 new tests, all passed, ruff+mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending

## PR Request: fix/issue-807-press-wrong-process
- **Base**: develop
- **Title**: fix: press --app exits with error when window focus fails (fixes #807)
- **Body**: Before this fix, focus_window() failures were silently swallowed via logger.debug, causing keypresses to be sent to whichever window happened to be in the foreground — the wrong process. Now matches the type command's behavior: exits with WINDOW_FOCUS_ERROR when focus fails, and WINDOW_NOT_FOUND when the target window cannot be resolved. 4 new tests (63 total), all passed, ruff and mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending

## PR Request: fix/issue-810-mcp-stdout-debug
- **Base**: develop
- **Title**: fix: suppress all logging in MCP stdio transport (fixes #810)
- **Body**: When MCP server uses stdio transport, stdout IS the JSON-RPC channel. Any logging output corrupts the protocol. Added _suppress_stdout_logging() that redirects stdout StreamHandlers to stderr and silences chatty library loggers. CLI entry point also sets root logger to CRITICAL and disables lastResort handler for stdio/json modes. 4 new tests, all passed, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending

## PR Request: fix/issue-840-type-newline-drop
- **Base**: develop
- **Title**: fix: handle newlines in type_text by splitting into Enter keypresses (fixes #840)
- **Body**: The native DLL's SendInput UNICODE path silently drops \n and \r control characters. Now type_text() splits text on line breaks (re.split on \r\n|\r|\n) and presses Enter between segments. Handles all newline styles: \n, \r\n, \r. 8 new tests, all passed, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-05
- **Status**: pending
