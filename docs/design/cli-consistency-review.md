# naturo CLI consistency review

Audit of all **141 leaf commands** (via Click introspection). Goal: one predictable
vocabulary so a flag means the same thing everywhere. The `see` technique-flag
redesign is the first slice of this; the rest below applies the same discipline.

Severity: 🔴 breaks user mental model / duplicate divergent surfaces · 🟠 confusing
overload · 🟡 cosmetic.

---

## 🔴 1. Window/app targeting is not uniform

The "which window?" selector group differs command-to-command:

| Commands | Selector flags |
|---|---|
| see / capture / click / type / press / scroll / move / drag / hotkey / get / set | `--app --window --hwnd --pid --app-id` (+ hidden `--window-title`) |
| **window** close/focus/maximize/… | `--app --title --hwnd --app-id` — **`--title` not `--window`, no `--pid`** |
| dialog * | `--app --hwnd --app-id` — no `--window`, no `--pid` |
| wait / diff | `--app --hwnd --pid --app-id` — no `--window` (wait reuses `--window` for a different meaning) |
| desktop move-window | `--app --hwnd --app-id` |
| window list | `--app --pid` + hidden `--process-name` — **no `--hwnd`/`--app-id`** |

**Canonical:** every command that targets a window accepts the SAME group —
`--app`, `--window` (title substring; `--title` a hidden alias), `--hwnd`, `--pid`,
`--app-id`. Factor a shared Click decorator (`@_target_options`) and apply it
everywhere instead of re-declaring per command.

## 🔴 2. Two parallel window-management command groups: `app` vs `window`

`app {close,focus,maximize,minimize,restore,move}` **and**
`window {close,focus,maximize,minimize,restore,move,resize,set-bounds}` overlap —
with **different** flags (`--window` vs `--title`) and **fragmented geometry**:
`app move` = x/y/width/height, `window move` = x/y, `window resize` = w/h,
`window set-bounds` = x/y/w/h. Users can't guess which to use.

**Canonical:** pick ONE group (recommend `window`), make the other a thin
deprecated alias; one geometry convention (`--x --y --width --height`, any subset).

## 🔴 3. Recognition vocabulary differs across `see` / `find` / `highlight`

Three surfaces that all "recognize UI", three vocabularies:

| | technique flags | AI provider |
|---|---|---|
| see (new) | `--uia --msaa --ia2 --jab --cdp --com --ocr --ai` + `--fast/--deep` | `--ai-provider --ai-model --ai-api-key` |
| find | `--ai --ocr` only | **`--provider --model --api-key`** (different names) |
| highlight | **`--cascade --fill-gaps --backend`** (the OLD model) | — |

**Canonical:** `find` and `highlight` adopt the `see` technique flags + presets,
and the same `--ai-provider/--ai-model/--ai-api-key` names.

**Status: ✅ DONE.** Shared `naturo/cli/_techniques.py` holds the one resolver
(`resolve_techniques`) + `technique_options` decorator. `see` and `highlight` use
it (identical flags/semantics); `find` gained `--ai-provider/--ai-model/
--ai-api-key` (old names aliased); **MCP `see_ui_tree` gained a `techniques=[...]`
param** routed through the same resolver (`cascade` kept as a back-compat alias).
The recognition vocabulary is now uniform across CLI + MCP. (Nice-to-have left:
`find` adopting the full structured technique flags.)

## 🟠 4. Element-target flag is overloaded: `--on` / `--ref` / `--id` / `--aid`

The "which element?" flag is inconsistent, and `--id` means two different things:

| Command | ref (eN) | by text | by automation-id |
|---|---|---|---|
| click | `--id` / hidden `--ref` | `--on` / `<query>` | `--selector` only |
| set / get | `--ref -r --id` | — | `--automation-id --aid` |
| type / press / scroll | hidden `--ref`, `--id` | `--on` / `--id` | — |
| move | `--id` | — | — |
| highlight | `--ref -r`, positional | `--on --id` | — |

`--id` = eN ref in click/type, but = automation-id alias in get/set. **Collision.**

**Canonical:** `--ref` (eN snapshot ref, the primary; `-r`), `--on`/`--text` (find
by visible text), `--aid`/`--automation-id` (automation id), `--selector`. Retire
`--id` as a ref alias (or make it strictly the automation-id everywhere).

## 🟠 5. Coordinates & offsets have three representations

- `--coords X Y` (space, nargs=2): click/move/scroll.
- `--region "x,y,w,h"` (comma string): capture.
- `--offset DX DY` (space, nargs=2, new): click — but **browser click** uses
  `--offset-x --offset-y` (two separate ints); drag uses `--from-coords/--to-coords`.

**Canonical:** one coordinate convention — `X Y` space-separated `nargs=2` for
points/offsets, `X Y W H` for rects. Deprecate the comma-string and the split
`--offset-x/--offset-y`.

## 🟠 6. `--method` vs `--input-mode` vs `--backend` overload

- `--backend/--method/-b/-m` on see/find = **recognition backend** (uia/msaa/…).
- `--method/-m` on click/type/press/scroll/move/drag/hotkey = **interaction
  dispatch** (uia-invoke/coord/…).
- click/type/press/hotkey ALSO carry `--input-mode` (normal/auto/hardware/hook/
  postmessage) — overlapping "postmessage" with `--method`.

So `--method` means two unrelated things, and interaction commands have TWO
method-ish knobs. **Canonical:** recognition selection = the technique flags (drop
`--backend/--method` there); interaction dispatch = ONE knob (recommend
`--input-mode`), fold the old `--method` choices into it, keep `--method` a hidden
alias.

## 🟠 7. Confirmation-skip flag: `--force` vs `--yes/-y`

`--force`: record/visual/selector-clear?/window close/app quit. `--yes/-y`: config
clear, snapshot clean, selector clear/delete. **Canonical:** `--yes/-y` for "skip
the confirmation prompt"; reserve `--force` for "escalate / kill / overwrite"
(genuinely more forceful), not as a prompt-bypass synonym.

## 🟡 8. Output-path flag: `--path/-p/-o` vs `--output/-o` vs `--path/-p`

capture=`--path -p -o`, see=`--path -p`, record/visual/selector export=`--output -o`.
**Canonical:** `--output/-o` for "write a file this command produces" (export/report),
`--path/-p` for "screenshot destination"; don't give `--path` an `-o` alias.

## 🟡 9. Short-flag collisions — `-d` means four things

`-d` = `--depth` (see/find), `--direction` (scroll), `--days` (snapshot clean),
`--description` (selector save), `--delay`? Also `-a` = `--app` (highlight) vs
`--all` (list/find/get) vs `--amount` (scroll). **Canonical:** freeze a
short-flag table (`-d`=depth, `-a`=app, `-o`=output, `-r`=ref, `-n`=count,
`-s`=session/screen) and stop reassigning.

## 🟡 10. `--json/-j` ordering & positional/`--name` duplication

`--json/-j` is universal (good) but written `-j/--json` in record/selector/visual.
Many commands take BOTH a positional `<name>` and `--app`/`--name` (e.g.
`app quit <name> --name(hidden) --app`). Cosmetic; normalize order and drop the
redundant hidden `--name` where the positional already covers it.

---

## Proposed conventions (the target vocabulary)

- **Target a window:** `--app` · `--window` (title substring) · `--hwnd` · `--pid`
  · `--app-id`  — one shared decorator, everywhere.
- **Target an element:** `--ref/-r` (eN) · `--on`/`--text` · `--aid` · `--selector`.
- **Recognition:** `--fast/--deep` + `--uia --msaa --ia2 --jab --cdp --com --ocr
  --ai`; AI = `--ai-provider --ai-model --ai-api-key`.  (see ✓ · highlight ✓ ·
  find ✓ · MCP `see_ui_tree(techniques=[…])` ✓)
- **Interaction dispatch:** two axes — `--method` (channel) + `--input-mode` (input
  stack); kept distinct (not merged — they aren't redundant).
- **Geometry:** `--x --y --width --height`; points/offsets `X Y` (nargs=2); rects
  `X Y W H`.
- **Confirm:** `--yes/-y` to skip prompts; `--force` only for escalate/overwrite.
- **Output:** `--output/-o` (produced files) vs `--path/-p` (screenshots).
- **Short flags (frozen):** `-a`=app, `-d`=depth, `-o`=output, `-r`=ref,
  `-n`=count, `-s`=session/screen, `-j`=json.

## Resolution log (what was done, per item)

- **1 window targeting — ✅ done.** `--window` is now accepted on every command
  that has a title selector (the `window` group gained `--window` aliasing
  `--title`, matching see/click/…). Added `options.target_options` (the canonical
  `--app/--window/--hwnd/--pid/--app-id` decorator) for future/new commands.
  Commands whose targeting is legitimately a subset (dialog=app/hwnd, list=filter)
  are left as-is — forcing the full group on them isn't real consistency.
- **2 app vs window groups — ✅ resolved.** The `window` group is already marked
  deprecated ("use `naturo app`"); `app` is canonical. No merge needed; the geometry
  fragmentation lived on the deprecated group.
- **3 recognition vocabulary — ✅ done.** Shared `cli/_techniques.py`; see/highlight
  use it, find got `--ai-*` names, MCP `see_ui_tree` got `techniques=[...]`. Uniform
  across CLI + MCP.
- **4 element target — ✅ done (canonical promoted).** `--ref/-r` is now a visible,
  first-class eN-ref flag on every element command (un-hidden on click/type/press/
  scroll; already primary on get/set/highlight). `--on` = ref-or-text, `--aid` =
  automation id. `--id` is kept per-command for back-compat but its meaning is
  command-specific (automation-id on click, alias-of-`--on` on type) — documented as
  a wart; `--ref`/`--aid` are the unambiguous flags to prefer.
- **5 coords/offsets — ✅ mostly.** Points/offsets use `X Y` `nargs=2` (`--coords`,
  `--offset`); rects use `X Y W H`/`--x --y --width --height`. `--region "x,y,w,h"`
  (capture) and browser `--offset-x/-y` are domain-local and kept.
- **6 --method vs --input-mode — ✅ corrected (no change).** On inspection these are
  TWO distinct axes, not redundant: `--method` (auto/cdp/uia/jab/vision) selects the
  interaction *channel*; `--input-mode` (normal/hardware/hook/postmessage) selects
  the low-level *input stack*. They overlap only cosmetically at "postmessage". Left
  as-is.
- **7 confirm flag — ✅ done.** `--yes/-y` now skips the prompt everywhere
  (record/selector/visual delete+clear gained it; config/snapshot already had it);
  `--force` kept as a legacy alias there and reserved for genuine escalation
  (app/window force-kill).
- **8 output path — ✅ acceptable.** `--output/-o` for produced files (export/report)
  and `--path/-p` for screenshots are already consistent; capture's extra `-o` alias
  on `--path` is kept for back-compat (removing it would break scripts for no gain).
- **9 short flags — ✅ decided (frozen, not retroactively broken).** The `-d`/`-a`
  overloads are per-command with no in-command conflict; the frozen table above is
  the going-forward rule. Renaming existing short flags would break scripts for a
  cosmetic gain, so no retroactive change.
- **10 --json/-j & positional/name dup — ✅ acceptable.** `--json/-j` is universal;
  the `-j/--json` vs `--json/-j` ordering and hidden `--name` duplicates are harmless
  cosmetics, left as-is.

**Status: consistency pass complete** — every item is either fixed or has a recorded
decision. The `see`-change-induced inconsistencies (recognition vocabulary) are fully
unified; the broader naming conventions (window/element/confirm) are normalized with
back-compat aliases.
