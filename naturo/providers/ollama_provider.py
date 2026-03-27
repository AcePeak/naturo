"""Ollama (local LLM) vision provider for Naturo.

Uses the Ollama HTTP API with vision-capable models (e.g., llava, bakllava).
Requires Ollama running locally (default: http://localhost:11434).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

from naturo.errors import AIAnalysisFailedError, AIProviderUnavailableError
from naturo.providers.base import (
    VisionResult,
    encode_image_base64,
    register_provider,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "llava"
_DEFAULT_BASE_URL = "http://localhost:11434"

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


class OllamaVisionProvider:
    """Ollama local vision provider.

    Uses Ollama's API with vision-capable models for screenshot analysis.
    No API key required — runs locally.

    Args:
        model: Vision model name (defaults to 'llava').
        base_url: Ollama API base URL (defaults to http://localhost:11434).
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self._model = model or os.environ.get("NATURO_OLLAMA_MODEL", _DEFAULT_MODEL)
        self._base_url = (
            base_url
            or os.environ.get("OLLAMA_HOST", _DEFAULT_BASE_URL)
        ).rstrip("/")

    @property
    def name(self) -> str:
        """Provider name."""
        return "ollama"

    @property
    def is_available(self) -> bool:
        """Check if Ollama is running and reachable."""
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self._base_url}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def describe_screenshot(
        self,
        image_path: str,
        *,
        prompt: Optional[str] = None,
        context: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> VisionResult:
        """Analyze a screenshot using Ollama vision model.

        Args:
            image_path: Path to screenshot file (PNG/JPG).
            prompt: Custom analysis prompt (overrides default).
            context: Additional context about the screenshot.
            max_tokens: Maximum tokens in the response.

        Returns:
            VisionResult with description.

        Raises:
            AIProviderUnavailableError: Ollama not running.
            AIAnalysisFailedError: API request failed.
        """
        text_prompt = prompt or _DEFAULT_DESCRIBE_PROMPT
        if context:
            text_prompt = f"Context: {context}\n\n{text_prompt}"

        return self._call_ollama(image_path, text_prompt)

    def identify_element(
        self,
        image_path: str,
        element_description: str,
        *,
        max_tokens: int = 512,
    ) -> VisionResult:
        """Find a specific UI element using Ollama vision model.

        Args:
            image_path: Path to screenshot file.
            element_description: Natural language description of the element.
            max_tokens: Maximum tokens in the response.

        Returns:
            VisionResult with element location info.

        Raises:
            AIProviderUnavailableError: Ollama not running.
            AIAnalysisFailedError: API request failed.
        """
        text_prompt = _DEFAULT_IDENTIFY_PROMPT.format(
            element_description=element_description
        )
        result = self._call_ollama(image_path, text_prompt)

        # Parse JSON from response
        try:
            json_text = result.description.strip()
            if json_text.startswith("```"):
                lines = json_text.split("\n")
                json_text = "\n".join(
                    line for line in lines
                    if not line.strip().startswith("```")
                )
            parsed = json.loads(json_text)
            if isinstance(parsed, dict):
                result.elements = [parsed]
        except json.JSONDecodeError:
            logger.warning("Failed to parse Ollama response as JSON: %s", result.description[:200])

        return result

    def _call_ollama(self, image_path: str, prompt: str) -> VisionResult:
        """Make an Ollama API call with image.

        Args:
            image_path: Path to image file.
            prompt: Text prompt.

        Returns:
            VisionResult with response.

        Raises:
            AIProviderUnavailableError: Ollama not reachable.
            AIAnalysisFailedError: Request failed.
        """
        import urllib.request
        import urllib.error

        image_data = encode_image_base64(image_path)

        payload = json.dumps({
            "model": self._model,
            "prompt": prompt,
            "images": [image_data],
            "stream": False,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                f"{self._base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise AIProviderUnavailableError(
                provider="ollama",
                suggested_action=f"Ensure Ollama is running at {self._base_url}: {e}",
            )
        except Exception as e:
            logger.error("Ollama API error: %s", e)
            raise AIAnalysisFailedError(
                message=f"Ollama API error: {e}",
            )

        description = data.get("response", "")
        tokens_used = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

        return VisionResult(
            description=description.strip(),
            model=self._model,
            tokens_used=tokens_used,
            raw_response=data,
        )


# Register this provider
register_provider("ollama", OllamaVisionProvider)
