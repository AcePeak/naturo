# Dev-Sirius Session Log
> Date: 2026-04-05

## Completed
- fix/issue-843-capture-popup-menus: rebased onto develop, pushed (fixes #843)
- fix/issue-844-mcp-pydantic-leak: added second protection layer — call_tool override catches FastMCP parameter validation errors (before function runs), sanitizes Pydantic internals. Combined with existing _safe_tool in-function catch. 9 additional tests. Rebased onto develop, pushed. (fixes #844)

## Pushed branches (awaiting PR)
- fix/issue-843-capture-popup-menus: composites popup menu windows into app capture
- fix/issue-844-mcp-pydantic-leak: two-layer Pydantic error sanitization
- fix/issue-807-press-wrong-process: exits with error when window focus fails
- fix/issue-810-mcp-stdout-debug: suppresses logging in MCP stdio transport
- fix/issue-834-browser-json-flag: browser subcommand emits JSON errors with -j
- fix/issue-840-type-newline-drop: handles newlines by splitting into Enter keypresses
- fix/issue-841-calculator-uia-test: Calculator UIA detection via comtypes
- docs/readme-missing-commands: adds 12 missing CLI commands to README
- refactor/issue-832-split-app-cmd: splits app_cmd.py into focused modules
- refactor/issue-833-split-shell: splits _shell.py into focused modules
- test/recording-cmd-coverage: recording command test coverage
- test/shell-mixin-coverage: 42 tests for ShellMixin

## Rebased branches
- fix/issue-807-press-wrong-process: rebased onto develop, pushed
- fix/issue-810-mcp-stdout-debug: rebased onto develop, pushed
- fix/issue-834-browser-json-flag: rebased onto develop, pushed
- fix/issue-840-type-newline-drop: rebased onto develop, pushed
- fix/issue-841-calculator-uia-test: rebased onto develop, pushed
- fix/issue-843-capture-popup-menus: rebased onto develop, pushed
- fix/issue-844-mcp-pydantic-leak: rebased onto develop, pushed
- docs/readme-missing-commands: rebased onto develop, pushed
- refactor/issue-832-split-app-cmd: rebased onto develop, pushed
- refactor/issue-833-split-shell: rebased onto develop, pushed
- test/recording-cmd-coverage: rebased onto develop, pushed
- test/shell-mixin-coverage: rebased onto develop, pushed

## Issues found but not fixed
- #842 (self-hosted runner offline): infra issue, cannot fix from Linux
- #777 (capture_screen Unicode path): DLL binary needs Windows rebuild

## Next session should
- Check if Orc-Mycelium created PRs for the 12 branches above
- If PRs merged, verify CI status and close issues
- Work on #777 (capture_screen Unicode file path — backlog P1)
- Work on #809 (unified find engine — P1 feature) if all bugs clear
