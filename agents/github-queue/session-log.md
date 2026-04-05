# Dev-Sirius Session Log
> Date: 2026-04-04

## Completed
- fix/issue-788-stale-pid-routing: validate HWND liveness before routing keystrokes (fixes #788) — P0
- fix/issue-834-browser-json-flag: browser subcommand respects -j flag for all error paths (fixes #834) — rebased on develop
- fix/issue-841-calculator-uia-test: comtypes UIA fallback probes WinUI child windows (fixes #841) — rebased on develop
- fix/issue-810-mcp-stdout-debug: suppress all logging in MCP stdio transport (fixes #810) — rebased on develop
- fix/issue-807-press-wrong-process: press --app exits with error when focus fails (fixes #807) — rebased on develop
- fix/issue-840-type-newline-drop: handle newlines in type_text by splitting into Enter keypresses (fixes #840) — rebased on develop

## Pushed branches (awaiting PR)
- fix/issue-788-stale-pid-routing: Two-layer HWND validation — _resolve_app_id + _resolve_hwnd (P0)
- fix/issue-834-browser-json-flag: _emit_browser_error helper with structured JSON for all 30+ error paths
- fix/issue-841-calculator-uia-test: comtypes probes AFH/WinUI children + integration test retry logic
- fix/issue-810-mcp-stdout-debug: NullHandler on root logger + lastResort=None for stdio transport
- fix/issue-807-press-wrong-process: Exit with WINDOW_FOCUS_ERROR instead of silent continue
- fix/issue-840-type-newline-drop: re.split on \r\n|\r|\n + press_key("enter") between segments

## Rebased branches
- All 6 branches rebased onto latest develop and force-pushed

## Issues found but not fixed
- #842 (P0): Self-hosted runner ROBOT-COMPILE offline — cannot fix from Linux cloud environment
- #809 (P1): Unified find engine — large feature, needs dedicated session

## Next session should
- Check if PRs were created for the 6 branches above by Orc-Mycelium
- Verify CI passes on all branches
- Start work on #809 (unified find engine) if milestone bugs are clear
- Address #832/#833 (refactor app_cmd.py and _shell.py) if time permits
