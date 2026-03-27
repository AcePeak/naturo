# AGENTS.md — Agent Registry & Working Guide

## Project: Naturo

Windows desktop automation engine. C++ core + Python wrapper.
Repo: https://github.com/AcePeak/naturo

## Agent Registry & Naming Convention

**Pattern**: `{Role}-{Name}`

| Role | Theme | Examples |
|------|-------|----------|
| **Dev** | Celestial bodies | Dev-Sirius, Dev-Vega, Dev-Rigel |
| **QA** | Earth's geography | QA-Mariana, QA-Everest, QA-Sahara |
| **Orc** | Microscopic organisms | Orc-Mycelium, Orc-Tardigrade, Orc-Neuron |

Every agent MUST know: its full name, its role, and which files to read on startup.

## File Map

| File | Dev reads | QA reads | Orc reads | Who maintains |
|------|-----------|----------|-----------|---------------|
| `AGENTS.md` | ✅ | ✅ | ✅ | Ace / Orc |
| `agents/RULES.md` | ✅ | ✅ | ✅ | Ace |
| `agents/VISION.md` | ✅ | ✅ | ✅ | Ace / Orc |
| `agents/STATE.md` | ✅ | ✅ | ✅ writes | Orc (auto) |
| `agents/dev/SOUL.md` | ✅ | | | Ace |
| `agents/qa/SOUL.md` | | ✅ | | Ace |
| `agents/orchestrator/dev-prompt.md` | ✅ | | | Ace / Orc |
| `agents/orchestrator/qa-prompt.md` | | ✅ | | Ace / Orc |
| `docs/ROADMAP.md` | ✅ | ✅ | ✅ | Dev / Orc |

## Language

- **All code, comments, docstrings, commit messages, docs, and issue titles must be in English.**
- No Chinese or other non-English text in the codebase, including TODOs and inline comments.
- Variable names, function names, class names — all English.
- This is non-negotiable for open-source readiness.

## Code Style

### General
- Comments must be complete and meaningful. Every public function, class, and module needs a docstring or header comment explaining what it does, its parameters, and return values.
- Avoid "TODO" without context — always include what needs to be done and why.
- Self-documenting code is preferred, but complex logic requires inline comments.

### C++ (core/)
- Standard: C++17
- Compiler: MSVC (primary), GCC/Clang (secondary)
- Naming: `snake_case` for functions, `PascalCase` for classes
- All public APIs must be `extern "C"` with `NATURO_API` macro
- Include guards, not `#pragma once`
- Every exported function in `exports.h` must have a Doxygen-style comment

### Python (naturo/, tests/)
- Version: 3.9+
- Type hints on all public APIs (required), internal functions (encouraged)
- Docstrings for all public classes, methods, and functions (Google style)
- No `from __future__` imports needed (3.9+ baseline)
- Test functions must have descriptive names and a brief docstring

## Testing

**TDD is mandatory.** Write tests first, then implement.

1. Write a failing test
2. Implement minimum code to pass
3. Refactor
4. Get review

### C++ Tests
- Location: `core/tests/`
- Framework: Simple main() with pass/fail printf (no gtest dependency for now)
- Run: `ctest --test-dir build --build-config Release`

### Python Tests
- Location: `tests/`
- Framework: pytest
- Markers: `@pytest.mark.ui` for tests needing a desktop session
- DLL tests: Use `@pytest.mark.skipif(platform.system() != "Windows")`

## Commit Messages

Use [conventional commits](https://www.conventionalcommits.org/):

```
feat: add screen capture API
fix: handle DPI scaling in click coordinates
test: add UI tree depth tests
docs: update architecture diagram
chore: bump vcpkg dependencies
```

## Branch Strategy & Git Workflow

**main is production. Never push directly to main.**

1. Create a feature branch from main:
   ```bash
   git checkout -b feat/capture-screen
   ```
2. Develop with TDD (write tests, implement, refactor)
3. Push the branch and create a PR:
   ```bash
   git push origin feat/capture-screen
   gh pr create --title "feat: add screen capture API" --body "..."
   ```
4. Wait for CI to pass (all jobs must be green)
5. Self-review with QA/PD/Security lenses
6. Squash merge to main:
   ```bash
   gh pr merge --squash
   ```

### Branch Naming

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feat/` | New feature | `feat/capture-screen` |
| `fix/` | Bug fix | `fix/dpi-scaling` |
| `docs/` | Documentation | `docs/api-reference` |
| `test/` | Test additions | `test/notepad-e2e` |
| `chore/` | Maintenance | `chore/bump-vcpkg` |
| `refactor/` | Code restructure | `refactor/backend-api` |

### Rules
- **Squash merge only** — keeps main history clean, one commit per feature
- **Delete branch after merge** — no stale branches
- **CI must pass** before merge — no exceptions
- **Commit early, commit often** on feature branches — messy is fine there
- **main should always be deployable**

## Feature Completeness Standard

Every feature change must ship with ALL of the following. No exceptions.

1. **Architecture** — Design doc or architecture notes updated (in `docs/`)
2. **Implementation** — Code with complete comments and docstrings
3. **Tests** — TEST_PLAN.md updated + all mapped test cases implemented and passing
4. **Documentation** — README, ROADMAP, CLI help text, and any relevant docs updated
5. **CI/CD** — Build pipeline covers the new code; CI must be green before merge

A Phase is NOT complete until all 5 are verified. PRs missing any of these will be rejected.

### Snapshot System Standard (Peekaboo Parity)

Every observation command (capture, see, list) should persist results to `~/.naturo/snapshots/{GUID}/`:
- Screenshot image (PNG)
- `snapshot.json` with full metadata: app info, window bounds, UI element tree (role/label/frame/isActionable/children), timestamp, version
- This is the data foundation for AI agent decision-making

## Key Files

- `core/include/naturo/exports.h` — Public C API (add new functions here)
- `naturo/bridge.py` — Python to DLL bridge (mirror new C functions)
- `naturo/cli/` — CLI commands package (user-facing)
- `.github/workflows/build.yml` — CI pipeline

## Build

### C++ Core
```bash
cmake -B build -S core -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
ctest --test-dir build --build-config Release
```

### Python
```bash
pip install -e ".[dev]"
pytest -v
```
