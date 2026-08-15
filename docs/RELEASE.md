# Release Process (Internal)

Only AcePeak org members and authorized Dev agents may publish releases.

> For the full process — release **cadence policy**, CHANGELOG / release-notes
> handling, and the complete step-by-step checklist — see
> [docs/RELEASING.md](RELEASING.md). This page is the terse crib sheet.

## Version Locations (ALL 4 must stay in sync)

1. `pyproject.toml` → `version = "x.y.z"`
2. `naturo/version.py` → `__version__ = "x.y.z"`
3. `core/src/version.cpp` → `NATURO_VERSION = "x.y.z"`
4. `core/CMakeLists.txt` → `project(naturo_core VERSION x.y.z ...)`

## When to Release

- **Patch (0.x.y → 0.x.y+1):** A batch of bugfixes/improvements tested and verified by QA
- **Minor (0.x → 0.x+1.0):** ROADMAP milestone completed + full QA pass
- **Never skip QA verification before release**

## How to Release

1. Update all 3 version locations
2. Commit: `chore: bump version to x.y.z`
3. Push to main
4. `git tag vx.y.z && git push origin vx.y.z`
5. Create GitHub Release: `gh release create vx.y.z --title "vx.y.z" --notes "..."`
6. CI (publish.yml) auto-builds DLL + publishes to PyPI
7. Verify: `pip install naturo==x.y.z` works

## DLL Version Check

The CI publish workflow compiles `naturo_core.dll` from `core/src/version.cpp`.
If the DLL version doesn't match the Python version, users get a mismatch warning.
Always update all 3 files together in the same commit.
