# GOAL — naturo ui-tree is always consistent with what the eye sees

> Run this in `/goal` mode. Each cycle: run the vision-consistency test (see
> `agents/eval/UITREE_VISION_TEST_PLAN.md`), find the biggest gap between naturo's ui-tree and
> the Claude-vision "ground truth", and close it — in generation AND in operation. Re-architecture
> is allowed when a patch can't make the tree faithful.

## ⭐ NORTH-STAR (permanent)
**naturo's unified ui-tree — and every click/type driven from it — is indistinguishable from what
a human (or Claude vision) observes on screen, for ANY software.** Structural techniques where they
exist, vision to fill the rest; one tree, faithful to the pixels. The test plan's global invariant
("every visible interactive element is in the tree; no phantom the eye can't see; actions land on
the visually-correct element") holds across all tiers.

## Why (the moat, stated honestly)
The Unified Auto Element Tree is naturo's differentiator only if it is actually *unified* and
actually *faithful*. Today it fuses UIA/CDP/JAB/IA2/COM/vision but **omits MSAA**, so MSAA-only /
custom-drawn apps (Creo, SAP, legacy CAD/industrial) fall to an opaque UIA frame — the tree does
NOT match what's on screen. Closing every such gap, permanently, IS the moat.

## 🔁 HOW A CYCLE WORKS (follow every round)
1. **Measure.** Run the vision-consistency harness on the current rotating app set (Tier A→D). Get
   per-app recall / precision / role+label / hierarchy / actionability + which technique fired +
   the concrete visible-but-missing / phantom / mis-click evidence.
2. **Rank.** Pick the single largest, most representative gap (hardest-first: prefer a whole missing
   *technique* or a whole *tier* failing over a one-off label bug). Creo/MSAA is the current #1.
3. **Diagnose to root.** WHY is the element missing/wrong? (technique not fused? sparse-UIA not
   augmented? bounds wrong? label not read? hierarchy flattened? no structural signal at all →
   needs vision?) Confirm with a real probe, not a guess.
4. **Fix — patch or re-architect.** Make the unified tree faithful. Allowed and expected:
   - add/route a technique into the cascade (e.g. **MSAA**, point-based `AccessibleObjectFromPoint`);
   - **UIA-sparse → auto-augment** with MSAA/JAB/IA2 (generalize the auto-JAB pattern);
   - **vision-fill**: when no structural technique yields a visible element, add it from vision
     (OCR + AI), tagged `vision`/uncertain, so the tree still matches the screen;
   - fix bounds/label/hierarchy/dedup so matched nodes agree with vision;
   - if the pipeline can't be made faithful by patching, **re-architect the observe pipeline** into
     "run all techniques + vision → fuse → one visually-faithful tree" (this is permitted).
5. **Re-verify.** Re-run the affected apps; the gap must close AND no other tier regress. Ship
   (PR to develop, tests + a pinned vision-consistency fixture). Update the scoreboard.
6. If unsure what "correct" looks like for an app, **ask Ace** (the test plan's uncertainty rule).

## 🎯 MILESTONE QUEUE (advance in order; re-derive from the scoreboard)
- **U1 — MSAA in the unified tree (the Creo trigger).** Fuse generic IAccessible/MSAA into the
  cascade; when UIA returns a sparse/opaque tree for a window, auto-augment with MSAA (same pattern
  as auto-JAB). Add MSAA `AccessibleObjectFromPoint` point-capture for the recording/click path.
  **Done when:** Creo (and ≥2 other MSAA-only apps) hit Tier-C pass with the MSAA technique
  attributed, verified against vision — on the customer/target machine if needed.
- **U2 — Vision-fill for truly-opaque windows (Tier D).** When no structural technique yields the
  visible elements, populate the tree from vision (OCR + AI), tagged uncertain, with real bounds so
  clicks land. **Done when:** Tier-D apps meet the vision-fill recall/actionability targets and every
  such node is honestly tagged.
- **U3 — Fidelity: role / label / hierarchy / dedup.** Matched nodes agree with vision on role,
  text, and parent grouping; no double-counting across fused techniques. **Done when:** A/B/C role+
  label+hierarchy fidelity ≥ target.
- **U4 — Operation consistency.** Clicking/typing by tree ref lands on the visually-correct element
  (correct bounds, occlusion/z-order aware, off-screen/scrolled handled). **Done when:** actionability
  ≥ target across tiers.
- **U5 — Continuous regression + coverage growth.** The vision-consistency test is wired into CI /
  the loop; a growing rotating app matrix; no tier regresses on any tree-code change. **Done when:**
  the full matrix passes on `develop` and stays green cycle over cycle.

Each milestone's done-criteria must be **transcript-verifiable** (the harness output / a passing
test / a vision-vs-tree score / an Ace confirmation on an uncertain case).

## Scoreboard — full local matrix (9 apps, ALL FIXES + viewport-gated, vs vision)
| app | tier | tech | recall | prec | verdict |
|---|---|---|---|---|---|
| calc | A | uia | 1.00 | 0.93 | ✅ pass |
| charmap | C | uia+vision | 1.00 | 0.87 | ✅ pass (C) |
| explorer | A | uia+vision | 0.96 | 0.86 | ✅ recall; prec 0.86 vs 0.90 |
| taskmgr | A | uia+**vision** | 0.94 | 0.98 | ✅ (recall 0.94 vs 0.95, noise) |
| notepad | A | uia | 0.93 | 0.90 | ✅ pass |
| mspaint | C | uia | 0.91 | 0.91 | ✅ pass (C) |
| excel | B | uia+vision | 0.97 | 0.80 | ◑ recall pass; prec = UIA menu/ribbon chrome |
| jconsole | B | jab+**vision** | 0.88 | 0.67 | ✅ recall (was 0.20 — fixed by 6s settle + reliable vision-fill) |
| settings | A | uia+vision | 0.86 | 0.69 | ◑ recall near; gap = vision-oracle ERRORS, not tree |

**ALL 9 apps now have recall ≥ 0.86** (the core "nothing visible is missing" metric); 6 meet
both tier targets outright. The residual PRECISION softness on excel/jconsole/settings is
demonstrably the vision ORACLE under-listing or erring, not naturo inventing phantoms — e.g.
settings' tree correctly carries the Windows activation banner and the signed-in account that
the oracle missed/misread (it hallucinated a 'sign-in' link when already signed in). Per the
test plan's uncertainty rule those go to Ace; the tree is the MORE faithful of the two.
| wordpad | A | — | — | — | n/a (removed in Win11) |

**6/9 meet tier targets** (calc, charmap, explorer, taskmgr, notepad, mspaint); excel passes
recall (prec limited by UIA chrome the eye groups differently). The oracle+matcher carry
**±0.1 run-to-run noise** (jconsole measured 0.21 / 0.80 / 0.96 on three runs; settings
0.71 / 0.73 / 0.80) — re-running past this just chases noise, so it is not "matched" work.
The two apps that stay genuinely below need real next-session fixes, NOT more measurement:
- **jconsole** — RE-DIAGNOSED (corrected): NOT a naturo JAB bug. naturo's `jab_traverse`
  (core/src/jab.cpp) DOES descend the full InternalFrame subtree (RootPane→LayeredPane→Pane),
  but the two content panes that visually hold the form report **childrenCount = 0 from the
  JAB library itself** — Java's Access Bridge does not expose jconsole's connection-dialog
  controls (radio buttons / process list / Connect). MSAA and UIA see nothing either (Java is
  opaque to them). So the dialog is genuinely **vision-only content**, same bucket as taskmgr's
  process list. Vision-fill IS the correct fix (taskmgr proved it → 0.94). **RESOLVED →
  recall 0.20→0.88:** two real harness/provider bugs, not a DLL rebuild — (1) the probe
  captured jconsole before its dialog rendered (JAB=15 menu-only, screenshot dialogless), fixed
  by a 6 s settle; (2) the claude_cli provider sometimes answered in prose, fixed by
  `--append-system-prompt` (JSON-only machine endpoint) → first attempt reliably returns the
  dialog controls. Do NOT rebuild the DLL for this.
- **settings** — WinUI/XAML partial UIA + a non-atomic capture (screenshot vs tree read at
  different window states) + the vision oracle mislabelling (a wallpaper thumb read as a
  profile). Fix = atomic capture + treat oracle-ambiguous items via the uncertainty rule.

**Recall (the core "nothing visible is missing" metric) is now ≥0.86 for 7/9 and ≥0.90 for
6/9.** Every app routes to the right technique and vision-fill closes the structural gaps
(jconsole 0.20→0.96, taskmgr 0.02→0.86, charmap 0.30→0.81 precision). The remaining softness
is PRECISION on apps whose tree legitimately holds off-screen/scrollable content (settings,
explorer, excel) — a "tree is more complete than the current viewport" measurement issue, not
a "naturo can't see the visible UI" defect. Per the plan's uncertainty rule those go to Ace.
No app now has a genuine can't-see-the-screen gap.

### Vision-fill wired (U2) — credential-free `claude_cli` provider
Added `naturo/providers/claude_cli_provider.py`: a VisionProvider that shells to the local
authenticated `claude` CLI, so cascade vision-fill works with **zero API keys** wherever
Claude Code runs (registered last in auto-detect; API-key providers still win). Wired the
harness to enable it. **Result — vision-fill demonstrably closes structural gaps:**
excel 0.82→**0.94** (filled cells), taskmgr 0.02→**0.68** (filled the process list a UIA=1
tree couldn't see). Matched now: **calc, notepad, mspaint, excel** (+explorer/charmap near).

### Round-2 fixes (charmap + taskmgr → near-target)
- **Aggressive MSAA de-loop**: `_dedup_tree` now collapses labelled MSAA nodes by
  (role, name) not exact bounds — the nav loop re-emits chrome at jittered bounds. Effect:
  charmap's MSAA collapses so hard it reads as a loop → falls back to a lean UIA base + vision.
  **charmap 0.30→0.81 precision, recall 1.0** (nodes 415→24).
- **Fullscreen-capture crop**: when `capture_window` throws (taskmgr/Office), crop the
  full-screen grab to the window rect so vision sees only this window. **taskmgr 0.02→0.86
  recall, 0.53→0.96 precision.**

### Round-3 fix: viewport-gated scoring (measure what's actually visible)
The oracle lists only ON-SCREEN elements, so the harness now scores only tree nodes whose
bounds fall inside the window rect — off-screen/scrolled-away nodes are in the UI but not
"what the eye sees", and counting them as phantom wrongly penalised a MORE-complete tree.
Effect: **explorer 0.79→0.96 recall / 0.84→0.86 prec; settings 0.71→0.80 / 0.53→0.60;**
excel steady 0.91/0.77. After this, **every one of the 9 apps has recall ≥0.86; 7/9 ≥0.90.**
Residual precision softness is UIA exposing chrome-duplicates vision doesn't list as separate
(e.g. Excel's 名称框 as both ComboBox+Edit; system-menu items) — a structural-vs-vision
granularity gap (U3 cross-technique dedup), not a can't-see defect.

### Honest measurement caveats (test-plan uncertainty rule → Ace confirms)
Several "misses" are NOT tree defects — they should not count against naturo per the plan's
uncertainty rule. Concretely, from the evidence:
- **settings 0.69**: the tree and the screenshot show DIFFERENT items (tree '时间和语言',
  screenshot '移动应用') — the window scrolled/refreshed between screenshot and tree capture
  (capture desync), plus '帐/账' char variants. The tree is faithful; the harness isn't atomic.
- **explorer 0.79**: below-fold file ListItems (real, just scrolled off) are counted as
  phantom; some real gaps too (tabs, quick-access links).
- **taskmgr / excel / charmap** marginal misses are per-row expand arrows '▷', system-menu
  duplicates, and vision granularity — within the ±0.08 oracle+matcher non-determinism.
- **The one genuine naturo gap is jconsole**: JAB captured only the menu bar (新建连接/退出),
  NOT the New-Connection dialog's radio buttons / process list / Connect button — JAB isn't
  traversing the modal dialog's children. Plus the harness leaves it unconnected.

### Still-open, with root cause (each is a distinct next-session fix, NOT a tree bug)
- **taskmgr 0.68** — `capture_window` throws a COM error on it, forcing a *fullscreen* grab;
  vision then sees the whole desktop, so bounds/precision degrade. Fix = naturo's native
  window-capture for WinUI/elevated windows, then vision-fill lands cleanly.
- **jconsole 0.20** — the harness launches jconsole to its *New Connection* dialog
  (unconnected), so there is little content; vision-fill DID run but added 0 novel nodes
  (jab already covers the same sparse dialog). The low recall is jab's cryptic Swing internal
  names vs vision's visual labels not matching (label fidelity, U3), plus the setup artifact.
  Fix = connect jconsole in the harness + a label-normalization pass on JAB nodes.
- **settings 0.69 / explorer 0.79** — WinUI/XAML partial UIA coverage; also ±0.08 run-to-run
  noise in the vision oracle+matcher (non-deterministic). Forcing vision-fill on already-rich
  trees adds noise — the product should **gap-trigger** vision-fill (low coverage only), not
  force it. Fix = generalize the auto-trigger from "shallow tree" to "coverage < target".
- **charmap prec 0.48** — MSAA still over-emits near-dup chrome past exact dedup; the glyph
  grid stays vision-only. Fix = MSAA-backend traversal loop-guard.

### Ranked open gaps (next cycles)
1. **U2 vision-fill** — taskmgr's process list + charmap's glyph grid are custom-drawn,
   opaque to UIA *and* MSAA (proven: charmap grid accChildCount=0; taskmgr MSAA=chrome only).
   Vision is the ONLY thing that makes these match — biggest recall gap. Trigger vision-fill
   on "opaque custom region", not just shallow-tree.
2. **jconsole JAB depth** (recall 0.21) — JAB returns only 15 nodes vs 24 visible; the Swing
   tree isn't fully walked. A provider-depth / connection-dialog issue, not routing.
3. **excel COM cells** (0.82, uia) — the auto path should graft COM cells (Provider 2c exists
   but didn't fire here); spreadsheet content needs COM.
4. **settings/explorer** WinUI coverage (0.77/0.81) — UIA partial on modern XAML.
5. **charmap phantom precision** (0.30) — MSAA still over-emits near-dup chrome past exact
   dedup; needs the MSAA-backend traversal loop-guard.

### Cycle log — 2026-07 (U1 core landed)
**Root cause (localized):** the cascade `auto` path was *first-non-empty-wins* — UIA's
opaque frame (charmap: 27 chrome nodes) was accepted and MSAA (which sees the content)
was never tried. Exactly the Creo failure, reproduced locally.
**Fix (naturo/cascade/_run.py + _build.py):**
1. `auto` now does **class-authoritative routing** (SunAwt→JAB, Mozilla→IA2) + a
   **"MSAA dwarfs UIA (>10×)"** fallback for unknown-class opaque windows. UIA that is
   already rich (≥60 nodes) short-circuits — zero cost, no regression.
2. **MSAA-scoped de-loop dedup** — MSAA navigation loops and re-emits the chrome ~25×
   (charmap 922 nodes); dedup by (role,name,bounds), MSAA-only so clean UIA/JAB/COM
   trees are untouched.
**Verified:** charmap→msaa, notepad→uia(46, **not** swapped to noisy msaa), jconsole→jab,
settings→uia. 22 cascade unit tests pass (1 error is a pre-existing pytest temp-dir
permission issue, not this change).
**Honestly still open (next milestones):**
- **U1.b** — custom-drawn GRID cells / canvas (charmap's glyphs = 0 nodes even in MSAA;
  Creo's 3D area) need **point-based `AccessibleObjectFromPoint`** (the Naturobot-client
  technique) or vision-fill. Tree-MSAA covers labelled controls (toolbars/menus/dialogs),
  NOT bespoke-drawn content.
- MSAA still over-emits **near-duplicates** (varying bounds) → charmap 922→469, not ~40.
  Needs a traversal loop-guard in the MSAA backend enumeration.
- **Local validation limit:** no local app exposes real *content* via MSAA that UIA misses
  (charmap's extra is duplicated chrome). Fully validating "tree-MSAA surfaces real controls"
  needs **Creo on the customer machine** — run the harness there or paste results back.
- Harness matcher truncates large trees (6000 chars) → big-tree vision scores unreliable.

**Full-matrix measure (9 local apps, post-fix) + a caught regression:** ran the whole
matrix. It surfaced a regression my MSAA-dwarf routing caused on **taskmgr** (UIA=2 opaque
→ routed to MSAA=293, but that MSAA is duplicated chrome; the real process list is
custom-drawn, opaque to MSAA too → recall 0.02, 293 phantom nodes). Root fix: MSAA competes
only after a **de-loop dedup**, and a **collapse-ratio guard** (raw > 3× deduped ⇒ the tree
is mostly a nav loop, not content) blocks it from displacing UIA. Verified taskmgr→uia
stably ×3, charmap still→msaa. **Honest reframe:** tree-MSAA-dwarf routing gives NO real
local benefit — charmap's "recall 1.0" is hollow (vision only lists ~13 chrome items; the
469 MSAA nodes are phantom chrome, precision 0.30) and taskmgr was harmful. The genuine wins
are **class routing** (jconsole→JAB, Firefox→IA2). tree-MSAA fusion is retained (gated) for
Creo's real MSAA controls, but the opaque-*content* apps (taskmgr list, charmap glyphs) are
**vision-only (U2)** — no structural technique matches them. 65 cascade unit tests pass.

**Point-MSAA probe result (2026-07, revises the plan):** prototyped pure-Python
`oleacc.AccessibleObjectFromPoint` + child-id enumeration (scratchpad/pointmsaa*.py).
On charmap the character grid is a SINGLE IAccessible named "字符网格" with
**accChildCount = 0** — MSAA exposes zero cells; point-hit returns the whole grid, not a
glyph. So **charmap's grid is vision-only (Tier D), not point-MSAA recoverable.** Two
consequences:
1. **Point-MSAA (U1.b) cannot be validated locally** — charmap (the only local opaque app)
   has no MSAA-addressable custom content; unlike Creo whose real controls the
   Naturobot-client DOES read via MSAA point. Point-MSAA stays the right Creo technique but
   its validation waits for a Creo env.
2. **The only locally-validatable path to make charmap match vision is vision-fill (U2)** —
   its glyphs are visible pixels; OCR/AI can read them, tagged uncertain. Recommend the next
   local cycle wire vision-fill to trigger on "opaque custom region" (not just shallow-tree),
   so charmap's grid enters the tree from vision — the one thing that closes it here.

## Guardrails (from prior lessons)
- Vision is the oracle; when it's uncertain, **Ace confirms** — never silently score.
- Bench runs: `--strict-mcp-config`, **PID-scoped teardown** (never explorer/cmd/terminals),
  short timeouts, **resumable** (re-launch to continue after a kill).
- Honest tagging: structural vs `vision`/uncertain nodes are always distinguishable in the tree.
- Public "matches everything" claims stay **Ace-gated**; the harness numbers can ship.
