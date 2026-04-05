# Dev-Sirius Session Log
> Date: 2026-04-05

## Completed
- fix/issue-807-press-wrong-process: press --app exits with error (WINDOW_FOCUS_ERROR / WINDOW_NOT_FOUND) when window focus fails, instead of silently sending keys to wrong process. Rebased onto remote, resolved conflicts. 4 new tests (66 total), ruff clean. (fixes #807)
- fix/issue-840-type-newline-drop: type_text splits on \r\n|\r|\n and presses Enter between segments. Rebased onto remote, resolved conflicts. 8 new tests (32 total in file), ruff clean. (fixes #840)
- fix/issue-834-browser-json-flag: _get_page() now accepts json_output param; emits structured JSON with BROWSER_CONNECTION_ERROR when connection fails with -j. Rebased onto remote (which already had emit_error helper), resolved conflicts, kept remote's superior approach. 5 new tests (60 total), ruff clean. (fixes #834)
- fix/issue-844-mcp-pydantic-leak: _safe_tool catches Pydantic ValidationError (by class name + .errors() duck-typing) and formats into INVALID_INPUT instead of leaking internals. Rebased onto remote (which had _is_validation_error/_format_validation_error helpers), resolved conflicts. 3 new tests, ruff clean. (fixes #844)

## Pushed branches (awaiting PR)
- fix/issue-807-press-wrong-process: rebased onto remote, force-pushed
- fix/issue-840-type-newline-drop: rebased onto remote, force-pushed
- fix/issue-834-browser-json-flag: rebased onto remote, force-pushed
- fix/issue-844-mcp-pydantic-leak: rebased onto remote, force-pushed

## Rebased branches
- All four branches above were rebased onto their remote counterparts (which contained work from earlier sessions today), conflicts resolved

## Issues found but not fixed
- #843 (capture --app popup menus): NOT in codebase despite earlier session claims. Needs implementation — capture_app_windows() compositing popup/sibling windows. Medium-large task, deferred to next session.
- #842 (self-hosted runner offline): infra issue, cannot fix from Linux
- #777 (capture_screen Unicode path): DLL binary needs Windows rebuild

## Next session should
- Fix #843 (capture --app excludes popup menu windows) — P1, highest remaining priority
- Check if Orc-Mycelium created PRs for the 4 rebased branches
- Investigate PR #838 CI failure (test/recording-cmd-coverage)
- Work on #809 (unified find engine) if P1 bugs are clear
