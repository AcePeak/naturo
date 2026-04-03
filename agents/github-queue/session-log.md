# Dev-Sirius Session Log
> Date: 2026-04-03

## Completed
- fix/issue-788-stale-pid-routing: validate HWND liveness via IsWindow() before routing keystrokes (fixes #788) — 2 new tests
- fix/issue-789-app-filter-basename: extract process basename with ntpath.basename() before --app matching (fixes #789) — 4 new tests
- fix/issue-786-uwp-menu-click: detect WinUI 3 apps via DesktopWindowXamlSource for UIA click path (fixes #786) — 4 new tests, 1 existing updated
- fix/issue-781-json-exit-code: exit non-zero in 3 locations where JSON mode reported failure with exit code 0 (fixes #781) — 6 new tests
- fix/issue-783-json-duplicate-stderr: add NullHandler to naturo logger in JSON mode to suppress stderr (fixes #783) — 2 new tests
- fix/issue-787-coords-bounds: reject negative and out-of-bounds click coordinates (fixes #787) — 5 new tests

## Pushed branches (awaiting PR)
- fix/issue-788-stale-pid-routing: _is_hwnd_alive() helper + APP_ID_STALE error in _resolve_app_id, IsWindow() check in _resolve_hwnd
- fix/issue-789-app-filter-basename: ntpath.basename() in _resolve_hwnd and _resolve_hwnds
- fix/issue-786-uwp-menu-click: _is_winui_window() detection + UIA click path for WinUI 3 apps
- fix/issue-781-json-exit-code: sys.exit(1) in selector clear, selector export, visual report
- fix/issue-783-json-duplicate-stderr: NullHandler on naturo logger when JSON mode active
- fix/issue-787-coords-bounds: negative + GetSystemMetrics bounds validation for click --coords

## Rebased branches
- All 6 branches force-pushed onto existing remote counterparts from previous sessions

## Issues found but not fixed
- None this session (focused on clearing the full bug backlog)

## Next session should
- Check if any of the 6 fix branches have been merged
- If merged, work on remaining items: #90 recording/playback engine, #104 built-in selector templates
- Migration guide gaps (#759, #760, #761) may need attention before v0.3.2
