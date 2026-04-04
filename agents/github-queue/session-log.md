# Dev-Sirius Session Log
> Date: 2026-04-04

## Completed
- fix/issue-781-json-exit-code: selector clear, selector export, and visual report now exit non-zero when emitting {"success": false} (fixes #781)
- fix/issue-789-app-filter-basename: process basename extraction before --app matching prevents path component matches (fixes #789)
- fix/issue-787-coords-bounds: click --coords now validates coordinates against screen bounds (fixes #787)
- fix/issue-788-stale-pid-routing: stale HWND detection via IsWindow() in _resolve_app_id and _resolve_hwnd (fixes #788)
- fix/issue-783-json-duplicate-stderr: NullHandler on root logger in JSON mode + WARNING→DEBUG downgrades (fixes #783)
- fix/issue-785-winui3-uia-probe: WinUI 3 DesktopWindowXamlSource fallback in UIA probe (fixes #785)
- fix/issue-786-uwp-menu-click: _is_winui_window() detection for UIA click path on WinUI 3 apps (fixes #786)

## Pushed branches (awaiting PR)
- fix/issue-781-json-exit-code: 5 new tests
- fix/issue-789-app-filter-basename: 5 new tests
- fix/issue-787-coords-bounds: 4 new tests
- fix/issue-788-stale-pid-routing: 7 new tests
- fix/issue-783-json-duplicate-stderr: 3 new tests
- fix/issue-785-winui3-uia-probe: 4 new tests
- fix/issue-786-uwp-menu-click: 4 new tests

## Rebased branches
- None needed — previous branches were gone from remote

## Issues found but not fixed
- Previous bug-fix branches keep being deleted from remote without being merged into develop — this is the 5th+ session recreating these fixes. Orc-Mycelium is not creating PRs from them.
- #105 (user selector management) appears to already be implemented on develop
- #763 (client script validation) still blocked on browser PRs being merged
- #766 (migration guide acceptance tests) still blocked on browser PRs being merged
- app_cmd.py (1,416 lines) and _shell.py (1,216 lines) still need split issues

## Next session should
- CRITICAL: Verify Orc-Mycelium actually creates PRs from the 7 pushed branches this time
- If branches are deleted again without PRs, escalate to Ace — the fix-rework cycle is wasting sessions
- Work on #763/#766 if browser dependencies resolve
- Consider test coverage for browser_cmd.py
