"""Anthropic (Claude) vision provider for Naturo.

Uses the Anthropic Messages API with vision capability to analyze screenshots.

Auth modes (in priority order):
1. ``api_key`` constructor argument (explicit override)
2. ``ANTHROPIC_API_KEY`` environment variable — may be a pay-per-use API key
   (``sk-ant-api03-*``) **or** an OAuth refresh token (``sk-ant-oat01-*``).
   When a refresh token is detected the provider automatically exchanges it for
   a short-lived access token before making API calls.
3. ``ANTHROPIC_AUTH_TOKEN`` environment variable (legacy session token)
4. ``~/.config/naturo/credentials.json`` — ``anthropic.token`` field

OAuth refresh tokens (``sk-ant-oat01-*``) are issued by Anthropic's CLI/browser
auth flow and cannot be used directly against ``api.anthropic.com``.  The
provider handles the exchange transparently, caches the resulting access token,
and automatically refreshes it before expiry.
"""
from __future__ import annotations

import json
import logging
import os
import time
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

# Model aliases — resolve shorthand to canonical model IDs
_MODEL_ALIASES: dict[str, str] = {
    "opus-4-6": "claude-opus-4-6",
    "opus": "claude-opus-4-20250514",
    "sonnet": "claude-sonnet-4-20250514",
    "haiku": "claude-3-haiku-20240307",
}

# Credentials file location
_CREDENTIALS_PATH: Path = Path.home() / ".config" / "naturo" / "credentials.json"

# OAuth constants (from Anthropic CLI / pi-ai SDK)
_OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
_OAUTH_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
_OAUTH_SCOPE = (
    "org:create_api_key user:profile user:inference "
    "user:sessions:claude_code user:mcp_servers user:file_upload"
)
# Buffer (seconds) to treat an access token as expired before it actually is
_OAUTH_EXPIRY_BUFFER = 300  # 5 minutes


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


def _is_oauth_refresh_token(token: str) -> bool:
    """Return True if *token* looks like an OAuth refresh token."""
    return "sk-ant-oat" in token


def _resolve_auth() -> tuple[str, str]:
    """Resolve the best available Anthropic credentials.

    Returns
    -------
    (auth_mode, token)
        *auth_mode* is ``"api_key"`` or ``"oauth"``.
        *token* is the raw credential string (empty string if none found).
    """
    # 1. ANTHROPIC_API_KEY env var — may be an API key or an OAuth refresh token
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        if _is_oauth_refresh_token(api_key):
            return ("oauth", api_key)
        return ("api_key", api_key)

    # 2. ANTHROPIC_AUTH_TOKEN env var (legacy session / OAuth token)
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    if auth_token:
        if _is_oauth_refresh_token(auth_token):
            return ("oauth", auth_token)
        return ("oauth", auth_token)

    # 3. Credentials file
    creds = _load_credentials()
    anthropic_creds = creds.get("anthropic", {})
    stored_token = anthropic_creds.get("token", "")
    stored_mode = anthropic_creds.get("auth_mode", "api_key")
    if stored_token:
        if _is_oauth_refresh_token(stored_token):
            return ("oauth", stored_token)
        return (stored_mode, stored_token)

    return ("api_key", "")


def _resolve_model(model: str) -> str:
    """Resolve a model alias or return *model* unchanged if not an alias."""
    return _MODEL_ALIASES.get(model, model)


# ---------------------------------------------------------------------------
# In-process OAuth token cache (per-process singleton via class attributes)
# ---------------------------------------------------------------------------

class _OAuthCache:
    """Simple in-memory cache for the OAuth access token."""

    _access_token: str = ""
    _expires_at: float = 0.0  # Unix timestamp when access token expires (with buffer)
    _refresh_token: str = ""  # Current refresh token (may be rotated by server)

    @classmethod
    def is_valid(cls) -> bool:
        return bool(cls._access_token) and time.monotonic() < cls._expires_at

    @classmethod
    def set(cls, access_token: str, expires_in: int, refresh_token: str = "") -> None:
        cls._access_token = access_token
        cls._expires_at = time.monotonic() + max(0, expires_in - _OAUTH_EXPIRY_BUFFER)
        if refresh_token:
            cls._refresh_token = refresh_token

    @classmethod
    def clear(cls) -> None:
        cls._access_token = ""
        cls._expires_at = 0.0


def _exchange_refresh_token(refresh_token: str) -> str:
    """Exchange an OAuth refresh token for a short-lived access token.

    Parameters
    ----------
    refresh_token:
        The ``sk-ant-oat01-*`` refresh token.

    Returns
    -------
    str
        The access token to use in API calls.

    Raises
    ------
    AIProviderUnavailableError
        If the token exchange fails.
    """
    import urllib.request
    import urllib.error

    payload = json.dumps({
        "grant_type": "refresh_token",
        "client_id": _OAUTH_CLIENT_ID,
        "refresh_token": refresh_token,
        "scope": _OAUTH_SCOPE,
    }).encode("utf-8")

    req = urllib.request.Request(
        _OAUTH_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.error(
            "OAuth token exchange failed: HTTP %s — %s", exc.code, body[:500]
        )
        raise AIProviderUnavailableError(
            provider="anthropic",
            suggested_action=(
                f"OAuth token exchange failed (HTTP {exc.code}). "
                "Your refresh token may be expired or revoked. "
                "Re-authenticate with: claude /login"
            ),
        ) from exc
    except Exception as exc:
        logger.error("OAuth token exchange error: %s", exc)
        raise AIProviderUnavailableError(
            provider="anthropic",
            suggested_action=f"OAuth token exchange error: {exc}",
        ) from exc

    access_token = data.get("access_token", "")
    expires_in = int(data.get("expires_in", 3600))
    new_refresh_token = data.get("refresh_token", "")

    if not access_token:
        raise AIProviderUnavailableError(
            provider="anthropic",
            suggested_action="OAuth token exchange returned no access_token",
        )

    logger.debug(
        "OAuth token exchange OK, expires_in=%s, got_new_refresh=%s",
        expires_in,
        bool(new_refresh_token),
    )

    # Cache the tokens in memory
    _OAuthCache.set(access_token, expires_in, new_refresh_token or refresh_token)

    # If the server rotated the refresh token, persist it to disk
    if new_refresh_token and new_refresh_token != refresh_token:
        _persist_refresh_token(new_refresh_token)

    return access_token


def _persist_refresh_token(new_refresh_token: str) -> None:
    """Persist a rotated refresh token to ``~/.config/naturo/credentials.json``."""
    try:
        creds = _load_credentials()
        if "anthropic" not in creds:
            creds["anthropic"] = {}
        creds["anthropic"]["token"] = new_refresh_token
        creds["anthropic"]["auth_mode"] = "oauth"
        _save_credentials(creds)
        logger.debug("Persisted rotated OAuth refresh token to %s", _CREDENTIALS_PATH)
    except Exception as exc:
        logger.warning("Failed to persist rotated refresh token: %s", exc)


def _get_oauth_access_token(refresh_token: str) -> str:
    """Return a valid OAuth access token, refreshing from *refresh_token* if needed."""
    if _OAuthCache.is_valid():
        return _OAuthCache._access_token
    return _exchange_refresh_token(refresh_token)


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

    * **API key** — ``ANTHROPIC_API_KEY`` env var or ``api_key`` constructor arg
      (tokens starting with ``sk-ant-api03-``).  Standard pay-per-use access.
    * **OAuth refresh token** — ``ANTHROPIC_API_KEY`` / ``ANTHROPIC_AUTH_TOKEN``
      env var or ``anthropic.token`` in ``~/.config/naturo/credentials.json``
      (tokens containing ``sk-ant-oat``).  The provider automatically exchanges
      the refresh token for a short-lived access token and caches it.

    Auth resolution order (highest to lowest priority):
    1. ``api_key`` constructor argument
    2. ``ANTHROPIC_API_KEY`` environment variable
    3. ``ANTHROPIC_AUTH_TOKEN`` environment variable
    4. ``~/.config/naturo/credentials.json``

    Args:
        api_key: Explicit API key or refresh token (overrides all env-var /
            file-based auth).
        model: Model name or alias (defaults to ``claude-sonnet-4-20250514`` or
            ``NATURO_AI_MODEL`` env var).  Supported aliases: ``opus-4-6``,
            ``opus``, ``sonnet``, ``haiku``.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        if api_key:
            if _is_oauth_refresh_token(api_key):
                self._auth_mode = "oauth"
            else:
                self._auth_mode = "api_key"
            self._token = api_key
        else:
            self._auth_mode, self._token = _resolve_auth()

        raw_model = model or os.environ.get("NATURO_AI_MODEL", _DEFAULT_MODEL)
        self._model = _resolve_model(raw_model)

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

        For OAuth refresh tokens this performs (or reuses a cached) token
        exchange before constructing the client.

        Returns:
            Anthropic client instance configured with the active auth mode.

        Raises:
            AIProviderUnavailableError: anthropic package not installed,
                no credentials configured, or OAuth exchange fails.
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
                    "Set ANTHROPIC_API_KEY (API key or OAuth refresh token) or "
                    "ANTHROPIC_AUTH_TOKEN, or run: naturo config setup anthropic"
                ),
            )

        if self._auth_mode == "oauth" and _is_oauth_refresh_token(self._token):
            # Exchange the refresh token for a short-lived access token, then
            # create an Anthropic client configured for OAuth bearer auth.
            access_token = _get_oauth_access_token(self._token)
            return anthropic.Anthropic(
                api_key=access_token,
                default_headers={
                    "anthropic-beta": "claude-code-20250219,oauth-2025-04-20",
                    "user-agent": "claude-cli/2.1.75",
                    "x-app": "cli",
                },
            )

        if self._auth_mode == "oauth":
            # Legacy session token (not a refresh token) — try auth_token param
            try:
                return anthropic.Anthropic(auth_token=self._token)
            except TypeError:
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
