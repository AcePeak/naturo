# GOAL — naturo's north-star and current sub-goal (the loop orients to THIS)

This is the single orienting target for the whole loop (Dev / QA / Orch). Every cycle reads this file FIRST
and asks: *"What is the single most goal-advancing action I can take right now?"* — not just "what's the next
issue by priority." The Orchestrator maintains this file (Step 3 / Step 3.7) and advances the sub-goal.

This is **goal mode**, not cadence mode: the timer is only a heartbeat. What drives a cycle is distance-to-goal.

---

## ⭐ NORTH-STAR (permanent — never "done")
**Become the #1 Windows RPA open-source engine on GitHub.**
The loop never converges on this; it continuously closes the gap. Sub-goals (releases) converge and auto-advance.

### Strategy / moat (how we win, not by racing UIA stars)
**Recognition supremacy:** commercial-RPA-grade multi-framework recognition — UIA + MSAA/IA2 + Java Access
Bridge + Electron/CDP + SAP GUI + AI-vision — where every OSS rival (UFO² / Windows-MCP / Terminator) is
UIA/accessibility-tree only. Backed by reliability (no silent failures) + honest docs + distribution.

### Scoreboard (measure the gap every week — Orch Step 3.5)
- **Stars vs rivals** (Terminator nearest peer) — tracked in `docs/COMPETITIVE.md`.
- **Recognition coverage matrix** — frameworks naturo handles that UIA-only rivals can't (the headline proof).
- **Reliability** — silent-failure count trending to zero; ship-gate bugs closed.
A week with no movement on the scoreboard is a failure of the north-star, even if cycles were "busy."

---

## 🎯 CURRENT SUB-GOAL: ship v0.3.2 — complete, not a half-product
**Done-criteria (ALL must hold; this is the convergence test):**
1. **Recognition moat hardened beyond UIA for the v0.3.2 set:** Electron/CDP (#933 ✅) + Java Access Bridge
   (#932/#1096) both prove real-app recognition via a passing test; `docs/RECOGNITION.md` matrix published (#982 ✅).
2. **find engine** (#809): `--selector` (✅) + `--image` (✅) + `--ocr` (#1060 — **OCR engine decided 06-28: RapidOCR
   optional extra `naturo[ocr]`, #1077 closed; now Dev-actionable, not yet shipped**) all shipped & QA-verified.
3. **Migration validation** (#766 fixtures + #763 rpa-client equivalence) green.
4. **All ship-gate bugs QA-verified+closed**, develop CI green, no half-finished feature.
5. **Release sign-off (#914) is HUMAN-ONLY** → queue it in needs:ace; do NOT block the loop on it.

**When done-criteria 1–4 hold:** put "v0.3.2 ready to cut (#914)" at the TOP of NEEDS-ACE.md, then
**auto-advance**: pull the next milestone (v0.3.3) as the current sub-goal and keep driving — do NOT idle
waiting for Ace's release click. The loop never stalls on a human-only gate; it advances the next sub-goal's
work while the gate waits.

### Known blockers on the current sub-goal (surface, don't silently skip)
- ~~**#1096 JAB attach fails** — local build blocked by no MSVC/cmake (#1097)~~ — **NATIVE-BUILD BLOCK CLEARED 06-28**:
  Ace provisioned the C++ toolchain on NATUROBOT (MSVC 14.44 + CMake + Ninja, smoke build produced `naturo_core.dll`);
  #1097 closed; build recipe on #1097; pointer + root-cause on #1096. **#1096 is now Dev-actionable** (fix the async
  JVM handshake in `jab_ensure_init`, build+verify locally) — no human gate remains; this is now Dev execution work.
- ~~**#1060 --ocr** — blocked on OCR-engine choice (#1077)~~ — **RESOLVED 06-28**: Ace picked **RapidOCR** as an
  optional extra (`pip install naturo[ocr]`; MIT/Apache, offline, Chinese-strong, bundled ONNX models); #1077 closed.
  **Dev picked #1060 06-28 ~15:14Z (`status:in-progress`, in flight)** — done-criterion #2 now actively being shipped.
- **#1168** — Dev/QA crons are **session-only**; loop freezes with no Orch session alive (scheduler, needs:ace).
  Now the **only** human-gated blocker on done-criteria 1–4 — both #1096 (JAB) and #1060 (OCR) are pure Dev execution.
These are the highest-leverage items for Ace — keep them at the top of the needs:ace digest with a clear ask.

---

## 🔜 SUB-GOAL QUEUE (auto-advance order)
1. **v0.3.2** (current) — recognition moat + find engine + migration validation.
2. **v0.3.3** — SAP GUI recognition (#934, needs SAP env) + remaining recognition hardening.
3. **v0.3.4** — reliability/contract backlog (envelope/exit-code/MCP consistency).
4. Then re-derive the next gap-closing milestone from the scoreboard vs rivals.

When the current sub-goal's done-criteria 1–4 hold, the Orchestrator updates "CURRENT SUB-GOAL" to the next
queue entry (rewrite its done-criteria from that milestone's open issues) and logs the advance in STATE.md.
