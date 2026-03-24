"""Anthropic (Claude) vision provider for Naturo.

Uses the Anthropic Messages API with vision capability to analyze screenshots.

Auth modes (in priority order):
1. ``api_key`` constructor argument (explicit override)
2. ``ANTHROPIC_API_KEY`` environment variable (pay-per-use)
3. ``ANTHROPIC_AUTH_TOKEN`` environment variable (subscription/OAuth session token)
4. ``~/.config/naturo/credentials.json`` — ``anthropic.token`` field

The session token path (2 and 3) is intended for Anthropic Pro/Max subscribers
who authenticate via browser OAuth rather than paying per-token.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from naturo.errors import AIAnalysisFailedError, AIProviderUnavailableError
from naturo.providers.base import (
    VisionResult,
    detect_media_type,
    encode_image_base64,
    register_provider,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-20250514"

# Credentials file location
_CREDENTIALS_PATH: Path = Path.home() / ".config" / "naturo" / "credentials.json"


def _load_credentials() -> dict:
    """Load credentials from ``~/.config/naturo/credentials.json``.

    Returns an empty dict if the file does not exist or cannot be parsed.
    """
    try:
        if _CREDENTIALS_PATH.exists():
            return json.loads(_CREDENTIALS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("Could not read credentials file %s: %s", _CREDENTIALS_PATH, exc)
    return {}


def _save_credentials(data: dict) -> None:
    """Write credentials dict to ``~/.config/naturo/credentials.json`` atomically."""
    import tempfile
    _CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=_CREDENTIALS_PATH.parent,
        prefix=".tmp_",
        suffix=".json",
        delete=False,
    ) as tmp:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp_path = tmp.name
    try:
        os.replace(tmp_path, _CREDENTIALS_PATH)
    except OSError:
        os.unlink(tmp_path)
        raise


def _resolve_auth() -> tuple[str, str]:
    """Resolve the best available Anthropic credentials.

    Returns
    -------
    (auth_mode, token)
        *auth_mode* is ``"api_key"`` or ``"oauth"``.
        *token* is the raw credential string (empty string if none found).
    """
    # 1. ANTHROPIC_API_KEY env var (traditional API key)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        return ("api_key", api_key)

    # 2. ANTHROPIC_AUTH_TOKEN env var (session / OAuth token)
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    if auth_token:
        return ("oauth", auth_token)

    # 3. Credentials file
    creds = _load_credentials()
    anthropic_creds = creds.get("anthropic", {})
    stored_token = anthropic_creds.get("token", "")
    stored_mode = anthropic_creds.get("auth_mode", "api_key")
    if stored_token:
        return (stored_mode, stored_token)

    return ("api_key", "")
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


class AnthropicVisionProvider:
    """Anthropic Claude vision provider.

    Supports two authentication modes:

    * **API key** — ``ANTHROPIC_API_KEY`` env var or ``api_key`` constructor arg.
      Standard pay-per-use access.
    * **OAuth / session token** — ``ANTHROPIC_AUTH_TOKEN`` env var or the
      ``anthropic.token`` field in ``~/.config/naturo/credentials.json``.
      For Anthropic Pro/Max subscribers who sign in via browser.

    Auth resolution order (highest to lowest priority):
    1. ``api_key`` constructor argument
    2. ``ANTHROPIC_API_KEY`` environment variable
    3. ``ANTHROPIC_AUTH_TOKEN`` environment variable
    4. ``~/.config/naturo/credentials.json``

    Args:
        api_key: Explicit API key (overrides all env-var / file-based auth).
        model: Model name (defaults to ``claude-sonnet-4-20250514`` or
            ``NATURO_AI_MODEL`` env var).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        if api_key:
            self._auth_mode = "api_key"
            self._token = api_key
        else:
            self._auth_mode, self._token = _resolve_auth()
        self._model = model or os.environ.get("NATURO_AI_MODEL", _DEFAULT_MODEL)

    @property
    def name(self) -> str:
        """Provider name."""
        return "anthropic"

    @property
    def auth_mode(self) -> str:
        """Active authentication mode: ``'api_key'`` or ``'oauth'``."""
        return self._auth_mode

    @property
    def is_available(self) -> bool:
        """Whether any Anthropic credentials are configured."""
        return bool(self._token)

    def _get_client(self) -> Any:
        """Get or create Anthropic client.

        Returns:
            Anthropic client instance configured with the active auth mode.

        Raises:
            AIProviderUnavailableError: anthropic package not installed or
                no credentials configured.
        """
        try:
            import anthropic
        except ImportError:
            raise AIProviderUnavailableError(
                provider="anthropic",
                suggested_action="Install anthropic: pip install anthropic",
            )
        if not self._token:
            raise AIProviderUnavailableError(
                provider="anthropic",
                suggested_action=(
                    "Set ANTHROPIC_API_KEY (API key) or ANTHROPIC_AUTH_TOKEN "
                    "(subscription/OAuth token), or run: naturo config setup anthropic"
                ),
            )

        if self._auth_mode == "oauth":
            # Session tokens use the same Anthropic SDK but are passed as
            # the api_key parameter with the "Bearer" scheme internally.
            # The Anthropic Python SDK >= 0.50 accepts auth_token for OAuth flows.
            try:
                return anthropic.Anthropic(auth_token=self._token)
            except TypeError:
                # Older SDK versions: fall back to api_key param
                logger.debug(
                    "anthropic SDK does not support auth_token kwarg; "
                    "falling back to api_key for OAuth token"
                )
                return anthropic.Anthropic(api_key=self._token)

        return anthropic.Anthropic(api_key=self._token)

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
            VisionResult with description and identified elements.

        Raises:
            AIProviderUnavailableError: API key not set or package missing.
            AIAnalysisFailedError: API request failed.
        """
        if not self.is_available:
            raise AIProviderUnavailableError(
                provider="anthropic",
                suggested_action="Set ANTHROPIC_API_KEY environment variable",
            )

        client = self._get_client()
        image_data = encode_image_base64(image_path)
        media_type = detect_media_type(image_path)

        text_prompt = prompt or _DEFAULT_DESCRIBE_PROMPT
        if context:
            text_prompt = f"Context: {context}\n\n{text_prompt}"

        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
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
            logger.error("Anthropic API error: %s", e)
            raise AIAnalysisFailedError(
                message=f"Anthropic API error: {e}",
            )

        description = ""
        for block in response.content:
            if hasattr(block, "text"):
                description += block.text

        tokens_used = 0
        if hasattr(response, "usage"):
            tokens_used = (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)

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
            VisionResult with element location info in the elements list.

        Raises:
            AIProviderUnavailableError: API key not set or package missing.
            AIAnalysisFailedError: API request failed.
        """
        if not self.is_available:
            raise AIProviderUnavailableError(
                provider="anthropic",
                suggested_action="Set ANTHROPIC_API_KEY environment variable",
            )

        client = self._get_client()
        image_data = encode_image_base64(image_path)
        media_type = detect_media_type(image_path)

        text_prompt = _DEFAULT_IDENTIFY_PROMPT.format(
            element_description=element_description
        )

        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
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
            logger.error("Anthropic API error: %s", e)
            raise AIAnalysisFailedError(
                message=f"Anthropic API error: {e}",
            )

        raw_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                raw_text += block.text

        tokens_used = 0
        if hasattr(response, "usage"):
            tokens_used = (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)

        # Parse the JSON response
        elements = []
        try:
            # Extract JSON from response (might have markdown code fences)
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
register_provider("anthropic", AnthropicVisionProvider)
