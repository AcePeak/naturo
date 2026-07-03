# Competitive Position — Windows Desktop Automation for AI Agents

> Living competitive analysis for naturo. **Goal: become the #1 Windows RPA OSS engine on GitHub.**
> Tracked by the competitiveness program (epic #919). Orc re-evaluates **weekly** (see the tracker below).
> Full visual report regenerated each week: `C:\Users\Naturobot\naturo-competitive-report-*.html`.

## Verdict (2026-06-16, revised)
**Behind on adoption, but ahead on the thing that matters most — recognition depth.**
By GitHub stars naturo is a near-unknown newcomer (last in its peer group). But on *capability*,
naturo already has the **broadest desktop-app recognition of any OSS engine** — commercial-RPA-grade,
multi-framework — while every OSS rival is essentially UIA-only. That capability lead is the leading
indicator; stars are the lagging one. The job is to **harden + prove + market** the recognition moat.

## ★ Core differentiator — multi-framework deep recognition (the moat)
naturo recognizes UI across the frameworks commercial RPA (UiPath/AA/Blue Prism) competes on — but
**open-source and AI-agent-native**. The OSS rivals (UFO²/Windows-MCP/Terminator) are UIA/accessibility-tree
only and **fail on Java (Swing/SWT), SAP GUI, and deep Electron**. This is where naturo can be genuinely #1.

| Recognition framework | naturo | UFO² | Windows-MCP | Terminator |
|---|---|---|---|---|
| UIA (UI Automation) | ✓ | ✓ | ✓ | ✓ |
| MSAA / IAccessible2 | ✓ | ~ | ~ | ~ |
| **Java Access Bridge** (Swing/SWT) | ✓ | ✗ | ✗ | ✗ |
| **Electron / CEF via CDP** | ✓ | ✗ | ✗ | ~ browser-only |
| **SAP GUI Scripting** | ✓ | ✗ | ✗ | ✗ |
| Native app APIs (Excel/Office COM) | ✓ excel | ✓ | ✗ | ✗ |
| AI-vision fusion (cascade) | ✓ | ✓ | ~ | ~ |

> Evidence (naturo source): `backends/windows/_core.py` declares `accessibility=[uia,msaa,ia2,…]` +
> `extensions=[excel,java,sap,registry,service]`; `cascade/_providers.py` fuses UIA + CDP + vision;
> Java Access Bridge / IA2 in `backends/windows/_core.py`/`_element.py`; SAP GUI Scripting CLI exists
> (needs consolidation out of the stray `naturo/naturo/` nested dir). Maturity varies — Java/Electron/SAP
> need hardening + a published coverage benchmark to *prove* the lead (#920).

## Measured benchmark results (real runs) — the honest matrix

The table above is a capability *claim*. This is what the runnable benchmark
(`benchmarks/competitive/`, `python -m benchmarks.competitive.run_competitive --markdown`)
actually **measured** on a real desktop (2026-07-04, JDK 21), with the UIA-only rival
**pywinauto** actually running — its comtypes gen-cache had to be unblocked first (#1262/#1263)
or it was silently scored blocked, which would have flattered naturo. Element counts per tool
on the same live windows:

| App / fixture | Framework | naturo | pywinauto (UIA-only) | PyAutoGUI |
|---|---|:--:|:--:|:--:|
| JavaSwing | Java Access Bridge | **46** | **6** | 0 |
| Chromium | Electron/CDP (web content) | 85 | 113 | 0 |
| ExcelCom | Excel COM | 1177 | 1307 | 0 |

**Honest reading — this is the whole point of running the rival, not a proxy:**
- **Java/Swing is the demonstrable moat** — naturo 46 vs pywinauto **6**. UIA collapses Swing to
  an opaque frame; the Java Access Bridge is where a UIA-only tool returns ~nothing. SAP GUI and
  deep CEF are the same UIA-blind class — that is the honest headline.
- **Electron/Chromium and Excel are NOT a raw-count win** — a UIA-only rival is competitive or
  higher (Chrome exposes its accessibility tree to UIA; Excel exposes cells to UIA).
- **Metric caveat:** naturo counts cascade-*recognized* elements; pywinauto counts raw UIA
  `descendants()` (layout containers + noise). Raw count ≠ agent usefulness — an actionable/
  "meaningful interactive element" metric is the right next refinement and may change the
  Electron/Excel picture. Until it exists, claim only the Java/SAP/CEF-depth moat.

> ⚠️ **Reconcile (positioning — Ace-gated):** the capability table above marks Electron/CEF and
> Excel COM as rival-✗; the measured pywinauto run contradicts that for a UIA-only rival. The
> public claim should narrow to *deep* CEF (post-navigation DOM via CDP) and Java/SAP, framed as
> recognition *quality*, not raw presence. The README headline stays Ace-gated.

## The landscape

| Tier | Projects | Note |
|------|----------|------|
| **Agent framework / AgentOS** (a layer above engines) | microsoft/**UFO²→UFO³** (9.2k⭐) | HostAgent/AppAgent orchestration + hybrid GUI–API + OmniParser vision + PiP isolated desktop. Now **UFO³ "Galaxy"** — multi-device / cross-platform agent orchestration (repo retitled "Weaving the Digital Agent Galaxy"). Microsoft-backed. |
| **Automation engine** (eyes+hands for any LLM) — *naturo's tier* | **Windows-MCP** (CursorTouch, 6.3k⭐) · **Terminator** (mediar-ai, 1.5k⭐) · **naturo (5⭐)** | UIA/accessibility tree + MCP. naturo is clearly last. Terminator's recent release adds a NodeJS SDK, YAML workflows, and OS-event→YAML recording. |
| **Classic libraries** (pre-AI) | pywinauto (6.1k⭐) · pyautogui (12.5k⭐, stale) | Mature but not AI-native (no MCP/vision/agent layer). |
| **Cross-platform sibling** | Peekaboo 3 (4.7k⭐, macOS) | Design north-star ("eyes+hands for AI"), different platform. |

## Secondary differentiators (support the moat)
- Hardware scan-code input (games / anti-cheat). Recording/playback + selector management. Visual regression.
- **Chinese-market / CJK app** coverage where Western tools are weak. → #921
- These reinforce the headline (multi-framework recognition) but are not the core wedge on their own.

## naturo's gaps (why we're last)
- **Adoption ≈ 0** (5⭐). No user → no feedback → no trust flywheel.
- **Reliability debt** (~90 open issues, silent-failure clusters) vs Terminator (5 open issues) / Windows-MCP (2M users).
- **No distribution** (no Claude Desktop Extension, low PyPI) vs Windows-MCP's 2M Claude-Desktop users. → #922
- **Thin SDK** (Python+CLI) vs Terminator (TS/Rust/Py). → #924
- **~2-month source freeze** (Apr→Jun 2026) while every rival shipped.

## Strategy (epic #919, 5 pillars)
1. **Reliability first** — existing v0.3.2/3/4 backlog + #912 (already in flight).
2. **Recognition supremacy (the moat)** — harden + benchmark the multi-framework lead (Java / Electron-CDP / SAP / UIA) vs UIA-only rivals, and publish the coverage matrix as the headline; CJK as support. → #920, #921
3. **Distribution** — MCP registries + Claude Desktop Extension (ship-gate-independent, pull forward). → #922
4. **Release cadence** — no multi-month gaps. → #925
5. **Onboarding + SDK** — 5-min quickstart + Python SDK parity. → #923, #924

---

## Weekly Competitiveness Tracker
Primary metric: **gap → nearest peer (Terminator)** and absolute stars. "Trend" = did the gap shrink (closer)
or grow (further) since last week. Orc appends one row every 7 days.

| Date | naturo ⭐ | Terminator ⭐ | Windows-MCP ⭐ | UFO² ⭐ | naturo Δ/wk | gap → Terminator | Trend |
|------|----------|---------------|----------------|---------|-------------|------------------|-------|
| 2026-06-16 | 5 | 1,530 | 6,058 | 9,014 | — (baseline) | −1,525 | — baseline |
| 2026-06-28 | 5 | 1,542 | 6,262 | 9,153 | 0 (12d span) | −1,537 | **further** (gap +12; tracker missed 06-23 during the 6-day Ace-decision freeze) |

### How Orc updates this (weekly, headless)
On an Orch cycle where ≥7 days have passed since the last tracker row:
1. `gh api repos/<r>` stars for `AcePeak/naturo`, `mediar-ai/terminator`, `CursorTouch/Windows-MCP`, `microsoft/UFO`.
2. Light web check for any major rival release/news that week.
3. Append a dated row; compute naturo's weekly Δ and the gap → Terminator; mark **Trend: closer / further**.
4. If a rival shifted the landscape (new entrant, big release), update the sections above.
5. Regenerate the HTML report; surface a one-line week-over-week verdict to Ace in `NEEDS-ACE.md`
   (and file/refresh a `needs:ace` note if a strategic pivot is warranted).
6. Commit `docs/COMPETITIVE.md` (+ report) to `develop`.
