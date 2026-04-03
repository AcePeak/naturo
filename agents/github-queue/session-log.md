# Dev-Sirius Session Log
> Date: 2026-04-03

## Completed
- fix/issue-788-stale-pid-routing: validate HWND liveness via IsWindow() before routing keystrokes (fixes #788) — 2 new tests
- fix/issue-785-calculator-uia-probe: pass exe= and use _detect_with_retry for Calculator tests, bypass cache on retries (fixes #785)
- fix/issue-789-app-filter-basename: extract process basename with ntpath.basename() before --app matching in _resolve_hwnd, _resolve_hwnds, _is_afh_window (fixes #789) — 4 new tests
- fix/issue-784-type-newline: convert \n/\r/\r\n to Enter keypresses in type_text instead of sending raw Unicode control chars (fixes #784) — 4 new tests
- fix/issue-781-json-exit-code: exit non-zero in selector clear, selector export, visual report when reporting failure (fixes #781) — 6 new tests
- fix/issue-786-uwp-menu-click: detect WinUI 3 apps via DesktopWindowXamlSource child windows for UIA click path (fixes #786) — 2 new tests

## Pushed branches (awaiting PR)
- fix/issue-788-stale-pid-routing: _is_hwnd_alive() helper + APP_ID_STALE error in _resolve_app_id
- fix/issue-785-calculator-uia-probe: exe= param + _detect_with_retry with cache bypass
- fix/issue-789-app-filter-basename: ntpath.basename() in _resolve_hwnd, _resolve_hwnds, _is_afh_window
- fix/issue-784-type-newline: newline splitting with Enter keypresses in InputMixin.type_text
- fix/issue-781-json-exit-code: sys.exit(1) in three CLI failure paths
- fix/issue-786-uwp-menu-click: _is_winui_window() detection + UIA click for WinUI 3

## Rebased branches
- fix/issue-788-stale-pid-routing: rebased onto remote counterpart
- fix/issue-789-app-filter-basename: rebased onto remote counterpart
- fix/issue-781-json-exit-code: rebased onto remote counterpart
- fix/issue-786-uwp-menu-click: rebased onto remote counterpart

## Issues found but not fixed
- None (focused on clearing the P0 + P1 bug backlog)

## Next session should
- Check if the 6 fix branches have been merged by Orc-Mycelium
- If merged, start on P1 features: #90 recording/playback engine or #104 built-in selector templates
- Migration guide gaps (#759, #760, #761) may need attention before v0.3.2
