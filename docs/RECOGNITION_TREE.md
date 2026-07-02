# Unified Auto Element Tree — Node Schema & Fusion Rules (ADR)

Status: **accepted** · Milestone: **M1** · Supersedes the single `source` tag
emitted by `naturo see` today.

This document is the schema-of-record for naturo's moat: **one app in → one fused,
correctness-tagged element tree out, automatically.** Every later slice (the
fusion tagger, the `--json` contract, `tests/test_unified_tree.py`, real-app QA)
conforms to what is defined here. It complements `RECOGNITION.md` (which covers
*coverage* vs rivals); this doc defines the *node contract*.

---

## 1. Why

Commercial RPA's first law is **correctness — enterprises need 100%**. naturo
already runs a cascade that fuses several recognition frameworks
(`naturo/cascade/`): UIA → MSAA/IA2 → Java Access Bridge → Electron/CDP →
AI vision. But each node today carries only a single opaque `properties["source"]`
string. That is not enough to *reason about correctness*:

- An agent cannot tell whether a node is a **guaranteed** accessibility hit or a
  **best-guess** AI/image detection.
- When the same on-screen element is seen by two techniques, there is no record
  that both saw it, and no rule for which one to trust for an action.
- The CLI cannot warn a human/agent that it is about to act on an *uncertain* node.

The Unified Auto Element Tree fixes this by tagging **every node** with the set of
techniques that recognized it, a confidence, and an explicit **correctness class**.

## 2. Recognition techniques

A *technique* is a single recognition method. The canonical technique ids (already
used as `source` tags in `naturo/cascade/`) and their correctness class:

| technique | class           | notes                                              |
| --------- | --------------- | -------------------------------------------------- |
| `uia`     | `deterministic` | Windows UI Automation                              |
| `msaa`    | `deterministic` | MSAA / IAccessible                                 |
| `ia2`     | `deterministic` | IAccessible2                                       |
| `jab`     | `deterministic` | Java Access Bridge (Swing/AWT/SWT)                 |
| `cdp`     | `deterministic` | Chrome DevTools Protocol (Electron/CEF/Chromium)   |
| `com`     | `deterministic` | App COM/scripting (e.g. Excel, SAP GUI Scripting)  |
| `image`   | `uncertain`     | Template/image matching                            |
| `vision`  | `uncertain`     | AI vision model detection                          |

**Correctness classes** are exactly two:

- **`deterministic`** — the element and its bounds come from a structured,
  reproducible source (an accessibility API, DevTools, or app COM). Guaranteed:
  same window state → same node. Safe to act/read without a warning.
- **`uncertain`** — the element comes from image matching or an AI vision model.
  Bounds are *estimated* and may shift run to run. **The CLI must WARN** before an
  agent relies on such a node.

The class of a *technique* is fixed (the table above). The class of a *node* is
derived by fusion (§4): a node is `deterministic` if **any** of its techniques is
deterministic, else `uncertain`.

## 3. Node schema

Every node in the fused tree carries these fields (added to the existing
`naturo see --json` node object; existing fields such as `id`, `role`, `name`,
`value`, `selector`, `x/y/width/height`, `children` are unchanged):

```jsonc
{
  "id": "e12",
  "role": "Button",
  "name": "Save",
  // ... existing fields (selector, bounds, children, ...) ...

  "techniques": ["uia"],          // string[]  — every technique that recognized
                                  //   this node, deterministic-first order.
                                  //   Never empty for a real node.
  "correctness": "deterministic", // "deterministic" | "uncertain" (derived, §4)
  "confidence": 1.0               // float 0.0–1.0 (see §3.1)
}
```

Backward compatibility: the legacy `"source"` field is **retained** and set to
`techniques[0]` (the preferred technique, §4) so existing consumers keep working.

### 3.1 Confidence

`confidence` is a float in `[0.0, 1.0]`:

- **Deterministic techniques** report `1.0` — an accessibility/DevTools/COM hit is
  not probabilistic. (A future adapter may lower this to flag a known-flaky
  control; the default is `1.0`.)
- **`vision`** carries the model's self-reported confidence when available
  (already threaded through `properties["confidence"]`, default `0.5`).
- **`image`** carries the template-match score (0.0–1.0).
- For a **fused** node seen by several techniques, confidence is the **max** across
  its techniques (a deterministic hit dominates).

## 4. Fusion rules

Fusion is deterministic and bounded. Given the per-technique element sets the
cascade already produces:

1. **Same element, several techniques → one node, all marked.** When two
   techniques recognize the same on-screen element (matched by the existing
   IoU + text/proximity dedup in `naturo/cascade/_merge.py`), they collapse to a
   **single** node whose `techniques[]` lists **all** contributing techniques.
2. **Deterministic-first ordering.** `techniques[]` is ordered deterministic
   techniques first (in cascade order `uia, msaa, ia2, jab, cdp, com`), then
   uncertain (`image, vision`). `techniques[0]` is the **preferred** technique —
   the one used for actions, reads, and the legacy `source` field.
3. **Node correctness is the strongest class.** `correctness = "deterministic"` if
   any technique in `techniques[]` is deterministic, else `"uncertain"`. Thus a
   button seen by both `uia` and `vision` is `deterministic` and preferred via
   `uia`; the AI detection only *corroborates*, it never downgrades a guaranteed
   node.
4. **Uncertain-only nodes survive but are flagged.** An element that *only* AI or
   image matching found (no deterministic technique covered that region) stays in
   the tree — that is the coverage moat — but is `correctness: "uncertain"` and
   triggers the CLI warning (§5).
5. **No fabricated fusion.** Techniques are only merged when the existing dedup
   matches them. Two genuinely distinct elements are never collapsed to inflate a
   node's correctness.

## 5. CLI contract (`naturo see`)

`naturo see … --json` emits **one** fused tree per app/window where **every node**
carries `techniques[]`, `correctness`, and `confidence`.

- **Deterministic preferred:** where the same element is seen by several
  techniques, the deterministic one is `techniques[0]` and drives actions/reads.
- **AI/image warning (required):** when the tree contains **any** node whose only
  source is `image`/`vision` (`correctness == "uncertain"`), the CLI prints a
  single clear warning to **stderr** (never polluting `--json` stdout), e.g.:

  ```
  warning: 3 element(s) were recognized only by AI/image (uncertain); their
  bounds are estimated and may shift. Deterministic sources are preferred for
  actions. Run with --no-vision to exclude them.
  ```

  In `--json` mode the same fact is also exposed structurally as a top-level
  `recognition_summary` object (counts per technique + `uncertain_nodes`) so an
  agent can branch on it without parsing stderr.
- **stdout purity:** the warning goes to stderr; `--json` stdout stays a single
  valid JSON document (honoring the existing stdout-purity contract).

## 6. Self-heal (bounded, deterministic)

When a stored selector breaks, naturo re-anchors to the **same** element via
multi-attribute anchors (role + name + AutomationId + relative position among
siblings) drawn from the deterministic tree. Self-heal **never** introduces an
uncertain technique to "heal" a deterministic node — healing that crosses into
`uncertain` must surface as a warning, not a silent substitution. (Implementation
tracked as a later M1/M4 slice; this ADR fixes the invariant.)

## 7. Extensible adapter architecture

Recognition is augmented by pluggable, per-app/version **adapters**. An adapter
may (a) contribute a new technique for a node, (b) refine bounds/roles for a known
app, or (c) raise/lower a node's confidence. Adapters MUST declare their technique
id and its correctness class (§2) and MUST NOT relabel an `uncertain` technique as
`deterministic`. The fusion rules (§4) apply uniformly to adapter-contributed
techniques. (Adapter API is a later milestone; this ADR reserves the contract so
adapters compose with the schema.)

## 8. Non-goals for M1

- Cross-window graph fusion (M1 is per app/window).
- SAP/Qt/terminal/OCR technique coverage (M2).
- The self-heal and adapter *implementations* (contracts fixed here; code later).
