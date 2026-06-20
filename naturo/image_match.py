"""Image template matching via normalized cross-correlation (NCC).

This is the engine behind ``naturo find --image`` (issue #1059, part of the
unified find engine #809). It locates a small *template* image inside a larger
*haystack* screenshot and returns the pixel coordinates of every match whose
similarity exceeds a threshold.

Design constraints (per #809):

* **No NumPy / OpenCV.** Pure Pillow plus the standard library, honouring the
  project's minimum-dependency principle. Pillow is already a hard dependency
  for capture and conversion.
* **Coarse-to-fine search.** A naive full-resolution slide over a 1080p
  screenshot is billions of operations in pure Python. Instead the haystack and
  template are downsampled for a fast coarse pass, candidate peaks are mapped
  back to full resolution, and only a small neighbourhood around each peak is
  refined at full resolution. This bounds the work while keeping the reported
  coordinates pixel-accurate.

The matcher operates purely on image coordinates (origin at the haystack's
top-left). The CLI layer is responsible for translating those into
screen-absolute coordinates by adding the captured window/monitor origin.
"""
from __future__ import annotations

import math
import operator
from dataclasses import dataclass

from PIL import Image

# Bound multiplication used inside the hot NCC loop; ``map(_MUL, ...)`` runs the
# per-pixel products at C speed rather than in a Python-level loop.
_MUL = operator.mul

# Longest-side target (pixels) for the downsampled coarse pass: the factor aims
# to shrink the haystack's longest side to roughly this.
_COARSE_TARGET = 240

# Hard cap on the coarse downsample factor. This matters for *correctness*, not
# just speed: independently downsampling the haystack and template introduces a
# phase error of up to ``factor`` pixels at the true location (the averaging
# grids do not align), degrading its coarse score. A small factor keeps that
# error low so the true match survives as a candidate; an aggressive factor (8x)
# can push it below hundreds of spurious hits on a texture-rich screenshot. A
# cap of 4 was validated to keep genuine matches well within the candidate pool
# on a full 1920x1080 desktop while bounding the coarse pass to a few seconds.
_MAX_COARSE_FACTOR = 4

# Absolute coarse-score floor for retaining a candidate. Phase error can pull a
# genuine match's coarse score well below the user threshold, so the floor is
# deliberately low; the exact full-resolution refinement is what enforces the
# real threshold. Lowering this trades more refinement work for recall.
_COARSE_FLOOR = 0.5

# Minimum downsampled template side (pixels). Below this the coarse template
# loses the structure NCC relies on, so the coarse factor is reduced instead.
_MIN_COARSE_SIDE = 3

# Cap on coarse hits fed into non-maximum suppression, and on candidates carried
# into the (pure-Python, hence costly) full-resolution refinement pass. The pool
# is processed strongest-first, and refinement is cheap per candidate (a tiny
# window around each), so a generous cap keeps recall high while bounding the
# worst case on a busy screenshot.
_COARSE_POOL = 4000
_MAX_REFINE_CANDIDATES = 400


@dataclass(frozen=True)
class ImageMatch:
    """A single template match within a haystack image.

    Coordinates are in the haystack image's own pixel space (origin at its
    top-left); callers translate to screen-absolute coordinates as needed.

    Attributes:
        x: Left edge of the matched region.
        y: Top edge of the matched region.
        width: Template width in pixels.
        height: Template height in pixels.
        score: Normalized cross-correlation score in ``[-1.0, 1.0]`` (1.0 is a
            perfect match).
    """

    x: int
    y: int
    width: int
    height: int
    score: float

    @property
    def center_x(self) -> int:
        """X coordinate of the match centre (a natural click target)."""
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        """Y coordinate of the match centre (a natural click target)."""
        return self.y + self.height // 2


def _to_luma_bytes(image: Image.Image) -> tuple[bytes, int, int]:
    """Return ``(row-major luminance bytes, width, height)`` for an image."""
    luma = image.convert("L")
    width, height = luma.size
    return luma.tobytes(), width, height


def _template_stats(t_bytes: bytes, count: int) -> tuple[float, float]:
    """Return ``(sum, centred-sum-of-squares)`` for template pixels.

    Args:
        t_bytes: Template luminance bytes.
        count: Number of template pixels (``width * height``).

    Returns:
        The pixel sum and the mean-centred sum of squares
        (``sum(v**2) - sum(v)**2 / count``), the denominator term NCC needs.
    """
    t_sum = sum(t_bytes)
    t_sqsum = sum(v * v for v in t_bytes)
    t_den = t_sqsum - (t_sum * t_sum) / count
    return float(t_sum), float(t_den)


def _rows(data: bytes, width: int, height: int) -> list[bytes]:
    """Split row-major luminance bytes into a list of per-row ``bytes`` slices."""
    return [data[r * width:(r + 1) * width] for r in range(height)]


def _ncc_at(
    hay: bytes,
    hay_w: int,
    t_rows: list[bytes],
    t_w: int,
    t_h: int,
    count: int,
    t_sum: float,
    t_den: float,
    ox: int,
    oy: int,
) -> float:
    """Compute the NCC of a template against the haystack window at ``(ox, oy)``.

    The per-pixel products and sums run at C speed via ``sum``/``map`` over
    ``bytes`` rows, so the only Python-level loop is over template *rows*, not
    individual pixels.

    Args:
        hay: Haystack luminance bytes (row-major).
        hay_w: Haystack width in pixels.
        t_rows: Template luminance rows (one ``bytes`` per row).
        t_w: Template width.
        t_h: Template height.
        count: Template pixel count (``t_w * t_h``).
        t_sum: Pre-computed template pixel sum.
        t_den: Pre-computed template mean-centred sum of squares.
        ox: Left offset of the candidate window in the haystack.
        oy: Top offset of the candidate window in the haystack.

    Returns:
        The NCC score in ``[-1.0, 1.0]``; ``-1.0`` when the haystack window is
        flat (zero variance) and therefore not a meaningful match.
    """
    dot = 0
    s_h = 0
    s_hh = 0
    for ry in range(t_h):
        base = (oy + ry) * hay_w + ox
        row = hay[base:base + t_w]
        dot += sum(map(_MUL, row, t_rows[ry]))
        s_h += sum(row)
        s_hh += sum(map(_MUL, row, row))

    h_den = s_hh - (s_h * s_h) / count
    if h_den <= 0.0:
        return -1.0
    numerator = dot - (s_h * t_sum) / count
    return numerator / math.sqrt(h_den * t_den)


def _scan(
    hay: bytes,
    hay_w: int,
    hay_h: int,
    template: bytes,
    t_w: int,
    t_h: int,
    t_sum: float,
    t_den: float,
    threshold: float,
) -> list[tuple[int, int, float]]:
    """Slide the template over the whole haystack, collecting hits.

    Returns a list of ``(x, y, score)`` for every offset whose NCC is at or
    above ``threshold``.
    """
    count = t_w * t_h
    t_rows = _rows(template, t_w, t_h)
    hits: list[tuple[int, int, float]] = []
    for oy in range(hay_h - t_h + 1):
        for ox in range(hay_w - t_w + 1):
            score = _ncc_at(hay, hay_w, t_rows, t_w, t_h, count, t_sum, t_den, ox, oy)
            if score >= threshold:
                hits.append((ox, oy, score))
    return hits


def _suppress(
    hits: list[tuple[int, int, float]],
    t_w: int,
    t_h: int,
) -> list[tuple[int, int, float]]:
    """Non-maximum suppression: collapse overlapping hits to local peaks.

    Hits are processed highest-score first; each accepted hit suppresses any
    later hit whose top-left lies within half a template size of it, so a single
    true occurrence (which scores highly across a cluster of adjacent offsets)
    yields exactly one result.

    Args:
        hits: ``(x, y, score)`` tuples.
        t_w: Template width (defines the suppression radius).
        t_h: Template height.

    Returns:
        The retained peaks, highest score first.
    """
    kept: list[tuple[int, int, float]] = []
    min_dx = max(1, t_w // 2)
    min_dy = max(1, t_h // 2)
    for hit in sorted(hits, key=lambda h: h[2], reverse=True):
        hx, hy, _ = hit
        if any(abs(hx - kx) < min_dx and abs(hy - ky) < min_dy for kx, ky, _ in kept):
            continue
        kept.append(hit)
    return kept


def _coarse_factor(hay_w: int, hay_h: int, t_w: int, t_h: int) -> int:
    """Choose a downsample factor for the coarse pass.

    The factor shrinks the haystack's longest side toward ``_COARSE_TARGET`` but
    is clamped to ``_MAX_COARSE_FACTOR`` (to keep the coarse phase error small)
    and reduced if it would make the downsampled template smaller than
    ``_MIN_COARSE_SIDE`` on either axis (which would destroy the structure NCC
    relies on).

    Returns:
        An integer factor ``>= 1`` (1 means "no coarse downsampling").
    """
    longest = max(hay_w, hay_h)
    factor = max(1, -(-longest // _COARSE_TARGET))  # ceil division
    factor = min(factor, _MAX_COARSE_FACTOR)
    while factor > 1 and (t_w // factor < _MIN_COARSE_SIDE or t_h // factor < _MIN_COARSE_SIDE):
        factor -= 1
    return factor


def match_template(
    haystack: Image.Image,
    template: Image.Image,
    *,
    threshold: float = 0.9,
    find_all: bool = False,
    max_results: int = 50,
) -> list[ImageMatch]:
    """Locate ``template`` inside ``haystack`` via normalized cross-correlation.

    Args:
        haystack: The larger image to search (e.g. a window/screen capture).
        template: The smaller image to find. Converted to luminance internally,
            so colour and alpha are ignored.
        threshold: Minimum NCC score in ``[-1.0, 1.0]`` for a match (default
            ``0.9``). Higher is stricter.
        find_all: When ``True`` return every non-overlapping match at or above
            the threshold; when ``False`` (default) return only the single best
            match (or an empty list if none qualifies).
        max_results: Upper bound on the number of matches returned.

    Returns:
        A list of :class:`ImageMatch`, highest score first. Empty when the
        template does not occur above the threshold or is larger than the
        haystack.

    Raises:
        ValueError: If the template has no internal contrast (a single flat
            colour), since NCC is undefined for a zero-variance signal.
    """
    hay_bytes, hay_w, hay_h = _to_luma_bytes(haystack)
    t_bytes, t_w, t_h = _to_luma_bytes(template)

    if t_w > hay_w or t_h > hay_h:
        return []

    count = t_w * t_h
    t_sum, t_den = _template_stats(t_bytes, count)
    if t_den <= 0.0:
        raise ValueError(
            "Template image has no internal contrast (uniform colour); "
            "normalized cross-correlation requires a template with variation."
        )

    factor = _coarse_factor(hay_w, hay_h, t_w, t_h)

    if factor > 1:
        hay_small = haystack.convert("L").reduce(factor)
        tmpl_small = template.convert("L").reduce(factor)
        hs_bytes, hs_w, hs_h = hay_small.tobytes(), hay_small.width, hay_small.height
        ts_bytes, ts_w, ts_h = tmpl_small.tobytes(), tmpl_small.width, tmpl_small.height
        ts_count = ts_w * ts_h
        ts_sum, ts_den = _template_stats(ts_bytes, ts_count)
        if ts_den <= 0.0:
            # Downsampling flattened the template (its detail was higher-frequency
            # than the coarse grid). Fall back to an exact full-resolution scan
            # rather than risk a divide-by-zero on a degenerate coarse pass.
            factor = 1
        else:
            # Collect coarse hits above the (low) floor, dedupe to peaks, and keep
            # the strongest pool. The floor is deliberately permissive because
            # phase error suppresses the true match's coarse score; the exact
            # refinement below is what enforces ``threshold``.
            coarse_hits = _scan(
                hs_bytes, hs_w, hs_h, ts_bytes, ts_w, ts_h, ts_sum, ts_den,
                min(threshold, _COARSE_FLOOR),
            )
            coarse_hits.sort(key=lambda h: h[2], reverse=True)
            candidates = _suppress(coarse_hits[:_COARSE_POOL], ts_w, ts_h)
            if len(candidates) > _MAX_REFINE_CANDIDATES:
                candidates = candidates[:_MAX_REFINE_CANDIDATES]

    if factor == 1:
        # Small haystack: a direct full-resolution scan is affordable and exact.
        full_hits = _scan(
            hay_bytes, hay_w, hay_h, t_bytes, t_w, t_h, t_sum, t_den, threshold,
        )
        peaks = _suppress(full_hits, t_w, t_h)
        results = [ImageMatch(x, y, t_w, t_h, score) for x, y, score in peaks]
    else:
        # Refine each coarse candidate at full resolution. Phase misalignment can
        # land the coarse peak on either neighbour of the true cell, so the true
        # top-left lies within +/-``factor`` pixels of ``(cx*factor, cy*factor)``;
        # the search window must be symmetric (a one-sided window misses matches
        # off by a pixel). With ``factor`` capped at 4 this is only 9x9 offsets.
        t_rows = _rows(t_bytes, t_w, t_h)
        refined: list[tuple[int, int, float]] = []
        for cx, cy, _ in candidates:
            fx0, fy0 = cx * factor, cy * factor
            best: tuple[int, int, float] | None = None
            for dy in range(-factor, factor + 1):
                oy = fy0 + dy
                if oy < 0 or oy + t_h > hay_h:
                    continue
                for dx in range(-factor, factor + 1):
                    ox = fx0 + dx
                    if ox < 0 or ox + t_w > hay_w:
                        continue
                    score = _ncc_at(
                        hay_bytes, hay_w, t_rows, t_w, t_h, count, t_sum, t_den, ox, oy,
                    )
                    if best is None or score > best[2]:
                        best = (ox, oy, score)
            if best is not None and best[2] >= threshold:
                refined.append(best)
        peaks = _suppress(refined, t_w, t_h)
        results = [ImageMatch(x, y, t_w, t_h, score) for x, y, score in peaks]

    results.sort(key=lambda m: m.score, reverse=True)
    if not find_all:
        results = results[:1]
    return results[:max_results]
