"""Annotated screenshot generation — draw bounding boxes and labels on screenshots.

Draws red rectangles and numbered labels on top of a screenshot image so that
AI vision models (or human inspectors) can identify UI elements by index.

Requires Pillow: ``pip install naturo[annotate]``
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from naturo.models.snapshot import UIElement

logger = logging.getLogger(__name__)

# Colour scheme (Peekaboo-style)
BOX_COLOR = (255, 0, 0)           # Red
LABEL_BG_COLOR = (255, 255, 255)  # White
LABEL_TEXT_COLOR = (255, 0, 0)    # Red
BOX_WIDTH = 2
LABEL_FONT_SIZE = 12
LABEL_PADDING = 2

# Minimum element size to annotate (skip tiny/invisible elements)
MIN_ELEMENT_SIZE = 4


def annotate_screenshot(
    screenshot_path: str,
    elements: List[UIElement],
    output_path: Optional[str] = None,
) -> str:
    """Draw bounding boxes and numbered labels on a screenshot.

    Only annotates actionable elements with non-trivial bounding rectangles.

    Args:
        screenshot_path: Path to the source screenshot image.
        elements: List of UIElement objects to annotate.
        output_path: Output path for the annotated image.
            If None, generates a path by appending ``_annotated`` to the input name.

    Returns:
        The absolute path to the annotated screenshot.

    Raises:
        ImportError: If Pillow is not installed.
        FileNotFoundError: If the screenshot file does not exist.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise ImportError(
            "Pillow is required for annotated screenshots. "
            "Install it with: pip install naturo[annotate]"
        )

    src = Path(screenshot_path)
    if not src.exists():
        raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")

    if output_path is None:
        output_path = str(src.parent / f"{src.stem}_annotated{src.suffix}")

    img = Image.open(src)
    draw = ImageDraw.Draw(img)

    # Try to load a reasonable font
    font = _get_font(LABEL_FONT_SIZE)

    # Filter to actionable elements with visible bounding boxes
    annotatable = [
        el for el in elements
        if el.is_actionable
        and el.frame[2] >= MIN_ELEMENT_SIZE
        and el.frame[3] >= MIN_ELEMENT_SIZE
    ]

    for idx, el in enumerate(annotatable):
        x, y, w, h = el.frame
        x2, y2 = x + w, y + h

        # Draw bounding box
        draw.rectangle([x, y, x2, y2], outline=BOX_COLOR, width=BOX_WIDTH)

        # Draw label (number)
        label = str(idx)
        bbox = font.getbbox(label) if hasattr(font, "getbbox") else (0, 0, *font.getsize(label))
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Position label at top-left of bounding box
        label_x = x
        label_y = max(0, y - text_h - LABEL_PADDING * 2)

        # Draw label background
        draw.rectangle(
            [
                label_x,
                label_y,
                label_x + text_w + LABEL_PADDING * 2,
                label_y + text_h + LABEL_PADDING * 2,
            ],
            fill=LABEL_BG_COLOR,
            outline=BOX_COLOR,
        )

        # Draw label text
        draw.text(
            (label_x + LABEL_PADDING, label_y + LABEL_PADDING),
            label,
            fill=LABEL_TEXT_COLOR,
            font=font,
        )

    img.save(output_path)
    logger.info("Annotated screenshot saved: %s (%d elements)", output_path, len(annotatable))
    return output_path


def _get_font(size: int):
    """Try to load a TrueType font, falling back to Pillow's default."""
    from PIL import ImageFont

    # Try common system font paths
    font_candidates = [
        "arial.ttf",
        "Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]

    for path in font_candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue

    # Fall back to default bitmap font
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()
