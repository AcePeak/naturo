#!/usr/bin/env python3
"""Download the latest naturo_core.dll from CI artifacts.

Usage:
    python scripts/sync_dll.py

This downloads the DLL built by the latest successful CI run on main
and places it into naturo/bin/ where the bridge module expects it.

Requires: gh CLI authenticated.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    """Download the latest CI-built DLL artifact to naturo/bin/."""
    repo_root = Path(__file__).resolve().parent.parent
    target_dir = repo_root / "naturo" / "bin"
    target_dir.mkdir(parents=True, exist_ok=True)

    print("Fetching latest successful CI run on main...")
    result = subprocess.run(
        [
            "gh", "run", "list",
            "--branch", "main",
            "--status", "success",
            "--limit", "1",
            "--json", "databaseId",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    if result.returncode != 0:
        print(f"Error listing runs: {result.stderr}", file=sys.stderr)
        return 1

    import json
    runs = json.loads(result.stdout)
    if not runs:
        print("No successful CI runs found on main.", file=sys.stderr)
        return 1

    run_id = runs[0]["databaseId"]
    print(f"Downloading DLL from run {run_id}...")

    with tempfile.TemporaryDirectory() as tmpdir:
        dl_result = subprocess.run(
            [
                "gh", "run", "download", str(run_id),
                "--name", "naturo-core-dll",
                "--dir", tmpdir,
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        if dl_result.returncode != 0:
            print(f"Error downloading artifact: {dl_result.stderr}", file=sys.stderr)
            return 1

        # The artifact contains bin/Release/naturo_core.dll
        dll_src = Path(tmpdir) / "bin" / "Release" / "naturo_core.dll"
        if not dll_src.exists():
            # Try flat layout
            dll_src = Path(tmpdir) / "naturo_core.dll"

        if not dll_src.exists():
            print(f"DLL not found in artifact. Contents: {list(Path(tmpdir).rglob('*'))}", file=sys.stderr)
            return 1

        dll_dst = target_dir / "naturo_core.dll"
        shutil.copy2(str(dll_src), str(dll_dst))
        print(f"✅ DLL copied to {dll_dst}")

        # Verify version
        try:
            import ctypes
            dll = ctypes.CDLL(str(dll_dst))
            dll.naturo_version.restype = ctypes.c_char_p
            dll_ver = dll.naturo_version().decode()

            from naturo.version import __version__
            print(f"   DLL version:    {dll_ver}")
            print(f"   Python version: {__version__}")
            if dll_ver != __version__:
                print(f"⚠️  Version mismatch! DLL={dll_ver} Python={__version__}", file=sys.stderr)
                return 1
            print("✅ Versions match!")
        except Exception as exc:
            print(f"⚠️  Could not verify version: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
