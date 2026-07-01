# Software Adaptation Degree

How well does naturo recognize a given piece of Windows software, and with what
correctness guarantee? This table is measured **live on the host that runs it** —
nothing is hand-authored. Frameworks that cannot be exercised on the measuring
host are marked **blocked / candidate** and are **not counted** as coverage
(no fabrication). Schema & scoring: [`docs/design/software-adaptation-degree.md`](design/software-adaptation-degree.md).

## What is measured

For one app, on the **same window in the same state**, we run naturo twice:

- **UIA-only** — `run_cascade(backend_name="uia")`: exactly the tree a UIA-only
  rival (Windows-MCP / Terminator / UFO²) would walk.
- **Cascade** — `run_cascade(backend_name="auto")`: naturo's full multi-framework
  cascade (UIA → CDP → JAB → COM, plus opt-in local OCR).

`Delta` is the elements the multi-framework cascade recovers that UIA-only cannot.
Every fused node carries `techniques[]` + `correctness` (`deterministic` for
uia/msaa/ia2/jab/cdp/com vs `uncertain` for image/ocr/vision) — see
[`docs/RECOGNITION_TREE.md`](RECOGNITION_TREE.md). The **adaptation degree** is an
honest coarse class, never a false-precision score:

| degree           | meaning                                                                       |
| ---------------- | ----------------------------------------------------------------------------- |
| `full`           | a **deterministic** non-UIA framework (cdp/jab/com/…) recovers net elements.   |
| `uncertain-only` | the only non-UIA contribution is image/OCR (recovered, but **warned**).        |
| `uia-only`       | only UIA adds value (a UIA-only rival would tie).                              |
| `blocked / candidate` | the framework is not exercisable / not wired on this host — **not counted**. |

## Measured coverage (host: this dev machine, 2026-07-01)

| Software | Framework | UIA-only | Cascade | Delta | Correctness | Degree | Source (re-runnable) |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| Chrome (local web app) | Electron/CDP (`cdp`) | 51 | 88 | **+37** | deterministic | `full` | `run_benchmark` (ChromiumFixtureApp) |
| Owned Java Swing app | Java Access Bridge (`jab`) | 6 | 46 | **+40** | deterministic | `full` | `run_benchmark` (JavaSwingFixtureApp) |
| Microsoft Excel workbook | Excel COM (`com`) | 596 | 604 | **+8** | deterministic | `full` | `naturo see --cascade --json` on a running Excel window † |
| Text baked into an image | Local OCR (`ocr`) | 20 | 25 | **+5** | uncertain (warned) | `uncertain-only` | `naturo see --cascade --ocr --json` ‡ |

- **cdp** contributes +34 web-content elements (New/Open/Save/Inbox/… inside the
  Chromium content layer UIA collapses to one node).
- **jab** contributes +40 Swing controls (Submit Order, Cancel Order, Customer
  Name, Express Shipping, the order table & catalog tree) below a `SunAwtFrame`
  UIA renders as opaque chrome. Requires the JAB-enabled JVM
  (`jabswitch -enable`) and a current `naturo_core.dll`.
- **com** recovers spreadsheet cells (Widget/Gadget/Sprocket/42/7/13) that Excel
  renders as one opaque UIA grid node; cells are projected to screen coordinates
  via Excel's `PointsToScreenPixels`.
- **ocr** recovers text baked into images/canvas (e.g. `NaturoOCR` @0.999,
  `Amount 98765` @0.986) that no accessibility API exposes; **uncertain** by
  construction, so the CLI warns and deterministic sources stay preferred.

† The automated `ExcelComFixtureApp` measured **+0 on this host** because Office
runs unactivated and pops a modal "Microsoft Excel" activation/nag dialog that
blocks the COM running-instance binding. The COM moat itself is verified by the
command above (which targets the workbook window directly). Re-run the fixture on
an **activated Office** (or with the nag pre-dismissed) to reproduce the delta
in-harness. Tracked as a fixture follow-up.

‡ OCR is **opt-in** (`--ocr`) and requires the `ocr` extra
(`pip install naturo[ocr]`, a local engine — no cloud key). Without `--ocr` the
tree contains no `ocr` nodes and no uncertain warning.

## Blocked / candidate frameworks (not counted)

| Framework | Technique | Status on this host | Reason |
| --- | --- | --- | --- |
| Firefox / IA2 | `ia2` | **candidate** | Firefox is installed, but the IA2 additive path is not yet wired into the cascade. |
| Legacy MSAA | `msaa` | **candidate** | Native path exists but is not run additively; no pure-MSAA app measured here. |
| SAP GUI | `com`/scripting | **blocked: needs env** | SAP GUI is not installed on this host. |
| Electron (npm fixture) | `cdp` | skipped | The owned Electron fixture needs `npm install`; the Chromium fixture already covers the CDP case. |

## Reproduce

```powershell
# UIA-vs-cascade coverage table (Chromium=cdp, Java Swing=jab; Excel needs activated Office):
python -m benchmarks.recognition.run_benchmark --markdown

# COM (Excel) — open a workbook with data, then target its window:
naturo see --hwnd <XLMAIN_hwnd> --cascade --backend auto --json

# OCR — a window showing text baked into an image:
naturo see --hwnd <hwnd> --cascade --ocr --json
```

All numbers above come from these commands on a real desktop. Frameworks not
exercisable here are listed as blocked/candidate and excluded from any
"N frameworks supported" count.
