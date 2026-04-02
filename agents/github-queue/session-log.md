# Dev-Sirius Session Log
> Date: 2026-04-02

## Completed
- fix/issue-788-stale-pid-hwnd: Detect stale PID/HWND after app restart, fall back to process name (fixes #788)
- fix/issue-789-app-filter-basename: Extract process basename before --app matching (fixes #789)
- fix/issue-781-json-exit-code: Exit non-zero when JSON mode reports failure (fixes #781)
- fix/issue-783-json-duplicate-stderr: Suppress stderr output in JSON mode (fixes #783)
- fix/issue-787-coords-bounds: Reject out-of-bounds click coordinates with clear error (fixes #787)
- fix/issue-786-uwp-menu-click: Detect WinUI 3 apps for UIA click path (fixes #786)

## Pushed branches (awaiting PR)
- fix/issue-788-stale-pid-hwnd: Two-layer PID/HWND validation with process-name fallback
- fix/issue-789-app-filter-basename: ntpath.basename() in _resolve_hwnd and _resolve_hwnds
- fix/issue-781-json-exit-code: sys.exit(1) in selector clear/export and visual report
- fix/issue-783-json-duplicate-stderr: NullHandler + WARNING→DEBUG downgrades
- fix/issue-787-coords-bounds: Coordinate bounds validation with GetSystemMetrics
- fix/issue-786-uwp-menu-click: _is_winui_window() DesktopWindowXamlSource detection

## Rebased branches
- (none needed — all branches created fresh from current develop)

## Issues found but not fixed
- Previous session's pending PRs for #90 (recording), #104 (selector templates), and many others still need Orc-Mycelium to create PRs

## Next session should
- Check if Orc-Mycelium has created PRs for the 6 new branches + previous pending branches
- If all P0/P1/P2 bugs are merged: enter self-driven mode
- Consider working on remaining migration guide gaps (#759 download, #761 drag, #760 stealth-check)
- Update ROADMAP.md to reflect completed features
