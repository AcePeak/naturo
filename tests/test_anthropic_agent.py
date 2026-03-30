"""Tests for naturo.providers.anthropic_agent — Anthropic tool-use agent provider.

Covers: construction, run_step (first step, subsequent steps, done signal,
error handling), conversation building, message merging.
"""
from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from naturo.agent import AgentStep, StepStatus, ToolCall, ToolResult
from naturo.errors import AIProviderUnavailableError
from naturo.providers.anthropic_agent import AnthropicAgentProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("NATURO_AGENT_MODEL", raising=False)


@pytest.fixture()
def fake_image(tmp_path: Path) -> str:
    def _chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"\x00\xff\x00\x00"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw)) + _chunk(b"IEND", b"")
    p = tmp_path / "test.png"
    p.write_bytes(png)
    return str(p)


def _make_tool_use_block(name: str, input_data: dict, block_id: str = "tool_1") -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = input_data
    block.id = block_id
    return block


def _make_text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _mock_agent_response(
    blocks: list[MagicMock] | None = None,
    stop_reason: str = "tool_use",
) -> MagicMock:
    if blocks is None:
        blocks = [_make_tool_use_block("click", {"x": 100, "y": 200})]
    resp = MagicMock()
    resp.content = blocks
    resp.stop_reason = stop_reason
    return resp


# ---------------------------------------------------------------------------
# Construction & properties
# ---------------------------------------------------------------------------

class TestAnthropicAgentInit:
    def test_explicit_key(self) -> None:
        p = AnthropicAgentProvider(api_key="sk-test")
        assert p.name == "anthropic"
        assert p.is_available is True

    def test_env_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
        p = AnthropicAgentProvider()
        assert p.is_available is True

    def test_no_key(self) -> None:
        p = AnthropicAgentProvider()
        assert p.is_available is False

    def test_default_model(self) -> None:
        p = AnthropicAgentProvider(api_key="sk-test")
        assert p._model == "claude-sonnet-4-20250514"

    def test_custom_model(self) -> None:
        p = AnthropicAgentProvider(api_key="sk-test", model="claude-3-opus-20240229")
        assert p._model == "claude-3-opus-20240229"

    def test_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NATURO_AGENT_MODEL", "claude-3-haiku")
        p = AnthropicAgentProvider(api_key="sk-test")
        assert p._model == "claude-3-haiku"

    def test_empty_conversation(self) -> None:
        p = AnthropicAgentProvider(api_key="sk-test")
        assert p._conversation == []


# ---------------------------------------------------------------------------
# _get_client
# ---------------------------------------------------------------------------

class TestAnthropicAgentGetClient:
    def test_creates_client(self) -> None:
        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            p = AnthropicAgentProvider(api_key="sk-test")
            p._get_client()
            mock_anthropic.Anthropic.assert_called_once_with(api_key="sk-test")

    def test_missing_package(self) -> None:
        p = AnthropicAgentProvider(api_key="sk-test")
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(AIProviderUnavailableError):
                p._get_client()


# ---------------------------------------------------------------------------
# run_step — first step
# ---------------------------------------------------------------------------

class TestAnthropicAgentRunStepFirst:
    @patch("naturo.providers.anthropic_agent.AnthropicAgentProvider._get_client")
    def test_first_step_with_tool_call(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_agent_response([
            _make_text_block("I'll click the button"),
            _make_tool_use_block("click", {"x": 100, "y": 200}, "call_1"),
        ])
        mock_get_client.return_value = mock_client

        p = AnthropicAgentProvider(api_key="sk-test")
        step = p.run_step("Click the Save button", fake_image, None, [])

        assert step.step_number == 1
        assert step.status == StepStatus.SUCCESS
        assert len(step.tool_calls) == 1
        assert step.tool_calls[0].name == "click"
        assert step.tool_calls[0].arguments == {"x": 100, "y": 200}
        assert step.reasoning == "I'll click the button"
        assert step.is_done is False

    @patch("naturo.providers.anthropic_agent.AnthropicAgentProvider._get_client")
    def test_first_step_no_screenshot(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_agent_response()
        mock_get_client.return_value = mock_client

        p = AnthropicAgentProvider(api_key="sk-test")
        step = p.run_step("List windows", None, None, [])

        assert step.status == StepStatus.SUCCESS
        # Verify no image block in message
        call_kwargs = mock_client.messages.create.call_args[1]
        user_content = call_kwargs["messages"][0]["content"]
        image_blocks = [c for c in user_content if c.get("type") == "image"]
        assert len(image_blocks) == 0

    @patch("naturo.providers.anthropic_agent.AnthropicAgentProvider._get_client")
    def test_first_step_with_ui_tree(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_agent_response()
        mock_get_client.return_value = mock_client

        ui_tree = {"root": {"role": "Window", "name": "Notepad"}}
        p = AnthropicAgentProvider(api_key="sk-test")
        p.run_step("Click save", None, ui_tree, [])

        call_kwargs = mock_client.messages.create.call_args[1]
        user_content = call_kwargs["messages"][0]["content"]
        text_block = [c for c in user_content if c.get("type") == "text"][0]
        assert "Notepad" in text_block["text"]

    @patch("naturo.providers.anthropic_agent.AnthropicAgentProvider._get_client")
    def test_ui_tree_truncation(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_agent_response()
        mock_get_client.return_value = mock_client

        # Create a large UI tree
        big_tree = {"elements": [{"name": f"element_{i}", "role": "Button"} for i in range(500)]}
        p = AnthropicAgentProvider(api_key="sk-test")
        p.run_step("Click", None, big_tree, [])

        call_kwargs = mock_client.messages.create.call_args[1]
        text_block = [c for c in call_kwargs["messages"][0]["content"] if c.get("type") == "text"][0]
        assert "truncated" in text_block["text"]


# ---------------------------------------------------------------------------
# run_step — done signal
# ---------------------------------------------------------------------------

class TestAnthropicAgentDoneSignal:
    @patch("naturo.providers.anthropic_agent.AnthropicAgentProvider._get_client")
    def test_done_tool(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_agent_response([
            _make_tool_use_block("done", {"summary": "Task completed successfully"}, "call_done"),
        ])
        mock_get_client.return_value = mock_client

        p = AnthropicAgentProvider(api_key="sk-test")
        step = p.run_step("Do something", None, None, [])

        assert step.is_done is True
        assert step.summary == "Task completed successfully"

    @patch("naturo.providers.anthropic_agent.AnthropicAgentProvider._get_client")
    def test_end_turn_without_tools(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_agent_response(
            [_make_text_block("All done, nothing more to do")],
            stop_reason="end_turn",
        )
        mock_get_client.return_value = mock_client

        p = AnthropicAgentProvider(api_key="sk-test")
        step = p.run_step("Check status", None, None, [])

        assert step.is_done is True
        assert "All done" in step.summary

    @patch("naturo.providers.anthropic_agent.AnthropicAgentProvider._get_client")
    def test_end_turn_no_text(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        resp = MagicMock()
        resp.content = []
        resp.stop_reason = "end_turn"
        mock_client.messages.create.return_value = resp
        mock_get_client.return_value = mock_client

        p = AnthropicAgentProvider(api_key="sk-test")
        step = p.run_step("Check", None, None, [])
        assert step.is_done is True
        assert "no further actions" in step.summary.lower()


# ---------------------------------------------------------------------------
# run_step — multiple tool calls
# ---------------------------------------------------------------------------

class TestAnthropicAgentMultipleToolCalls:
    @patch("naturo.providers.anthropic_agent.AnthropicAgentProvider._get_client")
    def test_multiple_tools(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_agent_response([
            _make_text_block("First click, then type"),
            _make_tool_use_block("click", {"x": 50, "y": 50}, "call_1"),
            _make_tool_use_block("type_text", {"text": "hello"}, "call_2"),
        ])
        mock_get_client.return_value = mock_client

        p = AnthropicAgentProvider(api_key="sk-test")
        step = p.run_step("Type hello in field", None, None, [])

        assert len(step.tool_calls) == 2
        assert step.tool_calls[0].name == "click"
        assert step.tool_calls[1].name == "type_text"
        assert step.tool_calls[1].arguments["text"] == "hello"


# ---------------------------------------------------------------------------
# run_step — error handling
# ---------------------------------------------------------------------------

class TestAnthropicAgentErrors:
    def test_unavailable(self) -> None:
        p = AnthropicAgentProvider()
        with pytest.raises(AIProviderUnavailableError):
            p.run_step("Do thing", None, None, [])

    @patch("naturo.providers.anthropic_agent.AnthropicAgentProvider._get_client")
    def test_api_error(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("rate limited")
        mock_get_client.return_value = mock_client

        p = AnthropicAgentProvider(api_key="sk-test")
        step = p.run_step("Click button", None, None, [])

        assert step.status == StepStatus.ERROR
        assert "rate limited" in step.summary


# ---------------------------------------------------------------------------
# run_step — subsequent steps with history
# ---------------------------------------------------------------------------

class TestAnthropicAgentSubsequentSteps:
    @patch("naturo.providers.anthropic_agent.AnthropicAgentProvider._get_client")
    def test_step_2_includes_history(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_agent_response([
            _make_tool_use_block("type_text", {"text": "world"}, "call_2"),
        ])
        mock_get_client.return_value = mock_client

        prev_step = AgentStep(step_number=1, status=StepStatus.SUCCESS)
        prev_step.reasoning = "Clicking the field"
        prev_step.tool_calls = [ToolCall(name="click", arguments={"x": 50, "y": 50}, call_id="tc_1")]
        prev_step.tool_results = [
            ToolResult(call_id="tc_1", name="click", result={"status": "ok"}, success=True),
        ]

        p = AnthropicAgentProvider(api_key="sk-test")
        step = p.run_step("Type world", None, None, [prev_step])

        assert step.step_number == 2
        assert step.status == StepStatus.SUCCESS
        # Verify conversation was built with history
        call_kwargs = mock_client.messages.create.call_args[1]
        assert len(call_kwargs["messages"]) >= 2  # at least prev assistant + current user

    @patch("naturo.providers.anthropic_agent.AnthropicAgentProvider._get_client")
    def test_step_2_with_failed_tool_result(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_agent_response([
            _make_tool_use_block("click", {"x": 200, "y": 200}, "call_retry"),
        ])
        mock_get_client.return_value = mock_client

        prev_step = AgentStep(step_number=1, status=StepStatus.SUCCESS)
        prev_step.tool_calls = [ToolCall(name="click", arguments={"x": 0, "y": 0}, call_id="tc_1")]
        prev_step.tool_results = [
            ToolResult(call_id="tc_1", name="click", result={"error": "out of bounds"}, success=False),
        ]

        p = AnthropicAgentProvider(api_key="sk-test")
        step = p.run_step("Click button", None, None, [prev_step])
        assert step.status == StepStatus.SUCCESS


# ---------------------------------------------------------------------------
# _build_assistant_content
# ---------------------------------------------------------------------------

class TestBuildAssistantContent:
    def test_with_reasoning_and_tools(self) -> None:
        p = AnthropicAgentProvider(api_key="sk-test")
        step = AgentStep(step_number=1)
        step.reasoning = "Thinking..."
        step.tool_calls = [ToolCall(name="click", arguments={"x": 1, "y": 2}, call_id="c1")]

        content = p._build_assistant_content(step)
        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "tool_use"
        assert content[1]["name"] == "click"

    def test_empty_step(self) -> None:
        p = AnthropicAgentProvider(api_key="sk-test")
        step = AgentStep(step_number=1)
        content = p._build_assistant_content(step)
        assert content == []

    def test_reasoning_only(self) -> None:
        p = AnthropicAgentProvider(api_key="sk-test")
        step = AgentStep(step_number=1)
        step.reasoning = "Just thinking"
        content = p._build_assistant_content(step)
        assert len(content) == 1
        assert content[0]["type"] == "text"


# ---------------------------------------------------------------------------
# _build_tool_result_content
# ---------------------------------------------------------------------------

class TestBuildToolResultContent:
    def test_success_result(self) -> None:
        p = AnthropicAgentProvider(api_key="sk-test")
        step = AgentStep(step_number=1)
        step.tool_results = [
            ToolResult(call_id="c1", name="click", result={"status": "ok"}, success=True),
        ]
        content = p._build_tool_result_content(step)
        assert len(content) == 1
        assert content[0]["type"] == "tool_result"
        assert content[0]["is_error"] is False

    def test_error_result(self) -> None:
        p = AnthropicAgentProvider(api_key="sk-test")
        step = AgentStep(step_number=1)
        step.tool_results = [
            ToolResult(call_id="c1", name="click", result={"error": "failed"}, success=False),
        ]
        content = p._build_tool_result_content(step)
        assert content[0]["is_error"] is True

    def test_empty_results(self) -> None:
        p = AnthropicAgentProvider(api_key="sk-test")
        step = AgentStep(step_number=1)
        content = p._build_tool_result_content(step)
        assert content == []


# ---------------------------------------------------------------------------
# _merge_consecutive_user_messages
# ---------------------------------------------------------------------------

class TestMergeConsecutiveMessages:
    def test_alternating_roles(self) -> None:
        msgs = [
            {"role": "user", "content": [{"type": "text", "text": "a"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "b"}]},
            {"role": "user", "content": [{"type": "text", "text": "c"}]},
        ]
        result = AnthropicAgentProvider._merge_consecutive_user_messages(msgs)
        assert len(result) == 3

    def test_consecutive_user_messages(self) -> None:
        msgs = [
            {"role": "user", "content": [{"type": "text", "text": "a"}]},
            {"role": "user", "content": [{"type": "text", "text": "b"}]},
        ]
        result = AnthropicAgentProvider._merge_consecutive_user_messages(msgs)
        assert len(result) == 1
        assert len(result[0]["content"]) == 2

    def test_string_content_normalized(self) -> None:
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "user", "content": "world"},
        ]
        result = AnthropicAgentProvider._merge_consecutive_user_messages(msgs)
        assert len(result) == 1
        assert len(result[0]["content"]) == 2
        assert result[0]["content"][0] == {"type": "text", "text": "hello"}

    def test_empty_list(self) -> None:
        assert AnthropicAgentProvider._merge_consecutive_user_messages([]) == []

    def test_single_message(self) -> None:
        msgs = [{"role": "user", "content": "solo"}]
        result = AnthropicAgentProvider._merge_consecutive_user_messages(msgs)
        assert len(result) == 1

    def test_three_consecutive_same_role(self) -> None:
        msgs = [
            {"role": "user", "content": [{"type": "text", "text": "a"}]},
            {"role": "user", "content": [{"type": "text", "text": "b"}]},
            {"role": "user", "content": [{"type": "text", "text": "c"}]},
        ]
        result = AnthropicAgentProvider._merge_consecutive_user_messages(msgs)
        assert len(result) == 1
        assert len(result[0]["content"]) == 3
