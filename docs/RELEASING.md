# Releasing naturo

How naturo cuts a release: the **cadence policy**, the **CHANGELOG / release-notes
process**, and a **step-by-step checklist**. This document describes the process
this repository actually uses today; where a step is manual or a tool is not yet
wired up, it says so explicitly.

> This is the full process reference. `docs/RELEASE.md` is the terse "how to
> publish" crib sheet; the two must stay consistent — prefer this file.

## Cadence policy

- **Ship at least every ~2 weeks.** Whenever `develop` is green and carries
  user-visible changes, cut a release. Do not let more than two weeks pass with a
  populated `[Unreleased]` section.
- **Never let `[Unreleased]` grow stale.** Every merged PR that changes behaviour
  updates `CHANGELOG.md` under `[Unreleased]` in the same PR. If `[Unreleased]`
  has accumulated entries and the last tag is older than two weeks, that is the
  signal to release now.
- **Patch vs minor.** A batch of fixes/improvements → patch (`0.x.y` → `0.x.y+1`).
  A completed `docs/ROADMAP.md` milestone → minor (`0.x` → `0.(x+1).0`). naturo is
  pre-1.0, so breaking changes are called out in the CHANGELOG rather than gated
  behind a major bump.
- Regular small releases are the goal: visible, frequent shipping is the point of
  this policy (issue #925).

## Branch model

- **`develop`** — active development. All feature/fix branches PR into `develop`.
- **`main`** — published releases only. The only commits that reach `main` are
  release merges from `develop`, and **only version tags (`vX.Y.Z`) land on
  `main`**. Never push directly to `main`.
- Pushing a `vX.Y.Z` tag is what publishes to PyPI (see CI below).

This mirrors the rule stated in `CONTRIBUTING.md`.

## Versioning

naturo is versioned `X.Y.Z` (SemVer). The version string is duplicated across
**four** source locations that CI requires to be identical:

1. `naturo/version.py` — `__version__`
2. `core/src/version.cpp` — `NATURO_VERSION`
3. `core/CMakeLists.txt` — `project(naturo_core VERSION X.Y.Z ...)`
4. `pyproject.toml` — `version`

A fifth file, `packaging/mcpb/manifest.json` (`"version"`), must also match for
the `.mcpb` bundle.

Two guards enforce this:

- **CI `version-check` job** (`.github/workflows/build.yml`) fails the build if
  files 1–4 disagree.
- **`tests/test_version_consistency.py`** asserts the built `naturo_core.dll`
  reports the same version as `naturo/version.py` (Windows only).

### `scripts/bump_version.py` (and its one gap)

`python scripts/bump_version.py X.Y.Z` rewrites the version in:
`naturo/version.py`, `core/src/version.cpp`, `pyproject.toml`, and
`packaging/mcpb/manifest.json`.

> **Manual step / known gap:** `bump_version.py` does **not** update
> `core/CMakeLists.txt`, yet the CI `version-check` job requires it to match.
> After running the script, edit `core/CMakeLists.txt`'s `project(... VERSION
> X.Y.Z ...)` by hand, then verify with `python scripts/bump_version.py --check`
> (note: `--check` also does not inspect `CMakeLists.txt`, so confirm it visually
> or rely on CI). Fixing the script to cover all four files is tracked separately.

## CHANGELOG process

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/) with a
running `[Unreleased]` section at the top (`Added` / `Fixed` / `Changed` /
`Removed` subsections). The discipline:

1. Every behaviour-changing PR adds its entry under `[Unreleased]` with a link to
   the issue/PR — done in the same PR, not at release time.
2. **At release time**, rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD` and open a
   fresh empty `[Unreleased]` above it.
3. The CHANGELOG is the human-authored source of truth for "what changed";
   GitHub's auto-generated release notes (below) are the commit-level companion.

## Release-notes process

The GitHub Release notes are produced by **GitHub's native auto-generation**, not
a custom script:

- The `release` job in `.github/workflows/build.yml` uses
  `softprops/action-gh-release@v3` with `generate_release_notes: true`, so pushing
  a `vX.Y.Z` tag creates the Release with notes generated from merged PRs. This is
  categorised by `.github/release.yml` (labels → sections).
- For a conventional-commit–derived preview (grouped by commit *type*, not PR
  label), run `python scripts/generate_release_notes.py --range <last-tag>..HEAD`
  — handy for filling the `CHANGELOG.md` `[Unreleased]` section (both added in #419).

The two are complementary: the GitHub-native flow labels merged PRs; the script
keys off commit types, so it works even for changes that never went through a
labelled PR.

## What CI does on a tag

Pushing `vX.Y.Z` (on `main`) drives two workflows:

- **`build.yml` → `release` job** (triggered by `refs/tags/v*`): builds the
  Windows `naturo_core.dll`, builds the wheel + sdist, and creates the **GitHub
  Release** (with auto-generated notes and the DLL/wheel/sdist attached).
- **`publish.yml`** (triggered by the `release: published` event): rebuilds the
  DLL, then **publishes the wheel + sdist to PyPI** via trusted publishing
  (OIDC, the `pypi` environment). PyPI publishing lives only here — the `release`
  job intentionally does not publish, to avoid duplicate uploads (#408).

## Release checklist

Run from a clean `develop` that is green on CI.

1. **Confirm cadence.** Is `[Unreleased]` populated and/or is the last tag > ~2
   weeks old? If yes, proceed.
2. **Pick the version** `X.Y.Z` (patch for fixes, minor for a milestone).
3. **Bump versions:** `python scripts/bump_version.py X.Y.Z`, then **manually edit
   `core/CMakeLists.txt`** to the same version (see gap above).
4. **Finalise the CHANGELOG:** move `[Unreleased]` → `[X.Y.Z] - YYYY-MM-DD` and add
   a fresh empty `[Unreleased]`.
5. **Verify locally:** `python scripts/bump_version.py --check` and confirm
   `core/CMakeLists.txt` matches; run `python -m ruff check naturo/`.
6. **Commit on `develop`:** `chore: release vX.Y.Z` (version files + CHANGELOG).
   Open/merge the PR and let CI (including `version-check`) go green.
7. **Promote to `main`:** merge `develop` → `main` (release merge). This is the
   only path from `develop` to `main`.
8. **Tag on `main`:** `git tag vX.Y.Z && git push origin vX.Y.Z`. This triggers the
   `build.yml` `release` job (GitHub Release) and, on publish, `publish.yml`
   (PyPI).
9. **Verify the GitHub Release** was created with notes and artifacts; edit the
   notes to lead with the CHANGELOG highlights if desired.
10. **Verify PyPI:** `pip install naturo==X.Y.Z` succeeds.
11. **Build & attach the `.mcpb` bundle (manual):**
    `python scripts/build_mcpb.py` → `dist/naturo.mcpb`, then attach it to the
    GitHub Release. This step is **not** automated in CI today.

## Where each artifact goes

| Artifact | Produced by | Destination |
| --- | --- | --- |
| Version strings | `scripts/bump_version.py` (+ manual `CMakeLists.txt`) | source tree |
| CHANGELOG entry | hand-authored per PR | `CHANGELOG.md` |
| `naturo_core.dll` | CMake build in CI | GitHub Release + wheel |
| Wheel + sdist | `python -m build` in CI | GitHub Release + **PyPI** |
| Release notes | `generate_release_notes: true` (GitHub native) | GitHub Release |
| `.mcpb` bundle | `scripts/build_mcpb.py` (manual) | `dist/naturo.mcpb` → GitHub Release |

## Developer helper

- `python scripts/sync_dll.py` downloads the latest CI-built `naturo_core.dll`
  into `naturo/bin/` for local work (requires an authenticated `gh`). It is a
  convenience for development, not part of the release flow.
