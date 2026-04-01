"""AI provider implementations for Naturo vision and agent capabilities.

Supports multiple AI backends: Anthropic (Claude), OpenAI (GPT-4), Ollama (local).
Each provider implements the VisionProvider protocol for screenshot analysis
and the AIProvider protocol for agentic tool-use loops.
"""
from __future__ import annotations

from naturo.providers.base import (
    VisionProvider,
    VisionResult,
    get_vision_provider,
    list_available_providers,
)
from naturo.providers.model_registry import (
    ModelInfo,
    get_default_model,
    get_model_info,
    list_aliases,
    list_models,
    resolve_model,
)

__all__ = [
    "ModelInfo",
    "VisionProvider",
    "VisionResult",
    "get_default_model",
    "get_model_info",
    "get_vision_provider",
    "list_aliases",
    "list_available_providers",
    "list_models",
    "resolve_model",
]
