"""Anthropic tool-use agent provider for Naturo.

Implements the AIProvider protocol from naturo.agent using Claude's
tool-use capability. Each step sends the current state (screenshot +
UI tree + history) and receives tool calls back.

This is Phase 4.4 of the Naturo roadmap.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from naturo.agent import AgentStep, StepStatus, ToolCall
from naturo.errors import AIProviderUnavailableError
from naturo.providers.agent_base import (
    AGENT_TOOLS,
    BaseAgentProvider,
    get_system_prompt,
)

from naturo.providers.model_registry import get_default_model

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = get_default_model("anthropic", "agent")

_SYSTEM_PROMPT = get_system_prompt(tool_noun="tool")

# Anthropic tool schema: {"name", "description", "input_schema"}
_TOOLS = [
    {
        "name": t["name"],
        "description": t["description"],
        "input_schema": t["parameters"],
    }
    for t in AGENT_TOOLS
]


class AnthropicAgentProvider(BaseAgentProvider):
    """Anthropic Claude tool-use agent provider.

    Implements the AIProvider protocol for the agent loop using Claude's
    tool-use messages API.

    Args:
        api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var).
        model: Model name (defaults to claude-sonnet-4-20250514).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            default_model=_DEFAULT_MODEL,
            api_key_env="ANTHROPIC_API_KEY",
        )

    @property
    def name(self) -> str:
        """Provider name."""
        return "anthropic"

    def _get_client(self) -> Any:
        """Get Anthropic client.

        Returns:
            Anthropic client instance.

        Raises:
            AIProviderUnavailableError: anthropic package not installed.
        """
        try:
            import anthropic
        except ImportError:
            raise AIProviderUnavailableError(
                provider="anthropic",
                suggested_action="Install anthropic: pip install anthropic",
            )
        return anthropic.Anthropic(api_key=self._api_key)

    def _format_screenshot_content(
        self, image_data: str, media_type: str,
    ) -> dict[str, Any]:
        """Format screenshot as Anthropic image content block."""
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_data,
            },
        }

    def _get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return Anthropic-format tool definitions."""
        return _TOOLS

    def _call_api(
        self,
        client: Any,
        conversation: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> Any:
        """Call Anthropic messages API."""
        return client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            tools=tools,
            messages=conversation,
        )

    def _parse_response(self, response: Any, step_num: int) -> AgentStep:
        """Parse Anthropic response into AgentStep."""
        step = AgentStep(step_number=step_num)
        reasoning_parts = []

        for block in response.content:
            if hasattr(block, "text") and block.type == "text":
                reasoning_parts.append(block.text)
            elif block.type == "tool_use":
                tc = ToolCall(
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {},
                    call_id=block.id,
                )
                step.tool_calls.append(tc)

                if block.name == "done":
                    step.is_done = True
                    step.summary = tc.arguments.get("summary", "Task completed")

        step.reasoning = "\n".join(reasoning_parts)

        # If model stopped without tool calls and said end_turn
        if not step.tool_calls and response.stop_reason == "end_turn":
            step.is_done = True
            step.summary = step.reasoning or "Task completed (no further actions)"

        step.status = StepStatus.SUCCESS
        return step

    def _append_history_messages(self, prev_step: AgentStep) -> None:
        """Append assistant + tool_result messages from previous step."""
        assistant_content = self._build_assistant_content(prev_step)
        if assistant_content:
            self._conversation.append({"role": "assistant", "content": assistant_content})

        tool_result_content = self._build_tool_result_content(prev_step)
        if tool_result_content:
            self._conversation.append({"role": "user", "content": tool_result_content})

    def _finalize_conversation(self) -> None:
        """Merge consecutive user messages (Anthropic requires alternating roles)."""
        self._conversation = self._merge_consecutive_user_messages(self._conversation)

    # -- Anthropic-specific helpers ------------------------------------------

    def _build_assistant_content(self, step: AgentStep) -> list[dict[str, Any]]:
        """Build assistant message content from an AgentStep.

        Args:
            step: Previous agent step.

        Returns:
            List of content blocks for the assistant message.
        """
        content: list[dict[str, Any]] = []

        if step.reasoning:
            content.append({"type": "text", "text": step.reasoning})

        for tc in step.tool_calls:
            content.append({
                "type": "tool_use",
                "id": tc.call_id,
                "name": tc.name,
                "input": tc.arguments,
            })

        return content

    def _build_tool_result_content(self, step: AgentStep) -> list[dict[str, Any]]:
        """Build tool_result messages from step results.

        Args:
            step: Previous agent step with tool results.

        Returns:
            List of tool_result content blocks.
        """
        content: list[dict[str, Any]] = []

        for tr in step.tool_results:
            content.append({
                "type": "tool_result",
                "tool_use_id": tr.call_id,
                "content": json.dumps(tr.result, ensure_ascii=False),
                "is_error": not tr.success,
            })

        return content

    @staticmethod
    def _merge_consecutive_user_messages(
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge consecutive user messages (Anthropic requires alternating roles).

        Args:
            messages: List of conversation messages.

        Returns:
            Messages with consecutive same-role messages merged.
        """
        if not messages:
            return messages

        merged: list[dict[str, Any]] = [messages[0]]
        for msg in messages[1:]:
            if msg["role"] == merged[-1]["role"]:
                # Merge content
                prev_content = merged[-1]["content"]
                curr_content = msg["content"]

                # Normalize to list
                if isinstance(prev_content, str):
                    prev_content = [{"type": "text", "text": prev_content}]
                if isinstance(curr_content, str):
                    curr_content = [{"type": "text", "text": curr_content}]

                merged[-1]["content"] = prev_content + curr_content
            else:
                merged.append(msg)

        return merged
