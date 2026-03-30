"""Tests for naturo.providers.openai_agent — OpenAI function-calling agent provider.

Covers: construction, run_step (first step, subsequent steps, done signal,
error handling), assistant message building, tool result messages.
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
from naturo.providers.openai_agent import OpenAIAgentProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
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


def _make_openai_tool_call(name: str, arguments: dict, call_id: str = "call_1") -> MagicMock:
    tc = MagicMock()
    tc.id = call_id
    tc.type = "function"
    tc.function = MagicMock()
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    return tc


def _mock_openai_agent_response(
    content: str | None = None,
    tool_calls: list[MagicMock] | None = None,
    finish_reason: str = "tool_calls",
) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls
    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = finish_reason
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ---------------------------------------------------------------------------
# Construction & properties
# ---------------------------------------------------------------------------

class TestOpenAIAgentInit:
    def test_explicit_key(self) -> None:
        p = OpenAIAgentProvider(api_key="sk-test")
        assert p.name == "openai"
        assert p.is_available is True

    def test_env_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
        p = OpenAIAgentProvider()
        assert p.is_available is True

    def test_no_key(self) -> None:
        p = OpenAIAgentProvider()
        assert p.is_available is False

    def test_default_model(self) -> None:
        p = OpenAIAgentProvider(api_key="sk-test")
        assert p._model == "gpt-4o"

    def test_custom_model(self) -> None:
        p = OpenAIAgentProvider(api_key="sk-test", model="gpt-4-turbo")
        assert p._model == "gpt-4-turbo"

    def test_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NATURO_AGENT_MODEL", "gpt-3.5-turbo")
        p = OpenAIAgentProvider(api_key="sk-test")
        assert p._model == "gpt-3.5-turbo"

    def test_base_url(self) -> None:
        p = OpenAIAgentProvider(api_key="sk-test", base_url="http://local:8080")
        assert p._base_url == "http://local:8080"

    def test_base_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_BASE_URL", "http://ollama:11434/v1")
        p = OpenAIAgentProvider(api_key="sk-test")
        assert p._base_url == "http://ollama:11434/v1"

    def test_empty_conversation(self) -> None:
        p = OpenAIAgentProvider(api_key="sk-test")
        assert p._conversation == []


# ---------------------------------------------------------------------------
# _get_client
# ---------------------------------------------------------------------------

class TestOpenAIAgentGetClient:
    def test_creates_client(self) -> None:
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            p = OpenAIAgentProvider(api_key="sk-test")
            p._get_client()
            mock_openai.OpenAI.assert_called_once_with(api_key="sk-test")

    def test_client_with_base_url(self) -> None:
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            p = OpenAIAgentProvider(api_key="sk-test", base_url="http://custom")
            p._get_client()
            call_kwargs = mock_openai.OpenAI.call_args[1]
            assert call_kwargs["base_url"] == "http://custom"

    def test_missing_package(self) -> None:
        p = OpenAIAgentProvider(api_key="sk-test")
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(AIProviderUnavailableError):
                p._get_client()


# ---------------------------------------------------------------------------
# run_step — first step
# ---------------------------------------------------------------------------

class TestOpenAIAgentRunStepFirst:
    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_first_step_with_tool_call(self, mock_get_client: MagicMock, fake_image: str) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_agent_response(
            content="I'll click the button",
            tool_calls=[_make_openai_tool_call("click", {"x": 100, "y": 200})],
        )
        mock_get_client.return_value = mock_client

        p = OpenAIAgentProvider(api_key="sk-test")
        step = p.run_step("Click Save", fake_image, None, [])

        assert step.step_number == 1
        assert step.status == StepStatus.SUCCESS
        assert len(step.tool_calls) == 1
        assert step.tool_calls[0].name == "click"
        assert step.tool_calls[0].arguments == {"x": 100, "y": 200}
        assert step.reasoning == "I'll click the button"

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_first_step_no_screenshot(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_agent_response(
            tool_calls=[_make_openai_tool_call("list_windows", {})],
        )
        mock_get_client.return_value = mock_client

        p = OpenAIAgentProvider(api_key="sk-test")
        step = p.run_step("List windows", None, None, [])
        assert step.status == StepStatus.SUCCESS

        # Verify no image_url block
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        user_msgs = [m for m in call_kwargs["messages"] if m["role"] == "user"]
        for msg in user_msgs:
            content = msg["content"]
            if isinstance(content, list):
                image_blocks = [c for c in content if c.get("type") == "image_url"]
                assert len(image_blocks) == 0

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_first_step_with_ui_tree(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_agent_response(
            tool_calls=[_make_openai_tool_call("click", {"x": 50, "y": 50})],
        )
        mock_get_client.return_value = mock_client

        ui_tree = {"root": {"role": "Window", "name": "Calculator"}}
        p = OpenAIAgentProvider(api_key="sk-test")
        p.run_step("Click =", None, ui_tree, [])

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        user_msgs = [m for m in call_kwargs["messages"] if m["role"] == "user"]
        text_blocks = []
        for msg in user_msgs:
            if isinstance(msg["content"], list):
                text_blocks.extend(c for c in msg["content"] if c.get("type") == "text")
        assert any("Calculator" in b["text"] for b in text_blocks)

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_ui_tree_truncation(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_agent_response(
            tool_calls=[_make_openai_tool_call("click", {"x": 1, "y": 1})],
        )
        mock_get_client.return_value = mock_client

        big_tree = {"elements": [{"name": f"el_{i}"} for i in range(1000)]}
        p = OpenAIAgentProvider(api_key="sk-test")
        p.run_step("Click", None, big_tree, [])

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        user_msgs = [m for m in call_kwargs["messages"] if m["role"] == "user"]
        all_text = ""
        for msg in user_msgs:
            if isinstance(msg["content"], list):
                for c in msg["content"]:
                    if c.get("type") == "text":
                        all_text += c["text"]
        assert "truncated" in all_text

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_system_prompt_included(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_agent_response(
            tool_calls=[_make_openai_tool_call("done", {"summary": "ok"})],
        )
        mock_get_client.return_value = mock_client

        p = OpenAIAgentProvider(api_key="sk-test")
        p.run_step("Do it", None, None, [])

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        system_msgs = [m for m in call_kwargs["messages"] if m["role"] == "system"]
        assert len(system_msgs) == 1
        assert "Naturo" in system_msgs[0]["content"]


# ---------------------------------------------------------------------------
# run_step — done signal
# ---------------------------------------------------------------------------

class TestOpenAIAgentDoneSignal:
    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_done_function(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_agent_response(
            tool_calls=[_make_openai_tool_call("done", {"summary": "All done"}, "call_done")],
        )
        mock_get_client.return_value = mock_client

        p = OpenAIAgentProvider(api_key="sk-test")
        step = p.run_step("Finish up", None, None, [])

        assert step.is_done is True
        assert step.summary == "All done"

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_stop_without_tools(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_agent_response(
            content="Nothing more to do",
            tool_calls=None,
            finish_reason="stop",
        )
        mock_get_client.return_value = mock_client

        p = OpenAIAgentProvider(api_key="sk-test")
        step = p.run_step("Check", None, None, [])

        assert step.is_done is True
        assert "Nothing more" in step.summary

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_stop_no_content(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_agent_response(
            content=None,
            tool_calls=None,
            finish_reason="stop",
        )
        mock_get_client.return_value = mock_client

        p = OpenAIAgentProvider(api_key="sk-test")
        step = p.run_step("Done?", None, None, [])
        assert step.is_done is True


# ---------------------------------------------------------------------------
# run_step — multiple tool calls
# ---------------------------------------------------------------------------

class TestOpenAIAgentMultipleToolCalls:
    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_multiple_tools(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_agent_response(
            content="Click then type",
            tool_calls=[
                _make_openai_tool_call("click", {"x": 50, "y": 50}, "c1"),
                _make_openai_tool_call("type_text", {"text": "hello"}, "c2"),
            ],
        )
        mock_get_client.return_value = mock_client

        p = OpenAIAgentProvider(api_key="sk-test")
        step = p.run_step("Type hello", None, None, [])

        assert len(step.tool_calls) == 2
        assert step.tool_calls[0].name == "click"
        assert step.tool_calls[1].name == "type_text"
        assert step.tool_calls[1].arguments["text"] == "hello"

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_malformed_arguments(self, mock_get_client: MagicMock) -> None:
        """Tool call with invalid JSON arguments should default to empty dict."""
        tc = MagicMock()
        tc.id = "c1"
        tc.function = MagicMock()
        tc.function.name = "click"
        tc.function.arguments = "not json"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_agent_response(
            tool_calls=[tc],
        )
        mock_get_client.return_value = mock_client

        p = OpenAIAgentProvider(api_key="sk-test")
        step = p.run_step("Click", None, None, [])
        assert step.tool_calls[0].arguments == {}


# ---------------------------------------------------------------------------
# run_step — error handling
# ---------------------------------------------------------------------------

class TestOpenAIAgentErrors:
    def test_unavailable(self) -> None:
        p = OpenAIAgentProvider()
        with pytest.raises(AIProviderUnavailableError):
            p.run_step("Do thing", None, None, [])

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_api_error(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("rate limited")
        mock_get_client.return_value = mock_client

        p = OpenAIAgentProvider(api_key="sk-test")
        step = p.run_step("Click", None, None, [])

        assert step.status == StepStatus.ERROR
        assert "rate limited" in step.summary


# ---------------------------------------------------------------------------
# run_step — subsequent steps with history
# ---------------------------------------------------------------------------

class TestOpenAIAgentSubsequentSteps:
    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_step_2_includes_history(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_agent_response(
            tool_calls=[_make_openai_tool_call("type_text", {"text": "world"})],
        )
        mock_get_client.return_value = mock_client

        prev_step = AgentStep(step_number=1, status=StepStatus.SUCCESS)
        prev_step.reasoning = "Clicking field"
        prev_step.tool_calls = [ToolCall(name="click", arguments={"x": 50, "y": 50}, call_id="tc_1")]
        prev_step.tool_results = [
            ToolResult(call_id="tc_1", name="click", result={"status": "ok"}, success=True),
        ]

        p = OpenAIAgentProvider(api_key="sk-test")
        step = p.run_step("Type world", None, None, [prev_step])

        assert step.step_number == 2
        assert step.status == StepStatus.SUCCESS

        # Verify conversation has system + assistant + tool + user messages
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        roles = [m["role"] for m in call_kwargs["messages"]]
        assert "system" in roles
        assert "assistant" in roles
        assert "tool" in roles

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_step_2_with_failed_result(self, mock_get_client: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_openai_agent_response(
            tool_calls=[_make_openai_tool_call("click", {"x": 200, "y": 200})],
        )
        mock_get_client.return_value = mock_client

        prev_step = AgentStep(step_number=1, status=StepStatus.SUCCESS)
        prev_step.tool_calls = [ToolCall(name="click", arguments={}, call_id="tc_1")]
        prev_step.tool_results = [
            ToolResult(call_id="tc_1", name="click", result={"error": "miss"}, success=False),
        ]

        p = OpenAIAgentProvider(api_key="sk-test")
        step = p.run_step("Click again", None, None, [prev_step])
        assert step.status == StepStatus.SUCCESS


# ---------------------------------------------------------------------------
# _build_assistant_message
# ---------------------------------------------------------------------------

class TestBuildAssistantMessage:
    def test_with_reasoning_and_tools(self) -> None:
        p = OpenAIAgentProvider(api_key="sk-test")
        step = AgentStep(step_number=1)
        step.reasoning = "Thinking"
        step.tool_calls = [ToolCall(name="click", arguments={"x": 1}, call_id="c1")]

        msg = p._build_assistant_message(step)
        assert msg is not None
        assert msg["role"] == "assistant"
        assert msg["content"] == "Thinking"
        assert len(msg["tool_calls"]) == 1
        assert msg["tool_calls"][0]["function"]["name"] == "click"

    def test_tools_only(self) -> None:
        p = OpenAIAgentProvider(api_key="sk-test")
        step = AgentStep(step_number=1)
        step.tool_calls = [ToolCall(name="done", arguments={}, call_id="c1")]

        msg = p._build_assistant_message(step)
        assert msg is not None
        assert msg["content"] is None

    def test_empty_step(self) -> None:
        p = OpenAIAgentProvider(api_key="sk-test")
        step = AgentStep(step_number=1)
        msg = p._build_assistant_message(step)
        assert msg is None

    def test_reasoning_only(self) -> None:
        p = OpenAIAgentProvider(api_key="sk-test")
        step = AgentStep(step_number=1)
        step.reasoning = "Just thinking"
        msg = p._build_assistant_message(step)
        assert msg is not None
        assert msg["content"] == "Just thinking"
        assert "tool_calls" not in msg


# ---------------------------------------------------------------------------
# _build_tool_result_messages
# ---------------------------------------------------------------------------

class TestBuildToolResultMessages:
    def test_success_results(self) -> None:
        p = OpenAIAgentProvider(api_key="sk-test")
        step = AgentStep(step_number=1)
        step.tool_results = [
            ToolResult(call_id="c1", name="click", result={"ok": True}, success=True),
            ToolResult(call_id="c2", name="type_text", result={"ok": True}, success=True),
        ]
        msgs = p._build_tool_result_messages(step)
        assert len(msgs) == 2
        assert all(m["role"] == "tool" for m in msgs)
        assert msgs[0]["tool_call_id"] == "c1"
        assert msgs[1]["tool_call_id"] == "c2"

    def test_empty_results(self) -> None:
        p = OpenAIAgentProvider(api_key="sk-test")
        step = AgentStep(step_number=1)
        msgs = p._build_tool_result_messages(step)
        assert msgs == []

    def test_result_content_is_json(self) -> None:
        p = OpenAIAgentProvider(api_key="sk-test")
        step = AgentStep(step_number=1)
        step.tool_results = [
            ToolResult(call_id="c1", name="list_windows", result={"windows": ["Notepad"]}, success=True),
        ]
        msgs = p._build_tool_result_messages(step)
        parsed = json.loads(msgs[0]["content"])
        assert parsed["windows"] == ["Notepad"]
