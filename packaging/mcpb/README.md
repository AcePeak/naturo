# naturo Claude Desktop Extension (`.mcpb`)

This directory packages naturo as an **MCP Bundle** (`.mcpb`, formerly `.dxt`) —
a single file that [Claude Desktop](https://claude.ai/download) and other
MCPB-aware clients can install in one click to add naturo's desktop-automation
tools.

## Two modes

`scripts/build_mcpb.py` builds two flavours from the same tool metadata:

| Mode | Output | Command in manifest | Prerequisite |
| --- | --- | --- | --- |
| **Thin wrapper** (default) | `dist/naturo.mcpb` | `naturo mcp start` | `pip install naturo` first |
| **Self-contained** (`--self-contained`, #997) | `dist/naturo-selfcontained.mcpb` | `${__dirname}/server/runtime/python/python.exe -m naturo mcp start` | none — runtime + native core are vendored |

Both stamp [`manifest.json`](manifest.json) with the current package version
(`naturo/version.py`) and the live MCP tool list parsed from `naturo/mcp/`. Only
the thin manifest is committed; the self-contained variant is generated in memory
(its command points at the bundled interpreter and its `long_description` drops
the `pip install` note), so the canonical thin manifest is never overwritten.

## Build

```bash
# Thin wrapper (pure-stdlib, no downloads)
python scripts/build_mcpb.py            # -> dist/naturo.mcpb
python scripts/build_mcpb.py --check    # validate the manifest, write nothing

# Self-contained (downloads the embedded CPython runtime; ~tens of MB)
python scripts/build_mcpb.py --self-contained          # -> dist/naturo-selfcontained.mcpb
python scripts/build_mcpb.py --self-contained --check  # validate layout, no download/zip
```

The self-contained build stacks on the embedded runtime from
[`scripts/bundle_python.py`](../../scripts/bundle_python.py) (#41): it assembles a
CPython 3.12 runtime under `server/runtime/python/`, installs
`naturo[mcp,windows]` into it (the MCP server plus the Windows native UIA/COM
extras), and ensures the native core `naturo_core.dll` is present in
`.../site-packages/naturo/bin/` — kept from the wheel if the wheel already ships
it, otherwise vendored from the local build tree (override with `--dll-source`).
The staging tree is then zipped with `manifest.json` at the archive root.

On a proxied host, export `HTTP_PROXY`/`HTTPS_PROXY` so the runtime downloads
(python.org embeddable zip, `get-pip.py`, PyPI wheels) succeed.

Everything the self-contained build emits lands under `dist/` (gitignored): the
embedded runtime, `get-pip.py`, and the `.mcpb` are build artifacts and are never
committed.

## Install

1. Thin wrapper only: `pip install naturo` first (the self-contained bundle needs
   no prior install).
2. Open Claude Desktop → **Settings → Extensions** → **Install Extension** and
   choose the `.mcpb`, or double-click the file.
3. naturo's tools (`see_ui_tree`, `click`, `type_text`, …) appear in Claude.

## Prerequisite (thin wrapper only): `pip install naturo`

The thin bundle's `manifest.json` launches the installed `naturo` console script
via `naturo mcp start`. It does **not** vendor naturo, because the engine depends
on a Windows-only native core (`naturo_core.dll`). The user must `pip install
naturo` first, exactly as for the manual
[README MCP install snippets](../../README.md). The **self-contained** bundle
removes this step by vendoring both the Python runtime and the native core.

## CI (reference snippet, not a committed workflow)

A Windows job can build and upload the self-contained bundle on demand. Add this
to a workflow under `.github/workflows/` when wiring it up:

```yaml
build-selfcontained-mcpb:
  runs-on: windows-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    - name: Build self-contained .mcpb
      run: python scripts/build_mcpb.py --self-contained
    - uses: actions/upload-artifact@v4
      with:
        name: naturo-selfcontained-mcpb
        path: dist/naturo-selfcontained.mcpb
```
