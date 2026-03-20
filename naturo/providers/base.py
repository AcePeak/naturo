"""Base protocol and factory for AI vision providers.

Defines the VisionProvider interface that all AI backends must implement,
plus a factory function to instantiate providers by name.
"""
from __future__ import annotations

import base64
import os
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
        max_tokens: int = 512,
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
    priority = ["anthropic", "openai", "ollama"]
    for pname in priority:
        cls = _PROVIDER_CLASSES.get(pname)
        if cls is None:
            continue
        try:
            provider = cls(**kwargs)
            if provider.is_available:
                return provider
        except Exception:
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
        except Exception:
            pass
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
