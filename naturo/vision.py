"""High-level vision API: screenshot → AI analysis.

Orchestrates capture + AI provider to describe screen contents
or identify specific UI elements by natural language description.
"""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Optional

from naturo.backends.base import Backend, get_backend
from naturo.errors import AIProviderUnavailableError, CaptureFailedError
from naturo.providers.base import VisionProvider, VisionResult, get_vision_provider

logger = logging.getLogger(__name__)


def describe_screen(
    *,
    provider: Optional[VisionProvider] = None,
    provider_name: str = "auto",
    backend: Optional[Backend] = None,
    window_title: Optional[str] = None,
    screenshot_path: Optional[str] = None,
    prompt: Optional[str] = None,
    context: Optional[str] = None,
    max_tokens: int = 1024,
) -> VisionResult:
    """Capture the screen (or a window) and describe it with AI.

    Either provide a screenshot_path to an existing image, or let this
    function capture one automatically using the backend.

    Args:
        provider: Pre-configured vision provider (overrides provider_name).
        provider_name: Provider to use ('anthropic', 'openai', 'ollama', 'auto').
        backend: Desktop automation backend (auto-detected if None).
        window_title: Capture a specific window instead of full screen.
        screenshot_path: Use an existing screenshot instead of capturing.
        prompt: Custom analysis prompt.
        context: Additional context for the AI.
        max_tokens: Maximum tokens in the AI response.

    Returns:
        VisionResult with description and metadata.

    Raises:
        AIProviderUnavailableError: No suitable AI provider found.
        CaptureFailedError: Screenshot capture failed.
    """
    if provider is None:
        provider = get_vision_provider(provider_name)

    # Get or capture screenshot
    image_path = screenshot_path
    temp_path = None

    if image_path is None:
        if backend is None:
            backend = get_backend()

        try:
            fd, temp_path = tempfile.mkstemp(suffix=".png", prefix="naturo_vision_")
            os.close(fd)
            image_path = temp_path

            if window_title:
                result = backend.capture_window(
                    window_title=window_title,
                    output_path=image_path,
                )
            else:
                result = backend.capture_screen(output_path=image_path)

            if context is None and window_title:
                context = f"Screenshot of window: {window_title}"

        except Exception as e:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise CaptureFailedError(
                message=f"Failed to capture screen: {e}",
            )

    try:
        vision_result = provider.describe_screenshot(
            image_path,
            prompt=prompt,
            context=context,
            max_tokens=max_tokens,
        )
        return vision_result
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def identify_element(
    element_description: str,
    *,
    provider: Optional[VisionProvider] = None,
    provider_name: str = "auto",
    backend: Optional[Backend] = None,
    window_title: Optional[str] = None,
    screenshot_path: Optional[str] = None,
    max_tokens: int = 512,
) -> VisionResult:
    """Capture the screen and find a specific UI element by description.

    Args:
        element_description: Natural language description (e.g., "the Save button").
        provider: Pre-configured vision provider (overrides provider_name).
        provider_name: Provider to use ('anthropic', 'openai', 'ollama', 'auto').
        backend: Desktop automation backend (auto-detected if None).
        window_title: Capture a specific window.
        screenshot_path: Use an existing screenshot.
        max_tokens: Maximum tokens in the AI response.

    Returns:
        VisionResult with element info in the elements list.

    Raises:
        AIProviderUnavailableError: No suitable AI provider found.
        CaptureFailedError: Screenshot capture failed.
    """
    if provider is None:
        provider = get_vision_provider(provider_name)

    image_path = screenshot_path
    temp_path = None

    if image_path is None:
        if backend is None:
            backend = get_backend()

        try:
            fd, temp_path = tempfile.mkstemp(suffix=".png", prefix="naturo_vision_")
            os.close(fd)
            image_path = temp_path

            if window_title:
                backend.capture_window(
                    window_title=window_title,
                    output_path=image_path,
                )
            else:
                backend.capture_screen(output_path=image_path)
        except Exception as e:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise CaptureFailedError(
                message=f"Failed to capture screen: {e}",
            )

    try:
        return provider.identify_element(
            image_path,
            element_description,
            max_tokens=max_tokens,
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
