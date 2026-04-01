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
- **Status**: pending (branch recreated and force-pushed 2026-04-01)

## PR Request: docs/issue-722-mcp-server-reference
- **Base**: develop
- **Title**: docs: create dedicated MCP server reference (fixes #722)
- **Body**: Comprehensive reference for all 58 MCP tools across 11 modules (capture, window, UI inspection, input, app control, wait, snapshot, clipboard, dialog, system, Excel). Includes setup instructions for stdio/SSE/HTTP transports, parameter details, common patterns, error handling, and a worked Notepad automation example.
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: pending (branch recreated and force-pushed 2026-04-01)

## PR Request: refactor/issue-719-cli-by-domain
- **Base**: develop
- **Title**: refactor: reorganize CLI commands by domain (fixes #719)
- **Body**: Moved system commands (clipboard, dialog, desktop, taskbar, tray) into `cli/system/` subdirectory and value commands (get, set) into `cli/values/`, following the existing pattern established by `cli/core/` and `cli/interaction/`. Renamed `system.py` to `_app_group.py` (it only defines the app Click group stub) and removed 100+ lines of dead code (unused menu, taskbar, tray stubs superseded by dedicated cmd files). All test mock patch paths updated. 4166 tests pass, ruff clean, mypy clean.
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: pending
