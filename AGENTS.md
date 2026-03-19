# AGENTS.md — AI Agent Working Guide

## Project: Naturo

Windows desktop automation engine. C++ core + Python wrapper.

## Language

- **All code, comments, docstrings, commit messages, docs, and issue titles must be in English.**
- No Chinese or other non-English text in the codebase, including TODOs and inline comments.
- Variable names, function names, class names — all English.
- This is non-negotiable for open-source readiness.

## Code Style

### General
- **Comments must be complete and meaningful.** Every public function, class, and module needs a docstring or header comment explaining what it does, its parameters, and return values.
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

## Review Roles

Before merging, consider these perspectives:

- **QA:** Test coverage? Edge cases? Error paths handled?
- **PD:** Good UX? CLI intuitive? Docs clear?
- **Security:** No credential leaks? Safe input? No privilege escalation?

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

### Workflow

1. Create a feature branch from main:
   ```bash
   git checkout -b feat/capture-screen
   ```
2. Develop with TDD (write tests → implement → refactor)
3. Push the branch and create a PR:
   ```bash
   git push origin feat/capture-screen
   gh pr create --title "feat: add screen capture API" --body "..."
   ```
4. Wait for CI to pass (all 4 jobs must be green)
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

## Test Plan

All test cases are defined in `docs/TEST_PLAN.md`.
- New features must reference which test IDs they cover
- PRs must include the test ID coverage in the description
- No phase is complete until all mapped test cases pass
- Role-based acceptance tests (R-QA, R-PD, R-SEC, R-DEV) validate real-world scenarios from QA, Product, Security, and DevOps perspectives

## Key Files

- `core/include/naturo/exports.h` — Public C API (add new functions here)
- `naturo/bridge.py` — Python ↔ DLL bridge (mirror new C functions)
- `naturo/cli.py` — CLI commands (user-facing)
- `.github/workflows/build.yml` — CI pipeline
