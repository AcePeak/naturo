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

## E2E Tests
- [TC-0004](e2e/calculator-basic-flow.yaml) — P1: Calculator see→click→verify flow — **active**
- [TC-0010](e2e/mcp-agent-workflow.yaml) — P1: MCP server E2E: initialize→tools/list→type_text→verify — **active**
- [TC-0014](e2e/scripted-notepad-workflow.yaml) — P1: Scripted workflow: launch→JSON parse→click→type→verify→close — **active**

- [TC-0007](regression/click-on-short-text.yaml) — P1: click --on fails for short English text ('C', 'CE', 'MC') (#442) — **active**

- [TC-0009](regression/uia-detection-after-hybrid.yaml) — P1: UIA detection missing after hybrid tree merge (#455) — **retired** (5 passes, #455 closed)
- [TC-0012](regression/pid-targeting-ignored.yaml) — P0: --pid flag ignored, always returns foreground window — **active**
- [TC-0013](regression/type-app-not-found-silent-failure.yaml) — P1: type --app exits 0 on "App not found", types to wrong window (#474) — **retired** (5 passes, #474 closed)

## Exploratory Tests
- [TC-0005](exploratory/capture-popup-menu.yaml) — P1: capture --app returns tiny image when popup menu is open — **blocked**
- [TC-0006](exploratory/press-after-menu-focus.yaml) — P1: press fails silently after menu open/close cycle — **blocked**
- [TC-0008](exploratory/multi-window-targeting.yaml) — P1: --app targets different windows for type vs capture — **active**
- [TC-0011](exploratory/app-filter-cross-process.yaml) — P2: --app matches wrong process when app name in other window title — **active**

- [TC-0015](regression/app-quit-silent-failure.yaml) — P1: app quit reports success but fails to close windows with unsaved changes — **active**
- [TC-0016](regression/uwp-app-name-matching.yaml) — P1: --app flag fails to match UWP apps by common name (#469) — **retired** (5 passes, #469 closed)
- [TC-0034](regression/capture-chinese-filepath.yaml) — P1: naturo capture fails with Chinese/Unicode file paths — **active**
- [TC-0017](regression/click-en-ref-not-found.yaml) — P0: click eN ref always fails with 'Element ref not found' even after see — **retired** (5 passes, #502 closed)
- [TC-0018](exploratory/get-value-unreadable.yaml) — P1: get command returns 'no readable pattern' for Calculator display element — **active**
- [TC-0019](exploratory/explorer-matches-program-manager.yaml) — P1: --app explorer matches Program Manager instead of File Explorer — **retired** (5 passes, #524 closed)
- [TC-0020](regression/click-nonexistent-app-silent-success.yaml) — P0: click --app nonexistent exits 0 and claims success (silent failure) — **retired** (5 passes, #533 closed)
- [TC-0021](regression/type-escape-sequences-literal.yaml) — P1: naturo type treats \t and \n as literal text, not escape sequences — **retired** (5 passes, #563 closed)
- [TC-0030](regression/type-backslash-escape-missing.yaml) — P1: naturo type has no \\\\ escape for literal backslash, breaks Windows paths — **active**
- [TC-0022](exploratory/capture-missing-pid-flag.yaml) — P2: capture command missing --pid flag (API inconsistency) — **retired** (5 passes, #556 closed)
- [TC-0023](exploratory/mcp-launch-missing-pid.yaml) — P2: MCP launch_app returns success but omits PID in response — **active**

## Real-World Verification (from Ace's v0.3.1 testing — 2026-03-29)
- [TC-0024](exploratory/click-background-window.yaml) — P0: click --app hits wrong window when target is behind others (#608) — **active**
- [TC-0025](exploratory/dpi-coordinate-verification.yaml) — P0: Element coordinates wrong on 4K + 150% DPI (#613) — **active**
- [TC-0026](exploratory/ai-vision-fill-gaps.yaml) — P0: AI Vision fill-gaps returns 0 elements, JSON parsing fails (#611) — **active**
- [TC-0027](exploratory/ai-vision-coverage-false-100.yaml) — P0: AI Vision skipped because coverage falsely reports 100% (#609) — **active**
- [TC-0028](exploratory/uwp-multi-tab-quit.yaml) — P1: app quit fails to close UWP Notepad with multiple tabs (#586) — **active**
- [TC-0029](exploratory/hybrid-mode-enrichment.yaml) — P1: Hybrid mode should discover more elements than UIA-only — **active**
- [TC-0031](exploratory/notepad-menu-click-targeting.yaml) — P1: click eN on Notepad UWP menu item does not open menu — **active**
- [TC-0032](exploratory/app-title-matching-multiwindow.yaml) — P1: --app cannot match by window title for multi-window processes — **active**
- [TC-0033](exploratory/mcp-click-element-id-fails.yaml) — P1: MCP click by element_id fails, see_ui_tree refs not usable in click tool — **active**
