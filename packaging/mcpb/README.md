# naturo Claude Desktop Extension (`.mcpb`)

This directory packages naturo as an **MCP Bundle** (`.mcpb`, formerly `.dxt`) —
a single file that [Claude Desktop](https://claude.ai/download) and other
MCPB-aware clients can install in one click to add naturo's desktop-automation
tools.

## Build

```bash
python scripts/build_mcpb.py            # -> dist/naturo.mcpb
python scripts/build_mcpb.py --check    # validate the manifest, write nothing
```

The build is pure-stdlib (no extra dependencies). It stamps
[`manifest.json`](manifest.json) with the current package version
(`naturo/version.py`) and the live MCP tool list parsed from `naturo/mcp/`, then
zips it into `dist/naturo.mcpb`.

## Install

1. `pip install naturo` (see the prerequisite below).
2. Open Claude Desktop → **Settings → Extensions** → **Install Extension** and
   choose `dist/naturo.mcpb`, or double-click the file.
3. naturo's tools (`see_ui_tree`, `click`, `type_text`, …) appear in Claude.

## Prerequisite: `pip install naturo`

This bundle is a thin wrapper: its `manifest.json` launches the installed
`naturo` console script via `naturo mcp start`. It does **not** vendor naturo
itself, because the engine depends on a Windows-only native core
(`naturo_core.dll`) that cannot be bundled cross-platform. The user must
`pip install naturo` first, exactly as for the manual
[README MCP install snippets](../../README.md).

A future, fully self-contained bundle that vendors the native core and Python
runtime (so no separate `pip install` is needed) is tracked as a follow-up.
