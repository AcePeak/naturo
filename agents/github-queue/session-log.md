# Dev-Sirius Session Log
> Date: 2026-04-04

## Completed
- fix/issue-781-json-exit-code: exit non-zero when JSON reports failure (fixes #781) — 6 new tests
- fix/issue-789-app-filter-basename: extract process basename before --app matching (fixes #789) — 5 new tests
- fix/issue-787-coords-bounds: reject out-of-bounds click coordinates (fixes #787) — 8 new tests
- fix/issue-783-json-stderr-suppress: suppress stderr in JSON mode (fixes #783) — 2 new tests
- fix/issue-788-stale-pid-routing: detect stale PID, fall back to process name (fixes #788) — 3 new tests
- fix/issue-786-uwp-menu-click: detect WinUI 3 for UIA click path (fixes #786) — 4 new tests

## Pushed branches (awaiting PR)
- fix/issue-781-json-exit-code
- fix/issue-789-app-filter-basename
- fix/issue-787-coords-bounds
- fix/issue-783-json-stderr-suppress
- fix/issue-788-stale-pid-routing
- fix/issue-786-uwp-menu-click

## Rebased branches
- None needed — all previous branches existed on remote, fetched and force-pushed with new implementations

## Issues found but not fixed
- Previous bug-fix branches keep getting deleted from remote without merging — this is a recurring process issue across multiple sessions. Orc-Mycelium may be cleaning branches before creating PRs.
- #763 (client script validation) still blocked — no rpa-client scripts in repo
- #766 (migration guide acceptance tests) still blocked — depends on browser PRs being merged
- app_cmd.py (1,416 lines) and _shell.py (1,216 lines) still need split issues

## Next session should
- Verify Orc-Mycelium created PRs for the 6 bug-fix branches
- If branches are deleted again without merging, escalate to Ace — this has happened 3+ sessions in a row
- Work on #763/#766 if dependencies resolve
- Consider self-driven mode: test coverage gaps, code health scan
