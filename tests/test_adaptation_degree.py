"""Adaptation-degree classification for the software-adaptation table (M2).

Linux-collectable: pure logic over synthetic harness results / summaries.
See docs/design/software-adaptation-degree.md (schema + scoring).
"""
from __future__ import annotations

from benchmarks.recognition.harness import (
    CoverageResult,
    adaptation_degree,
    _degree_fields_from_summary,
)


def _result(uia, cascade, techniques):
    return CoverageResult(
        app="App", framework="f",
        uia_only_count=uia, cascade_count=cascade,
        techniques=list(techniques),
    )


# ── adaptation_degree (§2 of the ADR) ─────────────────────────────────────

def test_degree_full_when_deterministic_non_uia_adds_elements():
    # cdp is deterministic + non-UIA + positive delta -> the moat case.
    assert adaptation_degree(_result(20, 34, ["uia", "cdp"])) == "full"


def test_degree_uia_only_when_only_uia():
    assert adaptation_degree(_result(20, 20, ["uia"])) == "uia-only"


def test_degree_uncertain_only_when_non_uia_is_ai_or_image():
    # vision adds elements but it is uncertain, not deterministic.
    assert adaptation_degree(_result(20, 26, ["uia", "vision"])) == "uncertain-only"


def test_degree_uia_only_when_non_uia_framework_adds_no_net_elements():
    # cdp fired but delta == 0 (all corroborating) -> no measured advantage.
    assert adaptation_degree(_result(20, 20, ["uia", "cdp"])) == "uia-only"


def test_degree_full_prefers_deterministic_over_present_uncertain():
    # Both a deterministic non-UIA (jab) and an uncertain (vision) fired,
    # with a positive delta -> deterministic wins the classification.
    assert adaptation_degree(_result(10, 30, ["uia", "jab", "vision"])) == "full"


# ── _degree_fields_from_summary (derives table fields from M1 summary) ─────

def test_degree_fields_orders_deterministic_first_and_counts_correctness():
    summary = {
        "total_nodes": 13,
        "by_technique": {"vision": 2, "uia": 8, "cdp": 3},
        "uncertain_nodes": 2,
        "has_uncertain": True,
    }
    techniques, counts = _degree_fields_from_summary(summary)
    # deterministic (cdp, uia) before uncertain (vision)
    assert techniques == ["cdp", "uia", "vision"]
    assert counts == {"deterministic": 11, "uncertain": 2}


def test_degree_fields_empty_summary():
    techniques, counts = _degree_fields_from_summary(
        {"total_nodes": 0, "by_technique": {}, "uncertain_nodes": 0}
    )
    assert techniques == []
    assert counts == {"deterministic": 0, "uncertain": 0}


# ── CoverageResult serialization carries the new fields ────────────────────

def test_coverage_result_to_dict_carries_new_fields():
    r = CoverageResult(
        app="App", framework="Electron/CDP",
        uia_only_count=20, cascade_count=34,
        techniques=["uia", "cdp"],
        correctness_counts={"deterministic": 34, "uncertain": 0},
    )
    d = r.to_dict()
    assert d["techniques"] == ["uia", "cdp"]
    assert d["correctness_counts"] == {"deterministic": 34, "uncertain": 0}
    assert d["degree"] == "full"
    # existing fields still present
    assert d["delta"] == 14
