"""Provider fetching: CDP and AI vision element discovery."""
from __future__ import annotations

import logging
from typing import List, Optional

from naturo.backends.base import ElementInfo

logger = logging.getLogger(__name__)


# ── CDP element helper ────────────────────────────────────────────────────────


def _fetch_cdp_elements(
    pid: int,
    debug_port: int,
    parent_bounds: tuple[int, int, int, int],
) -> List[ElementInfo]:
    """Fetch DOM elements via CDP for an Electron/CEF app.

    Parameters
    ----------
    pid:
        Process ID (used only for logging).
    debug_port:
        Chrome DevTools Protocol port.
    parent_bounds:
        (x, y, w, h) of the window for coordinate offsetting.

    Returns
    -------
    List[ElementInfo]
        Flat list of interactive DOM elements (buttons, inputs, links, etc.).
        Returns empty list on any error.
    """
    try:
        from naturo.cdp import CDPClient
    except ImportError:
        logger.debug("CDP module not available; skipping CDP provider")
        return []

    try:
        client = CDPClient(port=debug_port)
        client.connect()
        try:
            dom_elements = client.get_interactive_elements()
        finally:
            client.close()

        elements: List[ElementInfo] = []
        px, py = parent_bounds[0], parent_bounds[1]

        _ROLE_MAP = {
            "button": "Button", "input": "Edit", "a": "Link",
            "textarea": "Edit", "select": "ComboBox",
        }

        for dom_el in dom_elements:
            bounds = dom_el.get("bounds", {})
            ex = int(bounds.get("x", 0)) + px
            ey = int(bounds.get("y", 0)) + py
            ew = int(bounds.get("width", 0))
            eh = int(bounds.get("height", 0))

            if ew <= 0 or eh <= 0:
                continue

            tag = dom_el.get("tagName", "")
            raw_role = dom_el.get("role", "")
            role = raw_role.capitalize() if raw_role else _ROLE_MAP.get(tag, "Text")
            name = dom_el.get("name", "")
            css_selector = dom_el.get("selector", "")

            el_id = f"cdp_{dom_el.get('nodeIndex', id(dom_el))}"
            elements.append(ElementInfo(
                id=el_id,
                role=role,
                name=name,
                value=dom_el.get("value"),
                x=ex, y=ey, width=ew, height=eh,
                children=[],
                properties={
                    "source": "cdp",
                    "tag": tag,
                    "css_selector": css_selector,
                    "parent_id": None,
                },
            ))

        return elements
    except Exception as exc:
        logger.debug("CDP element fetch failed (port=%d): %s", debug_port, exc)
        return []


# ── AI vision helper ──────────────────────────────────────────────────────────


def _fetch_ai_elements(
    screenshot_path: str,
    window_bounds: tuple[int, int, int, int],
    provider_name: str = "auto",
    scale_factor: float = 1.0,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> List[ElementInfo]:
    """Use AI vision to identify additional elements from a screenshot.

    Parameters
    ----------
    screenshot_path:
        Path to the screenshot image file.
    window_bounds:
        (x, y, w, h) of the captured window in screen coordinates.
        AI pixel coords are offset by (x, y) to convert to screen coords.
    provider_name:
        AI provider to use.
    scale_factor:
        DPI scale factor of the captured monitor (e.g. 1.5 for 150% DPI).
        AI returns coords in screenshot pixels; UIA uses physical (scaled)
        pixels.  We multiply AI coords by scale_factor to align them.
    model:
        AI model override (e.g. ``"claude-opus-4-6"``, ``"gpt-4o"``).
        When ``None``, uses the provider's default model.
    api_key:
        API key override.  When ``None``, uses the provider's default
        credentials (env var or credentials file).

    Returns a flat list of elements identified by the AI provider.
    Falls back gracefully if the provider is unavailable.
    """
    try:
        from naturo.providers.base import get_vision_provider
        from naturo.errors import AIProviderUnavailableError

        try:
            kwargs: dict[str, str] = {}
            if model:
                kwargs["model"] = model
            if api_key:
                kwargs["api_key"] = api_key
            provider = get_vision_provider(provider_name, **kwargs)
        except AIProviderUnavailableError:
            return []

        logger.info("AI vision: calling provider '%s' with screenshot '%s'",
                    provider_name, screenshot_path)

        # (#694) Read actual screenshot dimensions for coordinate scaling.
        # Claude vision API downscales large images internally; AI returns
        # coords in that smaller space. We need to scale back up.
        img_w, img_h = 0, 0
        try:
            from PIL import Image as _PILImage
            with _PILImage.open(screenshot_path) as _img:
                img_w, img_h = _img.size
            logger.info("AI vision: screenshot dimensions %dx%d", img_w, img_h)
        except Exception as exc:
            logger.debug("AI vision: could not read screenshot dimensions: %s", exc)

        # Include image dimensions in prompt so AI can return accurate coords
        dim_hint = ""
        if img_w > 0 and img_h > 0:
            dim_hint = (
                f"\n\nIMPORTANT: This image is {img_w}x{img_h} pixels. "
                f"Return all bounding box coordinates in this {img_w}x{img_h} pixel space. "
                f"x ranges from 0 to {img_w}, y ranges from 0 to {img_h}."
            )

        result = provider.enumerate_elements(
            screenshot_path,
            prompt=(
                "You are a UI element detector. Analyze this screenshot and list EVERY "
                "individual clickable or interactive element you can see. Be exhaustive.\n\n"
                "Rules:\n"
                "- List LEAF elements, not containers. For example, list each individual "
                "conversation item in a chat list, not a generic 'conversation_list'.\n"
                "- List each button, link, tab, menu item, text input, checkbox, icon, "
                "avatar, timestamp, and clickable text separately.\n"
                "- For each element, estimate its PIXEL bounding box (x, y, width, height) "
                "as precisely as possible based on the screenshot.\n"
                "- 'x' and 'y' are the top-left corner of the element in pixels.\n"
                "- Include the visible text or label as 'name'.\n"
                "- Use standard roles: Button, Link, Tab, MenuItem, Edit, Text, Image, "
                "CheckBox, ListItem, TreeItem.\n\n"
                "Return a JSON array where each item has: "
                'role, name, bounds [x, y, width, height] (use JSON arrays like [100, 200, 50, 30], NOT tuples). '
                "Return ONLY the JSON array, no markdown fences, no explanation."
                + dim_hint
            ),
            max_tokens=16384,
        )

        # (#694) Window offset: AI coords are relative to the screenshot
        # (which is a window capture). Add window position to get screen coords.
        win_x, win_y = window_bounds[0], window_bounds[1]

        logger.info("AI vision: provider returned %d elements (window offset: %d,%d)",
                     len(result.elements), win_x, win_y)
        if not result.elements:
            raw = result.raw_response
            if raw:
                logger.warning("AI vision: 0 elements parsed from response: %.500s",
                               str(raw))

        # (#694) Auto-detect coordinate scale: if the AI returned coords in a
        # smaller image space (Claude API downscales large images), compute the
        # ratio from AI-max-coord to actual screenshot size.
        # Use the screenshot dimensions (img_w, img_h) as ground truth.
        ai_scale_x, ai_scale_y = 1.0, 1.0

        # (#694) Auto-detect bounds format: AI may return [x1,y1,x2,y2]
        # (top-left + bottom-right) instead of the requested [x,y,w,h].
        # Detect by checking if 3rd value >= 1st value for most elements.
        is_xyxy = False
        if result.elements:
            xyxy_count = 0
            total_checked = 0
            for raw_el in result.elements:
                if not isinstance(raw_el, dict):
                    continue
                b = raw_el.get("bounds", {})
                if isinstance(b, (list, tuple)) and len(b) >= 4:
                    v0, v1, v2, v3 = b[0], b[1], b[2], b[3]
                elif isinstance(b, dict):
                    v0 = b.get("x", 0)
                    v1 = b.get("y", 0)
                    v2 = b.get("width", 0)
                    v3 = b.get("height", 0)
                else:
                    continue
                total_checked += 1
                # In [x1,y1,x2,y2] format, x2 > x1 and y2 > y1 always.
                # In [x,y,w,h] format, w is typically much smaller than x
                # for elements not at the left edge.
                if v2 >= v0 and v3 >= v1:
                    xyxy_count += 1
            if total_checked > 0 and xyxy_count / total_checked > 0.8:
                is_xyxy = True
                logger.info("AI vision: detected [x1,y1,x2,y2] bounds format (%d/%d)",
                            xyxy_count, total_checked)

        if img_w > 0 and img_h > 0 and result.elements:
            max_ai_x = 0.0
            max_ai_y = 0.0
            for raw_el in result.elements:
                if not isinstance(raw_el, dict):
                    continue
                b = raw_el.get("bounds", {})
                if isinstance(b, (list, tuple)) and len(b) >= 4:
                    if is_xyxy:
                        # b[2],b[3] are already x2,y2 (max coords)
                        max_ai_x = max(max_ai_x, b[2])
                        max_ai_y = max(max_ai_y, b[3])
                    else:
                        max_ai_x = max(max_ai_x, b[0] + b[2])
                        max_ai_y = max(max_ai_y, b[1] + b[3])
                elif isinstance(b, dict):
                    max_ai_x = max(max_ai_x, b.get("x", 0) + b.get("width", 0))
                    max_ai_y = max(max_ai_y, b.get("y", 0) + b.get("height", 0))
            # Only apply scaling if AI coords are significantly smaller than
            # the actual image (at least 1.5x smaller — means API downscaled)
            if max_ai_x > 0 and img_w / max_ai_x > 1.5:
                ai_scale_x = img_w / max_ai_x
            if max_ai_y > 0 and img_h / max_ai_y > 1.5:
                ai_scale_y = img_h / max_ai_y
            if ai_scale_x != 1.0 or ai_scale_y != 1.0:
                logger.info(
                    "AI vision: auto-scale %.2fx,%.2fy (AI max: %.0f,%.0f → img: %d,%d)",
                    ai_scale_x, ai_scale_y, max_ai_x, max_ai_y, img_w, img_h,
                )

        elements: List[ElementInfo] = []
        for i, raw in enumerate(result.elements):
            if not isinstance(raw, dict):
                logger.debug("AI vision: skipping non-dict element at index %d: %r", i, raw)
                continue
            b = raw.get("bounds", {})
            if isinstance(b, (list, tuple)) and len(b) >= 4:
                bx, by, bw, bh = b[0], b[1], b[2], b[3]
            elif isinstance(b, dict):
                bx = b.get("x", 0)
                by = b.get("y", 0)
                bw = b.get("width", 50)
                bh = b.get("height", 20)
            else:
                logger.debug("AI vision: skipping element %d with bad bounds: %r", i, b)
                continue
            # Convert [x1,y1,x2,y2] → [x,y,w,h] if detected
            if is_xyxy:
                bw = bw - bx  # x2 - x1 = width
                bh = bh - by  # y2 - y1 = height
            # Scale AI coords to physical screenshot pixels, then offset.
            # Clamp to >= 0 since negative screen coords aren't useful.
            ex = max(0, int(bx * ai_scale_x) + win_x)
            ey = max(0, int(by * ai_scale_y) + win_y)
            ew = int(bw * ai_scale_x)
            eh = int(bh * ai_scale_y)
            role = raw.get("role", "Unknown").capitalize()
            name = raw.get("name", "")
            elements.append(ElementInfo(
                id=f"ai_{i}",
                role=role,
                name=name,
                value=None,
                x=ex, y=ey, width=ew, height=eh,
                children=[],
                properties={"source": "vision", "confidence": raw.get("confidence", 0.5)},
            ))
        return elements
    except Exception as exc:
        logger.warning("AI vision element fetch failed: %s", exc, exc_info=True)
        return []
