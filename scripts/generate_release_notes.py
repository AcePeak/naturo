#!/usr/bin/env python3
"""Generate categorized release notes from conventional-commit history (#419).

Release notes were written by hand. Since the repo already uses conventional
commits (``feat:``, ``fix:``, ``docs:`` …), this script derives categorized,
Markdown release notes from the git log — no manual curation.

Usage::

    python scripts/generate_release_notes.py                 # <last tag>..HEAD
    python scripts/generate_release_notes.py --range v0.3.1..v0.3.2
    python scripts/generate_release_notes.py --version v0.3.3 > notes.md

The parsing logic (:func:`parse_commits` / :func:`render`) is pure and unit
-tested; only :func:`main` shells out to git. Complements ``.github/release.yml``
(GitHub's native label-based categories) — this one keys off the commit *type*,
so it works even when a change never went through a labeled PR.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import OrderedDict
from typing import Iterable, Optional

# Conventional-commit type -> section heading, in the order they should render.
_SECTIONS: "OrderedDict[str, str]" = OrderedDict(
    [
        ("feat", "🚀 Features"),
        ("fix", "🐛 Bug Fixes"),
        ("perf", "⚡ Performance"),
        ("refactor", "♻️ Refactoring"),
        ("docs", "📝 Documentation"),
        ("test", "✅ Tests"),
        ("build", "📦 Build"),
        ("ci", "🔧 CI"),
        ("deps", "⬆️ Dependencies"),
        ("chore", "🧹 Chores"),
    ]
)

# Commit types dropped entirely from release notes (internal bookkeeping).
_SKIP_TYPES = {"orc"}
_SKIP_RE = re.compile(r"\[skip ci\]", re.IGNORECASE)

_COMMIT_RE = re.compile(
    r"^(?P<type>\w+)(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?:\s*(?P<desc>.+)$"
)


def parse_commits(lines: Iterable[str]) -> tuple[dict, list, list]:
    """Bucket ``"<sha> <subject>"`` lines by conventional-commit type.

    Returns ``(sections, other, breaking)`` where ``sections`` maps each known
    type to its list of entries (in :data:`_SECTIONS` order), ``other`` holds
    parsed-but-unknown types, and ``breaking`` holds any ``type!:`` entries.
    Merge/skip/``orc:``/``[skip ci]`` and unparseable lines are dropped.
    """
    sections: "OrderedDict[str, list]" = OrderedDict((t, []) for t in _SECTIONS)
    other: list = []
    breaking: list = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        sha, _, subject = raw.partition(" ")
        if _SKIP_RE.search(subject):
            continue
        m = _COMMIT_RE.match(subject)
        if not m:
            continue
        ctype = m.group("type").lower()
        if ctype in _SKIP_TYPES:
            continue
        entry = {
            "sha": sha[:8],
            "scope": m.group("scope"),
            "desc": m.group("desc").strip(),
            "breaking": bool(m.group("breaking")),
        }
        if entry["breaking"]:
            breaking.append(entry)
        if ctype in sections:
            sections[ctype].append(entry)
        else:
            other.append(entry)
    return sections, other, breaking


def _line(entry: dict) -> str:
    scope = f"**{entry['scope']}**: " if entry.get("scope") else ""
    return f"- {scope}{entry['desc']} ({entry['sha']})"


def render(
    sections: dict, other: list, breaking: list, version: Optional[str] = None
) -> str:
    """Render buckets to Markdown release notes."""
    out: list = []
    if version:
        out.append(f"# {version}\n")
    if breaking:
        out.append("## ⚠️ Breaking Changes\n")
        out.extend(_line(e) for e in breaking)
        out.append("")
    for ctype, heading in _SECTIONS.items():
        entries = sections.get(ctype) or []
        if entries:
            out.append(f"## {heading}\n")
            out.extend(_line(e) for e in entries)
            out.append("")
    if other:
        out.append("## Other\n")
        out.extend(_line(e) for e in other)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _git_log(rng: str) -> list:
    result = subprocess.run(
        ["git", "log", "--no-merges", "--pretty=%h %s", rng],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.splitlines()


def _last_tag() -> Optional[str]:
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip() or None


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Generate release notes from conventional commits (#419)."
    )
    ap.add_argument("--range", dest="rng", help="git range (default: <last tag>..HEAD)")
    ap.add_argument("--version", help="version heading to prepend")
    args = ap.parse_args(argv)

    rng = args.rng
    if not rng:
        tag = _last_tag()
        rng = f"{tag}..HEAD" if tag else "HEAD"
    sections, other, breaking = parse_commits(_git_log(rng))
    sys.stdout.write(render(sections, other, breaking, args.version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
