"""Tests for naturo/agent.py — agent loop, tool executor, data classes."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

from naturo.agent import (
    AgentResult,
    AgentStep,
    AIProvider,
    StepStatus,
    ToolCall,
    ToolExecutor,
    ToolResult,
    _serialize_tree,
    run_agent,
)
from naturo.errors import NaturoError


# ── Data class tests ───────────────────────────────


class TestStepStatus:
    def test_enum_values(self):
        assert StepStatus.SUCCESS == "success"
        assert StepStatus.ERROR == "error"
        assert StepStatus.PENDING == "pending"

    def test_is_str(self):
        assert isinstance(StepStatus.SUCCESS, str)


class TestToolCall:
    def test_defaults(self):
        tc = ToolCall(name="click", arguments={"x": 100})
        assert tc.name == "click"
        assert tc.arguments == {"x": 100}
        assert tc.call_id == ""

    def test_with_call_id(self):
        tc = ToolCall(name="type_text", arguments={"text": "hi"}, call_id="abc123")
        assert tc.call_id == "abc123"


class TestToolResult:
    def test_success_default(self):
        tr = ToolResult(call_id="c1", name="click", result={"success": True})
        assert tr.success is True
        assert tr.error is None

    def test_failure(self):
        tr = ToolResult(
            call_id="c2", name="click", result={"error": "not found"},
            success=False, error="not found",
        )
        assert tr.success is False
        assert tr.error == "not found"


class TestAgentStep:
    def test_defaults(self):
        step = AgentStep(step_number=1)
        assert step.step_number == 1
        assert step.reasoning == ""
        assert step.tool_calls == []
        assert step.tool_results == []
        assert step.status == StepStatus.PENDING
        assert step.is_done is False
        assert step.summary == ""


class TestAgentResult:
    def test_defaults(self):
        r = AgentResult(instruction="open notepad")
        assert r.instruction == "open notepad"
        assert r.steps == []
        assert r.success is False
        assert r.summary == ""
        assert r.total_time == 0.0
        assert r.error is None

    def test_step_count(self):
        r = AgentResult(instruction="test")
        r.steps = [AgentStep(step_number=1), AgentStep(step_number=2)]
        assert r.step_count == 2

    def test_step_count_empty(self):
        r = AgentResult(instruction="test")
        assert r.step_count == 0


# ── ToolExecutor tests ─────────────────────────────


class TestToolExecutor:
    def _make_executor(self) -> tuple[ToolExecutor, MagicMock]:
        backend = MagicMock()
        executor = ToolExecutor(backend)
        return executor, backend

    def test_known_tool_click(self):
        executor, backend = self._make_executor()
        tc = ToolCall(name="click", arguments={"x": 100, "y": 200}, call_id="c1")
        result = executor.execute(tc)
        assert result.success is True
        assert result.name == "click"
        assert result.call_id == "c1"
        backend.click.assert_called_once_with(
            x=100, y=200, element_id=None, button="left", double=False,
        )

    def test_known_tool_type_text(self):
        executor, backend = self._make_executor()
        tc = ToolCall(name="type_text", arguments={"text": "hello"}, call_id="c2")
        result = executor.execute(tc)
        assert result.success is True
        backend.type_text.assert_called_once_with(text="hello", wpm=120)

    def test_known_tool_press_key_count(self):
        executor, backend = self._make_executor()
        tc = ToolCall(name="press_key", arguments={"key": "enter", "count": 3}, call_id="c3")
        result = executor.execute(tc)
        assert result.success is True
        assert backend.press_key.call_count == 3

    def test_known_tool_hotkey(self):
        executor, backend = self._make_executor()
        tc = ToolCall(name="hotkey", arguments={"keys": ["ctrl", "s"]}, call_id="c4")
        result = executor.execute(tc)
        assert result.success is True
        backend.hotkey.assert_called_once_with("ctrl", "s")

    def test_known_tool_scroll(self):
        executor, backend = self._make_executor()
        tc = ToolCall(name="scroll", arguments={}, call_id="c5")
        result = executor.execute(tc)
        assert result.success is True
        backend.scroll.assert_called_once_with(
            direction="down", amount=3, x=None, y=None,
        )

    def test_known_tool_drag(self):
        executor, backend = self._make_executor()
        tc = ToolCall(
            name="drag",
            arguments={"from_x": 0, "from_y": 0, "to_x": 100, "to_y": 100},
            call_id="c6",
        )
        result = executor.execute(tc)
        assert result.success is True
        backend.drag.assert_called_once()

    def test_known_tool_move_mouse(self):
        executor, backend = self._make_executor()
        tc = ToolCall(name="move_mouse", arguments={"x": 50, "y": 60}, call_id="c7")
        result = executor.execute(tc)
        assert result.success is True
        backend.move_mouse.assert_called_once_with(x=50, y=60)

    def test_known_tool_list_windows(self):
        executor, backend = self._make_executor()
        mock_win = MagicMock(title="Notepad", process_name="notepad.exe", pid=1234)
        backend.list_windows.return_value = [mock_win]
        tc = ToolCall(name="list_windows", arguments={}, call_id="c8")
        result = executor.execute(tc)
        assert result.success is True
        assert result.result["windows"][0]["title"] == "Notepad"

    def test_known_tool_capture_screen(self):
        executor, backend = self._make_executor()
        capture_result = MagicMock(path="/tmp/shot.png", width=1920, height=1080)
        backend.capture_screen.return_value = capture_result
        tc = ToolCall(name="capture_screen", arguments={}, call_id="c9")
        result = executor.execute(tc)
        assert result.success is True
        assert result.result["path"] == "/tmp/shot.png"

    def test_known_tool_find_element_found(self):
        executor, backend = self._make_executor()
        mock_el = MagicMock()
        mock_el.id = "e1"
        mock_el.role = "Button"
        mock_el.name = "OK"
        mock_el.x = 10
        mock_el.y = 20
        mock_el.width = 80
        mock_el.height = 30
        backend.find_element.return_value = mock_el
        tc = ToolCall(name="find_element", arguments={"selector": "Button:OK"}, call_id="c10")
        result = executor.execute(tc)
        assert result.success is True
        assert result.result["element"]["name"] == "OK"

    def test_known_tool_find_element_not_found(self):
        executor, backend = self._make_executor()
        backend.find_element.return_value = None
        tc = ToolCall(name="find_element", arguments={"selector": "Button:Missing"}, call_id="c11")
        result = executor.execute(tc)
        assert result.success is True  # Handler returns success but with error in result
        assert result.result["success"] is False

    def test_known_tool_done(self):
        executor, _ = self._make_executor()
        tc = ToolCall(name="done", arguments={"summary": "All done"}, call_id="c12")
        result = executor.execute(tc)
        assert result.success is True
        assert result.result["done"] is True
        assert result.result["summary"] == "All done"

    def test_known_tool_focus_window(self):
        executor, backend = self._make_executor()
        tc = ToolCall(name="focus_window", arguments={"title": "Notepad"}, call_id="c13")
        result = executor.execute(tc)
        assert result.success is True
        backend.focus_window.assert_called_once_with(title="Notepad")

    def test_known_tool_close_window(self):
        executor, backend = self._make_executor()
        tc = ToolCall(name="close_window", arguments={"title": "Notepad"}, call_id="c14")
        result = executor.execute(tc)
        assert result.success is True

    def test_known_tool_launch_app(self):
        executor, backend = self._make_executor()
        tc = ToolCall(name="launch_app", arguments={"name": "notepad"}, call_id="c15")
        result = executor.execute(tc)
        assert result.success is True

    def test_known_tool_quit_app(self):
        executor, backend = self._make_executor()
        tc = ToolCall(name="quit_app", arguments={"name": "notepad"}, call_id="c16")
        result = executor.execute(tc)
        assert result.success is True

    def test_known_tool_clipboard_get(self):
        executor, backend = self._make_executor()
        backend.clipboard_get.return_value = "clipboard text"
        tc = ToolCall(name="clipboard_get", arguments={}, call_id="c17")
        result = executor.execute(tc)
        assert result.success is True
        assert result.result["text"] == "clipboard text"

    def test_known_tool_clipboard_set(self):
        executor, backend = self._make_executor()
        tc = ToolCall(name="clipboard_set", arguments={"text": "new"}, call_id="c18")
        result = executor.execute(tc)
        assert result.success is True

    def test_unknown_tool(self):
        executor, _ = self._make_executor()
        tc = ToolCall(name="nonexistent", arguments={}, call_id="c99")
        result = executor.execute(tc)
        assert result.success is False
        assert "Unknown tool" in result.error

    def test_naturo_error_handling(self):
        executor, backend = self._make_executor()
        backend.click.side_effect = NaturoError(
            "Element not found",
            code="ELEMENT_NOT_FOUND",
            suggested_action="Try a different selector",
            is_recoverable=True,
        )
        tc = ToolCall(name="click", arguments={"x": 0, "y": 0}, call_id="c20")
        result = executor.execute(tc)
        assert result.success is False
        assert "Element not found" in result.error
        assert result.result["code"] == "ELEMENT_NOT_FOUND"
        assert result.result["suggested_action"] == "Try a different selector"
        assert result.result["recoverable"] is True

    def test_generic_exception_handling(self):
        executor, backend = self._make_executor()
        backend.click.side_effect = RuntimeError("unexpected crash")
        tc = ToolCall(name="click", arguments={"x": 0, "y": 0}, call_id="c21")
        result = executor.execute(tc)
        assert result.success is False
        assert "RuntimeError" in result.result["error"]

    def test_tool_map_completeness(self):
        """Verify all expected tools are registered."""
        executor, _ = self._make_executor()
        expected = {
            "click", "type_text", "press_key", "hotkey", "scroll", "drag",
            "move_mouse", "find_element", "capture_screen", "list_windows",
            "focus_window", "close_window", "launch_app", "quit_app",
            "clipboard_get", "clipboard_set", "wait_for_element", "done",
        }
        assert set(executor._tools.keys()) == expected


# ── run_agent tests ────────────────────────────────


class _FakeProvider:
    """Minimal AIProvider for testing."""

    def __init__(self, steps: list[AgentStep]):
        self._steps = iter(steps)

    def run_step(self, instruction, screenshot_path, ui_tree, history):
        return next(self._steps)


class TestRunAgent:
    def test_immediate_done(self):
        done_step = AgentStep(step_number=0, is_done=True, summary="Finished")
        provider = _FakeProvider([done_step])
        backend = MagicMock()
        backend.capture_screen.side_effect = Exception("no display")

        result = run_agent("do something", provider=provider, backend=backend, max_steps=5)
        assert result.success is True
        assert result.summary == "Finished"
        assert result.step_count == 1

    def test_max_steps_reached(self):
        steps = [AgentStep(step_number=0) for _ in range(3)]
        provider = _FakeProvider(steps)
        backend = MagicMock()
        backend.capture_screen.side_effect = Exception("no display")
        backend.get_element_tree.side_effect = Exception("no display")

        result = run_agent("do something", provider=provider, backend=backend, max_steps=3)
        assert result.success is False
        assert "maximum steps" in result.error.lower()
        assert result.step_count == 3

    def test_tool_execution(self):
        step = AgentStep(
            step_number=0,
            tool_calls=[ToolCall(name="done", arguments={"summary": "Done via tool"}, call_id="t1")],
        )
        provider = _FakeProvider([step])
        backend = MagicMock()
        backend.capture_screen.side_effect = Exception("no display")
        backend.get_element_tree.side_effect = Exception("no display")

        result = run_agent("do something", provider=provider, backend=backend, max_steps=5)
        assert result.success is True
        assert result.summary == "Done via tool"

    def test_dry_run(self):
        step = AgentStep(
            step_number=0,
            tool_calls=[ToolCall(name="click", arguments={"x": 100, "y": 200}, call_id="t2")],
        )
        done_step = AgentStep(step_number=0, is_done=True, summary="done")
        provider = _FakeProvider([step, done_step])
        backend = MagicMock()
        backend.capture_screen.side_effect = Exception("no display")
        backend.get_element_tree.side_effect = Exception("no display")

        result = run_agent("do something", provider=provider, backend=backend, max_steps=5, dry_run=True)
        # In dry run, click is not executed
        backend.click.assert_not_called()
        assert result.step_count >= 1

    def test_provider_error(self):
        class FailProvider:
            def run_step(self, instruction, screenshot_path, ui_tree, history):
                raise RuntimeError("API down")

        backend = MagicMock()
        backend.capture_screen.side_effect = Exception("no display")
        backend.get_element_tree.side_effect = Exception("no display")

        result = run_agent("do something", provider=FailProvider(), backend=backend, max_steps=5)
        assert result.success is False
        assert "API down" in result.error

    def test_capture_dir_used(self, tmp_path):
        done_step = AgentStep(step_number=0, is_done=True, summary="ok")
        provider = _FakeProvider([done_step])
        backend = MagicMock()
        backend.capture_screen.side_effect = Exception("no display")

        result = run_agent(
            "test", provider=provider, backend=backend,
            capture_dir=str(tmp_path),
        )
        assert result.success is True
        # Capture was attempted with correct path
        backend.capture_screen.assert_called_once()
        call_args = backend.capture_screen.call_args
        assert str(tmp_path) in call_args.kwargs.get("output_path", "")

    def test_total_time_recorded(self):
        done_step = AgentStep(step_number=0, is_done=True, summary="ok")
        provider = _FakeProvider([done_step])
        backend = MagicMock()
        backend.capture_screen.side_effect = Exception("no display")

        result = run_agent("test", provider=provider, backend=backend)
        assert result.total_time > 0

    def test_ui_tree_captured_when_available(self):
        done_step = AgentStep(step_number=0, is_done=True, summary="ok")
        provider = _FakeProvider([done_step])
        backend = MagicMock()
        backend.capture_screen.side_effect = Exception("no display")
        mock_tree = _mock_element("root", "Window", "Test", width=800, height=600)
        backend.get_element_tree.return_value = mock_tree

        result = run_agent("test", provider=provider, backend=backend)
        assert result.success is True
        backend.get_element_tree.assert_called_once()


# ── _serialize_tree tests ──────────────────────────


def _mock_element(id, role, name, value=None, x=0, y=0, width=100, height=30, children=None):
    """Create a mock element with proper 'name' handling (MagicMock reserves 'name')."""
    el = MagicMock()
    el.id = id
    el.role = role
    el.name = name  # Must set after construction for MagicMock
    el.value = value
    el.x = x
    el.y = y
    el.width = width
    el.height = height
    el.children = children or []
    return el


class TestSerializeTree:
    def test_leaf_node(self):
        el = _mock_element("e1", "Button", "OK", x=10, y=20, width=80, height=30)
        d = _serialize_tree(el)
        assert d["id"] == "e1"
        assert d["role"] == "Button"
        assert d["name"] == "OK"
        assert "value" not in d
        assert d["bounds"] == {"x": 10, "y": 20, "w": 80, "h": 30}
        assert "children" not in d

    def test_with_value(self):
        el = _mock_element("e2", "Edit", "Search", value="hello", width=200, height=25)
        d = _serialize_tree(el)
        assert d["value"] == "hello"

    def test_with_children(self):
        child = _mock_element("e2", "Button", "OK", x=10, y=20, width=80, height=30)
        parent = _mock_element("e1", "Window", "Dialog", width=400, height=300, children=[child])
        d = _serialize_tree(parent)
        assert len(d["children"]) == 1
        assert d["children"][0]["id"] == "e2"

    def test_nested_children(self):
        grandchild = _mock_element("e3", "Text", "Label", value="hello", x=5, y=5, width=50, height=15)
        child = _mock_element("e2", "Group", "Panel", width=100, height=50, children=[grandchild])
        root = _mock_element("e1", "Window", "App", width=800, height=600, children=[child])
        d = _serialize_tree(root)
        assert d["children"][0]["children"][0]["id"] == "e3"
        assert d["children"][0]["children"][0]["value"] == "hello"


# ── AIProvider protocol test ───────────────────────


class TestAIProviderProtocol:
    def test_fake_provider_is_ai_provider(self):
        """Verify _FakeProvider satisfies the AIProvider protocol."""
        provider = _FakeProvider([])
        assert isinstance(provider, AIProvider)

    def test_non_provider_is_not_ai_provider(self):
        """An object without run_step is not an AIProvider."""

        class NotAProvider:
            pass

        assert not isinstance(NotAProvider(), AIProvider)
