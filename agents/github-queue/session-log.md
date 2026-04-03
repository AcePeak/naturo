# Dev-Sirius Session Log
> Date: 2026-04-03

## Completed
- fix/issue-788-stale-pid-routing: add PID liveness check in AppIdMap.resolve() (fixes #788)
- fix/issue-789-app-filter-basename: extract process basename before --app matching (fixes #789)
- fix/issue-786-uwp-menu-click: use UIA click for menu items on all apps, not just UWP (fixes #786)
- fix/issue-781-json-exit-code: exit code 1 when JSON output contains verified:false (fixes #781)
- fix/issue-787-coords-bounds: reject out-of-bounds click coordinates (fixes #787)
- fix/issue-783-json-duplicate-stderr: suppress logging stderr in JSON mode (fixes #783)

## Pushed branches (awaiting PR)
- fix/issue-788-stale-pid-routing: _is_pid_alive() in resolve(), 6 new tests
- fix/issue-789-app-filter-basename: ntpath.basename in _resolve_hwnd + _resolve_hwnds, 3 new tests
- fix/issue-786-uwp-menu-click: UIA click for MenuItem/Menu/MenuBar roles, 1 new + 1 updated test
- fix/issue-781-json-exit-code: _json_ok handles verified:false systemically, 4 new tests
- fix/issue-787-coords-bounds: coordinate validation in click command, 7 new tests
- fix/issue-783-json-duplicate-stderr: NullHandler on naturo logger in JSON mode, 1 new test

## Rebased branches
- All 6 branches force-pushed to replace stale remote branches from previous session

## Issues found but not fixed
- None — all P0/P1/P2 bugs from pending-issues.md are now addressed

## Next session should
- Check if Orc-Mycelium created PRs for all 6 fix branches
- If any PRs have CI issues, fix them
- Move to P1 features: #104 (selector templates for Top 20 Windows apps)
- #105 (user selector management) if time permits
