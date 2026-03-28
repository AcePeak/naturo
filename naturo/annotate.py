"""Annotated screenshot generation — draw bounding boxes and labels on screenshots.

Draws red rectangles and numbered labels on top of a screenshot image so that
AI vision models (or human inspectors) can identify UI elements by index.

Also provides :func:`highlight_annotate` for the ``highlight --annotate`` mode,
which renders colored borders and eN ref labels onto a screenshot for all
(or filtered) UI elements.

Requires Pillow: ``pip install naturo[annotate]``
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

# Depth-based colour palette for highlight_annotate (RGB tuples)
DEPTH_COLORS: List[Tuple[int, int, int]] = [
    (255, 0, 0),      # Red
    (0, 160, 0),      # Green
    (0, 80, 255),     # Blue
    (255, 160, 0),    # Orange
    (160, 0, 200),    # Purple
    (0, 180, 180),    # Teal
    (200, 0, 100),    # Crimson
    (80, 80, 255),    # Indigo
]

# Actionable roles for default filtering
ACTIONABLE_ROLES = frozenset({
    "Button", "Edit", "ComboBox", "CheckBox", "RadioButton",
    "Slider", "Tab", "TabItem", "MenuItem", "Menu", "MenuBar",
    "ListItem", "TreeItem", "DataItem", "Link", "Hyperlink",
    "SpinButton", "Spinner", "ScrollBar", "ToolBar",
    "AXButton", "AXTextField", "AXCheckBox", "AXRadioButton",
    "AXComboBox", "AXSlider", "AXTab", "AXMenuItem", "AXLink",
    "AXList", "AXRow",
})


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
        from PIL import Image, ImageDraw, ImageFont  # noqa: F401
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


# ── Label collision avoidance ────────────────────────────────────────────────


def _compute_label_positions(
    elements: List[Tuple[str, int, int, int, int]],
    label_sizes: Dict[str, Tuple[int, int]],
) -> Dict[str, Tuple[int, int]]:
    """Compute non-overlapping label positions for highlight annotations.

    For each element, tries four candidate positions (top-left, top-right,
    bottom-left, bottom-right of the bounding box) and picks the one that
    overlaps the fewest already-placed labels.

    Args:
        elements: List of (ref, x, y, w, h) tuples.
        label_sizes: Mapping ref → (text_width, text_height) including padding.

    Returns:
        Mapping ref → (label_x, label_y) in screen coordinates.
    """
    placed: List[Tuple[int, int, int, int]] = []  # (x1, y1, x2, y2) of placed labels
    positions: Dict[str, Tuple[int, int]] = {}

    pad = LABEL_PADDING * 2

    for ref, ex, ey, ew, eh in elements:
        tw, th = label_sizes[ref]
        full_w = tw + pad
        full_h = th + pad

        # Four candidate positions: above-left, above-right, below-left, below-right
        candidates = [
            (ex, max(0, ey - full_h)),            # above-left
            (ex + ew - full_w, max(0, ey - full_h)),  # above-right
            (ex, ey + eh),                         # below-left
            (ex + ew - full_w, ey + eh),           # below-right
        ]

        best_pos = candidates[0]
        best_overlap = float("inf")

        for cx, cy in candidates:
            cx = max(0, cx)
            cy = max(0, cy)
            overlap_count = 0
            for px1, py1, px2, py2 in placed:
                # AABB overlap test
                if cx < px2 and cx + full_w > px1 and cy < py2 and cy + full_h > py1:
                    overlap_count += 1
            if overlap_count < best_overlap:
                best_overlap = overlap_count
                best_pos = (cx, cy)
                if overlap_count == 0:
                    break

        positions[ref] = best_pos
        placed.append((best_pos[0], best_pos[1], best_pos[0] + full_w, best_pos[1] + full_h))

    return positions


def _element_depth(ref: str, ui_map: Dict[str, UIElement]) -> int:
    """Compute tree depth of an element by walking parent_id links.

    Args:
        ref: Element reference (e.g. ``"e5"``).
        ui_map: Full ui_map from a snapshot.

    Returns:
        Depth (0 for root, 1 for first children, etc.).
    """
    depth = 0
    el = ui_map.get(ref)
    seen: set = set()
    while el and el.parent_id and el.parent_id not in seen:
        seen.add(el.parent_id)
        depth += 1
        el = ui_map.get(el.parent_id)
    return depth


# ── highlight --annotate mode ────────────────────────────────────────────────


def highlight_annotate(
    screenshot_path: str,
    ui_map: Dict[str, UIElement],
    output_path: Optional[str] = None,
    refs: Optional[List[str]] = None,
    actionable_only: bool = True,
    role_filter: Optional[str] = None,
) -> str:
    """Render colored borders and eN ref labels onto a screenshot.

    Draws all matching UI elements simultaneously with depth-based coloring
    and label collision avoidance. Used by ``naturo highlight --annotate``.

    Args:
        screenshot_path: Path to the source screenshot image.
        ui_map: Mapping of ref → UIElement from a snapshot.
        output_path: Output path for the annotated image. Auto-generated if None.
        refs: Optional list of specific refs to highlight. None = all.
        actionable_only: If True (default), only highlight actionable elements.
        role_filter: If set, only highlight elements whose role contains this string.

    Returns:
        The absolute path to the annotated screenshot.

    Raises:
        ImportError: If Pillow is not installed.
        FileNotFoundError: If the screenshot file does not exist.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont  # noqa: F401
    except ImportError:
        raise ImportError(
            "Pillow is required for annotated screenshots. "
            "Install it with: pip install naturo[annotate]"
        )

    src = Path(screenshot_path)
    if not src.exists():
        raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")

    if output_path is None:
        output_path = str(src.parent / f"{src.stem}_highlight{src.suffix}")

    # Filter elements
    filtered: List[Tuple[str, UIElement]] = []
    for ref_key, el in ui_map.items():
        if refs is not None and ref_key not in refs:
            continue
        ex, ey, ew, eh = el.frame
        if ew < MIN_ELEMENT_SIZE or eh < MIN_ELEMENT_SIZE:
            continue
        if actionable_only and not el.is_actionable and el.role not in ACTIONABLE_ROLES:
            continue
        if role_filter and role_filter.lower() not in el.role.lower():
            continue
        filtered.append((ref_key, el))

    if not filtered:
        # Nothing to draw — copy screenshot as-is
        import shutil
        shutil.copy2(screenshot_path, output_path)
        return output_path

    img = Image.open(src)
    draw = ImageDraw.Draw(img, "RGBA")
    font = _get_font(LABEL_FONT_SIZE)

    # Compute depths and prepare label sizes
    element_tuples: List[Tuple[str, int, int, int, int]] = []
    label_sizes: Dict[str, Tuple[int, int]] = {}
    depths: Dict[str, int] = {}

    for ref_key, el in filtered:
        ex, ey, ew, eh = el.frame
        element_tuples.append((ref_key, ex, ey, ew, eh))
        depths[ref_key] = _element_depth(ref_key, ui_map)

        label_name = el.title or el.role
        if len(label_name) > 20:
            label_name = label_name[:18] + ".."
        label_text = f" {ref_key}: {label_name} "
        bbox = font.getbbox(label_text) if hasattr(font, "getbbox") else (0, 0, *font.getsize(label_text))
        label_sizes[ref_key] = (bbox[2] - bbox[0], bbox[3] - bbox[1])

    # Compute non-overlapping label positions
    label_positions = _compute_label_positions(element_tuples, label_sizes)

    # Draw borders and labels
    for ref_key, el in filtered:
        ex, ey, ew, eh = el.frame
        depth = depths[ref_key]
        color = DEPTH_COLORS[depth % len(DEPTH_COLORS)]

        # Draw bounding box
        draw.rectangle([ex, ey, ex + ew, ey + eh], outline=color, width=BOX_WIDTH)

        # Draw label
        label_name = el.title or el.role
        if len(label_name) > 20:
            label_name = label_name[:18] + ".."
        label_text = f" {ref_key}: {label_name} "
        lx, ly = label_positions[ref_key]
        tw, th = label_sizes[ref_key]

        # Semi-transparent background
        bg_color = color + (200,)  # RGBA with alpha
        draw.rectangle(
            [lx, ly, lx + tw + LABEL_PADDING * 2, ly + th + LABEL_PADDING * 2],
            fill=bg_color,
        )
        draw.text(
            (lx + LABEL_PADDING, ly + LABEL_PADDING),
            label_text,
            fill=(255, 255, 255),
            font=font,
        )

    img.save(output_path)
    logger.info(
        "Highlight annotation saved: %s (%d elements)", output_path, len(filtered)
    )
    return output_path
