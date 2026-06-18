#!/usr/bin/env python3
"""Bump version across all source files in one shot.

Updates:
  - naturo/version.py        (__version__)
  - core/src/version.cpp     (NATURO_VERSION)
  - pyproject.toml            (version)

Usage:
    python scripts/bump_version.py 0.3.0
    python scripts/bump_version.py --check   # verify all sources agree
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

FILES = {
    "naturo/version.py": {
        "pattern": r'(__version__\s*=\s*")[^"]+(")',
        "replace": r"\g<1>{version}\2",
    },
    "core/src/version.cpp": {
        "pattern": r'(NATURO_VERSION\s*=\s*")[^"]+(")',
        "replace": r"\g<1>{version}\2",
    },
    "pyproject.toml": {
        "pattern": r'^(version\s*=\s*")[^"]+(")',
        "replace": r"\g<1>{version}\2",
    },
    "packaging/mcpb/manifest.json": {
        # Matches the "version" line only, never "manifest_version".
        "pattern": r'^(\s*"version"\s*:\s*")[^"]+(")',
        "replace": r"\g<1>{version}\2",
    },
}

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def read_version(path: Path, pattern: str) -> str | None:
    """Extract current version from a file using the given regex."""
    text = path.read_text(encoding="utf-8")
    match = re.search(pattern, text, re.MULTILINE)
    if match:
        # The version is everything between the two captured groups
        full = match.group(0)
        prefix = match.group(1)
        suffix = match.group(2)
        return full[len(prefix) : -len(suffix)] if suffix else full[len(prefix) :]
    return None


def check_versions() -> int:
    """Verify all version sources agree. Returns 0 if consistent, 1 otherwise."""
    versions: dict[str, str | None] = {}
    for rel_path, spec in FILES.items():
        full_path = REPO_ROOT / rel_path
        if not full_path.exists():
            versions[rel_path] = None
            continue
        versions[rel_path] = read_version(full_path, spec["pattern"])

    found = {v for v in versions.values() if v is not None}

    print("Version check:")
    for rel_path, ver in versions.items():
        status = "✅" if ver and len(found) == 1 else "❌"
        print(f"  {status} {rel_path}: {ver or 'NOT FOUND'}")

    if len(found) == 1:
        print(f"\nAll sources consistent: {found.pop()}")
        return 0
    else:
        print(f"\n❌ Version mismatch detected: {found}")
        return 1


def bump(new_version: str) -> int:
    """Update all version sources to new_version."""
    if not VERSION_RE.match(new_version):
        print(f"Error: '{new_version}' is not a valid semver (expected X.Y.Z)")
        return 1

    print(f"Bumping version to {new_version}:\n")
    for rel_path, spec in FILES.items():
        full_path = REPO_ROOT / rel_path
        if not full_path.exists():
            print(f"  ⚠️  {rel_path}: file not found, skipping")
            continue

        text = full_path.read_text(encoding="utf-8")
        replacement = spec["replace"].format(version=new_version)
        new_text, count = re.subn(spec["pattern"], replacement, text, count=1, flags=re.MULTILINE)

        if count == 0:
            print(f"  ❌ {rel_path}: pattern not found — manual update needed")
            return 1

        full_path.write_text(new_text, encoding="utf-8")
        print(f"  ✅ {rel_path}: updated to {new_version}")

    print("\nDone. Run 'git diff' to verify, then commit.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump naturo version across all sources.")
    parser.add_argument("version", nargs="?", help="New version (X.Y.Z) or --check")
    parser.add_argument("--check", action="store_true", help="Verify all sources agree")
    args = parser.parse_args()

    if args.check or args.version == "--check":
        return check_versions()
    elif args.version:
        return bump(args.version)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
