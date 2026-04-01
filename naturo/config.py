"""Centralized configuration for naturo.

All file paths, environment variable names, and credential management
in one place. Import from here instead of hardcoding paths/env vars.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── File paths ──
CREDENTIALS_PATH = Path.home() / ".config" / "naturo" / "credentials.json"
SNAPSHOTS_DIR = Path.home() / ".naturo" / "snapshots"

# ── Environment variables ──
ENV_SESSION = "NATURO_SESSION"
ENV_SNAPSHOT_TTL = "NATURO_SNAPSHOT_TTL"
ENV_AI_MODEL = "NATURO_AI_MODEL"
ENV_LOG_LEVEL = "NATURO_LOG_LEVEL"


# ── Model Registry ──
# Maps well-known model names to their provider.
# Used by --model auto-detection to infer --provider when not specified.
MODEL_REGISTRY: dict[str, dict[str, str]] = {
    # Anthropic
    "claude-opus-4-6": {"provider": "anthropic", "display": "Claude Opus 4.6"},
    "claude-opus-4-20250514": {"provider": "anthropic", "display": "Claude Opus 4"},
    "claude-sonnet-4-20250514": {"provider": "anthropic", "display": "Claude Sonnet 4"},
    "claude-sonnet-4-6": {"provider": "anthropic", "display": "Claude Sonnet 4.6"},
    "claude-haiku-4-5-20251001": {"provider": "anthropic", "display": "Claude Haiku 4.5"},
    "claude-3-haiku-20240307": {"provider": "anthropic", "display": "Claude 3 Haiku"},
    # OpenAI
    "gpt-4o": {"provider": "openai", "display": "GPT-4o"},
    "gpt-4o-mini": {"provider": "openai", "display": "GPT-4o Mini"},
    "gpt-4-turbo": {"provider": "openai", "display": "GPT-4 Turbo"},
    "gpt-4.1": {"provider": "openai", "display": "GPT-4.1"},
    "gpt-4.1-mini": {"provider": "openai", "display": "GPT-4.1 Mini"},
    "o4-mini": {"provider": "openai", "display": "o4-mini"},
    # Google
    "gemini-2.5-pro": {"provider": "google", "display": "Gemini 2.5 Pro"},
    "gemini-2.5-flash": {"provider": "google", "display": "Gemini 2.5 Flash"},
    "gemini-2.0-flash": {"provider": "google", "display": "Gemini 2.0 Flash"},
    # Ollama (local)
    "llava": {"provider": "ollama", "display": "LLaVA (local)"},
    "llava:13b": {"provider": "ollama", "display": "LLaVA 13B (local)"},
    "bakllava": {"provider": "ollama", "display": "BakLLaVA (local)"},
}

# Aliases: shorthand names that resolve to canonical model IDs
MODEL_ALIASES: dict[str, str] = {
    "opus": "claude-opus-4-6",
    "opus-4-6": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-20250514",
    "sonnet-4-6": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5-20251001",
    "gpt4o": "gpt-4o",
    "gpt4o-mini": "gpt-4o-mini",
    "gemini-pro": "gemini-2.5-pro",
    "gemini-flash": "gemini-2.5-flash",
}


def resolve_model_alias(model: str) -> str:
    """Resolve a model alias to its canonical ID.

    Args:
        model: Model name or alias.

    Returns:
        Canonical model ID.
    """
    return MODEL_ALIASES.get(model, model)


def infer_provider_from_model(model: str) -> str | None:
    """Infer the provider name from a model ID or alias.

    Checks the registry first, then falls back to prefix-based detection.

    Args:
        model: Model name or alias.

    Returns:
        Provider name (e.g. 'anthropic'), or None if unknown.
    """
    canonical = resolve_model_alias(model)
    entry = MODEL_REGISTRY.get(canonical)
    if entry:
        return entry["provider"]

    # Prefix-based fallback for models not in the registry
    if canonical.startswith("claude-"):
        return "anthropic"
    if canonical.startswith(("gpt-", "o1-", "o3-", "o4-")):
        return "openai"
    if canonical.startswith("gemini-"):
        return "google"
    return None


def load_credentials() -> dict[str, Any]:
    """Load credentials from ~/.config/naturo/credentials.json."""
    try:
        if CREDENTIALS_PATH.exists():
            return json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("Could not read credentials: %s", exc)
    return {}


def save_credentials(data: dict[str, Any]) -> None:
    """Write credentials atomically."""
    import tempfile
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8",
        dir=CREDENTIALS_PATH.parent,
        prefix=".tmp_", suffix=".json", delete=False,
    ) as tmp:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp_path = tmp.name
    try:
        os.replace(tmp_path, CREDENTIALS_PATH)
    except OSError:
        os.unlink(tmp_path)
        raise
