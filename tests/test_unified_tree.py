"""Unified Auto Element Tree — fusion, correctness tagging, AI-warning (M1).

Schema of record: ``docs/RECOGNITION_TREE.md``.

These tests are **Linux-collectable**: the module top imports only pure helpers
(no Windows-only backend). CLI end-to-end imports live inside their test bodies
and the backend/platform guard are monkeypatched, so the fused ``see --json``
contract is exercised on any OS.
"""
from __future__ import annotations

import json

from naturo.backends.base import ElementInfo
from naturo.cascade import _correctness as C
from naturo.cascade._merge import _merge_ai_into_tree, _record_corroboration


def _el(role="Button", name="", source=None, x=0, y=0, w=10, h=10,
        confidence=None, children=None):
    props: dict = {}
    if source is not None:
        props["source"] = source
    if confidence is not None:
        props["confidence"] = confidence
    return ElementInfo(
        id=f"{role}-{name}", role=role, name=name, value=None,
        x=x, y=y, width=w, height=h,
        children=children or [], properties=props,
    )


# ── technique classification ──────────────────────────────────────────────

def test_deterministic_techniques_classified():
    for t in ("uia", "msaa", "ia2", "jab", "cdp", "com"):
        assert C.technique_class(t) == C.DETERMINISTIC


def test_uncertain_techniques_classified():
    for t in ("image", "vision", "ai"):
        assert C.technique_class(t) == C.UNCERTAIN


def test_unknown_technique_is_uncertain_failsafe():
    # naturo never claims correctness it cannot justify.
    assert C.technique_class("mystery-adapter") == C.UNCERTAIN


# ── node techniques / correctness / confidence ────────────────────────────

def test_node_techniques_deterministic_first_and_deduped():
    props = {"source": "vision", "corroborated_by": ["uia", "uia"],
             "techniques": ["cdp"]}
    # deterministic (uia, cdp in cascade order) before uncertain (vision)
    assert C.node_techniques(props) == ["uia", "cdp", "vision"]


def test_node_correctness_prefers_deterministic():
    assert C.node_correctness(["uia", "vision"]) == C.DETERMINISTIC
    assert C.node_correctness(["vision"]) == C.UNCERTAIN
    assert C.node_correctness([]) == C.UNCERTAIN


def test_node_confidence_rules():
    assert C.node_confidence({}, ["uia"]) == 1.0
    # vision default when no score reported
    assert C.node_confidence({}, ["vision"]) == 0.5
    # explicit vision score honored
    assert C.node_confidence({"confidence": 0.8}, ["vision"]) == 0.8
    # fused node: deterministic dominates
    assert C.node_confidence({"confidence": 0.8}, ["uia", "vision"]) == 1.0


def test_node_confidence_clamped_to_unit_range():
    # ADR §3.1: confidence is [0.0, 1.0]. A vision model's score is untrusted
    # (passed through from provider JSON) and must never leak out of range.
    assert C.node_confidence({"confidence": 95}, ["vision"]) == 1.0
    assert C.node_confidence({"confidence": -0.3}, ["vision"]) == 0.0
    fusion = C.annotate({"source": "vision", "confidence": 1.5})
    assert fusion["confidence"] == 1.0


def test_annotate_tagged_node():
    fusion = C.annotate({"source": "uia"})
    assert fusion == {
        "techniques": ["uia"],
        "correctness": "deterministic",
        "confidence": 1.0,
        "preferred": "uia",
    }


def test_annotate_untagged_node_returns_none():
    # A plain (non-cascade) node carries no technique — must stay untagged so
    # non-cascade output is never falsely flagged as uncertain.
    assert C.annotate({}) is None


def test_annotate_vision_only_is_uncertain():
    fusion = C.annotate({"source": "vision", "confidence": 0.6})
    assert fusion["correctness"] == "uncertain"
    assert fusion["preferred"] == "vision"
    assert fusion["confidence"] == 0.6


# ── recognition summary + warning ─────────────────────────────────────────

def test_recognition_summary_counts_and_uncertain():
    root = _el("Window", "App", source="uia", w=200, h=200, children=[
        _el("Button", "Save", source="uia", x=0, y=0, w=100, h=50),
        _el("Icon", "Avatar", source="vision", x=120, y=0, w=40, h=40,
            confidence=0.6),
    ])
    summary = C.recognition_summary(root)
    assert summary["total_nodes"] == 3
    assert summary["by_technique"] == {"uia": 2, "vision": 1}
    assert summary["uncertain_nodes"] == 1
    assert summary["has_uncertain"] is True


def test_recognition_summary_ignores_untagged_tree():
    # Non-cascade tree (no source tags) → empty summary, no warning.
    root = _el("Window", "App", w=200, h=200, children=[_el("Button", "Ok")])
    summary = C.recognition_summary(root)
    assert summary["total_nodes"] == 0
    assert summary["has_uncertain"] is False
    assert C.uncertain_warning(summary) is None


def test_uncertain_warning_present_when_ai_only_nodes():
    warning = C.uncertain_warning({"uncertain_nodes": 2, "has_uncertain": True})
    assert warning is not None
    assert "uncertain" in warning.lower()
    assert "2" in warning


# ── fusion: same element seen by several techniques → mark all ─────────────

def test_merge_records_corroboration_prefers_deterministic():
    button = _el("Button", "Save", source="uia", x=0, y=0, w=100, h=50)
    root = _el("Window", "App", source="uia", w=200, h=200, children=[button])
    # An AI vision hit overlapping the same button (IoU well above threshold).
    ai = _el("Button", "Save", source="vision", x=5, y=5, w=90, h=40,
             confidence=0.7)

    added, added_count, skipped = _merge_ai_into_tree(root, [ai])

    # The duplicate AI element is not added as a new node...
    assert added_count == 0
    assert skipped == 1
    # ...but the deterministic node now records the corroborating technique.
    assert button.properties.get("corroborated_by") == ["vision"]

    fusion = C.annotate(button.properties)
    assert fusion["techniques"] == ["uia", "vision"]   # deterministic first
    assert fusion["correctness"] == "deterministic"
    assert fusion["preferred"] == "uia"                # deterministic preferred
    assert fusion["confidence"] == 1.0


def test_merge_keeps_ai_only_novel_node_as_uncertain():
    root = _el("Window", "App", source="uia", w=400, h=400, children=[
        _el("Button", "Save", source="uia", x=0, y=0, w=50, h=20),
    ])
    # An AI hit in an empty region — no deterministic node covers it.
    ai = _el("Icon", "Avatar", source="vision", x=300, y=300, w=30, h=30,
             confidence=0.4)

    added, added_count, skipped = _merge_ai_into_tree(root, [ai])
    assert added_count == 1
    novel = added[0]
    fusion = C.annotate(novel.properties)
    assert fusion["correctness"] == "uncertain"
    assert fusion["preferred"] == "vision"


def test_record_corroboration_dedupes_technique():
    node = _el("Button", "Save", source="uia")
    ai = _el("Button", "Save", source="vision")
    _record_corroboration(node, ai)
    _record_corroboration(node, ai)
    assert node.properties["corroborated_by"] == ["vision"]


# ── CLI contract: `naturo see --cascade --json` (criterion 2) ──────────────

def test_see_json_emits_fused_correctness_tree(monkeypatch):
    from click.testing import CliRunner
    import naturo.cli.core._common as common
    import naturo.cascade as cascade_pkg
    from naturo.cli.core._see import see
    from naturo.cascade._types import CascadeResult, CascadeStats

    root = _el("Window", "App", source="uia", w=200, h=200, children=[
        _el("Button", "Save", source="uia", x=0, y=0, w=100, h=50),
        _el("Icon", "Avatar", source="vision", x=120, y=0, w=40, h=40,
            confidence=0.6),
    ])
    result = CascadeResult(tree=root, stats=CascadeStats(),
                           primary_provider="uia")

    monkeypatch.setattr(common, "_platform_supports_gui", lambda: True)

    class FakeBackend:
        def _resolve_hwnd(self, **kw):
            return 123

        def capture_window(self, **kw):
            raise RuntimeError("no gui in CI")

        def capture_screen(self, **kw):
            raise RuntimeError("no gui in CI")

        def get_dpi_scale(self, i):
            return 1.0

        def list_monitors(self):
            return []

    monkeypatch.setattr(common, "_get_backend", lambda jo: FakeBackend())
    monkeypatch.setattr(cascade_pkg, "run_cascade", lambda *a, **k: result)

    try:
        # click <8.2 mixes stderr into stdout unless disabled; >=8.2 always
        # separates them and dropped the kwarg.
        runner = CliRunner(mix_stderr=False)
    except TypeError:
        runner = CliRunner()
    res = runner.invoke(
        see, ["--app", "x", "--cascade", "--json", "--no-snapshot"],
    )
    assert res.exit_code == 0, (res.output, res.exception)

    data = json.loads(res.stdout)
    # Every fused node carries techniques[] + correctness.
    assert data["techniques"] == ["uia"]
    assert data["correctness"] == "deterministic"
    child_techs = {tuple(c["techniques"]) for c in data["children"]}
    assert ("uia",) in child_techs and ("vision",) in child_techs
    # Structured summary present and flags the AI-only node.
    assert data["recognition_summary"]["has_uncertain"] is True
    assert data["recognition_summary"]["uncertain_nodes"] == 1
    # Warning goes to stderr (keeps --json stdout pure).
    assert "uncertain" in res.stderr.lower()
    # stdout is a single valid JSON document (purity).
    assert res.stdout.strip().startswith("{")
