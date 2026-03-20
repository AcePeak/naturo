"""AI-powered element finding: screenshot + vision + UIA tree refinement.

Combines AI vision analysis with UIA accessibility tree for precise
element location. The AI identifies approximate bounds from a screenshot,
then we match against the UIA tree for exact element info.

This is Phase 4.3 of the Naturo roadmap.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional

from naturo.providers.base import VisionProvider, VisionResult, get_vision_provider
from naturo.vision import identify_element

logger = logging.getLogger(__name__)


@dataclass
class AIFindResult:
    """Result from AI-powered element finding.

    Attributes:
        found: Whether the element was located.
        description: AI's description of the element.
        ai_bounds: Raw bounds from AI vision (approximate).
        element: UIA element info if matched (exact).
        confidence: AI confidence score (0.0-1.0).
        model: AI model used.
        tokens_used: Token count for the AI call.
        method: How the element was found ('ai_only', 'ai+uia', 'uia_fallback').
    """

    found: bool
    description: str = ""
    ai_bounds: Optional[dict[str, Any]] = None
    element: Optional[dict[str, Any]] = None
    confidence: float = 0.0
    model: str = ""
    tokens_used: int = 0
    method: str = "ai_only"


def ai_find_element(
    query: str,
    *,
    provider: Optional[VisionProvider] = None,
    provider_name: str = "auto",
    window_title: Optional[str] = None,
    screenshot_path: Optional[str] = None,
    refine_with_uia: bool = True,
    max_tokens: int = 512,
) -> AIFindResult:
    """Find a UI element using natural language and AI vision.

    Takes a screenshot, asks the AI to locate the described element,
    and optionally refines the result against the UIA accessibility tree.

    Args:
        query: Natural language description (e.g., "the Save button",
               "the search field in the top right").
        provider: Pre-configured vision provider.
        provider_name: Provider name for auto-detection.
        window_title: Target a specific window.
        screenshot_path: Use an existing screenshot.
        refine_with_uia: If True, match AI bounds against UIA tree for
                         precise element info (Windows only).
        max_tokens: Maximum tokens for the AI response.

    Returns:
        AIFindResult with element info and confidence.

    Raises:
        AIProviderUnavailableError: No AI provider configured.
        CaptureFailedError: Screenshot capture failed.
    """
    if provider is None:
        provider = get_vision_provider(provider_name)

    # Step 1: AI vision identifies the element
    vision_result = identify_element(
        query,
        provider=provider,
        screenshot_path=screenshot_path,
        window_title=window_title,
        max_tokens=max_tokens,
    )

    # Parse AI response
    if not vision_result.elements:
        return AIFindResult(
            found=False,
            description=vision_result.description,
            confidence=0.0,
            model=vision_result.model,
            tokens_used=vision_result.tokens_used,
            method="ai_only",
        )

    ai_element = vision_result.elements[0]
    ai_found = ai_element.get("found", False)
    ai_confidence = ai_element.get("confidence", 0.0)
    ai_bounds = ai_element.get("bounds", {})

    if not ai_found:
        return AIFindResult(
            found=False,
            description=ai_element.get("description", vision_result.description),
            ai_bounds=ai_bounds if ai_bounds else None,
            confidence=ai_confidence,
            model=vision_result.model,
            tokens_used=vision_result.tokens_used,
            method="ai_only",
        )

    result = AIFindResult(
        found=True,
        description=ai_element.get("description", vision_result.description),
        ai_bounds=ai_bounds,
        confidence=ai_confidence,
        model=vision_result.model,
        tokens_used=vision_result.tokens_used,
        method="ai_only",
    )

    # Step 2: Optionally refine with UIA tree
    if refine_with_uia and ai_bounds and _has_valid_coords(ai_bounds):
        try:
            uia_element = _match_uia_element(ai_bounds, window_title=window_title)
            if uia_element is not None:
                result.element = uia_element
                result.method = "ai+uia"
        except Exception as e:
            logger.debug("UIA refinement failed (non-fatal): %s", e)
            # Keep AI-only result

    return result


def _has_valid_coords(bounds: dict[str, Any]) -> bool:
    """Check if bounds dict has valid x,y coordinates.

    Args:
        bounds: Dict with x, y (and optionally width, height).

    Returns:
        True if x and y are present and numeric.
    """
    x = bounds.get("x")
    y = bounds.get("y")
    return x is not None and y is not None and isinstance(x, (int, float)) and isinstance(y, (int, float))


def _match_uia_element(
    ai_bounds: dict[str, Any],
    *,
    window_title: Optional[str] = None,
    depth: int = 8,
    tolerance: float = 50.0,
) -> Optional[dict[str, Any]]:
    """Match AI-identified bounds against the UIA accessibility tree.

    Finds the UIA element closest to the AI's reported center point.

    Args:
        ai_bounds: Bounds from AI vision (x, y center point + optional w/h).
        window_title: Target window for the UIA tree.
        depth: Maximum depth for UIA tree traversal.
        tolerance: Maximum distance (pixels) between AI center and UIA element center.

    Returns:
        Dict with element info if a match is found, None otherwise.
    """
    import platform as _platform

    if _platform.system() != "Windows":
        return None

    from naturo.backends.base import get_backend

    backend = get_backend()
    tree = backend.get_element_tree(
        depth=depth,
        window_title=window_title,
    )
    if tree is None:
        return None

    target_x = float(ai_bounds.get("x", 0))
    target_y = float(ai_bounds.get("y", 0))

    # Flatten tree and find closest element to the target point
    best_match = None
    best_distance = float("inf")

    def _walk(element: Any) -> None:
        nonlocal best_match, best_distance

        # Skip elements with no bounds
        if element.width <= 0 or element.height <= 0:
            for child in element.children:
                _walk(child)
            return

        # Calculate center of the UIA element
        cx = element.x + element.width / 2
        cy = element.y + element.height / 2

        distance = math.sqrt((cx - target_x) ** 2 + (cy - target_y) ** 2)

        if distance < best_distance and distance <= tolerance:
            best_distance = distance
            best_match = element

        for child in element.children:
            _walk(child)

    _walk(tree)

    if best_match is None:
        return None

    return {
        "id": best_match.id,
        "role": best_match.role,
        "name": best_match.name,
        "value": best_match.value,
        "bounds": {
            "x": best_match.x,
            "y": best_match.y,
            "width": best_match.width,
            "height": best_match.height,
        },
        "properties": best_match.properties,
        "match_distance": round(best_distance, 1),
    }
