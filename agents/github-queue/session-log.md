# Dev-Sirius Session Log
> Date: 2026-04-03

## Completed
- fix/issue-781-json-exit-code: exit non-zero when JSON mode reports failure (fixes #781) — 4 new tests
- fix/issue-783-json-stderr-suppress: suppress stderr in JSON mode (fixes #783) — 1 new test
- fix/issue-787-coords-bounds: reject out-of-bounds click coordinates (fixes #787) — 5 new tests
- fix/issue-789-app-filter-basename: extract process basename before --app matching (fixes #789) — 5 new tests
- fix/issue-788-stale-pid-routing: detect stale PID, fall back to process name (fixes #788) — 3 new tests
- fix/issue-786-uwp-menu-click: detect WinUI 3 apps for UIA click path (fixes #786) — 3 new tests

## Pushed branches (awaiting PR)
- fix/issue-781-json-exit-code
- fix/issue-783-json-stderr-suppress
- fix/issue-787-coords-bounds
- fix/issue-789-app-filter-basename
- fix/issue-788-stale-pid-routing
- fix/issue-786-uwp-menu-click

## Rebased branches
- All 6 branches had prior remote versions; rebased onto them before pushing.

## Issues found but not fixed
- Previous branches for these same 6 bugs had been deleted from remote without merging — all fixes were redone from scratch this session
- #763 (client script validation) still blocked — no rpa-client scripts in repo
- #766 (migration guide acceptance tests) still blocked — depends on browser PRs being merged
- app_cmd.py (1,416 lines) and _shell.py (1,216 lines) still need split issues

## Next session should
- Check if Orc-Mycelium created PRs for the 6 new fix branches
- Work on #763/#766 if dependencies are resolved
- Consider test coverage for backends/windows/_shell.py
- Consider splitting large files (app_cmd.py, _shell.py) — create issues
