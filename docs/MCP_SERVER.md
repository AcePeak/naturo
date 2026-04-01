# MCP Server Reference

Naturo exposes all desktop automation capabilities as MCP (Model Context Protocol)
tools, enabling AI agents to control Windows applications through a structured API.

## Quick Start

```bash
# Install MCP dependencies
naturo mcp install

# Start server (stdio transport — for Claude Desktop, OpenClaw, etc.)
naturo mcp start

# Start server (SSE transport — for remote agents)
naturo mcp start --transport sse --port 3100

# Start server (HTTP transport — for web-based agents)
naturo mcp start --transport streamable-http --port 3100

# List all available tools
naturo mcp tools
```

## Claude Desktop Configuration

Add to `claude_desktop_config.json`:

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

For SSE transport (remote server):

```json
{
  "mcpServers": {
    "naturo": {
      "url": "http://localhost:3100/sse"
    }
  }
}
```

## Tool Reference

All tools return a dictionary with `"success": true/false`. On error, an `"error"` field
contains `{"code": "...", "message": "..."}`.

---

### Capture (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `capture_screen` | `output_path="capture.png"`, `screen_index=0` | Capture full screen screenshot |
| `capture_window` | `window_title=None`, `output_path="capture.png"` | Capture a specific window |
| `list_monitors` | — | List all connected displays |

**Example workflow:**
```
capture_screen(output_path="desktop.png")
→ {"success": true, "path": "desktop.png", "width": 1920, "height": 1080}
```

---

### Window Management (13 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_windows` | — | List all visible windows |
| `focus_window` | `title`, `app`, `hwnd` | Bring window to foreground |
| `window_close` | `app`, `title`, `hwnd`, `force=False` | Close a window |
| `window_minimize` | `app`, `title`, `hwnd` | Minimize a window |
| `window_maximize` | `app`, `title`, `hwnd` | Maximize a window |
| `window_restore` | `app`, `title`, `hwnd` | Restore from min/max |
| `window_move` | `x`, `y`, `app`, `title`, `hwnd` | Move window position |
| `window_resize` | `width`, `height`, `app`, `title`, `hwnd` | Resize window |
| `window_set_bounds` | `x`, `y`, `width`, `height`, `app`, `title`, `hwnd` | Set position + size |
| `app_hide` | `name` | Hide (minimize) all app windows |
| `app_unhide` | `name` | Restore all app windows |
| `app_switch` | `name` | Switch to app's most recent window |
| `app_inspect` | `name`, `pid`, `quick=False` | Detect app's UI framework |

**Targeting windows:** Provide at least one of `title`, `app`, or `hwnd`.
- `title` — window title (substring match)
- `app` — process name (e.g., "notepad", "chrome")
- `hwnd` — exact window handle (integer)

---

### UI Inspection (7 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `see_ui_tree` | `window_title`, `app`, `hwnd`, `pid`, `depth=7`, `accessibility_backend="uia"` | Inspect the accessibility tree |
| `find_element` | `selector`, `window_title` | Find element by selector |
| `get_element_value` | `ref`, `automation_id`, `role`, `name`, `window_title`, `hwnd` | Read element text/value |
| `set_element_value` | `value`, `ref`, `automation_id`, `role`, `name`, `window_title`, `hwnd` | Set element value via UIA |
| `toggle_element` | `ref`, `automation_id`, `role`, `name`, `window_title`, `hwnd` | Toggle checkbox/toggle button |
| `select_element` | `ref`, `automation_id`, `role`, `name`, `window_title`, `hwnd` | Select list item/radio/tab |
| `expand_collapse_element` | `expand=True`, `ref`, `automation_id`, `role`, `name`, `window_title`, `hwnd` | Expand or collapse combo box/tree |

**Element targeting:** Use `ref` (element ID from `see_ui_tree`, e.g., "e5") or identify by `automation_id`, `role`, and `name`.

**Accessibility backends:**
- `uia` — UI Automation (default, best for modern apps)
- `msaa` — MSAA (legacy apps)
- `ia2` — IAccessible2 (Firefox, LibreOffice)
- `jab` — Java Access Bridge
- `cdp` — Chrome DevTools Protocol (Chromium browsers)
- `hybrid` — Combines multiple backends
- `auto` — Automatic detection

---

### Input (7 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `click` | `x`, `y`, `element_id`, `button="left"`, `double=False`, `input_mode="normal"`, `method="auto"` | Click at coordinates or element |
| `type_text` | `text`, `wpm=120`, `input_mode="normal"`, `method="auto"` | Type text via keyboard |
| `press_key` | `key`, `count=1`, `input_mode="normal"`, `method="auto"` | Press key or key combo |
| `hotkey` | `keys` (list), `input_mode="normal"` | Press keyboard shortcut |
| `scroll` | `direction="down"`, `amount=3`, `x`, `y` | Scroll mouse wheel |
| `drag` | `from_x`, `from_y`, `to_x`, `to_y`, `duration_ms=500`, `steps=10` | Drag from point to point |
| `move_mouse` | `x`, `y` | Move cursor to position |

**Input modes:**
- `normal` — Standard Windows messages (default)
- `hardware` — Low-level hardware simulation
- `hook` — Hook-based injection

**Key names:** `enter`, `tab`, `escape`, `space`, `backspace`, `delete`, `up`, `down`, `left`, `right`, `home`, `end`, `pageup`, `pagedown`, `f1`–`f12`. Combos: `ctrl+s`, `alt+f4`, `ctrl+shift+n`.

---

### Application Control (4 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_apps` | — | List running applications |
| `launch_app` | `name` | Launch app by name |
| `quit_app` | `name`, `force=False` | Quit application |
| `menu_inspect` | `app` | Inspect app menu bar |

---

### Wait (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `wait_for_element` | `selector`, `timeout=10.0`, `interval=0.5`, `window_title` | Wait for element to appear |
| `wait_for_window` | `title`, `timeout=10.0`, `interval=0.5` | Wait for window to appear |
| `wait_until_gone` | `selector`, `timeout=10.0`, `interval=0.5`, `window_title` | Wait for element to disappear |

---

### Snapshot (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `create_snapshot` | `window_title`, `depth=7` | Save UI state (screenshot + element tree) |
| `get_snapshot` | `snapshot_id` | Retrieve a saved snapshot |
| `list_snapshots` | `limit=10` | List recent snapshots |

Snapshots combine a screenshot with the element tree, enabling before/after comparisons
and state verification.

---

### Clipboard (4 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `clipboard_get` | — | Read clipboard text |
| `clipboard_set` | `text` | Write text to clipboard |
| `clipboard_clear` | — | Clear clipboard |
| `clipboard_info` | — | Get clipboard format info |

---

### Dialog (5 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `dialog_detect` | `app`, `hwnd` | Detect active dialogs |
| `dialog_accept` | `app`, `hwnd` | Click OK/Yes/Save |
| `dialog_dismiss` | `app`, `hwnd` | Click Cancel/No/Close |
| `dialog_click_button` | `button`, `app`, `hwnd` | Click specific dialog button |
| `dialog_type` | `text`, `accept=False`, `app`, `hwnd` | Type into dialog input |

---

### System (9 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `taskbar_list` | — | List taskbar items |
| `taskbar_click` | `name` | Click taskbar item |
| `tray_list` | — | List system tray icons |
| `tray_click` | `name`, `button="left"`, `double_click=False` | Click tray icon |
| `virtual_desktop_list` | — | List virtual desktops |
| `virtual_desktop_switch` | `index` | Switch virtual desktop |
| `virtual_desktop_create` | `name` | Create virtual desktop |
| `virtual_desktop_close` | `index` | Close virtual desktop |
| `virtual_desktop_move_window` | `desktop_index`, `app`, `hwnd` | Move window to desktop |

---

### Excel (6 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `excel_open` | `path`, `visible=False`, `read_only=False` | Open workbook |
| `excel_read` | `path`, `cell`, `sheet` | Read cell/range |
| `excel_write` | `path`, `cell`, `value`, `sheet`, `create=False` | Write to cell |
| `excel_list_sheets` | `path` | List workbook sheets |
| `excel_run_macro` | `path`, `macro_name`, `args` | Run VBA macro |
| `excel_info` | `path`, `sheet` | Get used range info |

---

## Worked Example: Notepad Automation

A complete example using MCP tools to automate Notepad:

```
# 1. Launch Notepad
launch_app(name="notepad")

# 2. Wait for it to appear
wait_for_window(title="Notepad", timeout=5)

# 3. Inspect the UI
see_ui_tree(app="notepad", depth=3)
→ e1: [Window] "Untitled - Notepad"
    e2: [Edit] ""
    e3: [MenuBar] "Application"
    ...

# 4. Type into the editor
type_text(text="Hello from MCP!")

# 5. Save with Ctrl+S
press_key(key="ctrl+s")

# 6. Handle the Save As dialog
wait_for_window(title="Save As", timeout=5)
dialog_type(text="hello.txt", accept=True)

# 7. Verify the title changed
wait_for_window(title="hello.txt - Notepad", timeout=5)

# 8. Capture the result
capture_window(window_title="Notepad", output_path="result.png")

# 9. Quit
quit_app(name="notepad")
```

## Error Handling

All tools return structured errors:

```json
{
  "success": false,
  "error": {
    "code": "ELEMENT_NOT_FOUND",
    "message": "No element matching selector 'e99' in current snapshot"
  }
}
```

Common error codes:
- `ELEMENT_NOT_FOUND` — Element selector did not match
- `WINDOW_NOT_FOUND` — No window matching the criteria
- `TIMEOUT` — Wait operation exceeded timeout
- `BACKEND_ERROR` — Platform backend failed
- `INVALID_INPUT` — Invalid parameter value

## Transport Options

| Transport | Command | Use Case |
|-----------|---------|----------|
| stdio | `naturo mcp start` | Local AI agents (Claude Desktop, OpenClaw) |
| SSE | `naturo mcp start --transport sse --port 3100` | Remote agents, browser-based clients |
| HTTP | `naturo mcp start --transport streamable-http --port 3100` | REST-style integrations |
