# Dev-Sirius Session Log
> Date: 2026-04-03

## Completed
- fix/issue-788-stale-pid-routing: validate PID liveness in AppIdMap.resolve() (fixes #788)
- fix/issue-785-calculator-uia-probe: detect UIA for standalone WinUI 3 apps like Calculator (fixes #785)
- fix/issue-789-app-filter-basename: extract process basename before --app matching (fixes #789)
- fix/issue-784-type-newline: send Enter/Tab for control chars in keystroke simulation (fixes #784)
- fix/issue-781-json-exit-code: exit code 1 when JSON mode emits success:false (fixes #781)

## Pushed branches (awaiting PR)
- fix/issue-788-stale-pid-routing: PID liveness check in AppIdMap.resolve()
- fix/issue-785-calculator-uia-probe: WinUI 3 child window fallback in probe_uia + test retry
- fix/issue-789-app-filter-basename: ntpath.basename in _resolve_hwnd + removed substring title fallback
- fix/issue-784-type-newline: control char interception in type_text
- fix/issue-781-json-exit-code: sys.exit(1) in selector clear/export and visual compare

## Rebased branches
- All 5 branches force-pushed over stale remote branches from previous sessions

## Issues found but not fixed
- #786 (UWP Notepad menu click) — not started this session, remains in backlog
- #787 (coords bounds check) — P2, not started
- #783 (JSON duplicate stderr) — P2, not started

## Next session should
- Check if Orc-Mycelium created PRs for the 5 fix branches
- Fix remaining P1: #786 (click eN on UWP Notepad menu items)
- Then P2 bugs: #787 (coords bounds), #783 (JSON stderr)
- Then P1 features: #91 (visual regression), #104 (selector templates), #105 (selector management)
