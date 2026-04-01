"""Google Gemini vision provider for Naturo.

Uses the Google Generative AI API with vision capability to analyze screenshots.

Auth (in priority order):
1. ``api_key`` constructor argument (explicit override)
2. ``GOOGLE_API_KEY`` environment variable
3. ``~/.config/naturo/credentials.json`` — ``gemini.api_key`` field
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Optional

from naturo.config import load_credentials as _load_credentials
from naturo.errors import AIAnalysisFailedError, AIProviderUnavailableError
from naturo.providers.base import (
    VisionResult,
    detect_media_type,
    encode_image_base64,
    parse_ai_elements_json,
    register_provider,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Model aliases — resolve shorthand to canonical model IDs
_MODEL_ALIASES: dict[str, str] = {
    "gemini-flash": "gemini-2.5-flash",
    "gemini-pro": "gemini-2.5-pro",
    "flash": "gemini-2.5-flash",
    "pro": "gemini-2.5-pro",
}

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


def _resolve_api_key(explicit_key: Optional[str] = None) -> str:
    """Resolve the best available Google API key.

    Args:
        explicit_key: Explicitly provided API key (highest priority).

    Returns:
        API key string, or empty string if none found.
    """
    if explicit_key:
        return explicit_key

    env_key = os.environ.get("GOOGLE_API_KEY", "")
    if env_key:
        return env_key

    creds = _load_credentials()
    return str(creds.get("gemini", {}).get("api_key", ""))


def _resolve_model(model: Optional[str]) -> str:
    """Resolve model name, expanding aliases.

    Args:
        model: User-provided model name or alias.

    Returns:
        Canonical model ID.
    """
    if model is None:
        model = os.environ.get("NATURO_AI_MODEL", _DEFAULT_MODEL)
    return _MODEL_ALIASES.get(model, model)


class GeminiVisionProvider:
    """Google Gemini vision provider.

    Uses Gemini's vision capability to analyze screenshots via the
    REST API (no SDK dependency required).

    Args:
        api_key: Google API key (defaults to GOOGLE_API_KEY env var).
        model: Model name (defaults to gemini-2.5-flash).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._api_key = _resolve_api_key(api_key)
        self._model = _resolve_model(model)

    @property
    def name(self) -> str:
        """Provider name."""
        return "gemini"

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
        """Analyze a screenshot and describe its contents.

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

        result = self._call_gemini(image_path, text_prompt, max_tokens=max_tokens)
        return result

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
            element_description: Natural language description of the element.
            max_tokens: Maximum tokens in the response.

        Returns:
            VisionResult with element location info.

        Raises:
            AIProviderUnavailableError: API key not set.
            AIAnalysisFailedError: API request failed.
        """
        text_prompt = _DEFAULT_IDENTIFY_PROMPT.format(
            element_description=element_description
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
        """Enumerate all UI elements in a screenshot.

        Args:
            image_path: Path to screenshot file.
            prompt: Complete prompt text (no template wrapping).
            max_tokens: Maximum tokens in the response.

        Returns:
            VisionResult with all identified elements.
        """
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
        """Make a Gemini API call with image.

        Uses the REST API directly to avoid requiring the google-generativeai
        SDK as a hard dependency.

        Args:
            image_path: Path to image file.
            text_prompt: Text prompt.
            max_tokens: Maximum tokens in response.

        Returns:
            VisionResult with response.

        Raises:
            AIProviderUnavailableError: API key not set.
            AIAnalysisFailedError: Request failed.
        """
        if not self.is_available:
            raise AIProviderUnavailableError(
                provider="gemini",
                suggested_action="Set GOOGLE_API_KEY environment variable",
            )

        image_data = encode_image_base64(image_path)
        media_type = detect_media_type(image_path)

        url = (
            f"{_API_BASE_URL}/models/{self._model}:generateContent"
            f"?key={self._api_key}"
        )

        payload = json.dumps({
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": media_type,
                                "data": image_data,
                            }
                        },
                        {
                            "text": text_prompt,
                        },
                    ]
                }
            ],
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
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            logger.error("Gemini API HTTP %d: %s", e.code, body[:500])
            raise AIAnalysisFailedError(
                message=f"Gemini API error (HTTP {e.code}): {body[:200]}",
            )
        except urllib.error.URLError as e:
            raise AIAnalysisFailedError(
                message=f"Gemini API connection error: {e}",
            )
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            raise AIAnalysisFailedError(
                message=f"Gemini API error: {e}",
            )

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> VisionResult:
        """Parse a Gemini API response into a VisionResult.

        Args:
            data: Raw JSON response from the Gemini API.

        Returns:
            VisionResult with extracted text and token counts.

        Raises:
            AIAnalysisFailedError: Response has no valid content.
        """
        candidates = data.get("candidates", [])
        if not candidates:
            error_msg = data.get("error", {}).get("message", "No candidates returned")
            raise AIAnalysisFailedError(
                message=f"Gemini returned no results: {error_msg}",
            )

        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [p["text"] for p in parts if "text" in p]
        description = "\n".join(text_parts).strip()

        usage = data.get("usageMetadata", {})
        tokens_used = (
            usage.get("promptTokenCount", 0)
            + usage.get("candidatesTokenCount", 0)
        )

        return VisionResult(
            description=description,
            model=self._model,
            tokens_used=tokens_used,
            raw_response=data,
        )


# Register this provider
register_provider("gemini", GeminiVisionProvider)
