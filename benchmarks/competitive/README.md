# Competitive coverage benchmark

Reproducible proof of naturo's recognition moat vs the installable OSS baselines.
Launches the **same** real apps across UI frameworks and asks each tool how many UI
elements it recognizes.

## Run

```bash
python -m benchmarks.competitive.run
```

Prints a Markdown matrix (element recognition per tool per app). Requires a real
Windows desktop. The published results live in [`docs/COMPETITIVE.md`](../../docs/COMPETITIVE.md).

## Rivals

| Tool | How it recognizes | Install |
|---|---|---|
| **naturo** | unified cascade — UIA + JAB + COM + CDP + vision | this repo |
| **pywinauto** | UIA element tree (`descendants()`) | `pip install pywinauto` |
| **PyAutoGUI** | none — pixels only (structural = 0) | `pip install pyautogui` |

`_env.py` provisions a writable comtypes gen-cache before importing pywinauto —
under a system Python its default cache is read-only / can go stale, so pywinauto
fails to import without it (naturo self-heals this; the rivals don't).

## Honesty rules

- Rivals run with a fair/best config (pywinauto on its strongest `uia` backend).
- naturo's gaps are shown too — where UIA already works (e.g. Notepad) the matrix
  shows near-parity, and naturo claims no lead there.
- A rival that can't install/run in an environment is recorded `blocked: needs env`,
  never silently scored 0.

## Extending

- **More apps/frameworks** — add to `TARGETS` in `run.py` (Excel/COM, an Electron
  app/CDP, SAP GUI …). Each needs a launch spec + framework label.
- **More rivals** — add an adapter to `rivals.py` returning `{"elements": N, ...}`
  and register it in `RIVALS`. Non-installable rivals (UFO² / Windows-MCP /
  Terminator) are documented `blocked: needs env` until they install cleanly here.

The pure matrix-formatting logic is pinned by `tests/test_competitive_harness.py`
(Linux-collectable — no desktop needed).
