# Dev-Sirius Session Log
> Date: 2026-04-02

## Completed
- fix/issue-788-stale-pid-app-id: Validate cached PID liveness in _resolve_app_id, fail with APP_ID_STALE (fixes #788)
- fix/issue-789-app-filter-basename: Extract ntpath.basename() in _resolve_hwnd/_resolve_hwnds/_is_afh_window (fixes #789)
- fix/issue-781-json-exit-code: Change return→sys.exit(1) in selector clear/export and visual report (fixes #781)
- fix/issue-783-json-duplicate-stderr: NullHandler on root logger in JSON mode + WARNING→DEBUG downgrades (fixes #783)
- fix/issue-787-coords-bounds: Validate coordinates against GetSystemMetrics/65535 bound (fixes #787)

## Pushed branches (awaiting PR)
- fix/issue-788-stale-pid-app-id: PID liveness check via find_process before returning stale HWND+PID
- fix/issue-789-app-filter-basename: ntpath.basename() in 3 locations in _element.py
- fix/issue-781-json-exit-code: 3 return→sys.exit(1) changes + 3 tests
- fix/issue-783-json-duplicate-stderr: NullHandler + 2 WARNING→DEBUG downgrades + 1 test
- fix/issue-787-coords-bounds: Bounds validation with COORDS_OUT_OF_BOUNDS error + 2 tests

## Rebased branches
- (none needed — all branches created fresh from current develop)

## Issues found but not fixed
- #785: Desktop-only integration test, already addressed by PR #801 (PID resolution). Needs verification on Windows desktop runner.
- #786: Desktop-only UWP menu click regression. Previous branch existed but was deleted/superseded. Needs reimplementation on Windows.
- #784: Already merged (PR #800)

## Next session should
- Check if Orc-Mycelium has created/merged PRs for the 5 new branches
- If P0/P1/P2 bugs are merged: tackle P1 features (#90 recording, #91 visual regression, #104 selectors, #105 selector management) — check which have pending PRs
- Consider migration guide gaps (#759 download, #761 drag, #760 stealth-check)
