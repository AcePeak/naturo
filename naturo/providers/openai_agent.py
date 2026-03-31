"""OpenAI tool-use agent provider for Naturo.

Implements the AIProvider protocol from naturo.agent using OpenAI's
function-calling capability. Each step sends the current state
(screenshot + UI tree + history) and receives tool calls back.

Supports OpenAI API and any OpenAI-compatible endpoint (e.g., Ollama,
vLLM, LM Studio) via OPENAI_BASE_URL or --base-url.

This is Phase 4.8 of the Naturo roadmap.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from naturo.agent import AgentStep, StepStatus, ToolCall
from naturo.errors import AIProviderUnavailableError
from naturo.providers.agent_base import (
    AGENT_TOOLS,
    BaseAgentProvider,
    get_system_prompt,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-4o"

_SYSTEM_PROMPT = get_system_prompt(tool_noun="function")

# OpenAI function schema: {"type": "function", "function": {"name", "description", "parameters"}}
_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"],
        },
    }
    for t in AGENT_TOOLS
]


class OpenAIAgentProvider(BaseAgentProvider):
    """OpenAI tool-use agent provider.

    Implements the AIProvider protocol for the agent loop using OpenAI's
    function-calling API. Also works with any OpenAI-compatible endpoint
    (Ollama, vLLM, LM Studio, etc.) via base_url.

    Args:
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var).
        model: Model name (defaults to gpt-4o).
        base_url: Custom API base URL (for compatible APIs).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            default_model=_DEFAULT_MODEL,
            api_key_env="OPENAI_API_KEY",
        )
        self._base_url = base_url or os.environ.get("OPENAI_BASE_URL")

    @property
    def name(self) -> str:
        """Provider name."""
        return "openai"

    def _get_client(self) -> Any:
        """Get OpenAI client.

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

    def _format_screenshot_content(
        self, image_data: str, media_type: str,
    ) -> dict[str, Any]:
        """Format screenshot as OpenAI image_url content block."""
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{media_type};base64,{image_data}",
            },
        }

    def _get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return OpenAI-format function definitions."""
        return _FUNCTIONS

    def _call_api(
        self,
        client: Any,
        conversation: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> Any:
        """Call OpenAI chat completions API."""
        return client.chat.completions.create(
            model=self._model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                *conversation,
            ],
            tools=tools,
            tool_choice="auto",
        )

    def _parse_response(self, response: Any, step_num: int) -> AgentStep:
        """Parse OpenAI response into AgentStep."""
        step = AgentStep(step_number=step_num)
        message = response.choices[0].message

        if message.content:
            step.reasoning = message.content

        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    arguments = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    arguments = {}

                tool_call = ToolCall(
                    name=tc.function.name,
                    arguments=arguments,
                    call_id=tc.id,
                )
                step.tool_calls.append(tool_call)

                if tc.function.name == "done":
                    step.is_done = True
                    step.summary = arguments.get("summary", "Task completed")

        # If model stopped without tool calls
        if not step.tool_calls and response.choices[0].finish_reason == "stop":
            step.is_done = True
            step.summary = step.reasoning or "Task completed (no further actions)"

        step.status = StepStatus.SUCCESS
        return step

    def _append_history_messages(self, prev_step: AgentStep) -> None:
        """Append assistant + tool result messages from previous step."""
        assistant_msg = self._build_assistant_message(prev_step)
        if assistant_msg:
            self._conversation.append(assistant_msg)

        tool_msgs = self._build_tool_result_messages(prev_step)
        self._conversation.extend(tool_msgs)

    # -- OpenAI-specific helpers ---------------------------------------------

    def _build_assistant_message(self, step: AgentStep) -> Optional[dict[str, Any]]:
        """Build assistant message from an AgentStep.

        Args:
            step: Previous agent step.

        Returns:
            Assistant message dict for OpenAI API, or None if empty.
        """
        if not step.tool_calls and not step.reasoning:
            return None

        msg: dict[str, Any] = {"role": "assistant"}

        if step.reasoning:
            msg["content"] = step.reasoning
        else:
            msg["content"] = None

        if step.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.call_id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in step.tool_calls
            ]

        return msg

    def _build_tool_result_messages(
        self, step: AgentStep
    ) -> list[dict[str, Any]]:
        """Build tool result messages from step results.

        OpenAI requires each tool result as a separate message with role='tool'.

        Args:
            step: Previous agent step with tool results.

        Returns:
            List of tool result messages.
        """
        messages = []
        for tr in step.tool_results:
            messages.append({
                "role": "tool",
                "tool_call_id": tr.call_id,
                "content": json.dumps(tr.result, ensure_ascii=False),
            })
        return messages
