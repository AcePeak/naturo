"""OpenAI (GPT-4) vision provider for Naturo.

Uses the OpenAI Chat Completions API with vision to analyze screenshots.
Requires OPENAI_API_KEY environment variable.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from naturo.errors import AIAnalysisFailedError, AIProviderUnavailableError
from naturo.providers.base import (
    VisionResult,
    detect_media_type,
    encode_image_base64,
    register_provider,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-4o"
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


class OpenAIVisionProvider:
    """OpenAI GPT-4 Vision provider.

    Uses GPT-4o's vision capability to analyze screenshots.

    Args:
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var).
        model: Model name (defaults to gpt-4o).
        base_url: Custom API base URL (for Azure OpenAI or compatible APIs).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model or os.environ.get("NATURO_AI_MODEL", _DEFAULT_MODEL)
        self._base_url = base_url or os.environ.get("OPENAI_BASE_URL")

    @property
    def name(self) -> str:
        """Provider name."""
        return "openai"

    @property
    def is_available(self) -> bool:
        """Whether the OpenAI API key is configured."""
        return bool(self._api_key)

    def _get_client(self) -> Any:
        """Get or create OpenAI client.

        Returns:
            OpenAI client instance.

        Raises:
            AIProviderUnavailableError: openai package not installed.
        """
        try:
            import openai
        except ImportError:
            raise AIProviderUnavailableError(
                provider="openai",
                suggested_action="Install openai: pip install openai",
            )
        kwargs: dict[str, Any] = {"api_key": self._api_key}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        return openai.OpenAI(**kwargs)

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
            AIProviderUnavailableError: API key not set or package missing.
            AIAnalysisFailedError: API request failed.
        """
        if not self.is_available:
            raise AIProviderUnavailableError(
                provider="openai",
                suggested_action="Set OPENAI_API_KEY environment variable",
            )

        client = self._get_client()
        image_data = encode_image_base64(image_path)
        media_type = detect_media_type(image_path)

        text_prompt = prompt or _DEFAULT_DESCRIBE_PROMPT
        if context:
            text_prompt = f"Context: {context}\n\n{text_prompt}"

        try:
            response = client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_data}",
                                },
                            },
                            {
                                "type": "text",
                                "text": text_prompt,
                            },
                        ],
                    }
                ],
            )
        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            raise AIAnalysisFailedError(
                message=f"OpenAI API error: {e}",
            )

        description = response.choices[0].message.content or ""
        tokens_used = 0
        if response.usage:
            tokens_used = (response.usage.prompt_tokens or 0) + (response.usage.completion_tokens or 0)

        return VisionResult(
            description=description.strip(),
            model=self._model,
            tokens_used=tokens_used,
            raw_response=response,
        )

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
            element_description: Natural language description of the element.
            max_tokens: Maximum tokens in the response.

        Returns:
            VisionResult with element location info.

        Raises:
            AIProviderUnavailableError: API key not set or package missing.
            AIAnalysisFailedError: API request failed.
        """
        if not self.is_available:
            raise AIProviderUnavailableError(
                provider="openai",
                suggested_action="Set OPENAI_API_KEY environment variable",
            )

        client = self._get_client()
        image_data = encode_image_base64(image_path)
        media_type = detect_media_type(image_path)

        text_prompt = _DEFAULT_IDENTIFY_PROMPT.format(
            element_description=element_description
        )

        try:
            response = client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_data}",
                                },
                            },
                            {
                                "type": "text",
                                "text": text_prompt,
                            },
                        ],
                    }
                ],
            )
        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            raise AIAnalysisFailedError(
                message=f"OpenAI API error: {e}",
            )

        raw_text = response.choices[0].message.content or ""
        tokens_used = 0
        if response.usage:
            tokens_used = (response.usage.prompt_tokens or 0) + (response.usage.completion_tokens or 0)

        elements = []
        try:
            json_text = raw_text.strip()
            if json_text.startswith("```"):
                lines = json_text.split("\n")
                json_text = "\n".join(
                    line for line in lines
                    if not line.strip().startswith("```")
                )
            parsed = json.loads(json_text)
            if isinstance(parsed, dict):
                elements.append(parsed)
        except json.JSONDecodeError:
            logger.warning("Failed to parse element identification as JSON: %s", raw_text[:200])

        return VisionResult(
            description=raw_text.strip(),
            elements=elements,
            model=self._model,
            tokens_used=tokens_used,
            raw_response=response,
        )


# Register this provider
register_provider("openai", OpenAIVisionProvider)
