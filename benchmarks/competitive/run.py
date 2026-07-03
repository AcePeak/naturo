#!/usr/bin/env python
"""Competitive coverage benchmark: naturo vs reproducibly-installable OSS rivals.

Launches the SAME real apps across UI frameworks and asks each tool how many
elements it recognizes. naturo's unified cascade recognizes Java (JAB), Excel
cells (COM) and web (CDP) that a UIA-only rival (pywinauto) collapses to opaque
chrome and a pixel tool (PyAutoGUI) cannot see at all.

Run (Windows, real desktop):
    python -m benchmarks.competitive.run

Writes a reproducible matrix to stdout and updates the matrix block in
``docs/COMPETITIVE.md``. Rivals that cannot run in this environment are recorded
as ``blocked: needs env``. See ``benchmarks/competitive/README.md``.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

# Targets: (label, framework, launch spec). Each is a real app naturo automates.
TARGETS: list[dict[str, Any]] = [
    {"label": "Notepad", "framework": "UIA (native)", "app": "notepad"},
    {
        "label": "jconsole",
        "framework": "Java/Swing (JAB)",
        "path": r"C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot\bin\jconsole.exe",
        "boot_s": 7,
    },
]


def _launch_and_get_hwnd(spec: dict[str, Any]) -> Optional[int]:
    from naturo import process
    from naturo.backends.base import get_backend

    backend = get_backend()

    def _wins() -> dict:
        try:
            return {
                (getattr(w, "handle", None) or getattr(w, "hwnd", None)):
                    (getattr(w, "title", "") or "")
                for w in backend.list_windows()
            }
        except Exception:
            return {}

    before = set(_wins())
    process.launch_app(name=spec.get("app"), path=spec.get("path"))
    deadline = time.monotonic() + max(spec.get("boot_s", 3), 3) + 25
    while time.monotonic() < deadline:
        time.sleep(1)
        new = [h for h, t in _wins().items() if h is not None and h not in before and t]
        if new:
            return new[0]
    return None


def run_benchmark(rivals: dict[str, Callable[[int], dict]]) -> list[dict[str, Any]]:
    """Run every rival on every target. Returns matrix rows."""
    rows: list[dict[str, Any]] = []
    for spec in TARGETS:
        hwnd = _launch_and_get_hwnd(spec)
        row: dict[str, Any] = {
            "app": spec["label"], "framework": spec["framework"], "hwnd": hwnd,
        }
        for name, fn in rivals.items():
            if hwnd is None:
                row[name] = None  # could not launch → not the rival's fault
                continue
            try:
                row[name] = fn(hwnd)
            except Exception as exc:
                row[name] = {"error": f"{type(exc).__name__}: {exc}"[:80]}
        rows.append(row)
        # teardown by image name where we launched a concrete exe
        if spec.get("path"):
            import subprocess
            img = spec["path"].rsplit("\\", 1)[-1]
            subprocess.run(["taskkill", "/IM", img, "/T", "/F"], capture_output=True)
    return rows


def _cell(entry: Any) -> str:
    """Render one rival result for the matrix (pure — the test pins this)."""
    if entry is None:
        return "blocked: needs env"
    if not isinstance(entry, dict):
        return str(entry)
    if "error" in entry:
        return f"error ({entry['error']})"
    n = entry.get("elements", 0)
    by = entry.get("by_technique")
    if by:
        extra = "+".join(f"{k}:{v}" for k, v in by.items() if k)
        return f"{n} ({extra})" if extra else str(n)
    return str(n)


def format_matrix(rows: list[dict[str, Any]], rivals: list[str]) -> str:
    """Render matrix rows as a Markdown table. Pure function (unit-tested)."""
    header = "| App | Framework | " + " | ".join(rivals) + " |"
    sep = "|" + "---|" * (len(rivals) + 2)
    lines = [header, sep]
    for r in rows:
        cells = [_cell(r.get(name)) for name in rivals]
        lines.append(f"| {r['app']} | {r['framework']} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    from benchmarks.competitive._env import prepare_comtypes_gen
    from benchmarks.competitive.rivals import RIVALS

    prepare_comtypes_gen()  # unblock pywinauto's comtypes gen cache
    rows = run_benchmark(RIVALS)
    table = format_matrix(rows, list(RIVALS.keys()))
    print("\n=== Competitive coverage matrix (element recognition) ===\n")
    print(table)


if __name__ == "__main__":
    main()
