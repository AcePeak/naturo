# Naturo Design Principles

## Core Philosophy: Complex Engine, Simple Interface

The underlying engine may simultaneously use UIA / MSAA / Win32 HWND / AI Vision and other technologies,
but the user should only ever need the simplest commands.

## Three-Step User Workflow

```bash
# 1. See — automatically picks the best engine, shows all actionable elements
naturo see --app U8

# 2. Find — locate elements using natural language
naturo find "invoice number" --app U8

# 3. Act — operate directly using element refs
naturo click e70
naturo type e85 "12345"
naturo select e71 "VAT Special Invoice"
```

## Design Rules

### 1. Engine Transparency + Layer-by-Layer Hybrid

- Users should not need to know the difference between UIA / MSAA / Win32 / AI Vision
- `--backend auto` is the default (not `uia`)
- **Per-layer engine selection** (inspired by the Natural Robot selector architecture):
  - Each layer of the element tree independently selects the best engine
  - Outer containers use Win32 HWND enumeration (penetrating VB6/ActiveX)
  - Once an interactive control is reached, switch to UIA (to access internal Row/Cell)
  - Anything UIA cannot reach falls back to AI Vision
  - Example: Window[HWND] -> Pane[HWND] -> ThunderRT6[HWND] -> VSFlexGrid[HWND] -> Row[UIA] -> Cell[UIA]
- Each ElementInfo records its source engine (hwnd/uia/msaa/ai)
- Results are merged and deduplicated; the user sees only a unified element tree

### 2. --app Is All You Need

- `--app feishu` = all elements across all windows of Feishu
- Users should not need to use `app windows` to find an HWND and then specify `--hwnd`
- Multiple windows are merged automatically; refs are globally unique

### 3. If an Element Is Visible, It Is Actionable

- Every element returned by `see` can be directly used with click/type/find via its ref
- Element types are auto-detected: Edit is typeable, Button is clickable, ComboBox is selectable
- `naturo type e85 "hello"` automatically handles: locate element -> focus -> clear old value -> type

### 4. find Is the Core Entry Point

- `naturo find "invoice number"` does not require `--ai`; it searches by default
- Search scope: name, class name, value, role
- Supports fuzzy matching and CJK characters
- Returns the element ref + position, ready for click/type

### 5. highlight Is What-You-See-Is-What-You-Get

- `naturo highlight --app U8` draws all actionable elements directly on screen
- Each element displays its ref + name
- Users see the on-screen annotations and immediately know which ref to use

### 6. Error Messages Must Be Helpful

- Instead of "No window found", say "Cannot find 'U8'. Available apps: EnterprisePortal, cmd, explorer"
- Instead of "element not found", say "e85 does not exist. The latest snapshot contains e1-e64. Try naturo see to refresh"

### 7. Enterprise Applications Are First-Class Citizens

- Applications like Yonyou, Kingdee, SAP, and Inspur built with VB6/MFC/ActiveX are not edge cases
- Auto mode must handle them (Win32 HWND fallback)
- Users must not be required to install extra dependencies or run as administrator for basic functionality
