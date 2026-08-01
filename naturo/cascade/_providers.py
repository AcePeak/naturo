"""Provider fetching: CDP and AI vision element discovery."""
from __future__ import annotations

import logging
import time
from typing import List, Optional

from naturo.backends.base import ElementInfo

logger = logging.getLogger(__name__)

#: How many times to (re)connect to the CDP endpoint before giving up.
#: Real Electron apps frequently expose the DevTools endpoint a beat before the
#: renderer target is enumerable (or drop the first WebSocket while the agent
#: settles), so a single attempt is racy; a few bounded retries make the attach
#: reliable without hanging the cascade.
_CDP_ATTACH_ATTEMPTS = 4
#: Base back-off between CDP attach attempts (seconds); grows linearly.
_CDP_ATTACH_BACKOFF_S = 0.4


def _fetch_cdp_dom_elements(debug_port: int) -> List[dict]:
    """Connect to the CDP endpoint and return raw interactive DOM elements.

    Performs a bounded connect/enumerate/reconnect loop: a real Electron app may
    briefly report no enumerable page target or drop the first WebSocket while
    its DevTools agent settles, so a single attempt is unreliable.  Each attempt
    opens a fresh :class:`~naturo.cdp.CDPClient`, fetches elements, and closes
    it; the first attempt that returns a non-empty result wins.

    Args:
        debug_port: Chrome DevTools Protocol port to attach to.

    Returns:
        The raw DOM-element dicts from CDP, or an empty list if the optional
        CDP module is unavailable, every attempt failed, or the page genuinely
        has no interactive content.
    """
    try:
        from naturo.cdp import CDPClient
    except ImportError:
        logger.debug("CDP module not available; skipping CDP provider")
        return []

    last_exc: Optional[Exception] = None
    for attempt in range(1, _CDP_ATTACH_ATTEMPTS + 1):
        client = CDPClient(port=debug_port)
        try:
            client.connect()
            dom_elements = client.get_interactive_elements()
            if dom_elements:
                return dom_elements
            # Connected but nothing yet — the renderer may still be painting.
            logger.debug(
                "CDP attach %d/%d: connected but no elements yet (port=%d)",
                attempt, _CDP_ATTACH_ATTEMPTS, debug_port,
            )
        except Exception as exc:
            # Broad by design: any attach/enumeration failure is transient from
            # the cascade's view — record it and retry on the next attempt.
            last_exc = exc
            logger.debug(
                "CDP attach %d/%d failed (port=%d): %s",
                attempt, _CDP_ATTACH_ATTEMPTS, debug_port, exc,
            )
        finally:
            try:
                client.close()
            except Exception:
                # Best-effort cleanup; a failed close must not mask results.
                pass

        if attempt < _CDP_ATTACH_ATTEMPTS:
            time.sleep(_CDP_ATTACH_BACKOFF_S * attempt)

    if last_exc is not None:
        logger.debug(
            "CDP attach exhausted %d attempts (port=%d): %s",
            _CDP_ATTACH_ATTEMPTS, debug_port, last_exc,
        )
    return []


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
        dom_elements = _fetch_cdp_dom_elements(debug_port)

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


def _raw_bounds(
    b: object, default_w: float = 0.0, default_h: float = 0.0,
) -> Optional[tuple[float, float, float, float]]:
    """Normalize a raw AI ``bounds`` value to ``(a, b, c, d)`` floats.

    Accepts both the list form ``[x, y, w, h]`` (or ``[x1, y1, x2, y2]``) and the
    dict form ``{"x", "y", "width", "height"}``; returns ``None`` for anything
    unusable so callers can skip it. The third/fourth slots carry either w/h or
    x2/y2 — the caller knows which from the detected format.
    """
    if isinstance(b, (list, tuple)) and len(b) >= 4:
        return float(b[0]), float(b[1]), float(b[2]), float(b[3])
    if isinstance(b, dict):
        return (
            float(b.get("x", 0)), float(b.get("y", 0)),
            float(b.get("width", default_w)), float(b.get("height", default_h)),
        )
    return None


def _detect_xyxy_bounds(elements: list) -> bool:
    """Detect whether the AI returned ``[x1,y1,x2,y2]`` rather than ``[x,y,w,h]``.

    In corner form the 3rd/4th values are always >= the 1st/2nd; in width/height
    form they usually aren't. If >80% of elements look like corner form, treat the
    whole batch as ``xyxy``.
    """
    xyxy_count = total_checked = 0
    for raw in elements:
        if not isinstance(raw, dict):
            continue
        q = _raw_bounds(raw.get("bounds", {}))
        if q is None:
            continue
        v0, v1, v2, v3 = q
        total_checked += 1
        if v2 >= v0 and v3 >= v1:
            xyxy_count += 1
    if total_checked > 0 and xyxy_count / total_checked > 0.8:
        logger.info("AI vision: detected [x1,y1,x2,y2] bounds format (%d/%d)",
                    xyxy_count, total_checked)
        return True
    return False


def _detect_ai_scale(
    elements: list, img_w: int, img_h: int, is_xyxy: bool,
) -> tuple[float, float]:
    """Recover the downscale ratio when the AI answered in a smaller pixel space.

    Claude's vision API internally downscales large images, so the returned coords
    live in that smaller space. Compare the max coord the AI emitted against the
    real screenshot size; only correct when the gap is >1.5x (a genuine downscale,
    not measurement noise). Returns ``(1.0, 1.0)`` when no correction is needed.
    """
    ai_scale_x, ai_scale_y = 1.0, 1.0
    if not (img_w > 0 and img_h > 0 and elements):
        return ai_scale_x, ai_scale_y
    max_ai_x = max_ai_y = 0.0
    for raw in elements:
        if not isinstance(raw, dict):
            continue
        q = _raw_bounds(raw.get("bounds", {}))
        if q is None:
            continue
        v0, v1, v2, v3 = q
        if is_xyxy:  # v2,v3 are already the max (x2,y2) corner
            max_ai_x, max_ai_y = max(max_ai_x, v2), max(max_ai_y, v3)
        else:
            max_ai_x, max_ai_y = max(max_ai_x, v0 + v2), max(max_ai_y, v1 + v3)
    if max_ai_x > 0 and img_w / max_ai_x > 1.5:
        ai_scale_x = img_w / max_ai_x
    if max_ai_y > 0 and img_h / max_ai_y > 1.5:
        ai_scale_y = img_h / max_ai_y
    if ai_scale_x != 1.0 or ai_scale_y != 1.0:
        logger.info(
            "AI vision: auto-scale %.2fx,%.2fy (AI max: %.0f,%.0f → img: %d,%d)",
            ai_scale_x, ai_scale_y, max_ai_x, max_ai_y, img_w, img_h)
    return ai_scale_x, ai_scale_y


def _ai_raw_to_element(
    i: int, raw: object, is_xyxy: bool,
    ai_scale_x: float, ai_scale_y: float, win_x: int, win_y: int,
) -> Optional[ElementInfo]:
    """Convert one raw AI dict into a screen-coordinate :class:`ElementInfo`.

    Applies the detected corner->wh conversion and downscale ratio, then offsets
    by the window origin and clamps to non-negative screen coords. Returns
    ``None`` (and logs at debug) for malformed entries so the caller skips them.
    """
    if not isinstance(raw, dict):
        logger.debug("AI vision: skipping non-dict element at index %d: %r", i, raw)
        return None
    q = _raw_bounds(raw.get("bounds", {}), default_w=50.0, default_h=20.0)
    if q is None:
        logger.debug("AI vision: skipping element %d with bad bounds: %r",
                     i, raw.get("bounds", {}))
        return None
    bx, by, bw, bh = q
    if is_xyxy:  # corner form → width/height
        bw, bh = bw - bx, bh - by
    # Scale AI coords to physical screenshot pixels, then offset by the window
    # origin. Clamp to >= 0 since negative screen coords aren't useful.
    ex = max(0, int(bx * ai_scale_x) + win_x)
    ey = max(0, int(by * ai_scale_y) + win_y)
    ew = int(bw * ai_scale_x)
    eh = int(bh * ai_scale_y)
    return ElementInfo(
        id=f"ai_{i}",
        role=raw.get("role", "Unknown").capitalize(),
        name=raw.get("name", ""),
        value=None,
        x=ex, y=ey, width=ew, height=eh,
        children=[],
        properties={"source": "vision", "confidence": raw.get("confidence", 0.5)},
    )


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

        # (#694) The AI may answer in [x1,y1,x2,y2] corner form and/or in a
        # downscaled pixel space (Claude's API shrinks large images). Detect both
        # from the batch, then parse each element through the shared converter.
        is_xyxy = _detect_xyxy_bounds(result.elements)
        ai_scale_x, ai_scale_y = _detect_ai_scale(result.elements, img_w, img_h, is_xyxy)

        elements: List[ElementInfo] = []
        for i, raw in enumerate(result.elements):
            el = _ai_raw_to_element(
                i, raw, is_xyxy, ai_scale_x, ai_scale_y, win_x, win_y)
            if el is not None:
                elements.append(el)
        return elements
    except Exception as exc:
        logger.warning("AI vision element fetch failed: %s", exc, exc_info=True)
        return []
