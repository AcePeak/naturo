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

## 🎯 CURRENT MILESTONE — **M1: Unified Auto Element Tree (foundation, correctness-tagged)**
The single most moat-advancing thing to build first. **Done when ALL of these are observably true:**
1. **Design spec** committed: `docs/RECOGNITION_TREE.md` defines the unified node schema — `techniques[]`,
   `confidence`, and `correctness` class (`deterministic` vs `uncertain`).
2. **Command**: a `naturo` command emits **one fused tree** per app/window in `--json` where every node carries
   `techniques[]` + `correctness`; deterministic sources are preferred; the CLI prints a clear **warning** when a
   node's only source is image/AI.
3. **Test**: `pytest tests/test_unified_tree.py` exits 0 and is collectable on Linux CI (no Windows-only imports at
   module top) — proving the fusion, the tagging, and the AI-warning.
4. **Independent QA passed** on **≥2 real apps of different frameworks** (e.g. a UIA app + a Java or Electron app):
   the tree fuses + tags correctly, deterministic preferred, AI-only nodes warned — with **zero orphaned processes**
   after teardown.
5. **Merged to `develop`, CI green.**

(M1 is large — decompose it into one-slice-per-round: design spec → tree fusion for 2 frameworks → correctness/
warning tagging → the test → real-app QA. Each round still runs the full implement→independent-verify loop.)

## 🔜 MILESTONE QUEUE (advance in order; re-derive from the scoreboard as rivals move)
- **M1** — Unified Auto Element Tree foundation (current).
- **M2** — Broaden framework coverage in the tree (SAP, Qt, terminal, image/OCR fallback) + a public **software-
  adaptation-degree table** built from real apps tested on this machine (reproducible-only).
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
