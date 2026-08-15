"""OCR-based on-screen text finding for ``naturo find --ocr`` (#1060, part of #809).

This is the engine behind ``naturo find --ocr "text"``. It runs optical character
recognition over a window/screen/screenshot image and returns the bounding boxes
of every recognised text region whose content matches the query — letting naturo
target Canvas / game / Flash / custom-drawn controls that expose nothing to the
accessibility tree (UIA / MSAA / IA2 / JAB / CDP).

Engine
------
The OCR backend is **RapidOCR** (``rapidocr-onnxruntime``), installed via the
optional extra ``naturo[ocr]``:

* MIT/Apache-licensed and fully **offline** — it bundles ONNX detection /
  recognition models, so there is no network call and no system Tesseract to
  install;
* strong on both Latin and Chinese text.

The extra is optional so the base install stays lean: when it is absent the CLI
emits a recoverable ``OCR_NOT_AVAILABLE`` error pointing at the install command,
rather than failing opaquely (the agent self-correction contract).

The matcher operates purely in image coordinates (origin at the image's
top-left). The CLI layer translates those into screen-absolute coordinates by
adding the captured window/monitor origin, exactly as the ``--image`` path does.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


class OCRNotAvailableError(RuntimeError):
    """Raised when the optional OCR engine (RapidOCR) is not installed.

    The CLI maps this to the recoverable ``OCR_NOT_AVAILABLE`` error code with an
    install hint, so a caller can fix it with ``pip install naturo[ocr]``.
    """


@dataclass(frozen=True)
class TextMatch:
    """A single OCR text match within the haystack image (origin at top-left).

    Attributes:
        text: The recognised text of the matched region.
        x: Left edge of the bounding box, in image pixels.
        y: Top edge of the bounding box, in image pixels.
        width: Bounding-box width in pixels.
        height: Bounding-box height in pixels.
        score: The engine's recognition confidence in ``[0.0, 1.0]``.
    """

    text: str
    x: int
    y: int
    width: int
    height: int
    score: float


# Type alias for an OCR engine callable: given an image path it returns the
# RapidOCR result — either ``(detections, elapse)`` or just ``detections`` — where
# each detection is ``[box, text, score]`` and ``box`` is four ``[x, y]`` corner
# points. Injectable so the recognition→coordinate logic is testable without the
# heavy optional dependency installed.
OCREngine = Callable[[str], Any]


def load_engine() -> OCREngine:
    """Load the RapidOCR engine, or raise if the optional extra is missing.

    Returns:
        A callable OCR engine that maps an image path to RapidOCR detections.

    Raises:
        OCRNotAvailableError: When ``rapidocr-onnxruntime`` is not installed.
    """
    try:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore[import-not-found]
    except ImportError as exc:
        raise OCRNotAvailableError(
            "OCR text finding requires the optional RapidOCR engine, which is not "
            "installed. Install it with 'pip install naturo[ocr]' (offline, "
            "bundled ONNX models — no network or system Tesseract needed)."
        ) from exc
    return RapidOCR()


def _iter_detections(raw_result: Any) -> list[Any]:
    """Normalise a RapidOCR result into a list of ``[box, text, score]`` items.

    RapidOCR returns ``(detections, elapse_times)`` and ``detections`` is ``None``
    when no text is found. This unwraps both shapes defensively so the matcher
    never trips on the no-text case.

    Args:
        raw_result: The raw value returned by the OCR engine call.

    Returns:
        A list of detection items (possibly empty).
    """
    detections = raw_result
    if isinstance(raw_result, tuple):
        detections = raw_result[0] if raw_result else None
    return list(detections) if detections else []


def find_text(
    image_path: str,
    query: str,
    *,
    find_all: bool = False,
    max_results: int = 50,
    engine: Optional[OCREngine] = None,
) -> list[TextMatch]:
    """Locate on-screen text matching ``query`` in the image at ``image_path``.

    Runs OCR over the whole image, then keeps the regions whose recognised text
    contains ``query`` as a case-insensitive substring. Matches are returned
    highest-confidence first.

    Args:
        image_path: Path to the haystack image (a window/screen capture or a
            supplied screenshot).
        query: The text to search for (case-insensitive substring match).
        find_all: When True, return every matching region; otherwise only the
            single highest-confidence match.
        max_results: Maximum number of matches to return.
        engine: Optional pre-loaded OCR engine. Loaded via :func:`load_engine`
            when omitted (the production path); injectable for testing.

    Returns:
        The matching :class:`TextMatch` regions in image coordinates, ordered by
        descending confidence and truncated to ``max_results``.

    Raises:
        OCRNotAvailableError: When no engine is supplied and the optional RapidOCR
            extra is not installed.
    """
    ocr_engine = engine if engine is not None else load_engine()
    detections = _iter_detections(ocr_engine(image_path))

    needle = query.casefold()
    matches: list[TextMatch] = []
    for item in detections:
        # Each detection is ``[box, text, score]``; box is four [x, y] corners.
        box, text, score = item[0], item[1], item[2]
        if needle not in str(text).casefold():
            continue
        xs = [float(point[0]) for point in box]
        ys = [float(point[1]) for point in box]
        left, top = min(xs), min(ys)
        right, bottom = max(xs), max(ys)
        matches.append(
            TextMatch(
                text=str(text),
                x=int(round(left)),
                y=int(round(top)),
                width=int(round(right - left)),
                height=int(round(bottom - top)),
                score=float(score),
            )
        )

    matches.sort(key=lambda match: match.score, reverse=True)
    if not find_all:
        matches = matches[:1]
    return matches[:max_results]
