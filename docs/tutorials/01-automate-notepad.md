# Tutorial 1 — Automate Notepad in 5 Minutes

**What you'll build:** a tiny, fully scripted flow that launches Notepad, sees its
UI, types a line, and saves the file — driven entirely from the `naturo` CLI and,
if you prefer Python, the `import naturo` SDK. By the end you'll have a repeatable
script that reproduces the same result byte-for-byte, and you'll understand the
four verbs every naturo automation is built from: **see → click → type → save**.

> **Time:** ~5 minutes. **Platform:** Windows 10/11. **Python:** 3.9+.

## Prerequisites

```bash
pip install naturo
```

Verify the CLI is on your `PATH`:

```bash
naturo --version
```

Expected output:

```
naturo, version 0.3.2
```

That's the only setup. Notepad ships with Windows, so there's nothing else to
install.

> **Windows 11 note:** Windows 11 replaced classic Notepad with a UWP
> (WinUI) app. naturo handles both — it resolves the real Notepad process behind
> the `ApplicationFrameHost` window automatically, so the commands below work on
> Windows 10 *and* 11 without changes. The one thing that differs is the editor
> control's role: on Win11 it's a `Document`, on Win10 an `Edit`. The flow below
> doesn't depend on that difference.

---

## Step 1 — Launch Notepad

```bash
naturo app launch notepad
```

Expected output:

```
Launched notepad.exe (PID: 12044)
```

Want the launch call to block until the window actually exists (useful in a
script)? Add `--wait-until-ready`:

```bash
naturo app launch notepad --wait-until-ready --timeout 5
```

## Step 2 — See the UI

Before you act on a window, look at it. `naturo see` reads the live
accessibility tree and prints one compact line per element — no screenshot, no
tokens wasted on pixels.

```bash
naturo see --window "Notepad" --compact
```

Expected output (abridged — element refs `eN` will differ on your machine):

```
e1 [Window] "Untitled - Notepad"
  e3 [Document] "Text editor"
  e7 [MenuBar] "Application"
  ...
```

Each `eN` ref is a stable handle you can act on for the next ~10 minutes. `e3`
above is the editing surface.

## Step 3 — Type into the document

`naturo type` sends text through naturo's **IME-immune reliability ladder**
(UIA `ValuePattern` → clipboard paste → keystroke). This is what keeps input
honest for CJK/TSF input methods where a naive keystroke path corrupts text
("naturo" → "nature"). You don't choose the rung — naturo picks the one that
lands the text correctly and reports which it used.

Passing `--app` focuses the target window first, so the keystrokes reach Notepad
and not whatever window happened to be in the foreground:

```bash
naturo type "Hello from naturo!" --app notepad
```

Expected output:

```
action: typed
text: Hello from naturo!
length: 18
input_method: value_pattern
```

Prefer to target the exact element you saw in Step 2? Use its ref:

```bash
naturo type "Hello from naturo!" --on e3
```

## Step 4 — Save with Ctrl+S

`naturo press` sends a key or combo. Ctrl+S opens the Save dialog:

```bash
naturo press ctrl+s --app notepad
```

A **Save As** dialog appears. Fill in the filename and confirm in one call —
`naturo dialog type` types into the dialog's input field, and `--accept` clicks
the OK/Save button for you:

```bash
naturo dialog type "naturo-hello.txt" --accept
```

Expected output:

```
Typed "naturo-hello.txt" into dialog and accepted
```

## Step 5 — Verify it worked

The save renames the window from `Untitled - Notepad` to your file name. That
title change is the proof:

```bash
naturo list windows
```

Expected output includes the renamed window:

```
HWND       PID     TITLE
--------------------------------------------------
5574222    50852   naturo-hello.txt - Notepad
```

You just saw, typed, and saved on the real Windows desktop.

---

## The complete flow (CLI)

Save this as `notepad.sh` (or run the lines one by one):

```bash
# 1. Launch and wait for the window
naturo app launch notepad --wait-until-ready --timeout 5

# 2. See the UI (optional, but good practice)
naturo see --window "Notepad" --compact

# 3. Type a line (IME-immune, focuses Notepad first)
naturo type "Hello from naturo!" --app notepad

# 4. Save: Ctrl+S, then fill the dialog and confirm
naturo press ctrl+s --app notepad
naturo wait --window "Save As" --timeout 5
naturo dialog type "naturo-hello.txt" --accept

# 5. Confirm the title changed
naturo list windows
```

---

## The same flow in Python (the SDK)

`pip install naturo` also gives you `import naturo` — an in-process API over the
exact same engine, no subprocess, no output parsing. The verbs mirror the CLI:

```python
import naturo

# Launch and wait until the window exists; returns an App handle.
app = naturo.launch("notepad")

# See the UI — returns the root Element; walk .children / .descendants / .find.
tree = naturo.see(window="Notepad")

# Type through the IME-immune ladder (focuses the window first).
naturo.type("Hello from naturo!", window="Notepad")

# Save: Ctrl+S. press() accepts a combo string.
naturo.press("ctrl+s", window="Notepad")

# Give the Save As dialog a moment, then drive it.
naturo.wait("Save As", timeout=5)
naturo.type("naturo-hello.txt", window="Save As")
naturo.press("enter", window="Save As")

print("Saved. Window is now:", [w.title for w in naturo.windows()
                                 if "Notepad" in w.title])
```

Run it however you normally run Python — or hand it to naturo's own runner (see
below) so `import naturo` resolves without any environment fiddling.

## Run a script with `naturo run`

`naturo run` executes a Python script (or an inline `-c` snippet) under the
interpreter naturo resolved, with the SDK importable inside it:

```bash
# Run a script file
naturo run notepad.py

# Or a one-liner
naturo run -c "from naturo import windows; print(len(windows()))"
```

`naturo run` propagates the script's exit code and supports `--timeout` to kill
a runaway run and `--args "a b c"` to pass `sys.argv[1:]` through.

---

## Next steps

- **Automate Excel** — read and write cells, build charts:
  [Tutorial 2 — Automate Excel with naturo](02-automate-excel.md)
- **Build an AI agent** that drives naturo through the MCP server:
  [Tutorial 3 — Build an AI agent with naturo](03-ai-agent-with-naturo.md)
- **CLI reference** — every command and flag:
  [docs/CLI_REFERENCE.md](../CLI_REFERENCE.md)

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `naturo: command not found` | Ensure your Python `Scripts/` directory is on `PATH`; reopen the terminal after `pip install`. |
| `type` sent text to the wrong window | Always pass `--app notepad` (or `--window`/`--on`) so naturo focuses the target first — `type` without a target goes to the foreground window. |
| The `eN` ref from `see` no longer resolves | Refs expire after ~10 minutes. Re-run `naturo see` to capture a fresh snapshot, then reuse the new ref. |
| The Save As dialog didn't appear in time | Add `naturo wait --window "Save As" --timeout 5` between the `press ctrl+s` and the `dialog type` steps. |
