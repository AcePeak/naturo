# Naturo Software Support Program

This directory tracks naturo's **verified support for popular end-user software**, the
strict evidence bar an app must clear to be listed, and the reproducible artifacts
that prove it.

It complements [`../SOFTWARE_ADAPTATION.md`](../SOFTWARE_ADAPTATION.md): that doc
measures the *recognition delta* (UIA-only vs cascade) at the framework level; this
program measures whether naturo can **actually drive a real product, unattended and
repeatably, to extract the data that product is used for.**

## Goal

- **Phase 1 — 100 mainstream Chinese-world apps** (household names).
- **Phase 2 — 100 mainstream English-world apps.**

Every listed app records the **version range** it was validated against.

## Acceptance gate

An app is admitted to the support list only when **all** of the following hold. A
`candidate` that fails any gate stays `candidate` (or `in-progress`) with the failing
gate noted — it is never listed as supported on partial evidence.

| Gate | Requirement |
|------|-------------|
| **G1 Reach real value** | The naturo script gets *past* login / onboarding / setup and reaches the product's core valuable data. No credit for spinning on login or splash screens. |
| **G2 Extract valuable data** | naturo actually reads that valuable data (the thing the product exists for) — not just the window chrome, nav, or menus. |
| **G3 Operate** | naturo performs the real operation(s) needed to obtain / manipulate that data (search, open, filter, edit, export, …). |
| **G4 Vision cross-check** | Claude vision compares a screenshot against naturo's element tree: nothing fabricated, nothing valuable missing. |
| **G5 Token-lean tree** | `see_ui_tree` output is compact, the tree structure is reasonable and minimal, and it fits the token budget. |
| **G6 Repeatable & correct** | A fully automated naturo script runs the task **unattended and repeatedly**, staying correct on every run. |
| **G7 Version range** | The validated version range is recorded in the catalog. |

## Workflow (per app)

1. **Install** the app (record exact version) — winget preferred, else vendor installer.
2. **Define the valuable-data task** — the one thing this product is used for (e.g.
   NetEase Music → a ranked song list; Xunlei → the download-task list; Navicat → table rows).
3. **Author a repeatable naturo script** that reaches and extracts it (G1–G3).
4. **Measure & verify** — element tree + token count (G5), vision cross-check (G4).
5. **Repeat-run** the script to confirm determinism (G6).
6. **Record** the result in `catalog.yaml`; archive the evidence pack under `evidence/<id>/`.
7. **Uninstall** and move to the next candidate.

## Layout

```
docs/software_support/
  README.md          # this file — the gate & workflow
  catalog.yaml       # the 100 (+100) candidates and their status
  evidence/<id>/     # per-app: screenshots, element tree, vision verdict, token count, script
```

## Status values

- `candidate` — listed, not yet attempted.
- `in-progress` — being worked; note the current gate.
- `supported` — all gates G1–G7 passed; version range recorded.
- `blocked` — cannot be supported on this host / by current naturo (note why).
