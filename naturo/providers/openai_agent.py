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
from naturo.providers.base import encode_image_base64, detect_media_type

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-4o"

# OpenAI function definitions (equivalent to Anthropic tool definitions)
_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click at screen coordinates or on a UI element.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "element_id": {"type": "string", "description": "UI element ID (alternative to x/y)"},
                    "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Mouse button"},
                    "double": {"type": "boolean", "description": "Double-click"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type text at the current cursor position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"},
                    "wpm": {"type": "integer", "description": "Typing speed (WPM)"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a keyboard key (e.g., 'enter', 'tab', 'escape').",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key name"},
                    "count": {"type": "integer", "description": "Number of times to press"},
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hotkey",
            "description": "Press a keyboard shortcut (e.g., ['ctrl', 's']).",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key combination",
                    },
                },
                "required": ["keys"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll",
            "description": "Scroll the mouse wheel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                    "amount": {"type": "integer", "description": "Scroll amount (lines)"},
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drag",
            "description": "Drag from one position to another.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_x": {"type": "integer", "description": "Start X"},
                    "from_y": {"type": "integer", "description": "Start Y"},
                    "to_x": {"type": "integer", "description": "End X"},
                    "to_y": {"type": "integer", "description": "End Y"},
                    "duration_ms": {"type": "integer", "description": "Drag duration (ms)"},
                    "steps": {"type": "integer", "description": "Interpolation steps"},
                },
                "required": ["from_x", "from_y", "to_x", "to_y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_mouse",
            "description": "Move the mouse cursor without clicking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_element",
            "description": "Find a UI element by selector (e.g., 'Button:Save').",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Element selector"},
                    "window_title": {"type": "string", "description": "Target window"},
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capture_screen",
            "description": "Take a screenshot of the current screen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "File path for screenshot"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_windows",
            "description": "List all visible windows.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "focus_window",
            "description": "Bring a window to the foreground.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Window title (partial match)"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_window",
            "description": "Close a window by title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Window title (partial match)"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "launch_app",
            "description": "Launch an application by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Application name or path"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "quit_app",
            "description": "Quit an application by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Application name"},
                    "force": {"type": "boolean", "description": "Force kill"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clipboard_get",
            "description": "Get clipboard text content.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clipboard_set",
            "description": "Set clipboard text content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to put on clipboard"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wait_for_element",
            "description": "Wait for a UI element to appear.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Element selector"},
                    "timeout": {"type": "number", "description": "Max wait time (seconds)"},
                    "interval": {"type": "number", "description": "Poll interval (seconds)"},
                    "window_title": {"type": "string", "description": "Target window"},
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "done",
            "description": "Signal task completion with a summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Summary of what was accomplished"},
                },
                "required": ["summary"],
            },
        },
    },
]

_SYSTEM_PROMPT = """\
You are Naturo, a Windows desktop automation agent. You control a Windows computer \
by executing function calls to interact with the UI.

## Your Approach
1. First, observe the screenshot and UI tree to understand the current state.
2. Plan your next action based on the instruction and current state.
3. Execute one or a few related actions per step.
4. After executing, a new screenshot will be taken so you can verify the result.
5. Continue until the task is complete, then call the `done` function.

## Guidelines
- Always verify your actions had the expected effect by examining the next screenshot.
- If an action fails, try an alternative approach (e.g., use coordinates instead of element ID).
- For text input: click the target field first, then type.
- For keyboard shortcuts: use the `hotkey` function with key names like ['ctrl', 's'].
- When launching apps, wait a moment for them to load before interacting.
- Be precise with coordinates — use the screenshot and UI tree bounds.
- If the UI tree provides element IDs with bounds, prefer using coordinates from bounds \
(center of the bounding box) for reliability.
- Call `done` with a summary when the task is complete.
- If you cannot complete the task after several attempts, call `done` explaining what went wrong.
"""


class OpenAIAgentProvider:
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
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model or os.environ.get("NATURO_AGENT_MODEL", _DEFAULT_MODEL)
        self._base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self._conversation: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        """Provider name."""
        return "openai"

    @property
    def is_available(self) -> bool:
        """Whether the OpenAI API key is configured."""
        return bool(self._api_key)

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

    def run_step(
        self,
        instruction: str,
        screenshot_path: Optional[str],
        ui_tree: Optional[dict],
        history: list[AgentStep],
    ) -> AgentStep:
        """Run one step of the agent loop via OpenAI function-calling.

        Sends the current state to GPT-4o and receives tool calls back.
        Maintains conversation history across steps for context.

        Args:
            instruction: The user's natural language instruction.
            screenshot_path: Path to current screenshot.
            ui_tree: Current UI accessibility tree as dict.
            history: Previous steps for context.

        Returns:
            AgentStep with tool_calls to execute, or is_done=True.
        """
        if not self.is_available:
            raise AIProviderUnavailableError(
                provider="openai",
                suggested_action="Set OPENAI_API_KEY environment variable",
            )

        client = self._get_client()

        # Build the user message for this step
        content: list[dict[str, Any]] = []
        step_num = len(history) + 1

        # Add screenshot if available
        if screenshot_path and os.path.exists(screenshot_path):
            image_data = encode_image_base64(screenshot_path)
            media_type = detect_media_type(screenshot_path)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{image_data}",
                },
            })

        # Build text context
        text_parts = []

        if step_num == 1:
            text_parts.append(f"## Instruction\n{instruction}")
        else:
            text_parts.append(f"## Step {step_num}")
            # Summarize tool results from previous step
            if history:
                prev = history[-1]
                for tr in prev.tool_results:
                    status = "✅" if tr.success else "❌"
                    text_parts.append(
                        f"Tool `{tr.name}` result: {status} "
                        f"{json.dumps(tr.result, ensure_ascii=False)}"
                    )

        if ui_tree:
            tree_text = json.dumps(ui_tree, ensure_ascii=False, separators=(",", ":"))
            if len(tree_text) > 4000:
                tree_text = tree_text[:4000] + "...(truncated)"
            text_parts.append(f"## UI Accessibility Tree\n```json\n{tree_text}\n```")

        text_parts.append(
            "What is your next action? Use the available tools to make progress."
        )

        content.append({
            "type": "text",
            "text": "\n\n".join(text_parts),
        })

        # Build conversation
        if step_num == 1:
            self._conversation = [{"role": "user", "content": content}]
        else:
            # Add assistant's previous tool_call response
            if history:
                prev = history[-1]
                assistant_msg = self._build_assistant_message(prev)
                if assistant_msg:
                    self._conversation.append(assistant_msg)

                # Add tool results as separate messages
                tool_msgs = self._build_tool_result_messages(prev)
                self._conversation.extend(tool_msgs)

            # Add new observation
            self._conversation.append({"role": "user", "content": content})

        try:
            response = client.chat.completions.create(
                model=self._model,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    *self._conversation,
                ],
                tools=_FUNCTIONS,
                tool_choice="auto",
            )
        except Exception as e:
            logger.error("OpenAI agent API error: %s", e)
            step = AgentStep(step_number=step_num, status=StepStatus.ERROR)
            step.summary = f"AI provider error: {e}"
            return step

        # Parse response into AgentStep
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
