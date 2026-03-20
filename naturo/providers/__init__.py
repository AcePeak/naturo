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

__all__ = [
    "VisionProvider",
    "VisionResult",
    "get_vision_provider",
    "list_available_providers",
]
