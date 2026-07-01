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

## 🎯 CURRENT MILESTONE — **M3: AI-agent fit hardening (pillar B — co-equal, so far untouched)**
Make naturo the RPA tool an AI agent plugs into cleanest. **Done when ALL of these are observably true:**
1. **MCP exposes the moat** — naturo's MCP server exposes the core recognition + action capabilities, **including
   the M1/M2 unified `see --cascade` tree**, as clean MCP tools (clear name + description + typed params). Observable:
   a CI test enumerates the MCP tools and asserts each has a description + input schema, and the unified-tree
   capability is reachable via MCP.
2. **Self-correcting error contract on MCP** — every MCP tool error returns the full contract (**code + category +
   recovery-hint**) so an agent can self-correct (extend the #884/#1180 envelope work to the MCP surface).
   Observable: a CI test drives MCP error paths and asserts each returns a **registered** code + category + hint,
   never a bare string.
3. **"3-line" integration** — `docs/AGENT_INTEGRATION.md` shows wiring naturo's MCP into an agent in ~3 lines
   (e.g. `claude mcp add naturo -- python -m naturo mcp`, or an mcp-config snippet) + a runnable example, and the
   command it documents actually works.
4. **Agent-in-the-loop acceptance (desktop)** — a **real Claude-Code agent with naturo's MCP configured** (using
   the existing login auth; **no separate API key** — the Anthropic API is reachable via the 127.0.0.1:7890 proxy)
   completes an end-to-end desktop task **through naturo MCP tools** (e.g. launch Notepad → find the edit area via
   the unified tree → type text → read it back), verified by the independent QA sub-agent's transcript showing the
   agent actually used naturo MCP tools and succeeded, with **zero orphaned processes**.
5. **CI-runnable test** for the MCP schemas + error contracts exits 0, Linux-collectable (this layer needs no
   LLM/desktop — it is deterministic pytest).
6. **Merged to `develop`, CI green.**

(M3 is large — decompose one-slice-per-round: expose unified tree via MCP → MCP error-contract sweep + test →
integration doc + working `claude mcp add` → the agent-in-the-loop desktop acceptance. Each round runs the full
implement→independent-verify loop. The agent-in-the-loop uses Claude Code as the agent; the CI layer is pure pytest.)

## 🔜 MILESTONE QUEUE (advance in order; re-derive from the scoreboard as rivals move)
- **M1** — Unified Auto Element Tree foundation. ✅ DONE 2026-07-01 (PR #1214).
- **M2** — Broaden framework coverage + publish the software-adaptation-degree table. ✅ DONE 2026-07-01 (#1215/#1216/#1217).
- **M3** — AI-agent fit hardening: MCP tool schemas + self-correcting error contracts + "3-line" integration
  examples + agent-in-the-loop acceptance. ← **current** (see above).
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
