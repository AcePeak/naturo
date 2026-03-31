"""Shared base class for AI agent providers.

Extracts the common tool-use loop logic shared by AnthropicAgentProvider
and OpenAIAgentProvider. Provider-specific subclasses implement only the
API interaction details (client creation, message formatting, response parsing).
"""
from __future__ import annotations

import abc
import json
import logging
import os
from typing import Any, Optional

from naturo.agent import AgentStep, StepStatus
from naturo.errors import AIProviderUnavailableError
from naturo.providers.base import detect_media_type, encode_image_base64

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical tool definitions (provider-neutral)
# ---------------------------------------------------------------------------
# Each entry uses {"name", "description", "parameters"}.  Subclasses convert
# to the provider-specific schema via _get_tool_definitions().

AGENT_TOOLS: list[dict[str, Any]] = [
    {
        "name": "click",
        "description": "Click at screen coordinates or on a UI element. Use for buttons, links, checkboxes, etc.",
        "parameters": {
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
        "parameters": {
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
        "parameters": {
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
        "parameters": {
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
        "parameters": {
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
        "parameters": {
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
        "parameters": {
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
        "parameters": {
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
        "parameters": {
            "type": "object",
            "properties": {
                "output_path": {"type": "string", "description": "File path for screenshot", "default": "agent_capture.png"},
            },
        },
    },
    {
        "name": "list_windows",
        "description": "List all visible windows with their titles, process names, and PIDs.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "focus_window",
        "description": "Bring a window to the foreground by title.",
        "parameters": {
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
        "parameters": {
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
        "parameters": {
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
        "parameters": {
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
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "clipboard_set",
        "description": "Set the clipboard text content.",
        "parameters": {
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
        "parameters": {
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
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Summary of what was accomplished"},
            },
            "required": ["summary"],
        },
    },
]

_SYSTEM_PROMPT_TEMPLATE = """\
You are Naturo, a Windows desktop automation agent. You control a Windows computer \
by executing {tool_noun} calls to interact with the UI.

## Your Approach
1. First, observe the screenshot and UI tree to understand the current state.
2. Plan your next action based on the instruction and current state.
3. Execute one or a few related actions per step.
4. After executing, a new screenshot will be taken so you can verify the result.
5. Continue until the task is complete, then call the `done` {tool_noun}.

## Guidelines
- Always verify your actions had the expected effect by examining the next screenshot.
- If an action fails, try an alternative approach (e.g., use coordinates instead of element ID).
- For text input: click the target field first, then type.
- For keyboard shortcuts: use the `hotkey` {tool_noun} with key names like ['ctrl', 's'].
- When launching apps, wait a moment for them to load before interacting.
- Be precise with coordinates — use the screenshot and UI tree bounds.
- If the UI tree provides element IDs with bounds, prefer using coordinates from bounds \
(center of the bounding box) for reliability.
- Call `done` with a summary when the task is complete.
- If you cannot complete the task after several attempts, call `done` explaining what went wrong.
"""


def get_system_prompt(tool_noun: str = "tool") -> str:
    """Return the agent system prompt with the given tool noun.

    Args:
        tool_noun: Word to use for tool/function references (e.g., 'tool' or 'function').

    Returns:
        Formatted system prompt string.
    """
    return _SYSTEM_PROMPT_TEMPLATE.format(tool_noun=tool_noun)


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class BaseAgentProvider(abc.ABC):
    """Abstract base class for AI agent providers.

    Encapsulates the shared tool-use loop: build user content from the
    current state, manage conversation history, call the provider API,
    and parse the response into an ``AgentStep``.

    Subclasses implement the provider-specific details: client creation,
    screenshot formatting, tool schema conversion, API invocation, and
    response parsing.

    Args:
        api_key: Provider API key (falls back to *api_key_env* env var).
        model: Model name (falls back to NATURO_AGENT_MODEL env var, then *default_model*).
        default_model: Default model when no override is given.
        api_key_env: Environment variable name for the API key.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        *,
        default_model: str,
        api_key_env: str,
    ) -> None:
        self._api_key = api_key or os.environ.get(api_key_env, "")
        self._api_key_env = api_key_env
        self._model = model or os.environ.get("NATURO_AGENT_MODEL", default_model)
        self._conversation: list[dict[str, Any]] = []

    # -- Abstract interface --------------------------------------------------

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider name (e.g., ``'anthropic'``, ``'openai'``)."""

    @abc.abstractmethod
    def _get_client(self) -> Any:
        """Create and return the provider's API client.

        Raises:
            AIProviderUnavailableError: Required SDK package is not installed.
        """

    @abc.abstractmethod
    def _format_screenshot_content(
        self, image_data: str, media_type: str,
    ) -> dict[str, Any]:
        """Format a base64-encoded screenshot as a provider-specific content block.

        Args:
            image_data: Base64-encoded image data.
            media_type: MIME type (e.g., ``'image/png'``).

        Returns:
            Content block dict for the provider's message format.
        """

    @abc.abstractmethod
    def _get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return tool definitions in the provider's expected schema."""

    @abc.abstractmethod
    def _call_api(
        self,
        client: Any,
        conversation: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> Any:
        """Invoke the provider API and return the raw response.

        Args:
            client: Provider client instance.
            conversation: Conversation messages.
            tools: Tool definitions in provider format.

        Returns:
            Raw provider API response object.
        """

    @abc.abstractmethod
    def _parse_response(self, response: Any, step_num: int) -> AgentStep:
        """Parse a raw API response into an ``AgentStep``.

        Args:
            response: Raw provider API response.
            step_num: Current step number.

        Returns:
            Populated AgentStep.
        """

    @abc.abstractmethod
    def _append_history_messages(self, prev_step: AgentStep) -> None:
        """Append conversation messages for the previous step's results.

        Called before adding the new user observation message on steps 2+.
        Implementations should append assistant and tool-result messages
        to ``self._conversation``.

        Args:
            prev_step: The previous AgentStep with tool_calls and tool_results.
        """

    # -- Overridable hooks ---------------------------------------------------

    def _finalize_conversation(self) -> None:
        """Post-process conversation messages before sending to the API.

        Override to merge consecutive same-role messages (Anthropic) or
        perform other provider-specific fixups.  Default is a no-op.
        """

    # -- Shared implementation -----------------------------------------------

    @property
    def is_available(self) -> bool:
        """Whether the provider API key is configured."""
        return bool(self._api_key)

    def _build_user_content(
        self,
        instruction: str,
        screenshot_path: Optional[str],
        ui_tree: Optional[dict],
        step_num: int,
        history: list[AgentStep],
    ) -> list[dict[str, Any]]:
        """Build the user message content for a single step.

        Args:
            instruction: The user's natural language instruction.
            screenshot_path: Path to current screenshot (may be ``None``).
            ui_tree: Current UI accessibility tree as dict (may be ``None``).
            step_num: Current step number (1-based).
            history: Previous ``AgentStep`` objects.

        Returns:
            List of content blocks for the user message.
        """
        content: list[dict[str, Any]] = []

        # Screenshot
        if screenshot_path and os.path.exists(screenshot_path):
            image_data = encode_image_base64(screenshot_path)
            media_type = detect_media_type(screenshot_path)
            content.append(self._format_screenshot_content(image_data, media_type))

        # Text parts
        text_parts: list[str] = []

        if step_num == 1:
            text_parts.append(f"## Instruction\n{instruction}")
        else:
            text_parts.append(f"## Step {step_num}")
            if history:
                prev = history[-1]
                for tr in prev.tool_results:
                    status = "\u2705" if tr.success else "\u274c"
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
            "What is your next action? Use the available tools to make progress on the instruction."
        )

        content.append({"type": "text", "text": "\n\n".join(text_parts)})
        return content

    def run_step(
        self,
        instruction: str,
        screenshot_path: Optional[str],
        ui_tree: Optional[dict],
        history: list[AgentStep],
    ) -> AgentStep:
        """Run one step of the agent loop.

        Builds the current state into a user message, manages conversation
        history, calls the provider API, and parses the response.

        Args:
            instruction: The user's natural language instruction.
            screenshot_path: Path to current screenshot.
            ui_tree: Current UI accessibility tree as dict.
            history: Previous steps for context.

        Returns:
            AgentStep with tool_calls to execute, or is_done=True.

        Raises:
            AIProviderUnavailableError: API key not configured.
        """
        if not self.is_available:
            raise AIProviderUnavailableError(
                provider=self.name,
                suggested_action=f"Set {self._api_key_env} environment variable",
            )

        client = self._get_client()
        step_num = len(history) + 1
        content = self._build_user_content(
            instruction, screenshot_path, ui_tree, step_num, history,
        )

        # Build conversation
        if step_num == 1:
            self._conversation = [{"role": "user", "content": content}]
        else:
            if history:
                self._append_history_messages(history[-1])
            self._conversation.append({"role": "user", "content": content})
            self._finalize_conversation()

        try:
            response = self._call_api(
                client, self._conversation, self._get_tool_definitions(),
            )
        except Exception as e:
            logger.error("%s agent API error: %s", self.name.capitalize(), e)
            step = AgentStep(step_number=step_num, status=StepStatus.ERROR)
            step.summary = f"AI provider error: {e}"
            return step

        return self._parse_response(response, step_num)
