"""Unit tests for scripts/generate_release_notes.py (#419).

Pure parse/render logic — no git, no network. Runs on every CI lane.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_release_notes.py"
_spec = importlib.util.spec_from_file_location("generate_release_notes", _SCRIPT)
assert _spec and _spec.loader
grn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grn)


_SAMPLE = [
    "aaaaaaa1 feat(cli): add --field selection",
    "aaaaaaa2 fix(quit): verify by window-ownership before success",
    "aaaaaaa3 docs: populate SUPPORTED_APPS.md",
    "aaaaaaa4 test(type): pin ladder rungs",
    "aaaaaaa5 ci: bump action-gh-release",
    "aaaaaaa6 deps: update mcp",
    "aaaaaaa7 refactor!: rename BrowserPage.screenshot arg",  # breaking
    "aaaaaaa8 orc: daily review [skip ci]",                    # skipped (orc)
    "aaaaaaa9 chore: tidy [skip ci]",                          # skipped ([skip ci])
    "aaaaaab0 wip messy commit not conventional",             # skipped (unparseable)
    "aaaaaab1 wibble(x): novel type",                          # -> Other
]


def _parsed():
    return grn.parse_commits(_SAMPLE)


def test_types_bucket_into_known_sections():
    sections, other, _ = _parsed()
    assert [e["desc"] for e in sections["feat"]] == ["add --field selection"]
    assert sections["fix"][0]["scope"] == "quit"
    assert sections["docs"] and sections["test"] and sections["ci"] and sections["deps"]
    assert sections["refactor"][0]["desc"].startswith("rename BrowserPage")


def test_breaking_marker_collected():
    _, _, breaking = _parsed()
    assert len(breaking) == 1
    assert breaking[0]["breaking"] is True
    assert breaking[0]["desc"].startswith("rename BrowserPage")


def test_orc_and_skip_ci_and_unparseable_are_dropped():
    sections, other, _ = _parsed()
    all_descs = [e["desc"] for lst in sections.values() for e in lst] + [
        e["desc"] for e in other
    ]
    assert not any("daily review" in d for d in all_descs)      # orc: dropped
    assert not any("tidy" in d for d in all_descs)              # [skip ci] dropped
    assert not any("messy commit" in d for d in all_descs)     # unparseable dropped


def test_unknown_type_goes_to_other():
    _, other, _ = _parsed()
    assert len(other) == 1 and other[0]["desc"] == "novel type"


def test_short_sha_truncated_to_8():
    sections, _, _ = _parsed()
    assert all(len(e["sha"]) <= 8 for e in sections["feat"])


def test_render_orders_sections_and_marks_breaking():
    sections, other, breaking = _parsed()
    md = grn.render(sections, other, breaking, version="v9.9.9")
    assert md.startswith("# v9.9.9")
    assert "## ⚠️ Breaking Changes" in md
    # Features must render before Bug Fixes (section order)
    assert md.index("🚀 Features") < md.index("🐛 Bug Fixes")
    # scope is bolded
    assert "**cli**: add --field selection" in md
    # empty sections are omitted (no perf commits in the sample)
    assert "Performance" not in md


def test_empty_input_renders_cleanly():
    sections, other, breaking = grn.parse_commits([])
    md = grn.render(sections, other, breaking)
    assert md.strip() == ""
