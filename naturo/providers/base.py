"""Base protocol and factory for AI vision providers.

Defines the VisionProvider interface that all AI backends must implement,
plus a factory function to instantiate providers by name.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

from naturo.errors import AIProviderUnavailableError


@dataclass
class VisionResult:
    """Result from AI vision analysis of a screenshot.

    Attributes:
        description: Natural language description of what's on screen.
        elements: Identified UI elements with labels and locations.
        raw_response: Full provider response for debugging.
        model: Model name used for analysis.
        tokens_used: Approximate token count (input + output).
    """
    description: str
    elements: list[dict[str, Any]] = field(default_factory=list)
    raw_response: Any = None
    model: str = ""
    tokens_used: int = 0


@runtime_checkable
class VisionProvider(Protocol):
    """Interface for AI vision providers.

    Implementations must accept a screenshot (as file path or base64)
    and return a structured description of the screen contents.
    """

    @property
    def name(self) -> str:
        """Provider name (e.g., 'anthropic', 'openai', 'ollama')."""
        ...

    @property
    def is_available(self) -> bool:
        """Whether this provider is configured and usable (API key present, etc.)."""
        ...

    def describe_screenshot(
        self,
        image_path: str,
        *,
        prompt: Optional[str] = None,
        context: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> VisionResult:
        """Analyze a screenshot and describe its contents.

        Args:
            image_path: Path to screenshot file (PNG/JPG).
            prompt: Custom analysis prompt (overrides default).
            context: Additional context (e.g., "This is a Notepad window").
            max_tokens: Maximum tokens in the response.

        Returns:
            VisionResult with description and identified elements.

        Raises:
            AIProviderUnavailableError: Provider not configured.
            AIAnalysisFailedError: Analysis request failed.
        """
        ...

    def identify_element(
        self,
        image_path: str,
        element_description: str,
        *,
        max_tokens: int = 4096,
    ) -> VisionResult:
        """Find a specific UI element in a screenshot.

        Args:
            image_path: Path to screenshot file.
            element_description: Natural language description (e.g., "the Save button").
            max_tokens: Maximum tokens in the response.

        Returns:
            VisionResult with element location info.

        Raises:
            AIProviderUnavailableError: Provider not configured.
            AIAnalysisFailedError: Analysis request failed.
        """
        ...

    def enumerate_elements(
        self,
        image_path: str,
        prompt: str,
        *,
        max_tokens: int = 16384,
    ) -> VisionResult:
        """Enumerate all UI elements in a screenshot.

        Unlike ``identify_element`` which wraps the description in a
        template for single-element lookup, this sends the prompt directly
        to the AI.  Used by cascade AI vision for full element enumeration.

        Args:
            image_path: Path to screenshot file.
            prompt: Complete prompt text (no template wrapping).
            max_tokens: Maximum tokens in the response.

        Returns:
            VisionResult with all identified elements.
        """
        ...


def encode_image_base64(image_path: str) -> str:
    """Read an image file and return its base64-encoded contents.

    Args:
        image_path: Path to image file.

    Returns:
        Base64-encoded string.

    Raises:
        FileNotFoundError: Image file does not exist.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def detect_media_type(image_path: str) -> str:
    """Detect MIME type from file extension.

    Args:
        image_path: Path to image file.

    Returns:
        MIME type string (e.g., 'image/png').
    """
    ext = os.path.splitext(image_path)[1].lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }.get(ext, "image/png")


logger = logging.getLogger(__name__)

# Regex to extract JSON from markdown code fences (```json ... ``` or ``` ... ```)
# Flexible: handles \n, \r\n, or spaces after opening fence; closing fence on its own line or inline
_CODE_FENCE_RE = re.compile(r"```(?:json)?[ \t]*[\r\n]+(.*?)[\r\n]+\s*```", re.DOTALL)


def parse_ai_elements_json(raw_text: str) -> list[dict[str, Any]]:
    """Parse AI vision response text into a list of element dicts.

    Handles common AI response formats:
    - A plain JSON array: ``[{"role": "Button", ...}, ...]``
    - JSON wrapped in markdown code fences: ``\\`\\`\\`json\\n[...]\\n\\`\\`\\```
    - A wrapper object with an array field: ``{"elements": [...]}``
    - Prose before/after the JSON block

    Args:
        raw_text: Raw text response from an AI vision provider.

    Returns:
        List of element dicts. Empty list if parsing fails entirely.
    """
    if not raw_text or not raw_text.strip():
        return []

    json_text = _extract_json_text(raw_text)
    if json_text is None:
        logger.warning(
            "Failed to parse element identification as JSON: %s",
            raw_text[:200],
        )
        return []

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        # AI sometimes returns Python tuples (x, y, w, h) instead of
        # JSON arrays [x, y, w, h]. Convert and retry.
        import re as _re
        fixed = _re.sub(
            r'"bounds"\s*:\s*\(([^)]+)\)',
            r'"bounds": [\1]',
            json_text,
        )
        if fixed != json_text:
            try:
                parsed = json.loads(fixed)
            except json.JSONDecodeError:
                logger.warning(
                    "Failed to parse element identification as JSON: %s",
                    raw_text[:200],
                )
                return []
        else:
            logger.warning(
                "Failed to parse element identification as JSON: %s",
                raw_text[:200],
            )
            return []

    return _normalize_parsed(parsed)


def _extract_json_text(raw_text: str) -> Optional[str]:
    """Extract JSON string from raw AI response text.

    Tries in order:
    1. Content inside markdown code fences
    2. First JSON array ``[...]`` in the text
    3. First JSON object ``{...}`` in the text
    4. The entire stripped text as-is

    Args:
        raw_text: Raw AI response text.

    Returns:
        Extracted JSON string, or None if nothing looks like JSON.
    """
    text = raw_text.strip()

    # 1. Try markdown code fences (regex handles newlines)
    match = _CODE_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()

    # 1b. Fallback: strip code fences manually if regex missed
    #     Handles edge cases like no newline before closing ```
    if text.startswith("```"):
        # Remove opening fence line
        first_newline = text.find("\n")
        if first_newline != -1:
            inner = text[first_newline + 1:]
            # Remove closing fence
            last_fence = inner.rfind("```")
            if last_fence != -1:
                inner = inner[:last_fence]
            return inner.strip()

    # 2. Try to find a JSON array
    arr_start = text.find("[")
    if arr_start != -1:
        arr_end = text.rfind("]")
        if arr_end > arr_start:
            return text[arr_start:arr_end + 1]

    # 3. Try to find a JSON object
    obj_start = text.find("{")
    if obj_start != -1:
        obj_end = text.rfind("}")
        if obj_end > obj_start:
            return text[obj_start:obj_end + 1]

    # 4. Try the whole thing
    return text if text else None


def _normalize_parsed(parsed: Any) -> list[dict[str, Any]]:
    """Normalize parsed JSON into a flat list of element dicts.

    Args:
        parsed: Parsed JSON value (could be list, dict, or other).

    Returns:
        Flat list of element dicts.
    """
    # Already a list — return dicts only
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]

    # A wrapper object — look for a known array field
    if isinstance(parsed, dict):
        for key in ("elements", "items", "results", "found_elements"):
            if key in parsed and isinstance(parsed[key], list):
                return [item for item in parsed[key] if isinstance(item, dict)]
        # Single element dict with expected keys (role/name/bounds)
        if any(k in parsed for k in ("role", "name", "bounds", "label")):
            return [parsed]
        # Unknown dict structure — return empty
        logger.debug("AI returned dict without recognized element keys: %s", list(parsed.keys()))
        return []

    return []


# ── Provider Registry ──────────────────────────


_PROVIDER_CLASSES: dict[str, type] = {}


def register_provider(name: str, cls: type) -> None:
    """Register a provider class by name.

    Args:
        name: Provider name (e.g., 'anthropic').
        cls: Provider class to register.
    """
    _PROVIDER_CLASSES[name] = cls


def get_vision_provider(name: str = "auto", **kwargs: Any) -> VisionProvider:
    """Get a vision provider by name, with auto-detection fallback.

    Args:
        name: Provider name ('anthropic', 'openai', 'ollama', or 'auto').
        **kwargs: Extra arguments passed to the provider constructor.

    Returns:
        Configured VisionProvider instance.

    Raises:
        AIProviderUnavailableError: No suitable provider found.
    """
    # Lazy-import providers to register them
    _ensure_providers_registered()

    if name == "auto":
        return _auto_detect_provider(**kwargs)

    cls = _PROVIDER_CLASSES.get(name)
    if cls is None:
        available = ", ".join(sorted(_PROVIDER_CLASSES.keys())) or "none"
        raise AIProviderUnavailableError(
            provider=name,
            suggested_action=f"Available providers: {available}",
        )

    provider = cls(**kwargs)
    if not provider.is_available:
        raise AIProviderUnavailableError(
            provider=name,
            suggested_action=f"Set the required API key for {name}",
        )
    return provider


def _auto_detect_provider(**kwargs: Any) -> VisionProvider:
    """Try providers in priority order, return first available."""
    priority = ["anthropic", "openai", "gemini", "ollama"]
    for pname in priority:
        cls = _PROVIDER_CLASSES.get(pname)
        if cls is None:
            continue
        try:
            provider = cls(**kwargs)
            if provider.is_available:
                return provider
        except Exception as exc:
            logger.debug("Provider %s init failed: %s", pname, exc)
            continue

    raise AIProviderUnavailableError(
        provider="auto",
        suggested_action=(
            "No AI provider configured. Set one of: "
            "ANTHROPIC_API_KEY, OPENAI_API_KEY, or configure Ollama"
        ),
    )


def list_available_providers() -> list[str]:
    """Return names of providers that are currently configured and usable.

    Returns:
        List of provider name strings.
    """
    _ensure_providers_registered()
    available = []
    for pname, cls in sorted(_PROVIDER_CLASSES.items()):
        try:
            provider = cls()
            if provider.is_available:
                available.append(pname)
        except Exception as exc:
            logger.debug("Provider %s availability check failed: %s", pname, exc)
    return available


_registered = False


def _ensure_providers_registered() -> None:
    """Import provider modules to trigger registration (once)."""
    global _registered
    if _registered:
        return
    _registered = True
    # Import each provider module — they call register_provider() at import time
    try:
        import naturo.providers.anthropic_provider  # noqa: F401
    except ImportError:
        pass
    try:
        import naturo.providers.openai_provider  # noqa: F401
    except ImportError:
        pass
    try:
        import naturo.providers.ollama_provider  # noqa: F401
    except ImportError:
        pass
    try:
        import naturo.providers.gemini_provider  # noqa: F401
    except ImportError:
        pass
