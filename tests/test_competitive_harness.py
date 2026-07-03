"""Tests for the competitive benchmark matrix logic (Linux-collectable — the
pure formatting functions need no desktop, no naturo backend, no rivals)."""
from __future__ import annotations

from benchmarks.competitive.run import _cell, format_matrix


def test_cell_naturo_shows_per_technique_breakdown():
    got = _cell({"elements": 38, "by_technique": {"uia": 7, "jab": 31}})
    assert got == "38 (uia:7+jab:31)"


def test_cell_plain_count():
    assert _cell({"elements": 6}) == "6"


def test_cell_zero_for_pixel_tool():
    assert _cell({"elements": 0, "note": "no element model (pixels only)"}) == "0"


def test_cell_blocked_when_none():
    assert _cell(None) == "blocked: needs env"


def test_cell_error_is_labelled():
    assert _cell({"error": "ImportError: boom"}) == "error (ImportError: boom)"


def test_format_matrix_headers_and_moat_row():
    rows = [
        {
            "app": "jconsole", "framework": "Java/Swing (JAB)",
            "naturo": {"elements": 38, "by_technique": {"uia": 7, "jab": 31}},
            "pywinauto": {"elements": 6},
            "pyautogui": {"elements": 0},
        },
    ]
    table = format_matrix(rows, ["naturo", "pywinauto", "pyautogui"])
    assert "| App | Framework | naturo | pywinauto | pyautogui |" in table
    # the moat: naturo sees the Swing controls (jab:31); pywinauto sees only chrome
    assert "38 (uia:7+jab:31)" in table
    assert "| jconsole | Java/Swing (JAB) | 38 (uia:7+jab:31) | 6 | 0 |" in table
