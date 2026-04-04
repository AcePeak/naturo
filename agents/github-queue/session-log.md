# Dev-Sirius Session Log
> Date: 2026-04-04

## Completed
- fix/issue-834-browser-json-flag: browser subcommand emits JSON errors when -j flag set (fixes #834)
- fix/issue-841-calculator-uia-test: comtypes UIA fallback probes WinUI child windows (fixes #841)
- fix/issue-783-json-duplicate-stderr: rebased and fixed flaky NullHandler test (fixes #783)
- Rebased all 8 stale branches onto latest develop (resolved 1 merge conflict in test/visual-cmd-coverage)

## Pushed branches (awaiting PR)
- fix/issue-834-browser-json-flag: fix: browser -j flag for all error paths (fixes #834)
- fix/issue-841-calculator-uia-test: fix: comtypes UIA fallback for WinUI apps (fixes #841)
- fix/issue-788-stale-pid-routing: fix: stale PID routing (fixes #788)
- fix/issue-807-press-wrong-process: fix: press --app focus failure (fixes #807)
- fix/issue-810-mcp-stdout-debug: fix: MCP stdout debug (fixes #810)
- fix/issue-840-type-newline-drop: fix: type newline handling (fixes #840)
- refactor/issue-832-split-app-cmd: refactor: split app_cmd.py (fixes #832)
- refactor/issue-833-split-shell: refactor: split _shell.py (fixes #833)
- test/recording-cmd-coverage: test: recording CLI coverage
- test/visual-cmd-coverage: test: visual CLI coverage (conflict resolved)

## Rebased branches
- fix/issue-788-stale-pid-routing: rebased onto develop (2 behind, clean)
- fix/issue-807-press-wrong-process: rebased onto develop (2 behind, clean)
- fix/issue-810-mcp-stdout-debug: rebased onto develop (2 behind, clean)
- fix/issue-840-type-newline-drop: rebased onto develop (2 behind, clean)
- refactor/issue-832-split-app-cmd: rebased onto develop (2 behind, clean)
- refactor/issue-833-split-shell: rebased onto develop (2 behind, clean)
- test/recording-cmd-coverage: rebased onto develop (2 behind, clean)
- test/visual-cmd-coverage: rebased onto develop (2 behind, conflict resolved in test_visual.py)

## Issues found but not fixed
- #842 (P0): Self-hosted runner ROBOT-COMPILE offline — cannot fix from cloud environment
- #809 (P1): Unified find engine — large feature, needs dedicated session
- test/visual-cmd-coverage had a pre-existing syntax bug in test_update_json (missing ]) — fixed during rebase

## Next session should
- Check if PRs for #834, #841 have been created by Orc-Mycelium
- Check if remaining 8 branches have PRs created and merged
- Work on #809 (unified find engine) if v0.3.2 milestone allows
- If time permits, tackle P2 tech-debt (#832, #833 refactors)
