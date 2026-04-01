"""Google Gemini vision provider for Naturo.

Uses the Google Generative AI (Gemini) REST API to analyze screenshots.
Requires ``GOOGLE_API_KEY`` environment variable or explicit ``api_key``.

Get an API key at: https://aistudio.google.com/apikey
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from naturo.errors import AIAnalysisFailedError, AIProviderUnavailableError
from naturo.providers.base import (
    VisionResult,
    encode_image_base64,
    detect_media_type,
    parse_ai_elements_json,
    register_provider,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"

_DEFAULT_DESCRIBE_PROMPT = """\
Analyze this screenshot and describe what you see. Include:
1. The application name and window state
2. Key UI elements visible (buttons, text fields, menus, etc.)
3. Any text content shown
4. The current state/context (what appears to be happening)

Be concise but thorough. Focus on actionable information an automation tool would need."""

_DEFAULT_IDENTIFY_PROMPT = """\
Find the UI element described as: "{element_description}"

Look at the screenshot and identify the element. Return a JSON object with:
- "found": true/false
- "description": what you see at that location
- "bounds": {{"x": <center_x>, "y": <center_y>, "width": <estimated_width>, "height": <estimated_height>}}
- "confidence": 0.0-1.0

Return ONLY the JSON object, no other text."""


class GoogleVisionProvider:
    """Google Gemini vision provider.

    Uses the Gemini API's vision capability to analyze screenshots.
    Calls the ``generateContent`` REST endpoint directly (no SDK dependency).

    Args:
        api_key: Google API key (defaults to ``GOOGLE_API_KEY`` env var).
        model: Model name (defaults to ``gemini-2.5-flash``).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        self._model = model or os.environ.get("NATURO_AI_MODEL", _DEFAULT_MODEL)

    @property
    def name(self) -> str:
        """Provider name."""
        return "google"

    @property
    def is_available(self) -> bool:
        """Whether the Google API key is configured."""
        return bool(self._api_key)

    def describe_screenshot(
        self,
        image_path: str,
        *,
        prompt: Optional[str] = None,
        context: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> VisionResult:
        """Analyze a screenshot using Gemini vision.

        Args:
            image_path: Path to screenshot file (PNG/JPG).
            prompt: Custom analysis prompt (overrides default).
            context: Additional context about the screenshot.
            max_tokens: Maximum tokens in the response.

        Returns:
            VisionResult with description.

        Raises:
            AIProviderUnavailableError: API key not set.
            AIAnalysisFailedError: API request failed.
        """
        text_prompt = prompt or _DEFAULT_DESCRIBE_PROMPT
        if context:
            text_prompt = f"Context: {context}\n\n{text_prompt}"
        return self._call_gemini(image_path, text_prompt, max_tokens=max_tokens)

    def identify_element(
        self,
        image_path: str,
        element_description: str,
        *,
        max_tokens: int = 4096,
    ) -> VisionResult:
        """Find a specific UI element using Gemini vision.

        Args:
            image_path: Path to screenshot file.
            element_description: Natural language description of the element.
            max_tokens: Maximum tokens in the response.

        Returns:
            VisionResult with element location info.

        Raises:
            AIProviderUnavailableError: API key not set.
            AIAnalysisFailedError: API request failed.
        """
        text_prompt = _DEFAULT_IDENTIFY_PROMPT.format(
            element_description=element_description,
        )
        result = self._call_gemini(image_path, text_prompt, max_tokens=max_tokens)
        result.elements = parse_ai_elements_json(result.description)
        return result

    def enumerate_elements(
        self,
        image_path: str,
        prompt: str,
        *,
        max_tokens: int = 16384,
    ) -> VisionResult:
        """Enumerate all UI elements in a screenshot."""
        result = self._call_gemini(image_path, prompt, max_tokens=max_tokens)
        result.elements = parse_ai_elements_json(result.description)
        return result

    def _call_gemini(
        self,
        image_path: str,
        text_prompt: str,
        *,
        max_tokens: int = 4096,
    ) -> VisionResult:
        """Send an image + text prompt to the Gemini ``generateContent`` endpoint.

        Args:
            image_path: Path to image file.
            text_prompt: Text prompt.
            max_tokens: Maximum output tokens.

        Returns:
            VisionResult with response.

        Raises:
            AIProviderUnavailableError: API key missing.
            AIAnalysisFailedError: Request failed.
        """
        import urllib.request
        import urllib.error

        if not self._api_key:
            raise AIProviderUnavailableError(
                provider="google",
                suggested_action="Set GOOGLE_API_KEY environment variable",
            )

        image_data = encode_image_base64(image_path)
        media_type = detect_media_type(image_path)

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._api_key}"
        )

        payload = json.dumps({
            "contents": [{
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"text": text_prompt},
                ],
            }],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
            },
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            logger.error("Gemini API error: HTTP %s — %s", exc.code, body)
            raise AIAnalysisFailedError(
                message=f"Gemini API error (HTTP {exc.code}): {body}",
            )
        except Exception as exc:
            logger.error("Gemini API error: %s", exc)
            raise AIAnalysisFailedError(
                message=f"Gemini API error: {exc}",
            )

        # Extract text from response
        description = ""
        tokens_used = 0
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                if "text" in part:
                    description += part["text"]

        usage = data.get("usageMetadata", {})
        tokens_used = (
            usage.get("promptTokenCount", 0)
            + usage.get("candidatesTokenCount", 0)
        )

        return VisionResult(
            description=description.strip(),
            model=self._model,
            tokens_used=tokens_used,
            raw_response=data,
        )


# Register this provider
register_provider("google", GoogleVisionProvider)
