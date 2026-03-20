"""Tests for the OpenAI agent provider (Phase 4.8).

Tests cover:
- Provider construction and availability
- Step parsing from OpenAI responses
- Tool call extraction from function-calling format
- Conversation management (tool results as separate messages)
- End-to-end agent loop with mocked OpenAI provider
- CLI --provider openai flag
"""
import json
import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from click.testing import CliRunner

from naturo.agent import (
    AgentResult,
    AgentStep,
    StepStatus,
    ToolCall,
    ToolResult,
    run_agent,
)


# ── Provider Tests ──────────────────────────────


class TestOpenAIAgentProvider:
    """Tests for OpenAIAgentProvider."""

    def test_provider_not_available_without_key(self):
        """Provider should report unavailable without API key."""
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            from naturo.providers.openai_agent import OpenAIAgentProvider
            provider = OpenAIAgentProvider(api_key="")
            assert not provider.is_available

    def test_provider_available_with_key(self):
        """Provider should report available with API key."""
        from naturo.providers.openai_agent import OpenAIAgentProvider
        provider = OpenAIAgentProvider(api_key="test-key-123")
        assert provider.is_available

    def test_provider_name(self):
        """Provider name should be 'openai'."""
        from naturo.providers.openai_agent import OpenAIAgentProvider
        provider = OpenAIAgentProvider(api_key="test")
        assert provider.name == "openai"

    def test_provider_custom_model(self):
        """Provider should accept custom model."""
        from naturo.providers.openai_agent import OpenAIAgentProvider
        provider = OpenAIAgentProvider(api_key="test", model="gpt-4-turbo")
        assert provider._model == "gpt-4-turbo"

    def test_provider_custom_base_url(self):
        """Provider should accept custom base URL for compatible APIs."""
        from naturo.providers.openai_agent import OpenAIAgentProvider
        provider = OpenAIAgentProvider(
            api_key="test", base_url="http://localhost:11434/v1"
        )
        assert provider._base_url == "http://localhost:11434/v1"

    def test_provider_env_base_url(self):
        """Provider should read OPENAI_BASE_URL from env."""
        from naturo.providers.openai_agent import OpenAIAgentProvider
        with patch.dict(os.environ, {"OPENAI_BASE_URL": "http://custom:8080/v1"}):
            provider = OpenAIAgentProvider(api_key="test")
            assert provider._base_url == "http://custom:8080/v1"

    def test_run_step_without_key_raises(self):
        """run_step should raise when API key is not set."""
        from naturo.providers.openai_agent import OpenAIAgentProvider
        from naturo.errors import AIProviderUnavailableError
        provider = OpenAIAgentProvider(api_key="")
        with pytest.raises(AIProviderUnavailableError):
            provider.run_step("test", None, None, [])


# ── Message Building Tests ──────────────────────


class TestOpenAIAgentMessages:
    """Tests for message building helpers."""

    def test_build_assistant_message_with_tool_calls(self):
        """Should build assistant message with tool_calls array."""
        from naturo.providers.openai_agent import OpenAIAgentProvider
        provider = OpenAIAgentProvider(api_key="test")
        step = AgentStep(
            step_number=1,
            reasoning="I need to click the button",
            tool_calls=[
                ToolCall(name="click", arguments={"x": 100, "y": 200}, call_id="call_abc"),
            ],
        )
        msg = provider._build_assistant_message(step)
        assert msg is not None
        assert msg["role"] == "assistant"
        assert msg["content"] == "I need to click the button"
        assert len(msg["tool_calls"]) == 1
        assert msg["tool_calls"][0]["id"] == "call_abc"
        assert msg["tool_calls"][0]["type"] == "function"
        assert msg["tool_calls"][0]["function"]["name"] == "click"

    def test_build_assistant_message_no_reasoning(self):
        """Should set content=None when no reasoning."""
        from naturo.providers.openai_agent import OpenAIAgentProvider
        provider = OpenAIAgentProvider(api_key="test")
        step = AgentStep(
            step_number=1,
            tool_calls=[
                ToolCall(name="done", arguments={"summary": "ok"}, call_id="call_1"),
            ],
        )
        msg = provider._build_assistant_message(step)
        assert msg["content"] is None

    def test_build_assistant_message_empty_step(self):
        """Should return None for empty step."""
        from naturo.providers.openai_agent import OpenAIAgentProvider
        provider = OpenAIAgentProvider(api_key="test")
        step = AgentStep(step_number=1)
        msg = provider._build_assistant_message(step)
        assert msg is None

    def test_build_tool_result_messages(self):
        """Should build one tool message per result."""
        from naturo.providers.openai_agent import OpenAIAgentProvider
        provider = OpenAIAgentProvider(api_key="test")
        step = AgentStep(
            step_number=1,
            tool_results=[
                ToolResult(
                    call_id="call_1", name="click",
                    result={"success": True}, success=True,
                ),
                ToolResult(
                    call_id="call_2", name="type_text",
                    result={"error": "fail"}, success=False, error="fail",
                ),
            ],
        )
        msgs = provider._build_tool_result_messages(step)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "tool"
        assert msgs[0]["tool_call_id"] == "call_1"
        assert msgs[1]["role"] == "tool"
        assert msgs[1]["tool_call_id"] == "call_2"

    def test_tool_result_content_is_json(self):
        """Tool result content should be JSON string."""
        from naturo.providers.openai_agent import OpenAIAgentProvider
        provider = OpenAIAgentProvider(api_key="test")
        step = AgentStep(
            step_number=1,
            tool_results=[
                ToolResult(
                    call_id="c1", name="clipboard_get",
                    result={"success": True, "text": "你好"}, success=True,
                ),
            ],
        )
        msgs = provider._build_tool_result_messages(step)
        parsed = json.loads(msgs[0]["content"])
        assert parsed["text"] == "你好"


# ── Response Parsing Tests ──────────────────────


class TestOpenAIAgentResponseParsing:
    """Tests for parsing OpenAI responses into AgentSteps."""

    def _make_mock_response(
        self,
        content=None,
        tool_calls=None,
        finish_reason="stop",
    ):
        """Create a mock OpenAI chat completion response."""
        message = MagicMock()
        message.content = content
        message.tool_calls = tool_calls

        choice = MagicMock()
        choice.message = message
        choice.finish_reason = finish_reason

        response = MagicMock()
        response.choices = [choice]
        return response

    def _make_mock_tool_call(self, name, arguments, call_id="call_test"):
        """Create a mock OpenAI tool call."""
        tc = MagicMock()
        tc.id = call_id
        tc.type = "function"
        tc.function = MagicMock()
        tc.function.name = name
        tc.function.arguments = json.dumps(arguments)
        return tc

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_parse_tool_call_response(self, mock_get_client):
        """Should parse tool calls from OpenAI response."""
        from naturo.providers.openai_agent import OpenAIAgentProvider

        mock_tc = self._make_mock_tool_call("click", {"x": 100, "y": 200}, "call_abc")
        mock_response = self._make_mock_response(
            content="I'll click the button",
            tool_calls=[mock_tc],
            finish_reason="tool_calls",
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        provider = OpenAIAgentProvider(api_key="test-key")
        step = provider.run_step("click the button", None, None, [])

        assert step.status == StepStatus.SUCCESS
        assert len(step.tool_calls) == 1
        assert step.tool_calls[0].name == "click"
        assert step.tool_calls[0].arguments == {"x": 100, "y": 200}
        assert step.tool_calls[0].call_id == "call_abc"
        assert step.reasoning == "I'll click the button"

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_parse_done_tool(self, mock_get_client):
        """Should detect 'done' tool and set is_done."""
        from naturo.providers.openai_agent import OpenAIAgentProvider

        mock_tc = self._make_mock_tool_call(
            "done", {"summary": "Task finished"}, "call_done"
        )
        mock_response = self._make_mock_response(
            tool_calls=[mock_tc], finish_reason="tool_calls"
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        provider = OpenAIAgentProvider(api_key="test-key")
        step = provider.run_step("test", None, None, [])

        assert step.is_done is True
        assert step.summary == "Task finished"

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_parse_stop_without_tools(self, mock_get_client):
        """Should mark done when model stops without tool calls."""
        from naturo.providers.openai_agent import OpenAIAgentProvider

        mock_response = self._make_mock_response(
            content="The task appears to be complete.",
            tool_calls=None,
            finish_reason="stop",
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        provider = OpenAIAgentProvider(api_key="test-key")
        step = provider.run_step("test", None, None, [])

        assert step.is_done is True
        assert "complete" in step.summary.lower()

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_parse_multiple_tool_calls(self, mock_get_client):
        """Should handle multiple tool calls in one response."""
        from naturo.providers.openai_agent import OpenAIAgentProvider

        tc1 = self._make_mock_tool_call("click", {"x": 100, "y": 50}, "call_1")
        tc2 = self._make_mock_tool_call("type_text", {"text": "hello"}, "call_2")
        mock_response = self._make_mock_response(
            tool_calls=[tc1, tc2], finish_reason="tool_calls"
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        provider = OpenAIAgentProvider(api_key="test-key")
        step = provider.run_step("type hello", None, None, [])

        assert len(step.tool_calls) == 2
        assert step.tool_calls[0].name == "click"
        assert step.tool_calls[1].name == "type_text"

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_api_error_returns_error_step(self, mock_get_client):
        """Should return error step on API failure."""
        from naturo.providers.openai_agent import OpenAIAgentProvider

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("rate limited")
        mock_get_client.return_value = mock_client

        provider = OpenAIAgentProvider(api_key="test-key")
        step = provider.run_step("test", None, None, [])

        assert step.status == StepStatus.ERROR
        assert "rate limited" in step.summary

    @patch("naturo.providers.openai_agent.OpenAIAgentProvider._get_client")
    def test_invalid_json_arguments_fallback(self, mock_get_client):
        """Should fallback to empty dict on invalid JSON arguments."""
        from naturo.providers.openai_agent import OpenAIAgentProvider

        tc = MagicMock()
        tc.id = "call_1"
        tc.function = MagicMock()
        tc.function.name = "click"
        tc.function.arguments = "not valid json{{"

        mock_response = self._make_mock_response(
            tool_calls=[tc], finish_reason="tool_calls"
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        provider = OpenAIAgentProvider(api_key="test-key")
        step = provider.run_step("test", None, None, [])

        assert len(step.tool_calls) == 1
        assert step.tool_calls[0].arguments == {}


# ── Agent Loop Integration ──────────────────────


class TestOpenAIAgentLoop:
    """Tests for the agent loop with OpenAI provider."""

    def _make_mock_backend(self):
        """Create a mock backend."""
        backend = MagicMock()
        backend.capture_screen = MagicMock(return_value=MagicMock(
            path="test.png", width=1920, height=1080
        ))
        backend.get_element_tree = MagicMock(return_value=None)
        backend.click = MagicMock()
        backend.type_text = MagicMock()
        return backend

    def test_openai_agent_completes(self):
        """Agent loop should complete with OpenAI provider."""
        from naturo.providers.openai_agent import OpenAIAgentProvider

        done_step = AgentStep(step_number=1, is_done=True, summary="Done")
        done_step.status = StepStatus.SUCCESS

        provider = MagicMock(spec=OpenAIAgentProvider)
        provider.run_step = MagicMock(return_value=done_step)
        backend = self._make_mock_backend()

        result = run_agent("test", provider, backend=backend, max_steps=5)
        assert result.success is True

    def test_openai_agent_executes_tools(self):
        """Agent should execute tool calls from OpenAI provider."""
        step1 = AgentStep(step_number=1)
        step1.tool_calls = [
            ToolCall(name="click", arguments={"x": 50, "y": 100}, call_id="c1"),
        ]
        step1.status = StepStatus.SUCCESS

        step2 = AgentStep(step_number=2, is_done=True, summary="Clicked")
        step2.status = StepStatus.SUCCESS

        provider = MagicMock()
        provider.run_step = MagicMock(side_effect=[step1, step2])
        backend = self._make_mock_backend()

        result = run_agent("click something", provider, backend=backend, max_steps=5)
        assert result.success is True
        backend.click.assert_called_once()


# ── CLI Integration Tests ───────────────────────


class TestAgentCLIOpenAI:
    """Tests for the agent CLI with --provider openai."""

    def setup_method(self):
        from naturo.cli import main
        self.runner = CliRunner()
        self.cli = main

    def test_agent_provider_openai_no_key(self):
        """--provider openai should fail gracefully without API key."""
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = self.runner.invoke(
                self.cli, ["agent", "test task", "--provider", "openai"]
            )
            assert result.exit_code != 0

    def test_agent_provider_openai_no_key_json(self):
        """--provider openai with --json should output structured error."""
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = self.runner.invoke(
                self.cli,
                ["agent", "test task", "--provider", "openai", "--json"],
            )
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["success"] is False
            assert data["error"]["code"] == "AI_PROVIDER_UNAVAILABLE"

    def test_agent_provider_invalid(self):
        """Invalid provider name should be caught by Click choice validation."""
        result = self.runner.invoke(
            self.cli, ["agent", "test task", "--provider", "invalid"]
        )
        assert result.exit_code != 0


# ── _get_agent_provider Tests ───────────────────


class TestGetAgentProvider:
    """Tests for the _get_agent_provider factory function."""

    def test_get_anthropic_provider(self):
        """Should return Anthropic agent provider."""
        from naturo.cli.ai import _get_agent_provider
        from naturo.providers.anthropic_agent import AnthropicAgentProvider
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            provider = _get_agent_provider("anthropic")
            assert isinstance(provider, AnthropicAgentProvider)

    def test_get_openai_provider(self):
        """Should return OpenAI agent provider."""
        from naturo.cli.ai import _get_agent_provider
        from naturo.providers.openai_agent import OpenAIAgentProvider
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = _get_agent_provider("openai")
            assert isinstance(provider, OpenAIAgentProvider)

    def test_get_provider_with_model_override(self):
        """Should pass model to provider."""
        from naturo.cli.ai import _get_agent_provider
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = _get_agent_provider("openai", model="gpt-4-turbo")
            assert provider._model == "gpt-4-turbo"

    def test_get_unknown_provider_raises(self):
        """Should raise for unknown provider name."""
        from naturo.cli.ai import _get_agent_provider
        from naturo.errors import AIProviderUnavailableError
        with pytest.raises(AIProviderUnavailableError) as exc_info:
            _get_agent_provider("gemini")
        assert exc_info.value.suggested_action is not None
        assert "Available agent providers" in exc_info.value.suggested_action
