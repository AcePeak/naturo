# Contributing to Naturo

Thank you for your interest in contributing to Naturo! This guide will help you get started.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md). We are committed to providing a welcoming and inclusive experience for everyone.

## Getting Started

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/<your-username>/naturo.git
   cd naturo
   ```

3. Add the upstream remote:

   ```bash
   git remote add upstream https://github.com/AcePeak/naturo.git
   ```

### Development Environment

**Prerequisites:**

- Python 3.9 or higher
- Windows 10 or higher (for running tests against the automation engine)
- Git

**Setup:**

```bash
# Create a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) conventions
- Use **type hints** for all function signatures
- Write **docstrings** for all public modules, classes, and functions (Google style)
- Keep functions focused and small
- Use meaningful variable and function names

## Development Workflow (TDD)

We follow Test-Driven Development:

1. **Write a failing test** — Define the expected behavior first
2. **Implement** — Write the minimum code to make the test pass
3. **Refactor** — Clean up while keeping tests green

Run the test suite:

```bash
pytest
```

## Pull Request Process

1. **Create a feature branch** from `main`:

   ```bash
   git checkout main
   git pull upstream main
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** following the TDD workflow above

3. **Commit** with clear, descriptive messages:

   ```
   feat: add keyboard shortcut support for media keys
   fix: correct element matching for ComboBox controls
   docs: update CLI usage examples
   test: add coverage for screen capture edge cases
   ```

4. **Push** your branch and open a Pull Request against `main`

5. **Ensure CI is green** — all tests and checks must pass

6. **Address review feedback** — maintainers may request changes

7. PRs are **squash merged** into `main`

## Labels

### Issue Labels

| Label | Description |
|-------|-------------|
| `bug` | Something isn't working |
| `feature` | New feature request |
| `docs` | Documentation improvements |
| `good first issue` | Good for newcomers |
| `help wanted` | Extra attention is needed |
| `question` | Further information is requested |
| `wontfix` | This will not be worked on |

### PR Labels

| Label | Description |
|-------|-------------|
| `breaking` | Introduces breaking changes |
| `enhancement` | Improves existing functionality |
| `bugfix` | Fixes a bug |
| `docs` | Documentation only |
| `internal` | Internal refactoring, no user-facing changes |

## Reporting Issues

- Use the provided [issue templates](https://github.com/AcePeak/naturo/issues/new/choose)
- Search existing issues before opening a new one
- Include reproduction steps, expected vs actual behavior, and environment details

## Questions?

Open a [discussion](https://github.com/AcePeak/naturo/discussions) or file an issue tagged `question`.

Thank you for helping make Naturo better!
