"""Naturo Agent — AI-driven desktop automation via tool-use loop.

Implements the core agent loop:
1. Capture current screen state (screenshot + UI tree)
2. Send state + instruction to AI model
3. AI returns tool calls (click, type, etc.)
4. Execute tool calls and capture results
5. Repeat until task is complete or max steps reached

This module is provider-agnostic: it defines the interface and loop,
while provider-specific implementations live in naturo/providers/.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable

from naturo.backends.base import Backend, get_backend
from naturo.errors import NaturoError

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    """Status of an agent step."""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"


@dataclass
class ToolCall:
    """A single tool call from the AI model."""
    name: str
    arguments: dict[str, Any]
    call_id: str = ""


@dataclass
class ToolResult:
    """Result of executing a tool call."""
    call_id: str
    name: str
    result: dict[str, Any]
    success: bool = True
    error: Optional[str] = None


@dataclass
class AgentStep:
    """One step in the agent execution loop."""
    step_number: int
    reasoning: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    is_done: bool = False
    summary: str = ""


@dataclass
class AgentResult:
    """Final result of an agent execution."""
    instruction: str
    steps: list[AgentStep] = field(default_factory=list)
    success: bool = False
    summary: str = ""
    total_time: float = 0.0
    error: Optional[str] = None

    @property
    def step_count(self) -> int:
        return len(self.steps)


@runtime_checkable
class AIProvider(Protocol):
    """Interface for AI model providers (OpenAI, Anthropic, etc.)."""

    def run_step(
        self,
        instruction: str,
        screenshot_path: Optional[str],
        ui_tree: Optional[dict],
        history: list[AgentStep],
    ) -> AgentStep:
        """Run one step of the agent loop.

        Args:
            instruction: The user's natural language instruction.
            screenshot_path: Path to current screenshot (for vision).
            ui_tree: Current UI accessibility tree as dict.
            history: Previous steps for context.

        Returns:
            AgentStep with tool_calls to execute, or is_done=True.
        """
        ...


# ── Tool Executor ───────────────────────────────


class ToolExecutor:
    """Executes tool calls against the naturo backend."""

    def __init__(self, backend: Backend):
        self.backend = backend
        self._tools = self._build_tool_map()

    def _build_tool_map(self) -> dict[str, callable]:
        """Map tool names to backend methods."""
        return {
            "click": self._click,
            "type_text": self._type_text,
            "press_key": self._press_key,
            "hotkey": self._hotkey,
            "scroll": self._scroll,
            "drag": self._drag,
            "move_mouse": self._move_mouse,
            "find_element": self._find_element,
            "capture_screen": self._capture_screen,
            "list_windows": self._list_windows,
            "focus_window": self._focus_window,
            "close_window": self._close_window,
            "launch_app": self._launch_app,
            "quit_app": self._quit_app,
            "clipboard_get": self._clipboard_get,
            "clipboard_set": self._clipboard_set,
            "wait_for_element": self._wait_for_element,
            "done": self._done,
        }

    def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call."""
        handler = self._tools.get(tool_call.name)
        if handler is None:
            return ToolResult(
                call_id=tool_call.call_id,
                name=tool_call.name,
                result={"error": f"Unknown tool: {tool_call.name}"},
                success=False,
                error=f"Unknown tool: {tool_call.name}",
            )
        try:
            result = handler(**tool_call.arguments)
            return ToolResult(
                call_id=tool_call.call_id,
                name=tool_call.name,
                result=result,
                success=True,
            )
        except NaturoError as e:
            error_info: dict = {"error": str(e), "code": e.code}
            if e.suggested_action:
                error_info["suggested_action"] = e.suggested_action
            if e.is_recoverable:
                error_info["recoverable"] = True
            return ToolResult(
                call_id=tool_call.call_id,
                name=tool_call.name,
                result=error_info,
                success=False,
                error=str(e),
            )
        except Exception as e:
            logger.exception("Tool %s failed", tool_call.name)
            return ToolResult(
                call_id=tool_call.call_id,
                name=tool_call.name,
                result={"error": f"{type(e).__name__}: {e}"},
                success=False,
                error=str(e),
            )

    # ── Tool Implementations ────────────────────

    def _click(self, x: int = None, y: int = None, element_id: str = None,
               button: str = "left", double: bool = False) -> dict:
        self.backend.click(x=x, y=y, element_id=element_id, button=button, double=double)
        return {"success": True}

    def _type_text(self, text: str, wpm: int = 120) -> dict:
        self.backend.type_text(text=text, wpm=wpm)
        return {"success": True}

    def _press_key(self, key: str, count: int = 1) -> dict:
        for _ in range(count):
            self.backend.press_key(key=key)
        return {"success": True}

    def _hotkey(self, keys: list[str]) -> dict:
        self.backend.hotkey(*keys)
        return {"success": True}

    def _scroll(self, direction: str = "down", amount: int = 3,
                x: int = None, y: int = None) -> dict:
        self.backend.scroll(direction=direction, amount=amount, x=x, y=y)
        return {"success": True}

    def _drag(self, from_x: int, from_y: int, to_x: int, to_y: int,
              duration_ms: int = 500, steps: int = 10) -> dict:
        self.backend.drag(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y,
                         duration_ms=duration_ms, steps=steps)
        return {"success": True}

    def _move_mouse(self, x: int, y: int) -> dict:
        self.backend.move_mouse(x=x, y=y)
        return {"success": True}

    def _find_element(self, selector: str, window_title: str = None) -> dict:
        element = self.backend.find_element(selector=selector, window_title=window_title)
        if element is None:
            return {"success": False, "error": f"Element not found: {selector}"}
        return {
            "success": True,
            "element": {
                "id": element.id,
                "role": element.role,
                "name": element.name,
                "bounds": {"x": element.x, "y": element.y,
                          "width": element.width, "height": element.height},
            },
        }

    def _capture_screen(self, output_path: str = "agent_capture.png") -> dict:
        result = self.backend.capture_screen(output_path=output_path)
        return {"success": True, "path": result.path, "width": result.width, "height": result.height}

    def _list_windows(self) -> dict:
        windows = self.backend.list_windows()
        return {
            "success": True,
            "windows": [{"title": w.title, "process": w.process_name, "pid": w.pid} for w in windows],
        }

    def _focus_window(self, title: str) -> dict:
        self.backend.focus_window(title=title)
        return {"success": True}

    def _close_window(self, title: str) -> dict:
        self.backend.close_window(title=title)
        return {"success": True}

    def _launch_app(self, name: str) -> dict:
        self.backend.launch_app(name=name)
        return {"success": True}

    def _quit_app(self, name: str, force: bool = False) -> dict:
        self.backend.quit_app(name=name, force=force)
        return {"success": True}

    def _clipboard_get(self) -> dict:
        text = self.backend.clipboard_get()
        return {"success": True, "text": text}

    def _clipboard_set(self, text: str) -> dict:
        self.backend.clipboard_set(text=text)
        return {"success": True}

    def _wait_for_element(self, selector: str, timeout: float = 10.0,
                          interval: float = 0.5, window_title: str = None) -> dict:
        from naturo.wait import wait_for_element
        result = wait_for_element(
            selector=selector, timeout=timeout, poll_interval=interval,
            window_title=window_title, backend=self.backend,
        )
        return {"success": result.found, "wait_time": round(result.wait_time, 3)}

    def _done(self, summary: str = "") -> dict:
        """Special tool: signals task completion."""
        return {"success": True, "done": True, "summary": summary}


# ── Agent Runner ────────────────────────────────


def run_agent(
    instruction: str,
    provider: AIProvider,
    backend: Optional[Backend] = None,
    max_steps: int = 10,
    window_title: Optional[str] = None,
    dry_run: bool = False,
    capture_dir: Optional[str] = None,
) -> AgentResult:
    """Run the agent loop to complete a task.

    Args:
        instruction: Natural language instruction.
        provider: AI model provider implementation.
        backend: Desktop automation backend (auto-detected if None).
        max_steps: Maximum number of steps before stopping.
        window_title: Target window for screenshots/UI tree.
        dry_run: If True, plan steps but don't execute.
        capture_dir: Directory to save screenshots (temp if None).

    Returns:
        AgentResult with execution history and outcome.
    """
    if backend is None:
        backend = get_backend()

    executor = ToolExecutor(backend)
    result = AgentResult(instruction=instruction)
    start_time = time.monotonic()

    if capture_dir is None:
        import tempfile
        capture_dir = tempfile.mkdtemp(prefix="naturo_agent_")

    for step_num in range(1, max_steps + 1):
        logger.info("Agent step %d/%d", step_num, max_steps)

        # 1. Capture current state
        screenshot_path = os.path.join(capture_dir, f"step_{step_num}.png")
        try:
            backend.capture_screen(output_path=screenshot_path)
        except Exception as e:
            logger.warning("Failed to capture screen: %s", e)
            screenshot_path = None

        ui_tree = None
        try:
            tree = backend.get_element_tree(window_title=window_title, depth=3)
            if tree:
                ui_tree = _serialize_tree(tree)
        except Exception as e:
            logger.warning("Failed to get UI tree: %s", e)

        # 2. Ask AI for next action
        try:
            step = provider.run_step(
                instruction=instruction,
                screenshot_path=screenshot_path,
                ui_tree=ui_tree,
                history=result.steps,
            )
        except Exception as e:
            logger.error("AI provider failed: %s", e)
            step = AgentStep(step_number=step_num, status=StepStatus.ERROR)
            step.summary = f"AI provider error: {e}"
            result.steps.append(step)
            result.error = str(e)
            break

        step.step_number = step_num

        # 3. Check if done
        if step.is_done:
            step.status = StepStatus.SUCCESS
            result.steps.append(step)
            result.success = True
            result.summary = step.summary or "Task completed"
            break

        # 4. Execute tool calls (unless dry run)
        if not dry_run:
            for tc in step.tool_calls:
                tr = executor.execute(tc)
                step.tool_results.append(tr)
                # Check for "done" tool
                if tc.name == "done" and tr.success:
                    step.is_done = True
                    step.summary = tc.arguments.get("summary", "Task completed")
            if step.is_done:
                step.status = StepStatus.SUCCESS
                result.steps.append(step)
                result.success = True
                result.summary = step.summary
                break
        else:
            step.status = StepStatus.SUCCESS
            step.summary = f"[dry-run] Would execute: {[tc.name for tc in step.tool_calls]}"

        step.status = StepStatus.SUCCESS
        result.steps.append(step)

    else:
        # Reached max steps
        result.error = f"Reached maximum steps ({max_steps}) without completion"

    result.total_time = time.monotonic() - start_time
    return result


def _serialize_tree(el) -> dict:
    """Serialize element tree to dict for AI context."""
    d = {
        "id": el.id,
        "role": el.role,
        "name": el.name,
    }
    if el.value:
        d["value"] = el.value
    d["bounds"] = {"x": el.x, "y": el.y, "w": el.width, "h": el.height}
    if el.children:
        d["children"] = [_serialize_tree(c) for c in el.children]
    return d
