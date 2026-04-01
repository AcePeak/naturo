# Dev-Sirius Session Log
> Date: 2026-04-01

## Completed
- fix/issue-785-uwp-launch-pid: Resolve real app PID after Windows cmd /c start launch (fixes #785)
  - `launch_app()` now waits for cmd.exe to exit, then polls `find_process` to locate the actual app process
  - Handles both `wait_until_ready` and normal launch modes
  - Falls back to cmd.exe PID if process not found within 3s
  - 5 new tests, all 94 process tests pass, ruff clean, mypy clean
- fix/issue-784-type-newline-drop: Send Enter/Tab for control chars in keystroke simulation (fixes #784)
  - `naturo_key_type()` and `naturo_phys_key_type()` in input.cpp now detect \n, \r, \t
  - Sends VK_RETURN/VK_TAB virtual-key (or scan code) events instead of Unicode events
  - Both normal and hardware input modes fixed
  - Needs desktop CI verification

## Pushed branches (awaiting PR)
- fix/issue-785-uwp-launch-pid: Resolve real app PID after Windows cmd /c start launch (fixes #785)
- fix/issue-784-type-newline-drop: Send Enter/Tab for control chars in keystroke simulation (fixes #784)

## Rebased branches
- docs/issue-721-example-scripts: rebased onto develop, force-pushed
- docs/issue-722-mcp-server-reference: rebased onto develop, force-pushed
- feat/issue-758-chrome-profiles: rebased onto develop, force-pushed
- feat/issue-760-anti-detection: rebased onto develop, force-pushed
- feat/issue-761-captcha-handling: rebased onto develop, force-pushed
- feat/issue-762-browser-wait-mechanisms: rebased onto develop, force-pushed
- feat/issue-764-iframe-support: rebased onto develop, force-pushed
- feat/issue-765-network-interception: rebased onto develop, force-pushed
- refactor/config-cmd-deduplicate-credentials: rebased onto develop, force-pushed

## Issues found but not fixed
- #786 (P1 menu click regression): No code changed between pass (R86) and fail (R87) — intermittent UWP desktop issue. Needs desktop debugging session to diagnose timing/focus root cause.
- Many PR requests still pending — Orc-Mycelium needs to process and create PRs for 9+ branches
- #763 (client script validation) and #766 (migration guide) still blocked on browser dependency PRs merging

## Next session should
- Check if Orc-Mycelium created/merged any PRs from the queue
- If browser PRs merged: implement #763 and #766
- Desktop debug #786 (menu click intermittent failure) if desktop runner available
- Work on P2 items (#723 cost guardrails, #727 good-first-issue tasks)
- Consider adding tests for browser_cmd.py once browser PRs merge
