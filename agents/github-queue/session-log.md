# Dev-Sirius Session Log
> Date: 2026-04-05

## Completed
- fix/issue-807-press-wrong-process: press --app exits with WINDOW_FOCUS_ERROR when focus fails (fixes #807)
- fix/issue-840-type-newline-drop: split newlines into Enter keypresses in type_text (fixes #840)
- fix/issue-834-browser-json-flag: browser subcommand emits JSON errors when -j flag is set (fixes #834)
- fix/issue-841-calculator-uia-test: comtypes UIA fallback probes WinUI child windows (fixes #841)

## Pushed branches (awaiting PR)
- fix/issue-807-press-wrong-process: WINDOW_FOCUS_ERROR on focus failure, 2 tests
- fix/issue-840-type-newline-drop: re.split on \r\n|\r|\n + press_key("enter"), 3 tests
- fix/issue-834-browser-json-flag: _get_page() JSON errors for all 32 browser subcommands, 2 tests
- fix/issue-841-calculator-uia-test: comtypes probes AFH/WinUI children + integration test exe= param, 1 test

## Rebased branches
- All 4 branches based on latest develop (force-pushed over stale previous branches)

## Issues found but not fixed
- #842 (P0): Self-hosted runner ROBOT-COMPILE offline — cannot fix from Linux cloud environment
- #809 (P1): Unified find engine — large feature, needs dedicated session
- #810 (P1): MCP stdout debug suppression is already in develop via NullHandler on root logger

## Next session should
- Check if PRs were created for 4 branches above by Orc-Mycelium
- Verify CI passes on all branches
- Start work on #809 (unified find engine) if milestone bugs are clear
- Address #832/#833 (refactor app_cmd.py and _shell.py) if time permits
