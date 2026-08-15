# API Stability & Versioning

This document defines naturo's **public API surface** and the **stability
guarantee** attached to it. It is the contract you can build automation on.

> **Status: pre-1.0.** naturo is currently `0.3.2`. Read the
> [Versioning policy](#versioning-policy) below — while we are on `0.x`, a
> **minor** bump (`0.3.z` → `0.4.0`) is allowed to make breaking changes, and
> every such change is called out in [CHANGELOG.md](../CHANGELOG.md). Strict
> semver (breaking changes only on a major bump) begins at `1.0.0`.

## What we promise

- naturo has **three public surfaces** — the Python SDK, the `naturo` CLI, and
  the MCP server — and each has a defined public/internal boundary (below).
- Anything documented here as **public** changes only through the versioning and
  [deprecation process](#deprecation-process): breaking changes are announced in
  the CHANGELOG and, once we reach `1.0.0`, gated behind a major version.
- Anything documented as **internal** (underscore-prefixed modules, `naturo.cli`
  / `naturo.mcp` implementation code, unlisted helpers) may change in any
  release, including a patch. Do not import or depend on it.
- We do **not** promise stability of performance characteristics, log/prose
  wording, recognition-confidence values, or experimental features.

The version string lives in [`naturo/version.py`](../naturo/version.py) and
[`pyproject.toml`](../pyproject.toml) (kept in sync with the native core by CI —
see [docs/RELEASING.md](RELEASING.md#versioning)).

---

## Public vs internal

### 1. Python SDK

**Public** = the names re-exported at the top level of the package, i.e. the
`__all__` of [`naturo/__init__.py`](../naturo/__init__.py). These are what
`import naturo` is guaranteed to give you:

- **Ergonomic SDK (#924)** — `naturo.Desktop`, `naturo.Session`, `naturo.App`,
  `naturo.Element`, and the module-level verbs `see`, `find`, `click`, `type`,
  `press`, `get_value`, `set_value`, `capture`, `launch`, `quit`, `windows`
  (defined in [`naturo/sdk.py`](../naturo/sdk.py), whose own `__all__` is the
  authority for that module).
- **Errors** — `NaturoError` and its subclasses, `ErrorCode`, `ErrorCategory`.
- **Retry / wait / process / cache / diff** — `RetryPolicy`, `RetryResult`,
  `execute_with_retry`, `with_retry`; `WaitResult`, `wait_for_element`,
  `wait_until_gone`, `wait_for_window`; `ProcessInfo`, `launch_app`, `quit_app`,
  `relaunch_app`, `find_process`, `is_running`, `list_apps`; `ElementCache`;
  `ElementChange`, `TreeDiff`, `diff_trees`.
- `__version__`.

The submodules those names live in and that are documented as public API
(`naturo.errors`, `naturo.retry`, `naturo.wait`, `naturo.process`,
`naturo.cache`, `naturo.diff`, `naturo.sdk`) are also public. Note `naturo.wait`
stays a submodule and is deliberately **not** shadowed by a top-level `wait`
name; use `naturo.Desktop().wait(...)` or `naturo.sdk.wait`.

**Internal** (may change in any release — do not import):

- Any underscore-prefixed module or package, e.g.
  [`naturo/backends/windows/_element/`](../naturo/backends/windows/),
  `naturo/backends/windows/_input`, `naturo._worktree_guard`,
  `naturo.mcp._resolve`, `naturo.cli._jsonio`.
- The entire `naturo.cli.*` and `naturo.mcp.*` implementation trees — those exist
  to serve the CLI and MCP surfaces below, not to be imported directly. (The
  *behaviour* of the CLI and MCP surfaces is public; their Python modules are
  not.)
- `naturo.backends.*` — the SDK is a thin wrapper over the backend, but the
  backend classes/signatures are an implementation detail. Drive them through
  the SDK verbs, which delegate to the same code the CLI and MCP use.

### 2. CLI

The `naturo` command is a public surface. What is stable:

- **Subcommand and flag names.** The top-level command tree —
  `capture`, `list`, `see`, `find`, `get`, `set`, `menu-inspect`, `highlight`,
  `click`, `type`, `press`, `hotkey`, `scroll`, `drag`, `move`, `app`,
  `clipboard`, `dialog`, `taskbar`, `tray`, `desktop`, `window`, `snapshot`,
  `wait`, `diff`, `mcp`, `excel`, `browser`, `doctor`, `selector`, `visual`,
  `record`, `config` — and their documented flags. See
  [docs/CLI_REFERENCE.md](CLI_REFERENCE.md).
- **The `-j`/`--json` envelope.** Every JSON-emitting subcommand returns a
  top-level `{"success": true|false, ...}` object. On failure the envelope
  carries `error: {code, category, suggested_action, recoverable}` (see
  [docs/ERROR_CODES.md](ERROR_CODES.md)). This shape is enforced across the whole
  Click tree by `tests/test_json_envelope_sweep_1142.py` (#1142), so a new
  subcommand cannot ship without it.
- **Exit codes (#897)** — a three-value contract a scripter can branch on:
  - `0` — success.
  - `1` — runtime failure (the command ran but the operation failed, or a
    correctly-passed value was rejected during execution).
  - `2` — usage error (the command was invoked wrong: unknown command, missing
    argument, bad flag — matching Click's own parser and POSIX convention;
    `USAGE_ERROR_EXIT` in [`naturo/cli/error_helpers.py`](../naturo/cli/error_helpers.py)).

**Not stable:** human-readable (non-`-j`) text output, prose wording of
messages, hidden/alias commands (e.g. `info` as an alias for `doctor`), and any
flag or command marked experimental. Machine consumers should always pass `-j`
and branch on `success` + `error.code` + the exit code, never on message text.

### 3. MCP tools

naturo's MCP server (`python -m naturo mcp`, see
[docs/MCP_SERVER.md](MCP_SERVER.md) and
[docs/AGENT_INTEGRATION.md](AGENT_INTEGRATION.md)) exposes recognition and action
as tools. What is stable:

- **Tool names** and their **parameter and response shapes**. Tools are
  registered by the `register_*_tools` groups under
  [`naturo/mcp/`](../naturo/mcp/) (app, capture, clipboard, dialog, excel, input,
  inspect, snapshot, system, wait, window, word).
- **The error contract.** Every tool result carries a payload with a boolean
  `success`; the transport-level `isError` tracks it (`isError == not
  payload.success`, #882), and failures include a code + category + recovery
  hint.

These are guarded by **self-maintaining contract tests** so the shape cannot
drift silently: `tests/test_mcp_window_selector_contract_957.py` (#957) pins
window-selector/param handling, `tests/test_json_envelope_sweep_1142.py` (#1142)
covers the shared JSON envelope, and `tests/test_mcp_iserror_success_882.py`
(#882) pins the `isError`/`success` relationship. Additional per-tool contract
tests live alongside them (`tests/test_mcp_*.py`).

**Not stable:** internal helper functions (`_get_backend`, `_safe_tool`,
`naturo.mcp._resolve`, etc.) and any tool explicitly documented as experimental.

---

## Versioning policy

naturo follows [Semantic Versioning](https://semver.org/) `X.Y.Z`, with the
standard **pre-1.0 relaxation**:

| Phase | Bump | Rule |
| --- | --- | --- |
| **Now (`0.y.z`)** | **patch** (`0.3.2` → `0.3.3`) | Bug fixes and backward-compatible improvements only. **No breaking changes to any public surface.** |
| | **minor** (`0.3.z` → `0.4.0`) | New features **and** breaking changes are permitted. Every breaking change is documented in the CHANGELOG. |
| **From `1.0.0`** | **major** (`X.0.0`) | Breaking changes to the public API allowed only here. |
| | **minor** (`1.Y.0`) | New features, backward compatible. |
| | **patch** (`1.0.Z`) | Bug fixes only. |

This mirrors what [docs/RELEASING.md](RELEASING.md#versioning) already states:
"naturo is pre-1.0, so breaking changes are called out in the CHANGELOG rather
than gated behind a major bump." **1.0.0 is the freeze point** — reaching it is
the commitment that the public surfaces above are stable and change only under
strict semver.

---

## Deprecation process

Even while pre-1.0 permits breaking a minor, we minimize surprise:

1. **Announce in the CHANGELOG.** [CHANGELOG.md](../CHANGELOG.md) follows
   [Keep a Changelog](https://keepachangelog.com/); every behaviour-changing PR
   adds an entry under `[Unreleased]` in the same PR, and breaking changes are
   called out explicitly (the CHANGELOG already flags entries as **BREAKING**).
2. **Warn before removal.** When a public name/flag/tool is being removed, ship a
   `DeprecationWarning` (SDK) or a documented deprecation note (CLI/MCP) that
   keeps the old behaviour working for **at least one minor release** before the
   removal lands. The removal itself is a CHANGELOG entry with a migration note.
   *(Issue [#92](https://github.com/AcePeak/naturo/issues/92) proposes extending
   this to two minors at 1.0; the floor today is one.)*
3. **Migration guidance.** Breaking changes include a migration note in the
   CHANGELOG entry (e.g. the `see -j` reshape under `[Unreleased]` documents the
   exact `.role` → `.tree.role` move for scripts).

### Current guardrails vs. the 1.0 goal

Honest status: the shape guardrails that exist today are the **contract tests**
above (MCP #957/#1142/#882, the CLI envelope sweep #1142) plus the SDK's explicit
`__all__`. A full automated **public-API-diff CI gate** that fails a build on any
accidental breaking change (the remaining acceptance item on issue #92) is not
yet wired up; it is the last piece before the 1.0 freeze can be enforced
mechanically rather than by review + the targeted contract tests.

---

## See also

- [CHANGELOG.md](../CHANGELOG.md) — the source of truth for what changed, incl.
  breaking changes and migration notes.
- [docs/RELEASING.md](RELEASING.md) — cadence, versioning mechanics, and the
  release checklist.
- [docs/CLI_REFERENCE.md](CLI_REFERENCE.md) — full CLI surface.
- [docs/ERROR_CODES.md](ERROR_CODES.md) — the error `code`/`category` vocabulary.
- [docs/MCP_SERVER.md](MCP_SERVER.md) / [docs/AGENT_INTEGRATION.md](AGENT_INTEGRATION.md) — the MCP surface.
