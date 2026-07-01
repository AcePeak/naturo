# GOAL — naturo's north-star + how a `/goal` session drives toward it

This file is the single orienting blueprint. A `/goal` session opened in this repo reads THIS file first and
asks each turn: *"What is the single most goal-advancing action right now?"* — then does it, verifies it
independently, and repeats until the current milestone's done-criteria are observably met.

---

## ⭐ NORTH-STAR (permanent — never "done")
**Become the #1 open-source Windows RPA engine on GitHub, built for AI agents.**
Won when an AI-agent builder doing Windows automation reaches for naturo FIRST — because it (a) recognizes what
nothing else can and (b) plugs into agents cleaner than anything else. Never converges; milestones do.

### Two co-equal pillars (both drive the work)
- **A · RPA capability moat** — correctness-first, full-stack, self-healing recognition (see moat below).
- **B · AI-agent fit** — best-in-class MCP server, LLM-friendly tool schemas, self-correcting error contracts
  (code + category + recovery-hint), deterministic structured outputs, "3 lines to give your agent Windows control".

### The MOAT (the #1 thing to build): correctness-first **Unified Auto Element Tree**
Commercial RPA's first law is **correctness — enterprises need 100%**. So:
- **One app in → one fused element tree out, automatically.** Nodes fuse UIA / MSAA/IA2 / Java(JAB) / Electron·
  Chromium(CDP) / SAP / image / AI-vision. The user does **not** pick a technique by default; they may filter.
- Each node is tagged with **which techniques recognized it**, a **confidence**, and a **correctness class**:
  `deterministic` (UIA/MSAA/JAB/CDP/COM — guaranteed) vs `uncertain` (image/AI — **the CLI must WARN**). Same
  element seen by several techniques → mark all, **prefer the deterministic one** for actions/reads.
- **Self-heal (bounded, deterministic):** when a selector breaks, re-anchor to the SAME correct element via
  multi-attribute anchors — never introduce uncertainty to "heal".
- **Extensible adapter architecture:** recognition can be augmented by pluggable per-app/version adapters.

---

## 🔁 HOW A `/goal` SESSION WORKS (the process — follow this every round)
1. **Pick** the single highest-leverage slice toward the current milestone (hardest-first; whichever pillar/
   done-criterion is furthest behind). If it opens a NEW architecture area (the unified tree, adapter API, a new
   framework), first write a short **design spec / ADR** so slices compose coherently — otherwise skip straight to build.
2. **Implement** it (TDD: failing test first; ruff + mypy + pytest gates; minimal, tight diff; English only).
3. **Verify independently — spawn a FRESH-CONTEXT sub-agent** (via the Agent tool) that did NOT write the code and
   does not trust the claim: it reproduces the original problem, runs the change on the **real desktop**, tries to
   break it (non-default paths, error paths, cross-command parity), and for **agent-fit** work does an **agent-in-
   the-loop acceptance** (a real agent completes a task via naturo's MCP). FAIL → fix and re-verify (≤2 in-round
   attempts) → else revert. **Never open a PR on a failed verification.**
4. **Land** it: open a PR to `develop` (never `main`), let CI (Linux/macOS cross-platform) gate the merge.
5. **Re-eval**: update the scoreboard + this file; if the milestone's done-criteria are all observably met, advance
   to the next milestone. Append a plain-language round report to `naturo-progress.md` (capability delivered +
   distance to milestone + next).

**Non-negotiable principles:** correctness first (deterministic > AI; warn on AI/image); **test hygiene** — any
test/QA that launches an app/browser must hard-kill its **tracked PID** on teardown (no "Save/Don't-Save/Cancel"
dialog left open), PID-scoped only, **never** touch cmd/terminals or windows it didn't launch; English on all
GitHub output; never push to `main`.

---

## ✅ M1 DONE (2026-07-01) — Unified Auto Element Tree foundation
Merged to `develop` (PR #1214, commit `c4cb55e`, CI green). `naturo see --cascade --json` emits one fused,
correctness-tagged tree; `docs/RECOGNITION_TREE.md` + `tests/test_unified_tree.py` (17/17) landed; QA-verified on
UIA + Electron/CDP with zero orphaned processes. The moat foundation exists.

## 🎯 CURRENT MILESTONE — **M2: Broaden framework coverage + publish the Software-Adaptation table**
**First, cleanly re-read the existing #931 benchmark harness (authoritative source) — do NOT build on unverified
reads.** If M2 opens design questions (table schema, how coverage-degree is scored), write a short ADR first.
**Done when ALL of these are observably true:**
1. **Coverage broadened** — the fused `naturo see --cascade --json` tree correctly fuses + tags **≥2 additional
   frameworks beyond M1's UIA+CDP**, chosen from what's **reproducible on THIS machine** (e.g. Java/JAB via an owned
   Swing fixture, MSAA, image/OCR fallback). Observable: on a Java app the tree shows JAB-tagged nodes; where
   accessibility returns nothing, an image/OCR node appears tagged `uncertain` with the CLI warning.
2. **Software-adaptation table published** — `docs/SOFTWARE_ADAPTATION.md`, **generated from REAL runs on this
   machine**, one row per tested software: the techniques that recognized it + an adaptation degree (full-tree /
   partial / vision-only / none). Apps/frameworks NOT reproducible here (e.g. SAP GUI) are listed
   **`blocked: needs env`** and **NOT counted as covered** — no faked coverage.
3. **Harness-driven, not hand-authored** — the table numbers come from the (cleanly-read) #931 benchmark harness or
   a documented extension of it; re-running it reproduces the table.
4. **Test** — `pytest tests/test_adaptation_table.py` (or an extended `test_unified_tree.py`) exits 0, Linux-
   collectable, pinning the multi-framework fusion + the table-generation logic.
5. **Independent QA passed** on **≥2 of the newly-covered frameworks' real apps** — tree fuses + tags correctly,
   deterministic preferred, AI/image-only warned, **zero orphaned processes** (PID-scoped teardown, no
   Save/Don't-Save dialog left open).
6. **Merged to `develop`, CI green.**

(M2 is large — decompose one-slice-per-round: clean-read #931 → (ADR if needed) → add framework #1 to the tree →
framework #2 → adaptation-table generator + doc → the test → real-app QA. Each round runs the full
implement→independent-verify loop.)

## 🔜 MILESTONE QUEUE (advance in order; re-derive from the scoreboard as rivals move)
- **M1** — Unified Auto Element Tree foundation. ✅ DONE 2026-07-01 (PR #1214).
- **M2** — Broaden framework coverage in the tree + publish the public **software-adaptation-degree table**
  (reproducible-only; non-reproducible frameworks marked `blocked: needs env`). ← **current** (see above).
- **M3** — AI-agent fit hardening: MCP tool schemas + self-correcting error contracts + "3-line" integration
  examples that run green, proven by agent-in-the-loop acceptance.
- **M4** — Reliability/soak: no silent failures, crash-recovery, zero process leaks.
Each milestone's done-criteria must be **transcript-verifiable** (a command's output / a passing test / a QA verdict).

## ⚔️ COMPETITIVE TARGETS (prove "#1", in this order)
1. **vs OSS** (UFO² / Windows-MCP / Terminator / pywinauto / PyAutoGUI): a public, reproducible **coverage matrix**
   — same apps, naturo recognizes frameworks they return nothing on (them 0, us pass).
2. **vs commercial** (UiPath / Automation Anywhere / Power Automate Desktop): match recognition breadth + self-heal
   on common cases — open-source, AI-native, free.
3. **vs pure-vision AI** (Claude computer-use / Operator): on a benchmark task set, higher success + lower
   latency/cost via accessibility+CDP vs pixels.
Ship a **public, runnable benchmark suite** that anyone can use to verify these claims.

---

*This is a living target — re-evolved periodically by Ace. Distribution/adoption/community work is a later phase;
this phase is engineering (capability / reliability / agent-integration).*
