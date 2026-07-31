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
and the same `--ai-provider/--ai-model/--ai-api-key` names. (Tracked from the see
redesign as "MCP 同构 + highlight".)

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
  --ai`; AI = `--ai-provider --ai-model --ai-api-key`.  (see ✓; find, highlight TODO)
- **Interaction dispatch:** one `--input-mode`.
- **Geometry:** `--x --y --width --height`; points/offsets `X Y` (nargs=2); rects
  `X Y W H`.
- **Confirm:** `--yes/-y` to skip prompts; `--force` only for escalate/overwrite.
- **Output:** `--output/-o` (produced files) vs `--path/-p` (screenshots).
- **Short flags (frozen):** `-a`=app, `-d`=depth, `-o`=output, `-r`=ref,
  `-n`=count, `-s`=session/screen, `-j`=json.

## Phased plan (no back-compat required — small user base)

1. **Shared decorators** for the target-window group and the element-target group;
   convert all commands to use them (removes items 1, 4). Highest leverage.
2. **Recognition parity:** `find` + `highlight` adopt the see technique flags +
   `--ai-*` names (item 3); MCP `see_ui_tree` gains `techniques` (the 同构 task).
3. **Interaction dispatch:** collapse `--method`→`--input-mode` on all act commands
   (item 6).
4. **Merge app/window groups** + one geometry convention (items 2, 5-geometry).
5. **Sweep** confirm/output/short-flag conventions (items 5-coords, 7, 8, 9, 10).

Each phase is a self-contained change with tests; a shared decorator means most of
phase 1 is deletion, not addition.
