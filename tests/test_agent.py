"""Tests for agent module — tool executor and agent loop."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from naturo.agent import (
    AgentResult,
    AgentStep,
    StepStatus,
    ToolCall,
    ToolExecutor,
    ToolResult,
    run_agent,
)


# ── Fixtures ────────────────────────────────────


@pytest.fixture
def mock_backend():
    """Create a mock backend with all required methods."""
    backend = MagicMock()
    backend.click.return_value = None
    backend.type_text.return_value = None
    backend.press_key.return_value = None
    backend.hotkey.return_value = None
    backend.scroll.return_value = None
    backend.drag.return_value = None
    backend.move_mouse.return_value = None
    backend.find_element.return_value = None
    backend.focus_window.return_value = None
    backend.close_window.return_value = None
    backend.launch_app.return_value = None
    backend.quit_app.return_value = None
    backend.clipboard_get.return_value = "clipboard text"
    backend.clipboard_set.return_value = None
    backend.list_windows.return_value = []

    # capture_screen returns a result object
    capture_result = MagicMock()
    capture_result.path = "test.png"
    capture_result.width = 1920
    capture_result.height = 1080
    capture_result.format = "png"
    backend.capture_screen.return_value = capture_result

    # get_element_tree returns None (no UI tree)
    backend.get_element_tree.return_value = None

    return backend


@pytest.fixture
def executor(mock_backend):
    return ToolExecutor(mock_backend)


class FakeProvider:
    """Fake AI provider for testing the agent loop."""

    def __init__(self, steps: list[AgentStep]):
        self._steps = list(steps)
        self._call_count = 0

    def run_step(self, instruction, screenshot_path, ui_tree, history):
        if self._call_count < len(self._steps):
            step = self._steps[self._call_count]
            self._call_count += 1
            return step
        # Default: done
        done = AgentStep(step_number=0, is_done=True, summary="Completed")
        return done


# ── ToolExecutor Tests ──────────────────────────


class TestToolExecutor:

    def test_click(self, executor, mock_backend):
        tc = ToolCall(name="click", arguments={"x": 100, "y": 200}, call_id="1")
        result = executor.execute(tc)
        assert result.success
        mock_backend.click.assert_called_once_with(x=100, y=200, element_id=None, button="left", double=False)

    def test_type_text(self, executor, mock_backend):
        tc = ToolCall(name="type_text", arguments={"text": "hello"}, call_id="2")
        result = executor.execute(tc)
        assert result.success
        mock_backend.type_text.assert_called_once_with(text="hello", wpm=120)

    def test_press_key(self, executor, mock_backend):
        tc = ToolCall(name="press_key", arguments={"key": "enter", "count": 3}, call_id="3")
        result = executor.execute(tc)
        assert result.success
        assert mock_backend.press_key.call_count == 3

    def test_hotkey(self, executor, mock_backend):
        tc = ToolCall(name="hotkey", arguments={"keys": ["ctrl", "s"]}, call_id="4")
        result = executor.execute(tc)
        assert result.success
        mock_backend.hotkey.assert_called_once_with("ctrl", "s")

    def test_scroll(self, executor, mock_backend):
        tc = ToolCall(name="scroll", arguments={"direction": "up", "amount": 5}, call_id="5")
        result = executor.execute(tc)
        assert result.success
        mock_backend.scroll.assert_called_once()

    def test_unknown_tool(self, executor):
        tc = ToolCall(name="nonexistent", arguments={}, call_id="x")
        result = executor.execute(tc)
        assert not result.success
        assert "Unknown tool" in result.error

    def test_done_tool(self, executor):
        tc = ToolCall(name="done", arguments={"summary": "All done"}, call_id="d")
        result = executor.execute(tc)
        assert result.success
        assert result.result["done"] is True
        assert result.result["summary"] == "All done"

    def test_clipboard_get(self, executor, mock_backend):
        tc = ToolCall(name="clipboard_get", arguments={}, call_id="c1")
        result = executor.execute(tc)
        assert result.success
        assert result.result["text"] == "clipboard text"

    def test_clipboard_set(self, executor, mock_backend):
        tc = ToolCall(name="clipboard_set", arguments={"text": "new"}, call_id="c2")
        result = executor.execute(tc)
        assert result.success
        mock_backend.clipboard_set.assert_called_once_with(text="new")

    def test_list_windows(self, executor, mock_backend):
        tc = ToolCall(name="list_windows", arguments={}, call_id="lw")
        result = executor.execute(tc)
        assert result.success
        assert result.result["windows"] == []

    def test_find_element_not_found(self, executor, mock_backend):
        mock_backend.find_element.return_value = None
        tc = ToolCall(name="find_element", arguments={"selector": "Button:Missing"}, call_id="fe")
        result = executor.execute(tc)
        assert result.result["success"] is False

    def test_find_element_found(self, executor, mock_backend):
        elem = MagicMock()
        elem.id = "e1"
        elem.role = "Button"
        elem.name = "Save"
        elem.x, elem.y, elem.width, elem.height = 10, 20, 80, 30
        mock_backend.find_element.return_value = elem
        tc = ToolCall(name="find_element", arguments={"selector": "Button:Save"}, call_id="fe2")
        result = executor.execute(tc)
        assert result.result["success"] is True
        assert result.result["element"]["name"] == "Save"

    def test_backend_exception(self, executor, mock_backend):
        mock_backend.click.side_effect = RuntimeError("COM error")
        tc = ToolCall(name="click", arguments={"x": 1, "y": 1}, call_id="err")
        result = executor.execute(tc)
        assert not result.success
        assert "COM error" in result.error

    def test_capture_screen(self, executor, mock_backend):
        tc = ToolCall(name="capture_screen", arguments={}, call_id="cap")
        result = executor.execute(tc)
        assert result.success
        assert result.result["path"] == "test.png"

    def test_launch_app(self, executor, mock_backend):
        tc = ToolCall(name="launch_app", arguments={"name": "notepad"}, call_id="la")
        result = executor.execute(tc)
        assert result.success
        mock_backend.launch_app.assert_called_once_with(name="notepad")

    def test_focus_window(self, executor, mock_backend):
        tc = ToolCall(name="focus_window", arguments={"title": "Notepad"}, call_id="fw")
        result = executor.execute(tc)
        assert result.success
        mock_backend.focus_window.assert_called_once_with(title="Notepad")

    def test_drag(self, executor, mock_backend):
        tc = ToolCall(name="drag", arguments={
            "from_x": 0, "from_y": 0, "to_x": 100, "to_y": 100
        }, call_id="dr")
        result = executor.execute(tc)
        assert result.success


# ── Agent Loop Tests ────────────────────────────


class TestAgentLoop:

    def test_immediate_done(self, mock_backend):
        """Provider immediately says done."""
        step = AgentStep(step_number=0, is_done=True, summary="Nothing to do")
        provider = FakeProvider([step])
        result = run_agent("do nothing", provider=provider, backend=mock_backend, max_steps=5)
        assert result.success
        assert result.step_count == 1
        assert result.summary == "Nothing to do"

    def test_one_action_then_done(self, mock_backend):
        """One tool call, then done."""
        step1 = AgentStep(
            step_number=0,
            tool_calls=[ToolCall(name="click", arguments={"x": 100, "y": 200}, call_id="1")],
        )
        step2 = AgentStep(step_number=0, is_done=True, summary="Clicked the button")
        provider = FakeProvider([step1, step2])
        result = run_agent("click something", provider=provider, backend=mock_backend, max_steps=5)
        assert result.success
        assert result.step_count == 2
        mock_backend.click.assert_called_once()

    def test_done_via_tool(self, mock_backend):
        """Provider calls the 'done' tool to signal completion."""
        step = AgentStep(
            step_number=0,
            tool_calls=[ToolCall(name="done", arguments={"summary": "Task finished"}, call_id="d")],
        )
        provider = FakeProvider([step])
        result = run_agent("finish", provider=provider, backend=mock_backend, max_steps=5)
        assert result.success
        assert "finished" in result.summary

    def test_max_steps_reached(self, mock_backend):
        """Agent hits max steps without completion."""
        steps = [
            AgentStep(
                step_number=0,
                tool_calls=[ToolCall(name="click", arguments={"x": i, "y": i}, call_id=str(i))],
            )
            for i in range(10)
        ]
        provider = FakeProvider(steps)
        result = run_agent("loop forever", provider=provider, backend=mock_backend, max_steps=3)
        assert not result.success
        assert result.step_count == 3
        assert "maximum steps" in result.error

    def test_dry_run(self, mock_backend):
        """Dry run: plan but don't execute."""
        step1 = AgentStep(
            step_number=0,
            tool_calls=[ToolCall(name="click", arguments={"x": 100, "y": 200}, call_id="1")],
        )
        step2 = AgentStep(step_number=0, is_done=True, summary="Done planning")
        provider = FakeProvider([step1, step2])
        result = run_agent("plan it", provider=provider, backend=mock_backend, max_steps=5, dry_run=True)
        assert result.success
        # Backend should NOT be called (dry run)
        mock_backend.click.assert_not_called()

    def test_provider_error(self, mock_backend):
        """Provider raises an exception."""
        class FailProvider:
            def run_step(self, *args, **kwargs):
                raise RuntimeError("API key invalid")

        result = run_agent("fail", provider=FailProvider(), backend=mock_backend, max_steps=5)
        assert not result.success
        assert "API key invalid" in result.error

    def test_total_time_tracked(self, mock_backend):
        """Ensure total_time is recorded."""
        step = AgentStep(step_number=0, is_done=True, summary="Quick")
        provider = FakeProvider([step])
        result = run_agent("quick", provider=provider, backend=mock_backend, max_steps=5)
        assert result.total_time >= 0

    def test_multiple_tool_calls_per_step(self, mock_backend):
        """A step can have multiple tool calls."""
        step1 = AgentStep(
            step_number=0,
            tool_calls=[
                ToolCall(name="click", arguments={"x": 10, "y": 20}, call_id="a"),
                ToolCall(name="type_text", arguments={"text": "hello"}, call_id="b"),
                ToolCall(name="press_key", arguments={"key": "enter"}, call_id="c"),
            ],
        )
        step2 = AgentStep(step_number=0, is_done=True, summary="Typed and submitted")
        provider = FakeProvider([step1, step2])
        result = run_agent("type and submit", provider=provider, backend=mock_backend, max_steps=5)
        assert result.success
        assert len(result.steps[0].tool_results) == 3
        mock_backend.click.assert_called_once()
        mock_backend.type_text.assert_called_once()
        mock_backend.press_key.assert_called_once()


# ── Data Model Tests ────────────────────────────


class TestDataModels:

    def test_agent_result_defaults(self):
        r = AgentResult(instruction="test")
        assert r.instruction == "test"
        assert r.step_count == 0
        assert not r.success
        assert r.error is None

    def test_tool_call_defaults(self):
        tc = ToolCall(name="click", arguments={"x": 1})
        assert tc.call_id == ""

    def test_tool_result_defaults(self):
        tr = ToolResult(call_id="1", name="click", result={"success": True})
        assert tr.success
        assert tr.error is None

    def test_step_status_enum(self):
        assert StepStatus.SUCCESS == "success"
        assert StepStatus.ERROR == "error"
        assert StepStatus.PENDING == "pending"
