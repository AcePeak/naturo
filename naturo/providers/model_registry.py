"""Centralized model registry for AI providers.

Maps friendly model aliases to canonical API model IDs, defines defaults
per provider and use-case, and provides discovery helpers.

Design goals (issue #754):
- Users pick ``opus-4.6`` not ``claude-opus-4-6``
- Default = best model (Opus 4.6 for Anthropic), not cheapest
- Single source of truth for model names across vision + agent providers
- Extensible: add Google Gemini and future providers here
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModelInfo:
    """Metadata for a registered AI model.

    Attributes:
        canonical_id: The API model ID sent to the provider (e.g. ``claude-opus-4-6``).
        provider: Provider name (``anthropic``, ``openai``, ``ollama``, ``google``).
        aliases: Friendly short names users can type (e.g. ``["opus-4.6", "opus"]``).
        capabilities: What the model supports: ``vision``, ``agent``, or both.
        description: One-line human-readable description.
    """

    canonical_id: str
    provider: str
    aliases: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ("vision",)
    description: str = ""


# ── Model Definitions ───────────────────────────────────────────────────────
# Ordered by provider, then by capability tier (best first).

_MODELS: tuple[ModelInfo, ...] = (
    # ── Anthropic ──
    ModelInfo(
        canonical_id="claude-opus-4-6",
        provider="anthropic",
        aliases=("opus-4.6", "opus-4-6", "opus"),
        capabilities=("vision", "agent"),
        description="Claude Opus 4.6 — most capable, best for complex UI analysis",
    ),
    ModelInfo(
        canonical_id="claude-sonnet-4-20250514",
        provider="anthropic",
        aliases=("sonnet-4", "sonnet"),
        capabilities=("vision", "agent"),
        description="Claude Sonnet 4 — balanced speed and quality",
    ),
    ModelInfo(
        canonical_id="claude-haiku-4-5-20251001",
        provider="anthropic",
        aliases=("haiku-4.5", "haiku"),
        capabilities=("vision", "agent"),
        description="Claude Haiku 4.5 — fastest, best for simple tasks",
    ),
    # ── OpenAI ──
    ModelInfo(
        canonical_id="gpt-4o",
        provider="openai",
        aliases=("4o",),
        capabilities=("vision", "agent"),
        description="GPT-4o — multimodal, fast",
    ),
    ModelInfo(
        canonical_id="gpt-4o-mini",
        provider="openai",
        aliases=("4o-mini",),
        capabilities=("vision", "agent"),
        description="GPT-4o Mini — lightweight, cost-effective",
    ),
    ModelInfo(
        canonical_id="gpt-4-turbo",
        provider="openai",
        aliases=("4-turbo",),
        capabilities=("vision", "agent"),
        description="GPT-4 Turbo — high capability with vision",
    ),
    # ── Google Gemini ──
    ModelInfo(
        canonical_id="gemini-2.5-pro",
        provider="google",
        aliases=("gemini-pro", "gemini"),
        capabilities=("vision", "agent"),
        description="Gemini 2.5 Pro — Google's most capable multimodal model",
    ),
    ModelInfo(
        canonical_id="gemini-2.5-flash",
        provider="google",
        aliases=("gemini-flash",),
        capabilities=("vision",),
        description="Gemini 2.5 Flash — fast and cost-effective",
    ),
    # ── Ollama (local) ──
    ModelInfo(
        canonical_id="llava",
        provider="ollama",
        aliases=("llava-1.6",),
        capabilities=("vision",),
        description="LLaVA — local vision model via Ollama",
    ),
    ModelInfo(
        canonical_id="llava:13b",
        provider="ollama",
        aliases=("llava-13b",),
        capabilities=("vision",),
        description="LLaVA 13B — larger local vision model",
    ),
    ModelInfo(
        canonical_id="bakllava",
        provider="ollama",
        aliases=(),
        capabilities=("vision",),
        description="BakLLaVA — alternative local vision model",
    ),
)

# ── Defaults per provider (best model first) ────────────────────────────────
# Key: (provider, use_case) → canonical model ID.
# ``use_case`` is "vision" or "agent".

_DEFAULTS: dict[tuple[str, str], str] = {
    ("anthropic", "vision"): "claude-opus-4-6",
    ("anthropic", "agent"): "claude-sonnet-4-20250514",
    ("openai", "vision"): "gpt-4o",
    ("openai", "agent"): "gpt-4o",
    ("google", "vision"): "gemini-2.5-pro",
    ("google", "agent"): "gemini-2.5-pro",
    ("ollama", "vision"): "llava",
    ("ollama", "agent"): "llava",
}

# ── Pre-built lookup tables (built once at import time) ─────────────────────

# alias → canonical_id (includes the canonical_id itself as a key)
_ALIAS_MAP: dict[str, str] = {}

# canonical_id → ModelInfo
_MODEL_MAP: dict[str, ModelInfo] = {}

# provider → list of ModelInfo
_PROVIDER_MODELS: dict[str, list[ModelInfo]] = {}


def _build_indexes() -> None:
    """Populate lookup tables from ``_MODELS``."""
    _ALIAS_MAP.clear()
    _MODEL_MAP.clear()
    _PROVIDER_MODELS.clear()

    for info in _MODELS:
        _MODEL_MAP[info.canonical_id] = info
        # Canonical ID is also a valid lookup key
        _ALIAS_MAP[info.canonical_id] = info.canonical_id
        for alias in info.aliases:
            _ALIAS_MAP[alias] = info.canonical_id
        _PROVIDER_MODELS.setdefault(info.provider, []).append(info)


_build_indexes()


# ── Public API ──────────────────────────────────────────────────────────────


def resolve_model(name: str, provider: Optional[str] = None) -> str:
    """Resolve a friendly name or alias to a canonical model ID.

    Args:
        name: Model name, alias, or canonical ID (e.g. ``"opus-4.6"``).
        provider: Optional provider hint to disambiguate if multiple
            providers share an alias (currently unused but future-proof).

    Returns:
        Canonical model ID string (e.g. ``"claude-opus-4-6"``).
        If *name* is not recognized, it is returned unchanged so that
        users can pass arbitrary model IDs (e.g. fine-tunes).
    """
    if not name:
        return name or ""
    canonical = _ALIAS_MAP.get(name)
    if canonical is not None:
        return canonical
    # Case-insensitive fallback
    lower = name.lower()
    canonical = _ALIAS_MAP.get(lower)
    if canonical is not None:
        return canonical
    # Unknown — pass through (user may be using a custom/fine-tuned model)
    return name


def get_default_model(provider: str, use_case: str = "vision") -> str:
    """Return the recommended default model for a provider and use-case.

    Args:
        provider: Provider name (``"anthropic"``, ``"openai"``, etc.).
        use_case: ``"vision"`` or ``"agent"``.

    Returns:
        Canonical model ID. Falls back to the first registered model
        for that provider if no explicit default is configured.
    """
    if not provider:
        return ""
    key = (provider, use_case)
    if key in _DEFAULTS:
        return _DEFAULTS[key]
    # Fallback: first model with matching capability
    for info in _PROVIDER_MODELS.get(provider, []):
        if use_case in info.capabilities:
            return info.canonical_id
    # Ultimate fallback
    models = _PROVIDER_MODELS.get(provider, [])
    if models:
        return models[0].canonical_id
    return ""


def get_model_info(name: str) -> Optional[ModelInfo]:
    """Look up full model metadata by name or alias.

    Args:
        name: Model name, alias, or canonical ID.

    Returns:
        ModelInfo if found, None otherwise.
    """
    canonical = resolve_model(name)
    return _MODEL_MAP.get(canonical)


def list_models(
    provider: Optional[str] = None,
    capability: Optional[str] = None,
) -> list[ModelInfo]:
    """List registered models, optionally filtered.

    Args:
        provider: Filter by provider name (e.g. ``"anthropic"``).
        capability: Filter by capability (``"vision"`` or ``"agent"``).

    Returns:
        List of matching ModelInfo objects.
    """
    results: list[ModelInfo] = []
    if provider:
        candidates = _PROVIDER_MODELS.get(provider, [])
    else:
        candidates = list(_MODELS)
    for info in candidates:
        if capability and capability not in info.capabilities:
            continue
        results.append(info)
    return results


def list_aliases() -> dict[str, str]:
    """Return all known aliases mapped to their canonical model IDs.

    Returns:
        Dict of alias → canonical_id (includes canonical IDs themselves).
    """
    return dict(_ALIAS_MAP)
