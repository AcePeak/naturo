"""Tests for the recognition-coverage benchmark harness (issue #931).

The pure-logic parts (result math, provider counting, table formatting) are
tested without a desktop session.  The live measurement against a real
Chromium window is exercised by a single ``@pytest.mark.desktop`` test that
launches the bundled fixture and asserts a positive CDP delta — proving the
multi-framework advantage on real UI.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from benchmarks.recognition.harness import (
    ChromiumFixtureApp,
    CoverageResult,
    _provider_counts,
)
from benchmarks.recognition import run_benchmark


def _stat(name: str, elements: int, status: str = "ok") -> SimpleNamespace:
    """Build a minimal provider-stat stand-in for ``_provider_counts``."""
    return SimpleNamespace(name=name, elements=elements, status=status)


def test_delta_is_cascade_minus_uia() -> None:
    """``CoverageResult.delta`` reflects extra elements over the UIA baseline."""
    result = CoverageResult(
        app="x",
        framework="Electron/CDP",
        uia_only_count=50,
        cascade_count=84,
        extra_sources={"cdp": 34},
    )
    assert result.delta == 34


def test_to_dict_round_trips_core_fields() -> None:
    """``to_dict`` exposes the computed delta and the provider breakdown."""
    result = CoverageResult(
        app="App",
        framework="Electron/CDP",
        uia_only_count=10,
        cascade_count=25,
        extra_sources={"cdp": 15},
        sample_extra_names=["Send", "Discard"],
        notes="note",
    )
    payload = result.to_dict()
    assert payload["delta"] == 15
    assert payload["extra_sources"] == {"cdp": 15}
    assert payload["sample_extra_names"] == ["Send", "Discard"]
    assert payload["uia_only_count"] == 10
    assert payload["cascade_count"] == 25


def test_provider_counts_skips_failed_and_empty_providers() -> None:
    """Only ``status == "ok"`` providers with elements are counted."""
    stats = SimpleNamespace(providers=[
        _stat("uia", 40),
        _stat("cdp", 34),
        _stat("vision", 0, status="skipped"),
        _stat("jab", 5, status="error"),
    ])
    counts = _provider_counts(stats)
    assert counts == {"uia": 40, "cdp": 34}


def test_format_markdown_has_table_header_and_row() -> None:
    """The Markdown formatter renders a header and one row per result."""
    results = [
        CoverageResult(
            app="Chrome",
            framework="Electron/CDP",
            uia_only_count=52,
            cascade_count=86,
            extra_sources={"cdp": 34},
        )
    ]
    markdown = run_benchmark.format_markdown(results, gaps=["SAP: future"])
    assert "| App | Framework | UIA-only | Cascade | Delta | Extra via |" in markdown
    assert "Chrome" in markdown
    assert "**+34**" in markdown
    assert "cdp (+34)" in markdown
    assert "SAP: future" in markdown


def test_format_human_lists_gaps_without_fabrication() -> None:
    """The human formatter surfaces documented gaps verbatim."""
    text = run_benchmark.format_human(results=[], gaps=["DBeaver: not running"])
    assert "Documented gaps" in text
    assert "DBeaver: not running" in text


def test_main_returns_failure_when_no_positive_delta(monkeypatch) -> None:
    """The runner exits non-zero when nothing beats the UIA baseline."""
    flat = CoverageResult(
        app="Flat",
        framework="UIA",
        uia_only_count=10,
        cascade_count=10,
    )
    monkeypatch.setattr(
        run_benchmark, "collect_results", lambda: ([flat], ["gap"])
    )
    assert run_benchmark.main([]) == 1


def test_main_returns_success_with_positive_delta(monkeypatch, capsys) -> None:
    """The runner exits zero and prints JSON when a delta is measured."""
    winner = CoverageResult(
        app="Win",
        framework="Electron/CDP",
        uia_only_count=10,
        cascade_count=25,
        extra_sources={"cdp": 15},
    )
    monkeypatch.setattr(
        run_benchmark, "collect_results", lambda: ([winner], [])
    )
    assert run_benchmark.main(["--json"]) == 0
    out = capsys.readouterr().out
    assert '"delta": 15' in out


@pytest.mark.desktop
def test_chromium_fixture_shows_cdp_delta() -> None:
    """Live proof: the cascade recognizes Chromium web content UIA cannot see.

    Launches the bundled HTML fixture in a controlled Chrome/Edge instance and
    asserts that the full cascade recognizes meaningfully more elements than
    the UIA-only baseline, with the extra elements coming from the CDP
    provider.
    """
    fixture = ChromiumFixtureApp()
    if not fixture.available:
        pytest.skip("No Chrome/Edge browser available for the CDP fixture.")
    try:
        from naturo.cdp import CDPClient  # noqa: F401
    except Exception:
        pytest.skip("websocket-client (naturo[cdp]) not installed.")

    with fixture:
        result = fixture.measure()

    assert result.cascade_count > result.uia_only_count
    assert result.extra_sources.get("cdp", 0) >= 20, (
        "Expected the CDP provider to recognize the fixture's web content "
        f"that UIA cannot see; got {result.extra_sources}."
    )
