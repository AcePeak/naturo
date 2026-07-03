# Competitive coverage benchmark (D1)

**Prove #1 with numbers anyone can reproduce.** This harness runs naturo
head-to-head against the *real, installed* OSS rival libraries on the **same**
live windows, then renders the coverage matrix published in
[`docs/COMPETITIVE.md`](../../docs/COMPETITIVE.md).

It is the competitive counterpart to [`../recognition/`](../recognition): that
one compares naturo's cascade to naturo's *own* UIA-only baseline (a fair proxy
for a UIA-only rival); **this** one runs the rival tools themselves so the
matrix is reproducible from real runs, not authored from source claims.

## What it measures

For each `(app, framework)` it records how many interactive UI elements **each
tool** recognizes on the identical window:

| Tool | How it recognizes | Expected shape |
| --- | --- | --- |
| **naturo** | fused cascade (UIA + MSAA/IA2 + JAB + CDP + COM …) | passes across frameworks |
| **pywinauto** | walks its own **UIA** control tree (strongest UIA-only rival) | passes on UIA-native apps; **0** on Electron/Java/COM content |
| **PyAutoGUI** | pixels/coordinates only — **no element model** | **0** everywhere (reported honestly, not hidden) |

Cells: `✓ (n)` recognized n elements · `✗ (0)` ran but recognized nothing (the
moat cell when naturo passes) · `` `blocked: needs env` `` the tool could not run
on this host. **naturo's own gaps render the same way** — the matrix can't
cherry-pick.

Windows-only rivals that don't install cleanly (UFO² / Windows-MCP / Terminator)
are recorded `blocked: needs env`, never guessed.

## Layout

- **`matrix.py`** — pure aggregation + Markdown rendering. Imports neither
  naturo nor any rival, so it stays Linux-collectable; this is the logic the CI
  test (`tests/test_competitive_benchmark.py`) pins (D1 criterion 4).
- **`harness.py`** — Windows-only runtime: one `Adapter` per tool +
  `measure_competitive()` driving them against a window.
- **`run_competitive.py`** — CLI runner; reuses the reproducible fixture apps
  from `../recognition/` (Chromium, real Electron, Java/Swing, Excel COM) plus a
  UIA-native app, and emits the matrix.

## Run it (real Windows desktop)

```bash
pip install -e ".[competitive,cdp]"      # naturo + pywinauto + pyautogui
python -m benchmarks.competitive.run_competitive --markdown   # the docs matrix
python -m benchmarks.competitive.run_competitive --json       # raw data
```

The pure logic (Linux/macOS):

```bash
pytest tests/test_competitive_benchmark.py
```

## Honesty rules (D1 criterion 3)

1. Numbers come from **real runs** on the same window — never authored.
2. Rivals run with a **fair/best config** (pywinauto on its UIA backend).
3. naturo's gaps are shown, not hidden.
4. Unrunnable frameworks/rivals are `blocked: needs env`, not fabricated.
