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

## ✅ M2 DONE (2026-07-01) — Broadened coverage + Software-Adaptation table
Merged (PRs #1215 `6024f2d` + #1216 `f93266c` + #1217, CI green). Added COM/Excel + local OCR + JAB/Java Swing to
the fused tree; `docs/SOFTWARE_ADAPTATION.md` published from real runs (non-reproducible frameworks marked
`blocked: needs env`). Open follow-ups (own issues, not M2 blockers): IA2/Firefox wiring, Excel-fixture nag
dismissal (COM verified +8 via direct command; automated fixture reads +0 on un-activated Office), MSAA additive.

## ✅ M3 DONE (2026-07-01) — AI-agent fit hardening
Merged (PR #1218 `a550c6d`, CI green). MCP exposes the unified `see --cascade` tree; self-correcting error contract
across MCP (42 paths, 0 violations); `docs/AGENT_INTEGRATION.md` 3-line integration; a real Claude agent completed
an end-to-end desktop task through naturo MCP (type→read-back character-exact), QA-verified, zero orphans. Bonus:
an enterprise correctness bug fixed — stale comtypes gen-cache silently killed the whole UIA write layer → now
self-heals + WARNs (#1219/#1220, `7d5925c`).

## 🎯 CURRENT MILESTONE — **M4: Reliability & soak (the commercial-grade 100%-correctness floor)**
Capability is strong; now make it **trustworthy** — enterprises need 100%, and a capable-but-flaky tool loses.
**Done when ALL of these are observably true:**
1. **No silent failures (guarded)** — extend the #885/#1180 work: a CI source/behavior guard **fails** if any CLI
   or MCP path can return `success:true` on a failed operation; the known silent-failure classes are closed.
   Observable: `pytest` for the silent-failure guard exits 0 AND the guard catches a planted violation (positive control).
2. **Crash-recovery generalized** — after a backend/DLL/COM failure the **next** call self-heals (re-inits) rather
   than staying broken (generalize the comtypes self-heal #1220 to the recognition/input layers). Observable: a test
   forces a backend failure, then asserts the next call succeeds + logs a WARNING.
3. **Zero process leaks (enforced)** — the #1202 guaranteed-teardown fixtures cover **every** launching test; a
   before/after process-snapshot harness asserts **zero** orphaned test-launched processes after the full
   desktop+browser suite (PID-scoped, dialogs dismissed, cmd/terminals never touched). Observable: the snapshot
   harness reports 0 orphans.
4. **Soak stable** — a bounded soak (**≥100 consecutive** recognition+action cycles on **≥2 real apps**) completes
   with zero crashes, zero degradation, zero leaks. Observable: a soak harness runs the cycles and reports 0
   failures/0 leaks (desktop QA).
5. **CI-runnable** reliability tests (silent-failure guard, crash-recovery, teardown-snapshot) exit 0, Linux-collectable.
6. **Merged to `develop`, CI green.**

(M4 is large — decompose one-slice-per-round: silent-failure guard+sweep → crash-recovery generalization → the
teardown-snapshot harness across all launching tests → the soak harness + real-app soak run. Each round runs the
full implement→independent-verify loop; the CI layer is deterministic pytest, the soak/crash-recovery layer is desktop QA.)

## 🔜 MILESTONE QUEUE (advance in order; re-derive from the scoreboard as rivals move)
- **M1** — Unified Auto Element Tree foundation. ✅ DONE 2026-07-01 (PR #1214).
- **M2** — Broaden framework coverage + publish the software-adaptation-degree table. ✅ DONE 2026-07-01 (#1215/#1216/#1217).
- **M3** — AI-agent fit hardening: MCP + self-correcting error contracts + integration + agent-in-the-loop. ✅ DONE 2026-07-01 (#1218).
- **M4** — Reliability/soak: no silent failures, crash-recovery, zero process leaks. ← **current** (see above).
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
