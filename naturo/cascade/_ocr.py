"""Local OCR recognition provider (M2).

Reads text from a window screenshot with a local OCR engine
(``rapidocr_onnxruntime``) and emits each detected text run as an ``ocr``-tagged
**uncertain** :class:`ElementInfo`. Text baked into images/canvas is invisible
to accessibility APIs; OCR recovers it — but its bounds are estimated, so the
nodes are ``uncertain`` and the CLI warns (see ``docs/RECOGNITION_TREE.md``).

``rapidocr_onnxruntime`` is an optional dependency; if it is unavailable, or OCR
fails, the provider returns ``[]`` — it never raises into the cascade. The
engine is built once and cached (model load is the expensive part).
"""
from __future__ import annotations

import logging
from typing import List, Optional

from naturo.backends.base import ElementInfo

logger = logging.getLogger(__name__)

#: Drop OCR runs below this confidence (rapidocr scores are 0.0–1.0).
_MIN_OCR_SCORE = 0.5

_ocr_engine = None  # lazily constructed singleton


def _get_ocr_engine():
    """Return a cached RapidOCR engine, or ``None`` if unavailable."""
    global _ocr_engine
    if _ocr_engine is not None:
        return _ocr_engine
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception as exc:  # pragma: no cover - optional dep guard
        logger.debug("OCR: rapidocr_onnxruntime unavailable: %s", exc)
        return None
    try:
        _ocr_engine = RapidOCR()
    except Exception as exc:  # pragma: no cover - init guard
        logger.debug("OCR: engine init failed: %s", exc)
        return None
    return _ocr_engine


def _run_ocr(engine, screenshot_path: str):
    """Run the engine and return its raw ``[[box, text, score], ...]`` (or [])."""
    result, _elapse = engine(screenshot_path)
    return result or []


def fetch_ocr_elements(
    screenshot_path: str,
    window_bounds: Optional[tuple],
    *,
    min_score: float = _MIN_OCR_SCORE,
) -> List[ElementInfo]:
    """OCR a window screenshot into ``ocr``-tagged (uncertain) text elements.

    Args:
        screenshot_path: Path to the window screenshot (physical pixels).
        window_bounds: ``(x, y, w, h)`` of the captured window; OCR box coords
            are relative to the screenshot, so ``(x, y)`` is added to reach
            screen coordinates (mirroring the AI-vision provider).
        min_score: Minimum OCR confidence to keep a text run.

    Returns:
        A flat list of text :class:`ElementInfo` (``source="ocr"``,
        ``confidence`` = OCR score). Empty on any failure.
    """
    engine = _get_ocr_engine()
    if engine is None or not screenshot_path:
        return []
    try:
        raw = _run_ocr(engine, screenshot_path)
    except Exception as exc:
        logger.debug("OCR: run failed on '%s': %s", screenshot_path, exc)
        return []

    win_x = int(window_bounds[0]) if window_bounds else 0
    win_y = int(window_bounds[1]) if window_bounds else 0

    elements: List[ElementInfo] = []
    for i, item in enumerate(raw):
        try:
            box, text, score = item[0], item[1], item[2]
        except (TypeError, IndexError, ValueError):
            continue
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            continue
        if not text or score_f < min_score:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x0 = int(min(xs)) + win_x
        y0 = int(min(ys)) + win_y
        w = int(max(xs) - min(xs))
        h = int(max(ys) - min(ys))
        if w <= 0 or h <= 0:
            continue
        elements.append(ElementInfo(
            id=f"ocr_{i}",
            role="Text",
            name=str(text),
            value=str(text),
            x=x0, y=y0, width=w, height=h,
            children=[],
            properties={"source": "ocr", "confidence": score_f},
        ))
    return elements
