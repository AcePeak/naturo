# Test Case Catalog
> Maintained by QA-Mariana. Each test case is a YAML file in a subdirectory.

## Status Legend
- **active** — Run every round
- **retired** — Issue closed + passed 5 consecutive rounds, no longer run
- **blocked** — Depends on unmerged fix, skip until unblocked

## Regression Tests
- [TC-0001](regression/type-chinese-ime.yaml) — P0: naturo type wrong text on Chinese IME (#425) — **retired** (5 passes, #425 closed)
- [TC-0002](regression/click-exit-code.yaml) — P1: click/press returns exit code 2 on success (#426) — **retired** (5 passes, #426 closed)
- [TC-0003](regression/chinese-app-name-matching.yaml) — P1: --app with Chinese titles inconsistent across commands — **active**

- [TC-0038](regression/uwp-notepad-enumeration.yaml) — P0: UWP Notepad intermittently invisible to list apps after launch — **active**
- [TC-0040](regression/capture-unicode-path-dll.yaml) — P1: naturo_core.dll capture_screen fails with Unicode file path — **active**
- [TC-0041](regression/json-mode-exit-code-zero-on-failure.yaml) — P1: JSON mode (-j) returns exit code 0 on failure, breaking scripts — **active**
- [TC-0042](regression/type-escape-newline-dropped.yaml) — P1: type -E silently drops newline chars during keystroke simulation — **active**
- [TC-0043](regression/calculator-uwp-invisible.yaml) — P0: app launch calculator reports success but Calculator invisible to list/see (#785) — **active**
- [TC-0045](regression/type-stale-pid-silent-failure.yaml) — P0: type --app routes to stale PID after app restart, silently drops keystrokes — **active**
- [TC-0046](regression/see-error-exit-code-zero.yaml) — P1: see --app returns exit 0 on error in non-JSON mode — **active**

## E2E Tests
- [TC-0004](e2e/calculator-basic-flow.yaml) — P1: Calculator see→click→verify flow — **active**
- [TC-0010](e2e/mcp-agent-workflow.yaml) — P1: MCP server E2E: initialize→tools/list→type_text→verify — **active**
- [TC-0014](e2e/scripted-notepad-workflow.yaml) — P1: Scripted workflow: launch→JSON parse→click→type→verify→close — **active**

- [TC-0007](regression/click-on-short-text.yaml) — P1: click --on fails for short English text ('C', 'CE', 'MC') (#442) — **retired** (5 passes, #442 closed)

- [TC-0009](regression/uia-detection-after-hybrid.yaml) — P1: UIA detection missing after hybrid tree merge (#455) — **retired** (5 passes, #455 closed)
- [TC-0012](regression/pid-targeting-ignored.yaml) — P0: --pid flag ignored, always returns foreground window — **retired** (5 passes, #471 closed)
- [TC-0013](regression/type-app-not-found-silent-failure.yaml) — P1: type --app exits 0 on "App not found", types to wrong window (#474) — **retired** (5 passes, #474 closed)

## Exploratory Tests
- [TC-0005](exploratory/capture-popup-menu.yaml) — P1: capture --app returns tiny image when popup menu is open — **active**
- [TC-0006](exploratory/press-after-menu-focus.yaml) — P1: press fails silently after menu open/close cycle — **blocked**
- [TC-0008](exploratory/multi-window-targeting.yaml) — P1: --app targets different windows for type vs capture — **active**
- [TC-0011](exploratory/app-filter-cross-process.yaml) — P2: --app matches wrong process when app name in other window title — **active**

- [TC-0015](regression/app-quit-silent-failure.yaml) — P1: app quit reports success but fails to close windows with unsaved changes — **active**
- [TC-0016](regression/uwp-app-name-matching.yaml) — P1: --app flag fails to match UWP apps by common name (#469) — **retired** (5 passes, #469 closed)
- [TC-0034](regression/capture-chinese-filepath.yaml) — P1: naturo capture fails with Chinese/Unicode file paths — **retired** (6 passes, #693 closed)
- [TC-0017](regression/click-en-ref-not-found.yaml) — P0: click eN ref always fails with 'Element ref not found' even after see — **retired** (5 passes, #502 closed)
- [TC-0018](exploratory/get-value-unreadable.yaml) — P1: get command returns 'no readable pattern' for Calculator display element — **active**
- [TC-0019](exploratory/explorer-matches-program-manager.yaml) — P1: --app explorer matches Program Manager instead of File Explorer — **retired** (5 passes, #524 closed)
- [TC-0020](regression/click-nonexistent-app-silent-success.yaml) — P0: click --app nonexistent exits 0 and claims success (silent failure) — **retired** (5 passes, #533 closed)
- [TC-0021](regression/type-escape-sequences-literal.yaml) — P1: naturo type treats \t and \n as literal text, not escape sequences — **retired** (5 passes, #563 closed)
- [TC-0030](regression/type-backslash-escape-missing.yaml) — P1: naturo type has no \\\\ escape for literal backslash, breaks Windows paths — **retired** (6 passes, #619 closed)
- [TC-0022](exploratory/capture-missing-pid-flag.yaml) — P2: capture command missing --pid flag (API inconsistency) — **retired** (5 passes, #556 closed)
- [TC-0023](exploratory/mcp-launch-missing-pid.yaml) — P2: MCP launch_app returns success but omits PID in response — **retired** (6 passes, #575 closed)

## Real-World Verification (from Ace's v0.3.1 testing — 2026-03-29)
- [TC-0024](exploratory/click-background-window.yaml) — P0: click --app hits wrong window when target is behind others (#608) — **active**
- [TC-0025](exploratory/dpi-coordinate-verification.yaml) — P0: Element coordinates wrong on 4K + 150% DPI (#613) — **retired** (5 passes, #613 closed)
- [TC-0026](exploratory/ai-vision-fill-gaps.yaml) — P0: AI Vision fill-gaps returns 0 elements, JSON parsing fails (#611) — **active**
- [TC-0027](exploratory/ai-vision-coverage-false-100.yaml) — P0: AI Vision skipped because coverage falsely reports 100% (#609) — **active**
- [TC-0028](exploratory/uwp-multi-tab-quit.yaml) — P1: app quit fails to close UWP Notepad with multiple tabs (#586) — **retired** (5 passes, #586 closed)
- [TC-0029](exploratory/hybrid-mode-enrichment.yaml) — P1: Hybrid mode should discover more elements than UIA-only — **active**
- [TC-0031](exploratory/notepad-menu-click-targeting.yaml) — P1: click eN on Notepad UWP menu item does not open menu — **active**
- [TC-0032](exploratory/app-title-matching-multiwindow.yaml) — P1: --app cannot match by window title for multi-window processes — **active**
- [TC-0033](exploratory/mcp-click-element-id-fails.yaml) — P1: MCP click by element_id fails, see_ui_tree refs not usable in click tool — **active**
- [TC-0035](exploratory/press-standalone-modifier.yaml) — P2: naturo press fails for standalone modifier keys (alt, ctrl, shift) — **active**
- [TC-0036](regression/quit-chinese-app-name.yaml) — P1: app quit with Chinese app name targets wrong PID and fails — **retired** (5 passes, #743 closed)
- [TC-0039](exploratory/app-id-filter-see.yaml) — P1: --app aN (app ID) fails for see/click but --app-id aN works — **retired** (5 passes, #752 closed)
- [TC-0042](exploratory/json-stderr-duplicate-error.yaml) — P2: JSON mode (-j) emits duplicate error to stderr, breaks 2>&1 pipe — **active**
- [TC-0044](exploratory/click-coords-out-of-bounds.yaml) — P2: click --coords accepts out-of-bounds coordinates without warning — **active**
- [TC-0047](exploratory/press-app-focus-mismatch.yaml) — P1: press --app hotkey sends to wrong process when target is not focused (#807) — **active**
- [TC-0048](regression/mcp-stdout-debug-output.yaml) — P1: MCP server emits debug text to stdout, breaking JSON-RPC stdio protocol — **retired** (5 passes, #810 closed)
- [TC-0049](exploratory/browser-json-error-format.yaml) — P1: Browser commands ignore -j flag, output plain text errors instead of JSON — **active**
- [TC-0050](regression/type-default-multiline-dropped.yaml) — P1: Default type mode drops literal newlines from multi-line text — **active**
- [TC-0051](exploratory/mcp-pydantic-error-leak.yaml) — P2: MCP tool call with wrong param leaks Pydantic internals in error — **active**
- [TC-0052](exploratory/get-id-flag-rejected.yaml) — P2: Only `click` accepts `--id eN`; 8 other element-targeting commands reject it (#864) — **active**
- [TC-0053](exploratory/see-json-envelope-inconsistency.yaml) — P2: `see -j` returns bare tree on success but envelope on error (#865) — **active**
- [TC-0054](exploratory/input-cmd-exit-code-on-no-desktop.yaml) — P2: input commands exit 2 + 'Usage:' on runtime errors instead of exit 1 (#866) — **active**
- [TC-0055](exploratory/hidden-snapshot-typo-leak.yaml) — P2: Hidden `snapshot` command leaks into Click's 'Did you mean' suggestions (#867) — **active**
- [TC-0056](regression/mcp-capture-screen-silent-black.yaml) — P0: MCP `capture_screen` returns all-black PNG with success:true when desktop not bindable (#868) — **active**
- [TC-0057](exploratory/deps-prompt-leaks-into-json.yaml) — P2: Optional-dep install prompt leaks into -j JSON output (#869) — **active**
- [TC-0058](exploratory/window-targeting-flag-matrix.yaml) — P2: Window-targeting flag matrix (--app/--window/--hwnd/--pid) inconsistent across subcommands (#871) — **active**
