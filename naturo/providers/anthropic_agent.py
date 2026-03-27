"""Anthropic tool-use agent provider for Naturo.

Implements the AIProvider protocol from naturo.agent using Claude's
tool-use capability. Each step sends the current state (screenshot +
UI tree + history) and receives tool calls back.

This is Phase 4.4 of the Naturo roadmap.
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

_DEFAULT_MODEL = "claude-sonnet-4-20250514"

# Tool definitions for Claude tool-use API
_TOOLS = [
    {
        "name": "click",
        "description": "Click at screen coordinates or on a UI element. Use for buttons, links, checkboxes, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate (pixels from left)"},
                "y": {"type": "integer", "description": "Y coordinate (pixels from top)"},
                "element_id": {"type": "string", "description": "UI element ID from the accessibility tree (alternative to x/y)"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Mouse button", "default": "left"},
                "double": {"type": "boolean", "description": "Double-click", "default": False},
            },
        },
    },
    {
        "name": "type_text",
        "description": "Type text at the current cursor position. Use after clicking on a text field.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type"},
                "wpm": {"type": "integer", "description": "Typing speed in words per minute", "default": 120},
            },
            "required": ["text"],
        },
    },
    {
        "name": "press_key",
        "description": "Press a keyboard key (e.g., 'enter', 'tab', 'escape', 'backspace', 'delete', 'up', 'down', 'left', 'right', 'home', 'end', 'f1'-'f12').",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key name"},
                "count": {"type": "integer", "description": "Number of times to press", "default": 1},
            },
            "required": ["key"],
        },
    },
    {
        "name": "hotkey",
        "description": "Press a keyboard shortcut (e.g., ['ctrl', 's'] for save, ['alt', 'f4'] to close).",
        "input_schema": {
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key combination (e.g., ['ctrl', 'c'] for copy)",
                },
            },
            "required": ["keys"],
        },
    },
    {
        "name": "scroll",
        "description": "Scroll the mouse wheel. Use to navigate long pages or lists.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "default": "down"},
                "amount": {"type": "integer", "description": "Scroll amount (lines)", "default": 3},
                "x": {"type": "integer", "description": "X coordinate to scroll at (optional)"},
                "y": {"type": "integer", "description": "Y coordinate to scroll at (optional)"},
            },
        },
    },
    {
        "name": "drag",
        "description": "Drag from one position to another. Use for moving items, resizing, selecting text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_x": {"type": "integer", "description": "Start X"},
                "from_y": {"type": "integer", "description": "Start Y"},
                "to_x": {"type": "integer", "description": "End X"},
                "to_y": {"type": "integer", "description": "End Y"},
                "duration_ms": {"type": "integer", "description": "Drag duration in ms", "default": 500},
                "steps": {"type": "integer", "description": "Number of interpolation steps", "default": 10},
            },
            "required": ["from_x", "from_y", "to_x", "to_y"],
        },
    },
    {
        "name": "move_mouse",
        "description": "Move the mouse cursor to a position without clicking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "find_element",
        "description": "Find a UI element by selector string (e.g., 'Button:Save', 'Edit', 'MenuItem:File'). Returns element ID and bounds.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector (Role:Name or partial name match)"},
                "window_title": {"type": "string", "description": "Target window (optional)"},
            },
            "required": ["selector"],
        },
    },
    {
        "name": "capture_screen",
        "description": "Take a screenshot of the current screen. Use to see the current state after performing actions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_path": {"type": "string", "description": "File path for screenshot", "default": "agent_capture.png"},
            },
        },
    },
    {
        "name": "list_windows",
        "description": "List all visible windows with their titles, process names, and PIDs.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "focus_window",
        "description": "Bring a window to the foreground by title.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "close_window",
        "description": "Close a window by title.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "launch_app",
        "description": "Launch an application by name (e.g., 'notepad', 'calc', 'chrome').",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Application name or path"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "quit_app",
        "description": "Quit an application by name. Use --force for unresponsive apps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Application name"},
                "force": {"type": "boolean", "description": "Force kill", "default": False},
            },
            "required": ["name"],
        },
    },
    {
        "name": "clipboard_get",
        "description": "Get the current clipboard text content.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "clipboard_set",
        "description": "Set the clipboard text content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to put on clipboard"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "wait_for_element",
        "description": "Wait for a UI element to appear. Use after launching apps or navigating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector to wait for"},
                "timeout": {"type": "number", "description": "Max wait time in seconds", "default": 10.0},
                "interval": {"type": "number", "description": "Poll interval in seconds", "default": 0.5},
                "window_title": {"type": "string", "description": "Target window (optional)"},
            },
            "required": ["selector"],
        },
    },
    {
        "name": "done",
        "description": "Signal that the task is complete. Call this when you have finished the instruction. Include a summary of what was accomplished.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Summary of what was accomplished"},
            },
            "required": ["summary"],
        },
    },
]

_SYSTEM_PROMPT = """\
You are Naturo, a Windows desktop automation agent. You control a Windows computer \
by executing tool calls to interact with the UI.

## Your Approach
1. First, observe the screenshot and UI tree to understand the current state.
2. Plan your next action based on the instruction and current state.
3. Execute one or a few related actions per step.
4. After executing, a new screenshot will be taken so you can verify the result.
5. Continue until the task is complete, then call the `done` tool.

## Guidelines
- Always verify your actions had the expected effect by examining the next screenshot.
- If an action fails, try an alternative approach (e.g., use coordinates instead of element ID).
- For text input: click the target field first, then type.
- For keyboard shortcuts: use the `hotkey` tool with key names like ['ctrl', 's'].
- When launching apps, wait a moment for them to load before interacting.
- Be precise with coordinates — use the screenshot and UI tree bounds.
- If the UI tree provides element IDs with bounds, prefer using coordinates from bounds \
(center of the bounding box) for reliability.
- Call `done` with a summary when the task is complete.
- If you cannot complete the task after several attempts, call `done` explaining what went wrong.
"""


class AnthropicAgentProvider:
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
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = model or os.environ.get("NATURO_AGENT_MODEL", _DEFAULT_MODEL)
        self._conversation: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        """Provider name."""
        return "anthropic"

    @property
    def is_available(self) -> bool:
        """Whether the Anthropic API key is configured."""
        return bool(self._api_key)

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

    def run_step(
        self,
        instruction: str,
        screenshot_path: Optional[str],
        ui_tree: Optional[dict],
        history: list[AgentStep],
    ) -> AgentStep:
        """Run one step of the agent loop via Claude tool-use.

        Sends the current state to Claude and receives tool calls back.
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
                provider="anthropic",
                suggested_action="Set ANTHROPIC_API_KEY environment variable",
            )

        client = self._get_client()

        # Build the user message for this step
        content: list[dict[str, Any]] = []

        # Add screenshot if available
        if screenshot_path and os.path.exists(screenshot_path):
            image_data = encode_image_base64(screenshot_path)
            media_type = detect_media_type(screenshot_path)
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                },
            })

        # Build text context
        text_parts = []
        step_num = len(history) + 1

        if step_num == 1:
            text_parts.append(f"## Instruction\n{instruction}")
        else:
            text_parts.append(f"## Step {step_num}")
            # Summarize tool results from previous step
            if history:
                prev = history[-1]
                for tr in prev.tool_results:
                    status = "✅" if tr.success else "❌"
                    text_parts.append(f"Tool `{tr.name}` result: {status} {json.dumps(tr.result, ensure_ascii=False)}")

        if ui_tree:
            # Compact UI tree to save tokens
            tree_text = json.dumps(ui_tree, ensure_ascii=False, separators=(",", ":"))
            if len(tree_text) > 4000:
                tree_text = tree_text[:4000] + "...(truncated)"
            text_parts.append(f"## UI Accessibility Tree\n```json\n{tree_text}\n```")

        text_parts.append("What is your next action? Use the available tools to make progress on the instruction.")

        content.append({
            "type": "text",
            "text": "\n\n".join(text_parts),
        })

        # Build conversation messages
        # For step 1, start fresh; for subsequent steps, append to conversation
        if step_num == 1:
            self._conversation = [{"role": "user", "content": content}]
        else:
            # Add assistant's previous tool_use response
            if history:
                prev = history[-1]
                assistant_content = self._build_assistant_content(prev)
                if assistant_content:
                    self._conversation.append({"role": "assistant", "content": assistant_content})

                # Add tool results
                tool_result_content = self._build_tool_result_content(prev)
                if tool_result_content:
                    self._conversation.append({"role": "user", "content": tool_result_content})

            # Add new observation
            self._conversation.append({"role": "user", "content": content})

            # Merge consecutive user messages (Anthropic requires alternating roles)
            self._conversation = self._merge_consecutive_user_messages(self._conversation)

        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=2048,
                system=_SYSTEM_PROMPT,
                tools=_TOOLS,
                messages=self._conversation,
            )
        except Exception as e:
            logger.error("Anthropic agent API error: %s", e)
            step = AgentStep(step_number=step_num, status=StepStatus.ERROR)
            step.summary = f"AI provider error: {e}"
            return step

        # Parse response into AgentStep
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

                # Check for "done" tool
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
