# Quickstart — Automate Notepad in 5 Minutes with Claude

Go from zero to your first agent-driven desktop automation in under five minutes.
By the end, Claude will open Notepad, type a line, and save the file — and you
will verify it worked. Every command below is copy-paste and runs on a clean
Windows 10/11 box.

> **Prerequisites:** Windows 10/11, Python 3.9+, and [Claude Code](https://docs.claude.com/en/docs/claude-code)
> (or Claude Desktop). That's it.

## 1. Install naturo (30 seconds)

```bash
pip install naturo
```

Verify the CLI is on your `PATH`:

```bash
naturo --version
```

Expected output:

```
naturo, version 0.3.1
```

Naturo's MCP server ships in the box. Pull in the MCP runtime dependency once:

```bash
naturo mcp install
```

## 2. Connect naturo to your agent (1 minute)

**Claude Code** — one line, then restart Claude Code:

```bash
claude mcp add naturo -- naturo mcp start
```

**Claude Desktop** — add naturo to `claude_desktop_config.json`, then restart
the app:

```json
{
  "mcpServers": {
    "naturo": {
      "command": "naturo",
      "args": ["mcp", "start"]
    }
  }
}
```

> **Config file location:**
> - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
> - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

Confirm naturo exposes its tools (this lists 60+ MCP tools without starting a
session):

```bash
naturo mcp tools
```

Expected output (truncated):

```
Naturo MCP Server — 64 tools available:

  launch_app            Launch an application by name.
  type_text             Type text using keyboard input.
  press_key             Press a key or key combination.
  wait_for_window       Wait for a window to appear.
  ...
```

## 3. Ask Claude to automate Notepad (2 minutes)

Open a chat with Claude (Code or Desktop) and paste this prompt:

> Open Notepad, type "Hello from naturo!", and save it as `naturo-hello.txt`.
> Tell me when the title bar shows the saved file name.

Claude drives naturo's MCP tools to do the work. Under the hood it runs the same
sequence you could script by hand — here is exactly what it does, so you know
what to expect:

```
# 1. Launch Notepad
launch_app(name="notepad")
→ {"success": true, "pid": 12044}

# 2. Wait for the window
wait_for_window(title="Notepad", timeout=5)
→ {"success": true, "title": "Untitled - Notepad"}

# 3. Type the line
type_text(text="Hello from naturo!")
→ {"success": true, "verified": true}

# 4. Save with Ctrl+S
press_key(key="ctrl+s")
→ {"success": true}

# 5. Fill the Save As dialog and confirm
wait_for_window(title="Save As", timeout=5)
dialog_type(text="naturo-hello.txt", accept=True)
→ {"success": true}
```

> **Tip:** every naturo input tool re-reads the UI after acting and returns
> `"verified": true` only when the change actually landed. If an action did not
> take effect, the tool reports `"success": false` instead of pretending — so
> Claude never tells you it worked when it did not.

## 4. Verify it worked (30 seconds)

Ask Claude to confirm, or check yourself. The save renames the window from
`Untitled - Notepad` to your file name — that title change is the proof:

```bash
naturo list windows
```

Expected output includes the renamed Notepad window:

```
HWND             PID      SIZE           TITLE
----------------------------------------------------------------------
5574222          50852    1440x753       naturo-hello.txt - Notepad
```

You can also inspect the live UI tree to confirm Notepad is the saved document:

```bash
naturo see --window "naturo-hello.txt" --depth 2
```

Expected output (the window title carries your file name):

```
[Window] "naturo-hello.txt - Notepad" (78,78 1440x753) e1 [uia]
  [Document] "Text editor" (84,153 1428x640) e3 [uia]
```

🎉 **Done.** Claude just saw, typed, and saved on the real Windows desktop — your
first agent-driven automation, end to end.

## Where to go next

- **All MCP tools** — [docs/MCP_SERVER.md](MCP_SERVER.md) (60+ tools, parameters,
  worked examples)
- **CLI reference** — [docs/CLI_REFERENCE.md](CLI_REFERENCE.md)
- **Why naturo recognizes apps rivals can't** — [docs/RECOGNITION.md](RECOGNITION.md)
- **Migrating from Selenium / pywinauto / DrissionPage** —
  [docs/MIGRATION_FROM_RPA_SCRIPTS.md](MIGRATION_FROM_RPA_SCRIPTS.md)

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `naturo: command not found` | Ensure your Python `Scripts/` dir is on `PATH`; reopen the terminal after `pip install`. |
| Claude does not see naturo's tools | Restart the client after editing its MCP config; run `naturo mcp tools` to confirm the server starts. |
| `naturo mcp start` exits immediately | Run `naturo mcp install` to pull the MCP runtime dependency. |
| An action reports `"success": false` | naturo refuses to fake success — read the `error.message`; the window may not be focused or the target may not exist yet. |
