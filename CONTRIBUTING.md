# Contributing to Naturo

## For Testers (External Agents)

### Getting Started
1. Install: `pip install naturo`
2. Read the testing guide: `agents/external-tester/SOUL.md`
3. Run tests on a Windows machine
4. Report issues via GitHub Issues

### Reporting Issues
- Use GitHub Issues: https://github.com/AcePeak/naturo/issues
- One issue per problem
- Use the bug report template
- Include: reproduction steps, actual vs expected result, environment info
- Prefix your comments with your role: `**[External-Tester]**`

### Agent API Access
Agents can use `gh` CLI to interact with issues:
```bash
# List open bugs
gh issue list --repo AcePeak/naturo --label bug

# Create a new issue
gh issue create --repo AcePeak/naturo \
  --title "[BUG] Short description" \
  --label "bug,P1,from:external" \
  --body "### Steps\n1. ...\n\n### Actual\n...\n\n### Expected\n..."

# Comment on an issue
gh issue comment 123 --repo AcePeak/naturo \
  --body "**[External-Tester]** Confirmed on Win11 3840x2160 150% DPI"

# Close after verified
gh issue close 123 --repo AcePeak/naturo
```

### Fine-grained Token (for external agents without `gh` login)
Request a fine-grained PAT from the maintainer with Issues read/write permission only.

## For Developers

### Bug Fix Workflow
1. Pick an issue from GitHub Issues (P0 first)
2. Create a branch off `develop`: `fix/issue-<number>-short-description` (e.g. `fix/issue-12-dpi-awareness`)
3. One bug = one commit, reference the issue: `fix: [BUG-073] DPI awareness (fixes #12)`
4. Push branch and open a PR against `develop` — CI runs automatically
5. CI green + review passed → squash merge to `develop`
6. Comment on the issue with fix details: `**[Dev]** Fixed in PR #XX`

> **All development happens on `develop`.** Feature branches → PR → `develop`.
> Only release merges go `develop` → `main`, and only version tags land on `main`
> (which is what publishes to PyPI). **Never push directly to `main`.**

### Code Standards
- All tests must pass on Ubuntu + macOS + Windows
- Python version and DLL version must match
- README.md must be updated after feature changes

### Language Policy
- **All GitHub content must be in English**: issues, PRs, commit messages, comments, code comments, documentation
- This is a public open-source project — English-only ensures global accessibility
- Internal agent/team discussions may use Chinese, but nothing on GitHub
