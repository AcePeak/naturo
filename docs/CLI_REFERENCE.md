# CLI Reference

Complete reference for all `naturo` commands. Auto-generated from Click command definitions.

*Generated: 2026-03-29*

## Global Options

These options can be passed to any command:

```bash
naturo [--json] [--verbose] [--log-level LEVEL] COMMAND [ARGS]
```

| Flag | Description |
|------|-------------|
| `--version` | Show version and exit |
| `-j`, `--json` | JSON output for all commands |
| `-v`, `--verbose` | Verbose logging |
| `--log-level` | Log level: trace, debug, info, warning, error |
| `--help` | Show help and exit |

## Commands

### See (Inspect UI)

- [`naturo capture`](#naturo-capture) — Capture a live screenshot, optionally cropped to an element or region.
- [`naturo find`](#naturo-find) — Search for UI elements matching a query.
- [`naturo get`](#naturo-get) — Read element text/value.
- [`naturo highlight`](#naturo-highlight) — Highlight UI elements on screen with colored borders and labels.
- [`naturo list`](#naturo-list) — List apps, windows, and screens.
  - [`naturo list apps`](#naturo-list-apps) — List running applications (delegates to 'app list').
  - [`naturo list screens`](#naturo-list-screens) — List connected screens/monitors.
  - [`naturo list windows`](#naturo-list-windows) — List open windows.
- [`naturo menu-inspect`](#naturo-menu-inspect) — List the menu bar structure of the foreground application.
- [`naturo see`](#naturo-see) — Capture screenshot and analyze UI elements.

### Act (Interact)

- [`naturo click`](#naturo-click) — Click on a UI element, text, or coordinates.
- [`naturo drag`](#naturo-drag) — Drag from one element/position to another.
- [`naturo move`](#naturo-move) — Move the mouse cursor to a target element or coordinates.
- [`naturo press`](#naturo-press) — Press keys — single keys, combos, or sequential key sequences.
- [`naturo scroll`](#naturo-scroll) — Scroll in a direction.
- [`naturo set`](#naturo-set) — Set element value/state.
- [`naturo type`](#naturo-type) — Type text with configurable speed and profile.

### App & Window Management

- [`naturo app`](#naturo-app) — Manage applications and windows: launch, quit, focus, close, minimize, maximize,
  - [`naturo app close`](#naturo-app-close) — Close an application window (graceful or forced).
  - [`naturo app find`](#naturo-app-find) — Find a running application by name or PID.
  - [`naturo app focus`](#naturo-app-focus) — Focus an application window (bring to foreground).
  - [`naturo app inspect`](#naturo-app-inspect) — Probe an application and report available interaction methods.
  - [`naturo app launch`](#naturo-app-launch) — Launch an application by name or path.
  - [`naturo app list`](#naturo-app-list) — List running applications with visible windows.
  - [`naturo app maximize`](#naturo-app-maximize) — Maximize an application window.
  - [`naturo app minimize`](#naturo-app-minimize) — Minimize an application window.
  - [`naturo app move`](#naturo-app-move) — Move and/or resize an application window.
  - [`naturo app quit`](#naturo-app-quit) — Quit an application gracefully (or force kill).
  - [`naturo app relaunch`](#naturo-app-relaunch) — Quit and relaunch an application.
  - [`naturo app restore`](#naturo-app-restore) — Restore a minimized or maximized window to normal state.
  - [`naturo app windows`](#naturo-app-windows) — List open windows (optionally filtered by app name or PID).
- [`naturo dialog`](#naturo-dialog) — Detect and interact with system dialogs.
  - [`naturo dialog accept`](#naturo-dialog-accept) — Accept (confirm) the active dialog.
  - [`naturo dialog click-button`](#naturo-dialog-click-button) — Click a specific button in the active dialog.
  - [`naturo dialog detect`](#naturo-dialog-detect) — Detect active dialog windows.
  - [`naturo dialog dismiss`](#naturo-dialog-dismiss) — Dismiss (cancel) the active dialog.
  - [`naturo dialog type`](#naturo-dialog-type) — Type text into a dialog's input field.
- [`naturo diff`](#naturo-diff) — Compare two UI element trees to detect changes.
- [`naturo wait`](#naturo-wait) — Wait for a duration, or for a UI element/window to appear or disappear.

### System

- [`naturo desktop`](#naturo-desktop) — Virtual desktop management (Windows 10/11).
  - [`naturo desktop close`](#naturo-desktop-close) — Close a virtual desktop.
  - [`naturo desktop create`](#naturo-desktop-create) — Create a new virtual desktop.
  - [`naturo desktop list`](#naturo-desktop-list) — List all virtual desktops.
  - [`naturo desktop move-window`](#naturo-desktop-move-window) — Move a window to a different virtual desktop.
  - [`naturo desktop switch`](#naturo-desktop-switch) — Switch to a virtual desktop by index.
- [`naturo taskbar`](#naturo-taskbar) — Interact with the Windows taskbar.
  - [`naturo taskbar click`](#naturo-taskbar-click) — Click a taskbar item to activate its window.
  - [`naturo taskbar list`](#naturo-taskbar-list) — List items on the taskbar.
- [`naturo tray`](#naturo-tray) — Interact with the system tray (notification area).
  - [`naturo tray click`](#naturo-tray-click) — Click a system tray icon.
  - [`naturo tray list`](#naturo-tray-list) — List system tray icons.

### Tools

- [`naturo clipboard`](#naturo-clipboard) — Read, write, and manage clipboard contents.
  - [`naturo clipboard clear`](#naturo-clipboard-clear) — Clear the clipboard contents.
  - [`naturo clipboard get`](#naturo-clipboard-get) — Read current clipboard content.
  - [`naturo clipboard info`](#naturo-clipboard-info) — Show information about current clipboard contents.
  - [`naturo clipboard set`](#naturo-clipboard-set) — Write text to the clipboard.
- [`naturo config`](#naturo-config) — Manage Naturo configuration and provider credentials.
  - [`naturo config clear`](#naturo-config-clear) — Remove stored credentials for a provider (or all providers).
  - [`naturo config setup`](#naturo-config-setup) — Interactive setup for AI provider credentials.
    - [`naturo config setup anthropic`](#naturo-config-setup-anthropic) — Configure Anthropic (Claude) credentials.
  - [`naturo config show`](#naturo-config-show) — Show current credential configuration (tokens are redacted).
- [`naturo mcp`](#naturo-mcp) — MCP (Model Context Protocol) server for AI agent integration.
  - [`naturo mcp install`](#naturo-mcp-install) — Install MCP server dependencies.
  - [`naturo mcp start`](#naturo-mcp-start) — Start the MCP server.
  - [`naturo mcp tools`](#naturo-mcp-tools) — List available MCP tools.

---

## See (Inspect UI)

## `naturo capture`

Capture a live screenshot, optionally cropped to an element or region.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Target application (name or partial match) |
| `--pid` | integer | Process ID |
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--screen`, `-s` | integer | Screen/monitor index (default: `0`) |
| `--path`, `-p`, `-o` | text | Output file path (default: capture.<format>) |
| `--format` | {png, jpg, bmp} | Image format (default: png) |
| `--element`, `-e`, `--ref` | text | Crop to element ref (eN) from most recent snapshot, e.g. --element e5 or --ref e5 |
| `--region` | text | Crop to region: x,y,width,height (e.g. --region 100,50,400,300) |
| `--padding` | integer | Extra padding (px) added around --element or --region crop (default: `0`) |
| `--snapshot`, `--no-snapshot` | boolean | Store result in snapshot (default: on) |
| `--session` | text | Snapshot session for isolation (default: NATURO_SESSION env or 'default') |
| `--json`, `-j` | boolean | JSON output |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |

**Examples:**

```bash
naturo capture                                  # full screen
naturo capture --element e5                     # crop to element e5
naturo capture --ref e5 --padding 20            # with 20px padding
naturo capture --region 100,50,400,300          # crop to region
naturo capture --app feishu --element e12       # element in specific app
naturo capture --pid 51764                      # capture by process ID
naturo capture --app-id a1 --element e12        # element by app ID
naturo capture -o output.png                    # save to output.png
```

## `naturo find`

Search for UI elements matching a query.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `QUERY` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--query`, `-q` | text | Search query (alternative to positional arg; survives shell glob expansion) |
| `--all` | boolean | Find all elements (equivalent to query "*"). Safe from shell glob expansion. |
| `--role` | text | Filter by element role (e.g., Button, Edit) |
| `--actionable` | boolean | Only show actionable elements |
| `--depth`, `-d` | integer | Maximum tree depth (default 20; use lower values for performance) |
| `--limit` | integer | Maximum number of results (default: `50`) |
| `--ai` | boolean | Use AI vision to find element by natural language |
| `--screenshot` | path | Use existing screenshot (for --ai mode) |
| `--app` | text | Target app window |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--json`, `-j` | boolean | JSON output |
| `--backend`, `--method`, `-b`, `-m` | {uia, msaa, ia2, jab, cdp, win32, win32hybrid, auto, hybrid} | Accessibility backend / interaction method: auto (default: tries all), uia, msaa (legacy apps), ia2 (Firefox/Thunderbird), jab (Java/Swing), cdp (Chrome/Electron web content), win32 (VB6/ActiveX), hybrid (per-node backend selection) |
| `--provider` | {auto, anthropic, openai, ollama} | AI provider for --ai mode (auto, anthropic, openai, ollama) (default: `auto`) |
| `--model` | text | AI model name override (e.g. claude-sonnet-4-20250514, gpt-4o) |
| `--api-key` | text | AI provider API key (overrides env var) |

**Examples:**

```bash
naturo find "Save"                      # fuzzy name search
naturo find "Button:Save"               # role + name
naturo find "role:Edit"                  # by role only
naturo find --all --actionable           # all actionable elements
naturo find --all --role Button          # all buttons
naturo find "the save button" --ai       # AI vision search
naturo find "Save" --app "Notepad"              # search in specific app
naturo find "search field" --ai --app "Chrome"  # AI + specific app
naturo find "OK" --backend msaa          # MSAA for legacy apps
```

## `naturo get`

Read element text/value.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `TARGET` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--ref`, `-r` | text | Element ref from snapshot (e.g. e47) |
| `--automation-id`, `--aid` | text | UIA AutomationId of the target element |
| `--role` | text | Element role filter (e.g. Edit, Button) |
| `--name` | text | Element name filter |
| `--all`, `-a` | boolean | Return all matching elements (requires --role or --name) |
| `--property`, `-p` | text | Return only a specific property (value, name, role, pattern) |
| `--app` | text | Target application (name or partial match) |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo get e47                      # Read value by ref
naturo get e47 --json               # JSON output
naturo get --aid txtSearch          # By AutomationId
naturo get --role Edit --name Search # By role + name
naturo get e47 -p value             # Just the value text
naturo get --role Button --app explorer --all -j  # All buttons
naturo get --role Edit --all        # All edit fields
```

## `naturo highlight`

Highlight UI elements on screen with colored borders and labels.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `POSITIONAL_REFS` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--on` | text | Target element ref (eN) to highlight |
| `--ref`, `-r` | text | Specific refs to highlight (e.g. -r e5 -r e10). Omit for all. |
| `--app`, `-a` | text | Application name (partial match) |
| `--hwnd` | integer | Direct window handle |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--depth`, `-d` | integer | Tree depth for element discovery (default: `30`) |
| `--duration` | float | Highlight duration in seconds (default: `5.0`) |
| `--json`, `-j` | boolean | JSON output |
| `--backend`, `-b` | {uia, win32, win32hybrid} | Highlight backend: uia (default), win32 (HWND-only), win32hybrid (HWND + UIA drill-down) |
| `--all` | boolean | Show all elements, not just actionable ones |
| `--annotate`, `-A` | path | Save annotated screenshot to file instead of live overlay (requires Pillow) |
| `--filter` | text | Filter elements by role (e.g. --filter Button) |

**Examples:**

```bash
naturo highlight --app notepad             # Actionable only
naturo highlight --app notepad --all       # All elements
naturo highlight e11 --app notepad         # Specific ref
naturo highlight --app notepad --filter Button
naturo highlight --app notepad -A out.png  # Annotated screenshot
naturo highlight --hwnd 10697004 -r e69 -r e77
naturo highlight --app notepad --duration 10
naturo highlight --app legacy --backend win32
```

## `naturo list`

List apps, windows, and screens.

### `naturo list apps`

List running applications (delegates to 'app list').

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--all` | boolean | Show all processes (not just apps with windows) |
| `--json`, `-j` | boolean | JSON output |

### `naturo list screens`

List connected screens/monitors.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--json`, `-j` | boolean | JSON output |

### `naturo list windows`

List open windows.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Target application (name or partial match) |
| `--pid` | integer | Process ID |
| `--json`, `-j` | boolean | JSON output |

## `naturo menu-inspect`

List the menu bar structure of the foreground application.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Application name |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--flat` | boolean | Flatten menu tree into paths |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo menu-inspect                     # Foreground app
naturo menu-inspect --app notepad       # Specific app
naturo menu-inspect --flat              # Flat path list
naturo menu-inspect --app notepad --json # JSON output
```

## `naturo see`

Capture screenshot and analyze UI elements.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Target application (name or partial match) |
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--pid` | integer | Process ID |
| `--mode` | {full, interactive, fast} | Analysis mode: full (all elements), interactive (clickable only), fast (quick scan) (default: `full`) |
| `--depth`, `-d` | integer | Maximum tree depth (1-50) (default: `7`) |
| `--path`, `-p` | text | Save screenshot to path |
| `--annotate` | boolean | Annotate screenshot with element labels |
| `--snapshot`, `--no-snapshot` | boolean | Store result in snapshot (default: on) |
| `--session` | text | Snapshot session name for isolation (default: NATURO_SESSION env or 'default') |
| `--cascade` | boolean | Progressive recognition: try UIA, then CDP (Electron/CEF), then AI vision |
| `--fill-gaps` | boolean | Use AI vision to fill uncovered UI regions (requires AI provider) |
| `--stats` | boolean | Show per-provider recognition statistics after output |
| `--coverage` | float | Coverage target (0.0–1.0) before trying next provider (default: 0 = UIA only) |
| `--visible-only` | boolean | Hide offscreen/zero-bounds elements |
| `--selectors` | boolean | Show unified selectors alongside eN refs (always included in JSON mode) |
| `--json`, `-j` | boolean | JSON output |
| `--backend`, `--method`, `-b`, `-m` | {uia, msaa, ia2, jab, cdp, win32, win32hybrid, auto, hybrid} | Accessibility backend / interaction method: auto (default: tries all), uia, msaa (legacy apps), ia2 (Firefox/Thunderbird), jab (Java/Swing), cdp (Chrome/Electron web content via DevTools), win32 (VB6/ActiveX), hybrid (per-node backend selection) |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |

**Examples:**

```bash
naturo see --app feishu --cascade      # UIA + CDP for Electron content
naturo see --app feishu --cascade --fill-gaps  # Also use AI vision
naturo see --app feishu --cascade --stats      # Show provider breakdown
naturo see --app feishu --backend auto         # Try all A11y backends
naturo see --app feishu --backend hybrid       # Per-node backend selection
```

---

## Act (Interact)

## `naturo click`

Click on a UI element, text, or coordinates.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `QUERY` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--on` | text | Target element (eN ref or text label) |
| `--id` | text | Automation element ID |
| `--coords` | integer | X Y coordinates |
| `--double` | boolean | Double-click |
| `--right` | boolean | Right-click |
| `--app` | text | Target application (name or partial match) |
| `--pid` | integer | Process ID |
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--input-mode` | {normal, hardware, hook} | Input method: normal (SendInput), hardware (Phys32 driver), hook (MinHook injection) (default: `normal`) |
| `--method`, `-m` | {auto, cdp, uia, msaa, ia2, jab, vision} | Interaction method override: auto (default), cdp, uia, msaa, ia2, jab, vision. Bypasses auto-detection when set explicitly. |
| `--selector` | text | Unified selector to locate target element. URI: app://notepad.exe/Button[@name="Save"]. Short: //Edit[@name="Search"] (any app, descendant search). App names are flexible: chrome, chrome.exe, Chrome all match. |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--verify`, `--no-verify` | boolean | Verify action had effect (default: on). Use --no-verify to skip. |
| `--see` | boolean | Capture and display updated UI tree after action |
| `--settle` | integer | Wait time in ms before re-snapshot (used with --see) (default: `300`) |
| `--paste` | boolean | Paste clipboard after click (Ctrl+V) |
| `--copy` | boolean | Select all + copy after click (Ctrl+A, Ctrl+C) |
| `--cut` | boolean | Select all + cut after click (Ctrl+A, Ctrl+X) |
| `--restore`, `--no-restore` | boolean | Restore clipboard after --paste (default: True) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo click --coords 500 300
naturo click --coords 500 300 --right
naturo click --id "button_ok"
naturo click e42 --paste
naturo click e42 --copy
```

## `naturo drag`

Drag from one element/position to another.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--from` | text | Source element text |
| `--from-coords` | integer | Source X Y coordinates |
| `--from-selector` | text | Unified selector for source element. URI format: app://notepad.exe/Button[@name="Save"]. XML format: <selector app="notepad.exe"><node role="Button" name="Save"/></selector>. |
| `--to` | text | Destination element text |
| `--to-coords` | integer | Destination X Y coordinates |
| `--to-selector` | text | Unified selector for destination element. URI format: app://notepad.exe/ListItem[@name="Folder"]. XML format: <selector app="notepad.exe"><node role="ListItem" name="Folder"/></selector>. |
| `--duration` | float | Drag duration (seconds) (default: `0.5`) |
| `--steps` | integer | Interpolation steps (default: `10`) |
| `--modifiers` | text | Modifier keys to hold (ctrl, shift, alt) |
| `--profile` | {linear, ease-in-out} | Motion profile (default: `linear`) |
| `--app` | text | Target application (name or partial match) |
| `--pid` | integer | Process ID |
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--method`, `-m` | {auto, cdp, uia, msaa, ia2, jab, vision} | Interaction method override: auto (default), cdp, uia, msaa, ia2, jab, vision. Bypasses auto-detection when set explicitly. |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo drag --from e5 --to e12
naturo drag --from-coords 100 100 --to-coords 500 300
naturo drag --from e5 --to-coords 500 300
naturo drag --from-selector 'app://*/ListItem[@name="File1"]' --to-selector 'app://*/TreeItem[@name="Folder"]'
```

## `naturo move`

Move the mouse cursor to a target element or coordinates.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--to` | text | Target element text |
| `--coords` | integer | Target X Y coordinates |
| `--id` | text | Target element automation ID |
| `--app` | text | Target application (name or partial match) |
| `--pid` | integer | Process ID |
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--selector` | text | Unified selector to locate target element. URI: app://notepad.exe/Button[@name="Save"]. Short: //Edit[@name="Search"] (any app, descendant search). App names are flexible: chrome, chrome.exe, Chrome all match. |
| `--method`, `-m` | {auto, cdp, uia, msaa, ia2, jab, vision} | Interaction method override: auto (default), cdp, uia, msaa, ia2, jab, vision. Bypasses auto-detection when set explicitly. |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo move --coords 500 300
naturo move --selector 'app://*/Button[@name="Save"]'
```

## `naturo press`

Press keys — single keys, combos, or sequential key sequences.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `KEYS` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--count`, `-n` | integer | Number of times to press (default: `1`) |
| `--delay` | float | Delay between presses (ms) (default: `50.0`) |
| `--hold-duration` | float | Hold duration for combos (ms) |
| `--on` | text | Target element (eN ref or text label) — click to focus before pressing |
| `--app` | text | Target application (name or partial match) |
| `--pid` | integer | Process ID |
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--input-mode` | {normal, hardware, hook} | Input method: normal (SendInput), hardware (Phys32 driver), hook (MinHook injection) (default: `normal`) |
| `--method`, `-m` | {auto, cdp, uia, msaa, ia2, jab, vision} | Interaction method override: auto (default), cdp, uia, msaa, ia2, jab, vision. Bypasses auto-detection when set explicitly. |
| `--selector` | text | Unified selector to locate target element. URI: app://notepad.exe/Button[@name="Save"]. Short: //Edit[@name="Search"] (any app, descendant search). App names are flexible: chrome, chrome.exe, Chrome all match. |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--verify`, `--no-verify` | boolean | Verify action had effect (default: on). Use --no-verify to skip. |
| `--see` | boolean | Capture and display updated UI tree after action |
| `--settle` | integer | Wait time in ms before re-snapshot (used with --see) (default: `300`) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo press enter                  # single key
naturo press tab --count 3          # repeat
naturo press ctrl+c                 # key combination (was: hotkey)
naturo press ctrl+a ctrl+c          # sequential combos
naturo press alt+f4
naturo press enter --selector 'app://*/Button[@name="OK"]'
```

## `naturo scroll`

Scroll in a direction.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `DIRECTION_ARG` | choice | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--direction`, `-d` | {up, down, left, right} | Scroll direction |
| `--amount`, `-a` | integer | Scroll amount (notches) (default: `3`) |
| `--on` | text | Element text or eN ref to scroll on |
| `--id` | text | Element ID to scroll on |
| `--coords` | integer | Coordinates to scroll at |
| `--smooth` | boolean | Smooth scrolling (planned) |
| `--delay` | float | Delay between scroll steps (ms) |
| `--app` | text | Target application (name or partial match) |
| `--pid` | integer | Process ID |
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--selector` | text | Unified selector to locate target element. URI: app://notepad.exe/Button[@name="Save"]. Short: //Edit[@name="Search"] (any app, descendant search). App names are flexible: chrome, chrome.exe, Chrome all match. |
| `--method`, `-m` | {auto, cdp, uia, msaa, ia2, jab, vision} | Interaction method override: auto (default), cdp, uia, msaa, ia2, jab, vision. Bypasses auto-detection when set explicitly. |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--see` | boolean | Capture and display updated UI tree after action |
| `--settle` | integer | Wait time in ms before re-snapshot (used with --see) (default: `300`) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo scroll down
naturo scroll up --amount 5
naturo scroll --on e3 down --amount 5
naturo scroll --coords 500 300 down
naturo scroll --selector 'app://*/List[@name="Items"]' down
```

## `naturo set`

Set element value/state.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `TARGET` | text | no |
| `VALUE` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--ref`, `-r` | text | Element ref from snapshot (e.g. e47) |
| `--automation-id`, `--aid` | text | UIA AutomationId of the target element |
| `--role` | text | Element role filter (e.g. Edit, CheckBox) |
| `--name` | text | Element name filter |
| `--toggle` | boolean | Toggle a checkbox or toggle button (TogglePattern) |
| `--select` | boolean | Select a list item or radio button (SelectionItemPattern) |
| `--expand` | boolean | Expand a combo box or tree item (ExpandCollapsePattern) |
| `--collapse` | boolean | Collapse a combo box or tree item (ExpandCollapsePattern) |
| `--app` | text | Target application (name or partial match) |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo set e47 "hello world"       # Set text field value
naturo set --aid txtSearch "query"  # Set by AutomationId
naturo set e12 --toggle            # Toggle a checkbox
naturo set e8 --select             # Select a list/radio item
naturo set e5 --expand             # Expand a combo box
naturo set e5 --collapse           # Collapse a combo box
naturo set --role Edit --name Search "test" --app notepad
```

## `naturo type`

Type text with configurable speed and profile.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `TEXT` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--delay` | float | Delay between keystrokes (ms) (default: `5.0`) |
| `--profile` | {human, linear} | Typing profile: human (variable delay), linear (constant delay) (default: `linear`) |
| `--wpm` | integer | Words per minute (for human profile) (default: `120`) |
| `--return` | boolean | Press Return after typing |
| `--tab` | integer | Press Tab N times after typing |
| `--escape` | boolean | Press Escape after typing |
| `--delete` | boolean | Delete existing text first |
| `--clear` | boolean | Select all + delete before typing |
| `--paste` | boolean | Paste via clipboard (Ctrl+V) instead of typing |
| `--file` | path | Read text from file (use with --paste) |
| `--restore`, `--no-restore` | boolean | Restore clipboard after --paste |
| `--on` | text | Target element (eN ref or text label) — click to focus before typing |
| `--app` | text | Target application (name or partial match) |
| `--pid` | integer | Process ID |
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--input-mode` | {normal, hardware, hook} | Input method: normal (SendInput), hardware (Phys32 driver), hook (MinHook injection) (default: `normal`) |
| `--method`, `-m` | {auto, cdp, uia, msaa, ia2, jab, vision} | Interaction method override: auto (default), cdp, uia, msaa, ia2, jab, vision. Bypasses auto-detection when set explicitly. |
| `--selector` | text | Unified selector to locate target element. URI: app://notepad.exe/Button[@name="Save"]. Short: //Edit[@name="Search"] (any app, descendant search). App names are flexible: chrome, chrome.exe, Chrome all match. |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--verify`, `--no-verify` | boolean | Verify action had effect (default: on). Use --no-verify to skip. |
| `--see` | boolean | Capture and display updated UI tree after action |
| `--settle` | integer | Wait time in ms before re-snapshot (used with --see) (default: `300`) |
| `--raw` | boolean | Disable escape sequence interpretation (type text literally) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo type "Hello World"
naturo type "Hello" --return
naturo type "text" --profile human --wpm 60
naturo type "large content" --paste
naturo type --paste --file mytext.txt
naturo type --paste                        # paste current clipboard
naturo type "hello" --on e42               # click e42 then type
naturo type "hello" --on e42 --app feishu  # target app + element
naturo type "hello" --selector 'app://notepad.exe/Edit[@automationid="15"]'
```

---

## App & Window Management

## `naturo app`

Manage applications and windows: launch, quit, focus, close, minimize, maximize, restore, move, and more.

### `naturo app close`

Close an application window (graceful or forced).

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Application name (alternative to positional NAME) |
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--force` | boolean | Force terminate the process |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo app close notepad
naturo app close --app notepad
naturo app close feishu --window "Chat"
naturo app close --hwnd 12345 --force
```

### `naturo app find`

Find a running application by name or PID.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | yes |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--pid` | integer | Search by PID instead of name |
| `--json`, `-j` | boolean | JSON output |

### `naturo app focus`

Focus an application window (bring to foreground).

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Application name (alternative to positional NAME) |
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo app focus feishu
naturo app focus --app feishu
naturo app focus feishu --window "Chat"
naturo app focus --app feishu
naturo app focus --hwnd 12345
```

### `naturo app inspect`

Probe an application and report available interaction methods.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Application name (alternative to positional NAME) |
| `--pid` | integer | Inspect by process ID |
| `--all` | boolean | Scan all visible windows |
| `--quick` | boolean | Fast probe — stop at first available method |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo app inspect notepad
naturo app inspect --app notepad
naturo app inspect --pid 12345
naturo app inspect --all
naturo app inspect chrome --quick --json
```

### `naturo app launch`

Launch an application by name or path.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Application name (alternative to positional NAME) |
| `--path` | text | Explicit executable path |
| `--wait-until-ready` | boolean | Wait for app to create a window |
| `--timeout` | float | Timeout for wait-until-ready (default: `30.0`) |
| `--no-focus` | boolean | Launch without focusing |
| `--args` | text | Arguments to pass to the application |
| `--json`, `-j` | boolean | JSON output |

### `naturo app list`

List running applications with visible windows.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--all` | boolean | Show all processes (not just apps with windows) |
| `--json`, `-j` | boolean | JSON output |

### `naturo app maximize`

Maximize an application window.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo app maximize feishu
naturo app maximize --hwnd 12345
```

### `naturo app minimize`

Minimize an application window.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo app minimize feishu
naturo app minimize --hwnd 12345
```

### `naturo app move`

Move and/or resize an application window.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--x` | integer | Target X position |
| `--y` | integer | Target Y position |
| `--width` | integer | New width in pixels (optional) |
| `--height` | integer | New height in pixels (optional) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo app move feishu --x 100 --y 100
naturo app move feishu --x 100 --y 100 --width 800 --height 600
naturo app move feishu --width 800 --height 600
```

### `naturo app quit`

Quit an application gracefully (or force kill).

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Application name (alternative to positional NAME) |
| `--pid` | integer | Process ID |
| `--force` | boolean | Force kill immediately |
| `--timeout` | float | Graceful shutdown timeout (default: `10.0`) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo app quit notepad
naturo app quit chrome --force
naturo app quit --pid 12345
```

### `naturo app relaunch`

Quit and relaunch an application.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Application name (alternative to positional NAME) |
| `--wait-until-ready` | boolean | Wait for app (default: on) |
| `--timeout` | float | Timeout in seconds (default: `30.0`) |
| `--json`, `-j` | boolean | JSON output |

### `naturo app restore`

Restore a minimized or maximized window to normal state.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--window` | text | Window title pattern (substring match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo app restore feishu
naturo app restore --hwnd 12345
```

### `naturo app windows`

List open windows (optionally filtered by app name or PID).

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--pid` | integer | Process ID |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo app windows
naturo app windows feishu
naturo app windows --pid 1234
```

## `naturo dialog`

Detect and interact with system dialogs.

**Examples:**

```bash
naturo dialog detect                   # List active dialogs
naturo dialog detect --app notepad     # Filter by app
naturo dialog accept                   # Click OK/Yes/Open
naturo dialog dismiss                  # Click Cancel/No/Close
naturo dialog click-button "Save"      # Click a specific button
naturo dialog type "hello.txt"         # Type into dialog input
```

### `naturo dialog accept`

Accept (confirm) the active dialog.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Owner application name filter |
| `--hwnd` | integer | Specific dialog window handle |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo dialog accept                   # Accept first dialog
naturo dialog accept --app notepad     # Accept notepad's dialog
naturo dialog accept --app-id a1       # Accept by app ID
naturo dialog accept --json            # JSON output
```

### `naturo dialog click-button`

Click a specific button in the active dialog.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `BUTTON` | text | yes |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Owner application name filter |
| `--hwnd` | integer | Specific dialog window handle |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo dialog click-button "Save"              # Click Save
naturo dialog click-button "Don't Save"        # Click Don't Save
naturo dialog click-button "Retry" --app-id a1 # By app ID
```

### `naturo dialog detect`

Detect active dialog windows.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Filter by owner application name |
| `--hwnd` | integer | Filter by dialog window handle |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo dialog detect                   # List all dialogs
naturo dialog detect --app notepad     # Filter by app
naturo dialog detect --app-id a1       # Filter by app ID
naturo dialog detect --json            # JSON output
```

### `naturo dialog dismiss`

Dismiss (cancel) the active dialog.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Owner application name filter |
| `--hwnd` | integer | Specific dialog window handle |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo dialog dismiss                  # Dismiss first dialog
naturo dialog dismiss --app notepad    # Dismiss notepad's dialog
naturo dialog dismiss --app-id a1      # Dismiss by app ID
naturo dialog dismiss --json           # JSON output
```

### `naturo dialog type`

Type text into a dialog's input field.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `TEXT` | text | yes |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--accept` | boolean | Click OK/Accept after typing |
| `--app` | text | Owner application name filter |
| `--hwnd` | integer | Specific dialog window handle |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo dialog type "hello.txt"                  # Type filename
naturo dialog type "hello.txt" --accept         # Type then click OK
naturo dialog type "C:\Users" --app-id a1       # By app ID
```

## `naturo diff`

Compare two UI element trees to detect changes.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--snapshot` | text | Snapshot ID (specify twice) |
| `--window` | text | Window to diff (captures before/after) |
| `--interval` | float | Seconds between captures (with --window) (default: `2.0`) |
| `--app` | text | Target application (name or partial match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--pid` | integer | Process ID |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo diff --snapshot snap1 --snapshot snap2
```

## `naturo wait`

Wait for a duration, or for a UI element/window to appear or disappear.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `DURATION` | float | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--element` | text | Element selector to wait for |
| `--window` | text | Window title to wait for |
| `--gone` | text | Element selector to wait to disappear |
| `--timeout` | float | Timeout in seconds (default: 10) |
| `--interval` | float | Poll interval in seconds (default: 0.1) |
| `--app` | text | Target application (name or partial match) |
| `--hwnd` | integer | Window handle (HWND) |
| `--pid` | integer | Process ID |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo wait 3                            # Sleep 3 seconds
```

---

## System

## `naturo desktop`

Virtual desktop management (Windows 10/11).

**Examples:**

```bash
naturo desktop list                    # List all desktops
naturo desktop switch 1                # Switch to desktop 1
naturo desktop create --name "Dev"     # Create a named desktop
naturo desktop close                   # Close current desktop
naturo desktop move-window 1 --app X   # Move app to desktop 1
```

### `naturo desktop close`

Close a virtual desktop.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `INDEX` | integer | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo desktop close                   # Close current desktop
naturo desktop close 2                 # Close desktop index 2
naturo desktop close --json            # JSON output
```

### `naturo desktop create`

Create a new virtual desktop.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--name` | text | Name for the new desktop |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo desktop create                  # Create unnamed desktop
naturo desktop create --name "Work"    # Create named desktop
naturo desktop create --json           # JSON output
```

### `naturo desktop list`

List all virtual desktops.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo desktop list                    # Human-readable list
naturo desktop list --json             # JSON output
```

### `naturo desktop move-window`

Move a window to a different virtual desktop.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `INDEX` | integer | yes |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--app` | text | Application name (partial match) |
| `--hwnd` | integer | Window handle |
| `--app-id` | text | Stable app/window ID from "naturo app list" output (e.g. a1) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo desktop move-window 1 --app "Notepad"    # Move Notepad
naturo desktop move-window 0 --hwnd 12345       # Move by handle
naturo desktop move-window 1 --app-id a1        # Move by app ID
naturo desktop move-window 2                    # Move foreground
```

### `naturo desktop switch`

Switch to a virtual desktop by index.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `INDEX` | integer | yes |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo desktop switch 0               # Switch to first desktop
naturo desktop switch 2               # Switch to third desktop
naturo desktop switch 1 --json        # JSON output
```

## `naturo taskbar`

Interact with the Windows taskbar.

**Examples:**

```bash
naturo taskbar list                    # List all taskbar items
naturo taskbar list --json             # JSON output
naturo taskbar click "Notepad"         # Activate Notepad
```

### `naturo taskbar click`

Click a taskbar item to activate its window.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | yes |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo taskbar click "Chrome"          # Activate Chrome
naturo taskbar click "Notepad" --json  # JSON output
```

### `naturo taskbar list`

List items on the taskbar.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo taskbar list                    # Human-readable list
naturo taskbar list --json             # JSON output
```

## `naturo tray`

Interact with the system tray (notification area).

**Examples:**

```bash
naturo tray list                       # List all tray icons
naturo tray click "Volume"             # Left-click Volume
naturo tray click "Wi-Fi" --right      # Right-click for menu
```

### `naturo tray click`

Click a system tray icon.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `NAME` | text | yes |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--right` | boolean | Right-click (context menu) |
| `--double` | boolean | Double-click (open) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo tray click "Volume"             # Left-click
naturo tray click "Wi-Fi" --right      # Right-click for menu
naturo tray click "Dropbox" --double   # Double-click to open
```

### `naturo tray list`

List system tray icons.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo tray list                       # Human-readable list
naturo tray list --json                # JSON output
```

---

## Tools

## `naturo clipboard`

Read, write, and manage clipboard contents.

**Examples:**

```bash
naturo clipboard get                    # Read clipboard text
naturo clipboard set "hello world"      # Write text to clipboard
naturo clipboard clear                  # Clear clipboard contents
naturo clipboard info                   # Show format and size
```

### `naturo clipboard clear`

Clear the clipboard contents.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo clipboard clear                  # Clear clipboard
```

### `naturo clipboard get`

Read current clipboard content.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--format` | {text} | Output format (currently only text supported) (default: `text`) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo clipboard get                    # Print clipboard text
naturo clipboard get --json             # JSON output with metadata
```

### `naturo clipboard info`

Show information about current clipboard contents.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo clipboard info                   # Show clipboard info
naturo clipboard info --json            # JSON output
```

### `naturo clipboard set`

Write text to the clipboard.

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `TEXT` | text | no — supply via `TEXT`, `--file`, or stdin (`-`) |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--file PATH` | path | Read text from a file (mirrors `naturo type --file`) |
| `--json`, `-j` | boolean | JSON output |

Exactly one source must be supplied. `--file` and stdin avoid the shell
ARG_MAX limit (~32 KB) that caps a positional argument, and preserve real
newlines without shell-specific quoting.

**Examples:**

```bash
naturo clipboard set "hello world"      # Literal text
naturo clipboard set --file notes.txt   # Read text from a file
naturo see -j | naturo clipboard set -  # Read text from stdin
```

## `naturo config`

Manage Naturo configuration and provider credentials.

### `naturo config clear`

Remove stored credentials for a provider (or all providers).

**Arguments:**

| Name | Type | Required |
|------|------|----------|
| `PROVIDER` | text | no |

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--yes`, `-y` | boolean | Skip confirmation |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo config clear anthropic
naturo config clear all --yes
```

### `naturo config setup`

Interactive setup for AI provider credentials.

#### `naturo config setup anthropic`

Configure Anthropic (Claude) credentials.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--mode` | {api_key, oauth} | Auth mode: api_key (pay-per-use) or oauth (subscription/session token) |
| `--token` | text | API key or session token (skip interactive prompt) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo config setup anthropic                   # interactive
naturo config setup anthropic --mode api_key    # API key mode
naturo config setup anthropic --mode oauth      # OAuth mode
naturo config setup anthropic --token sk-ant-xxx --mode api_key
```

### `naturo config show`

Show current credential configuration (tokens are redacted).

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo config show
naturo config show --json
```

## `naturo mcp`

MCP (Model Context Protocol) server for AI agent integration.

### `naturo mcp install`

Install MCP server dependencies.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--json`, `-j` | boolean | JSON output |

### `naturo mcp start`

Start the MCP server.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--transport` | {stdio, sse, streamable-http} | Transport protocol (default: stdio) |
| `--host` | text | Bind host (for sse/http) (default: `localhost`) |
| `--port` | integer | Bind port (for sse/http) (default: `3100`) |
| `--json`, `-j` | boolean | JSON output |

**Examples:**

```bash
naturo mcp start                    # stdio transport
naturo mcp start --transport sse    # SSE transport on port 3100
```

### `naturo mcp tools`

List available MCP tools.

**Options:**

| Flag | Type | Description |
|------|------|-------------|
| `--json`, `-j` | boolean | JSON output |

---

