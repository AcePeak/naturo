"""Correctness tagging & fusion for the Unified Auto Element Tree.

Schema of record: ``docs/RECOGNITION_TREE.md``.

Every node in a fused cascade tree is tagged with:

* ``techniques`` — every recognition technique that saw the node,
  deterministic-first (the first entry is the *preferred* technique used for
  actions/reads and the legacy ``source`` field).
* ``correctness`` — ``"deterministic"`` if any technique is deterministic, else
  ``"uncertain"``.
* ``confidence`` — float in ``[0.0, 1.0]``; ``1.0`` for deterministic techniques,
  the model/match score for uncertain ones, ``max`` across a fused node.

This module is pure Python (no platform imports) so the fusion, tagging, and
AI-warning logic is unit-testable on any OS.
"""
from __future__ import annotations

from typing import Optional

from naturo.backends.base import ElementInfo

#: Techniques whose hits are structured and reproducible (guaranteed).
DETERMINISTIC_TECHNIQUES = ("uia", "msaa", "ia2", "jab", "cdp", "com")
#: Techniques whose hits are estimated (image match / AI vision).
UNCERTAIN_TECHNIQUES = ("image", "vision", "ai")

#: Canonical ordering: deterministic first (cascade order), then uncertain.
_TECHNIQUE_ORDER = [
    "uia", "msaa", "ia2", "jab", "cdp", "com",  # deterministic
    "image", "vision", "ai",                    # uncertain
]

DETERMINISTIC = "deterministic"
UNCERTAIN = "uncertain"

#: Default confidence for an uncertain hit that reports no score.
_DEFAULT_UNCERTAIN_CONFIDENCE = 0.5


def technique_class(technique: str) -> str:
    """Return the correctness class of a single technique.

    Unknown techniques are treated as ``uncertain`` — a fail-safe: naturo never
    claims correctness it cannot justify.
    """
    return DETERMINISTIC if technique in DETERMINISTIC_TECHNIQUES else UNCERTAIN


def _order_key(technique: str) -> int:
    try:
        return _TECHNIQUE_ORDER.index(technique)
    except ValueError:
        return len(_TECHNIQUE_ORDER)


def node_techniques(props: dict) -> list[str]:
    """Collect every technique that recognized a node, deterministic-first.

    Reads, in order of authority, ``properties``:

    * ``source`` — the primary technique that produced the node.
    * ``corroborated_by`` — techniques whose duplicate hit was fused into this
      node during merge (§4 of the ADR).
    * ``techniques`` — an explicit pre-set list (e.g. from an adapter).

    Duplicates are removed and the result is sorted deterministic-first.
    """
    collected: list[str] = []
    source = props.get("source")
    if source:
        collected.append(source)
    for extra in props.get("corroborated_by") or []:
        collected.append(extra)
    for extra in props.get("techniques") or []:
        collected.append(extra)
    # Stable de-dup, then deterministic-first ordering.
    deduped = list(dict.fromkeys(collected))
    return sorted(deduped, key=_order_key)


def node_correctness(techniques: list[str]) -> str:
    """A node is deterministic if *any* of its techniques is deterministic."""
    if any(technique_class(t) == DETERMINISTIC for t in techniques):
        return DETERMINISTIC
    return UNCERTAIN


def node_confidence(props: dict, techniques: list[str]) -> float:
    """Max confidence across a node's techniques (deterministic ⇒ 1.0)."""
    best = 0.0
    for t in techniques:
        if technique_class(t) == DETERMINISTIC:
            best = max(best, 1.0)
        else:
            raw = props.get("confidence")
            try:
                score = float(raw) if raw is not None else _DEFAULT_UNCERTAIN_CONFIDENCE
            except (TypeError, ValueError):
                score = _DEFAULT_UNCERTAIN_CONFIDENCE
            best = max(best, score)
    return best


def annotate(props: dict) -> Optional[dict]:
    """Return the fusion tags for a node, or ``None`` if it carries no technique.

    ``None`` means the node was not produced by the cascade (e.g. a plain
    ``get_element_tree`` walk); callers leave such nodes untagged so non-cascade
    output is unchanged and never falsely warned as uncertain.
    """
    techniques = node_techniques(props)
    if not techniques:
        return None
    return {
        "techniques": techniques,
        "correctness": node_correctness(techniques),
        "confidence": round(node_confidence(props, techniques), 3),
        "preferred": techniques[0],
    }


def recognition_summary(root: ElementInfo) -> dict:
    """Aggregate technique/correctness counts over a fused tree.

    Nodes with no technique tag (non-cascade nodes) are ignored so the summary
    reflects only what the cascade actually recognized.
    """
    from naturo.cascade._coverage import _flatten

    by_technique: dict[str, int] = {}
    total = 0
    uncertain = 0
    for el in _flatten(root):
        props = getattr(el, "properties", {}) or {}
        techniques = node_techniques(props)
        if not techniques:
            continue
        total += 1
        for t in techniques:
            by_technique[t] = by_technique.get(t, 0) + 1
        if node_correctness(techniques) == UNCERTAIN:
            uncertain += 1
    return {
        "total_nodes": total,
        "by_technique": by_technique,
        "uncertain_nodes": uncertain,
        "has_uncertain": uncertain > 0,
    }


def uncertain_warning(summary: dict) -> Optional[str]:
    """Human-readable warning when a tree contains AI/image-only nodes.

    Returns ``None`` when every recognized node is deterministic.
    """
    n = summary.get("uncertain_nodes", 0)
    if n <= 0:
        return None
    return (
        f"warning: {n} element(s) were recognized only by AI/image "
        "(uncertain); their bounds are estimated and may shift. Deterministic "
        "sources are preferred for actions."
    )
