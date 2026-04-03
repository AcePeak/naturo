# Dev-Sirius Session Log
> Date: 2026-04-03

## Completed
- fix/issue-788-stale-pid-routing: validate PID liveness in AppIdMap.resolve() (fixes #788)
- fix/issue-789-app-filter-basename: extract process basename + remove substring title fallback (fixes #789)
- fix/issue-786-uwp-menu-click: use UIA click for menu items on all apps, not just UWP (fixes #786)
- fix/issue-781-json-exit-code: systemic fix — exit code 1 when JSON mode emits success:false (fixes #781)
- fix/issue-787-coords-bounds: reject out-of-bounds click coordinates (fixes #787)
- fix/issue-783-json-duplicate-stderr: suppress logging stderr in JSON mode (fixes #783)

## Pushed branches (awaiting PR)
- fix/issue-788-stale-pid-routing: PID liveness check via _is_pid_alive() in resolve()
- fix/issue-789-app-filter-basename: ntpath.basename in _resolve_hwnd + exact-only title fallback
- fix/issue-786-uwp-menu-click: try UIA click for MenuItem/Menu/MenuBar roles on any app type
- fix/issue-781-json-exit-code: _json_error_emitted flag + __main__.py exit code correction
- fix/issue-787-coords-bounds: coordinate bounds validation in click command
- fix/issue-783-json-duplicate-stderr: NullHandler on naturo logger in JSON mode

## Rebased branches
- All 6 branches rebased onto latest develop and force-pushed

## Issues found but not fixed
- None — all P0/P1/P2 bugs from pending-issues.md are now addressed

## Next session should
- Check if Orc-Mycelium created PRs for all 6 fix branches
- If any PRs have CI issues, fix them
- Move to P1 features: #104 (selector templates for Top 20 Windows apps)
- Note: #90, #91, #105 already merged into develop
