#!/usr/bin/env python3
"""End-to-end acceptance tests — run on a REAL Windows desktop.

These tests verify actual user experience, not just code logic.
Run after every change before declaring a feature "done".

Usage:
    python tests/e2e/acceptance.py

Requirements:
    - Must run on Windows with a desktop session (not SSH)
    - naturo must be installed (`pip install -e .`)
    - At least one visible window must be open
"""

import json
import os
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PASS = 0
FAIL = 0
ERRORS = []


def check(name: str, condition: bool, detail: str = ""):
    """Record a test result."""
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        msg = f"  ❌ {name}" + (f" — {detail}" if detail else "")
        print(msg)
        ERRORS.append(msg)


def run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a naturo command and return the result."""
    cmd = [sys.executable, "-m", "naturo"] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def file_is_png(path: str) -> bool:
    """Check if a file starts with PNG magic bytes."""
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x89PNG"
    except (OSError, IOError):
        return False


def file_is_bmp(path: str) -> bool:
    """Check if a file starts with BMP magic bytes."""
    try:
        with open(path, "rb") as f:
            return f.read(2) == b"BM"
    except (OSError, IOError):
        return False


# ═══════════════════════════════════════════════════════════════════════
# 1. HELP & VERSION — What users see must match what works
# ═══════════════════════════════════════════════════════════════════════

def test_help_and_version():
    print("\n📋 Help & Version")

    # --version works
    r = run(["--version"])
    check("--version exits 0", r.returncode == 0)
    check("--version shows version string", "naturo" in r.stdout.lower())

    # --help works
    r = run(["--help"])
    check("--help exits 0", r.returncode == 0)

    # Every command in --help is functional (not a stub)
    lines = r.stdout.strip().split("\n")
    in_commands = False
    commands = []
    for line in lines:
        if line.strip().startswith("Commands:"):
            in_commands = True
            continue
        if in_commands and line.strip():
            cmd_name = line.strip().split()[0]
            commands.append(cmd_name)

    check("At least 10 commands visible", len(commands) >= 10,
          f"found {len(commands)}")

    for cmd in commands:
        r = run([cmd, "--help"])
        check(f"'{cmd} --help' exits 0", r.returncode == 0,
              r.stderr[:200] if r.returncode != 0 else "")
        check(f"'{cmd}' is not a stub",
              "not implemented" not in (r.stdout + r.stderr).lower(),
              (r.stdout + r.stderr)[:200])


# ═══════════════════════════════════════════════════════════════════════
# 2. CAPTURE — Screenshot must be real PNG, correct size, usable path
# ═══════════════════════════════════════════════════════════════════════

def test_capture():
    print("\n📸 Capture")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Default capture → PNG
        png_path = os.path.join(tmpdir, "test.png")
        r = run(["capture", "live", "--path", png_path, "--no-snapshot"])
        check("capture exits 0", r.returncode == 0, r.stderr[:200])
        check("capture output file exists", os.path.exists(png_path))
        check("capture output is PNG (not BMP)", file_is_png(png_path))
        check("capture output is NOT BMP", not file_is_bmp(png_path))

        # Check file size is reasonable (> 10KB for a real screenshot)
        if os.path.exists(png_path):
            size = os.path.getsize(png_path)
            check("capture file size > 10KB", size > 10240,
                  f"size={size} bytes")

        # Output shows full absolute path
        check("output shows absolute path",
              os.sep in r.stdout or ":" in r.stdout,
              r.stdout.strip())

        # --format jpg works
        jpg_path = os.path.join(tmpdir, "test.jpg")
        r = run(["capture", "live", "--path", jpg_path, "--format", "jpg",
                 "--no-snapshot"])
        check("capture --format jpg exits 0", r.returncode == 0)
        if os.path.exists(jpg_path):
            with open(jpg_path, "rb") as f:
                check("jpg output starts with JFIF/JPEG header",
                      f.read(2) == b"\xff\xd8")

        # --json output is valid JSON
        r = run(["capture", "live", "--path",
                 os.path.join(tmpdir, "json_test.png"),
                 "--no-snapshot", "--json"])
        check("capture --json exits 0", r.returncode == 0)
        try:
            data = json.loads(r.stdout)
            check("--json output is valid JSON", True)
            check("--json has 'path' key", "path" in data)
            check("--json has 'width' key", "width" in data)
            check("--json width > 0", data.get("width", 0) > 0)
        except json.JSONDecodeError:
            check("--json output is valid JSON", False, r.stdout[:200])


# ═══════════════════════════════════════════════════════════════════════
# 3. LIST WINDOWS — Must return real windows with titles
# ═══════════════════════════════════════════════════════════════════════

def test_list_windows():
    print("\n🪟 List Windows")

    r = run(["list", "windows", "--json"])
    check("list windows --json exits 0", r.returncode == 0, r.stderr[:200])

    try:
        data = json.loads(r.stdout)
        check("list windows returns a JSON array", isinstance(data, list))
        check("at least 1 window found", len(data) >= 1,
              f"found {len(data)}")

        if data:
            w = data[0]
            check("window has 'title' field", "title" in w)
            check("window has 'hwnd' field", "hwnd" in w)
            check("window has 'pid' field", "pid" in w)

        # Check we can handle Chinese/Unicode titles
        has_non_ascii = any(
            any(ord(c) > 127 for c in w.get("title", ""))
            for w in data
        )
        # Not a failure if no Chinese titles, just info
        if has_non_ascii:
            print("  ℹ️  Found non-ASCII window titles (encoding OK)")
        else:
            print("  ℹ️  No non-ASCII titles found (encoding untested)")

    except json.JSONDecodeError:
        check("list windows returns valid JSON", False, r.stdout[:200])


# ═══════════════════════════════════════════════════════════════════════
# 4. SEE — UI tree must target the right window
# ═══════════════════════════════════════════════════════════════════════

def test_see():
    print("\n👁️ See (UI Tree)")

    # see without --app should work (foreground window)
    r = run(["see", "--json", "--no-snapshot", "--depth", "2"])
    check("see exits 0", r.returncode == 0, r.stderr[:200])

    try:
        data = json.loads(r.stdout)
        check("see --json returns valid JSON", True)
        check("see has 'role' field", "role" in data)
    except json.JSONDecodeError:
        check("see --json returns valid JSON", False, r.stdout[:200])

    # see --app with a known window
    # First find a real window to target
    r_list = run(["list", "windows", "--json"])
    try:
        windows = json.loads(r_list.stdout)
        # Find a window with a non-empty title that isn't our terminal
        target = None
        for w in windows:
            title = w.get("title", "")
            proc = w.get("process_name", "").lower()
            if title and "cmd.exe" not in proc and "powershell" not in proc \
               and "terminal" not in proc.lower() and "conhost" not in proc:
                target = title
                break

        if target:
            r = run(["see", "--app", target, "--json", "--no-snapshot",
                     "--depth", "2"])
            check(f"see --app '{target[:30]}' exits 0",
                  r.returncode == 0, r.stderr[:200])

            if r.returncode == 0:
                try:
                    tree = json.loads(r.stdout)
                    check("see --app returns UI tree (not terminal)",
                          "role" in tree)
                except json.JSONDecodeError:
                    check("see --app returns valid JSON", False)
        else:
            print("  ⚠️  No non-terminal window found to test --app targeting")

    except json.JSONDecodeError:
        print("  ⚠️  Could not parse window list, skipping --app test")


# ═══════════════════════════════════════════════════════════════════════
# 5. APP LIST — Must return real processes
# ═══════════════════════════════════════════════════════════════════════

def test_app():
    print("\n📱 App Commands")

    r = run(["app", "list", "--json"])
    check("app list --json exits 0", r.returncode == 0, r.stderr[:200])

    try:
        data = json.loads(r.stdout)
        check("app list returns valid JSON", True)
        check("app list has 'apps' key", "apps" in data)
        check("app list has 'count' key", "count" in data)

        apps = data.get("apps", [])
        check("app list finds > 10 processes", len(apps) > 10,
              f"found {len(apps)}")

        if apps:
            a = apps[0]
            check("app has 'pid' field", "pid" in a)
            check("app has 'name' field", "name" in a)
            check("app has 'is_running' field", "is_running" in a)

        # app find with known process
        r = run(["app", "find", "explorer", "--json"])
        check("app find 'explorer' exits 0", r.returncode == 0)

    except json.JSONDecodeError:
        check("app list returns valid JSON", False, r.stdout[:200])


# ═══════════════════════════════════════════════════════════════════════
# 6. FIND — Element search
# ═══════════════════════════════════════════════════════════════════════

def test_find():
    print("\n🔍 Find Elements")

    r = run(["find", "Button", "--json"])
    check("find 'Button' exits 0", r.returncode == 0, r.stderr[:200])


# ═══════════════════════════════════════════════════════════════════════
# 7. WAIT — Timeout behavior
# ═══════════════════════════════════════════════════════════════════════

def test_wait():
    print("\n⏳ Wait Command")

    # Wait for a window that exists should return quickly
    start = time.time()
    r = run(["wait", "--window", "explorer", "--timeout", "3"])
    elapsed = time.time() - start
    # Just check it doesn't crash
    check("wait --window exits without crash",
          r.returncode in (0, 1))

    # Wait for nonexistent should timeout
    start = time.time()
    r = run(["wait", "--window", "NONEXISTENT_WINDOW_12345",
             "--timeout", "2"])
    elapsed = time.time() - start
    check("wait for nonexistent times out", r.returncode != 0)
    check("wait respects timeout (< 5s)", elapsed < 5.0,
          f"took {elapsed:.1f}s")


# ═══════════════════════════════════════════════════════════════════════
# 8. ERROR HANDLING — Errors must be clear, not stack traces
# ═══════════════════════════════════════════════════════════════════════

def test_errors():
    print("\n💥 Error Handling")

    # Nonexistent app
    r = run(["see", "--app", "NONEXISTENT_APP_99999", "--no-snapshot"])
    check("see nonexistent app returns error (not crash)",
          r.returncode != 0)
    check("error message is user-friendly (no traceback)",
          "Traceback" not in r.stderr and "Traceback" not in r.stdout,
          (r.stderr + r.stdout)[:300])

    # Invalid coordinates
    r = run(["click", "-99999", "-99999"])
    # Should error or handle gracefully
    check("click invalid coords doesn't crash with traceback",
          "Traceback" not in r.stderr and "Traceback" not in r.stdout)


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Naturo E2E Acceptance Tests")
    print(f"   Platform: {sys.platform}")
    print(f"   Python: {sys.version.split()[0]}")
    print("=" * 60)

    if sys.platform != "win32":
        print("\n⚠️  These tests must run on Windows with a desktop session.")
        print("   Run on Lead: python tests/e2e/acceptance.py")
        sys.exit(1)

    test_help_and_version()
    test_capture()
    test_list_windows()
    test_see()
    test_app()
    test_find()
    test_wait()
    test_errors()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")

    if ERRORS:
        print("\nFailed checks:")
        for e in ERRORS:
            print(e)

    print("=" * 60)
    sys.exit(1 if FAIL > 0 else 0)
