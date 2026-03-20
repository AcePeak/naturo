"""Tests for the agent command and Anthropic agent provider (Phase 4.4).

Tests cover:
- Agent CLI argument validation
- Agent provider construction and availability
- Agent step parsing from Claude responses
- Tool call extraction
- Conversation management
- End-to-end agent loop with mocked provider
"""
import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from click.testing import CliRunner

from naturo.agent import (
    AgentResult,
    AgentStep,
    StepStatus,
    ToolCall,
    ToolResult,
    ToolExecutor,
    run_agent,
)


# ── Agent CLI Tests ─────────────────────────────


class TestAgentCLI:
    """Tests for the agent CLI command."""

    def setup_method(self):
        from naturo.cli import main
        self.runner = CliRunner()
        self.cli = main

    def test_agent_help(self):
        """Agent command should show in help (no longer hidden)."""
        result = self.runner.invoke(self.cli, ["agent", "--help"])
        assert result.exit_code == 0
        assert "Execute a natural language automation instruction" in result.output

    def test_agent_max_steps_zero(self):
        """--max-steps 0 should fail with validation error."""
        result = self.runner.invoke(self.cli, ["agent", "test", "--max-steps", "0"])
        assert result.exit_code != 0
        assert "--max-steps must be >= 1" in (result.output + (result.stderr if hasattr(result, 'stderr') else ''))

    def test_agent_max_steps_too_large(self):
        """--max-steps > 50 should fail with validation error."""
        result = self.runner.invoke(self.cli, ["agent", "test", "--max-steps", "100"])
        assert result.exit_code != 0
        assert "--max-steps must be <= 50" in (result.output + (result.stderr if hasattr(result, 'stderr') else ''))

    def test_agent_max_steps_zero_json(self):
        """--max-steps 0 with --json should output structured error."""
        result = self.runner.invoke(self.cli, ["agent", "test", "--max-steps", "0", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_agent_no_api_key(self):
        """Agent should fail gracefully when no API key is set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove all API keys
            env = {k: v for k, v in os.environ.items()
                   if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")}
            with patch.dict(os.environ, env, clear=True):
                result = self.runner.invoke(self.cli, ["agent", "test task"])
                assert result.exit_code != 0

    def test_agent_no_api_key_json(self):
        """Agent should output JSON error when no API key is set."""
        env = {k: v for k, v in os.environ.items()
               if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")}
        with patch.dict(os.environ, env, clear=True):
            result = self.runner.invoke(self.cli, ["agent", "test task", "--json"])
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["success"] is False
            assert data["error"]["code"] == "AI_PROVIDER_UNAVAILABLE"


# ── Agent Provider Tests ────────────────────────


class TestAnthropicAgentProvider:
    """Tests for AnthropicAgentProvider."""

    def test_provider_not_available_without_key(self):
        """Provider should report unavailable without API key."""
        with patch.dict(os.environ, {}, clear=True):
            env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
            with patch.dict(os.environ, env, clear=True):
                from naturo.providers.anthropic_agent import AnthropicAgentProvider
                provider = AnthropicAgentProvider(api_key="")
                assert not provider.is_available

    def test_provider_available_with_key(self):
        """Provider should report available with API key."""
        from naturo.providers.anthropic_agent import AnthropicAgentProvider
        provider = AnthropicAgentProvider(api_key="test-key-123")
        assert provider.is_available

    def test_provider_name(self):
        """Provider name should be 'anthropic'."""
        from naturo.providers.anthropic_agent import AnthropicAgentProvider
        provider = AnthropicAgentProvider(api_key="test")
        assert provider.name == "anthropic"

    def test_provider_custom_model(self):
        """Provider should accept custom model."""
        from naturo.providers.anthropic_agent import AnthropicAgentProvider
        provider = AnthropicAgentProvider(api_key="test", model="claude-opus-4-20250514")
        assert provider._model == "claude-opus-4-20250514"

    def test_run_step_without_key_raises(self):
        """run_step should raise when API key is not set."""
        from naturo.providers.anthropic_agent import AnthropicAgentProvider
        from naturo.errors import AIProviderUnavailableError
        provider = AnthropicAgentProvider(api_key="")
        with pytest.raises(AIProviderUnavailableError):
            provider.run_step("test", None, None, [])

    def test_merge_consecutive_user_messages(self):
        """Should merge consecutive user messages."""
        from naturo.providers.anthropic_agent import AnthropicAgentProvider
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "hello"}]},
            {"role": "user", "content": [{"type": "text", "text": "world"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
        ]
        merged = AnthropicAgentProvider._merge_consecutive_user_messages(messages)
        assert len(merged) == 2
        assert merged[0]["role"] == "user"
        assert len(merged[0]["content"]) == 2
        assert merged[1]["role"] == "assistant"

    def test_merge_no_consecutive(self):
        """Should not merge non-consecutive messages."""
        from naturo.providers.anthropic_agent import AnthropicAgentProvider
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "hello"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
            {"role": "user", "content": [{"type": "text", "text": "bye"}]},
        ]
        merged = AnthropicAgentProvider._merge_consecutive_user_messages(messages)
        assert len(merged) == 3

    def test_merge_string_content(self):
        """Should handle string content in messages."""
        from naturo.providers.anthropic_agent import AnthropicAgentProvider
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "user", "content": "world"},
        ]
        merged = AnthropicAgentProvider._merge_consecutive_user_messages(messages)
        assert len(merged) == 1
        assert len(merged[0]["content"]) == 2

    def test_build_assistant_content(self):
        """Should build assistant content from AgentStep."""
        from naturo.providers.anthropic_agent import AnthropicAgentProvider
        provider = AnthropicAgentProvider(api_key="test")
        step = AgentStep(
            step_number=1,
            reasoning="I need to click the button",
            tool_calls=[
                ToolCall(name="click", arguments={"x": 100, "y": 200}, call_id="call_1"),
            ],
        )
        content = provider._build_assistant_content(step)
        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "tool_use"
        assert content[1]["name"] == "click"
        assert content[1]["id"] == "call_1"

    def test_build_tool_result_content(self):
        """Should build tool_result content from step results."""
        from naturo.providers.anthropic_agent import AnthropicAgentProvider
        provider = AnthropicAgentProvider(api_key="test")
        step = AgentStep(
            step_number=1,
            tool_results=[
                ToolResult(call_id="call_1", name="click", result={"success": True}, success=True),
                ToolResult(call_id="call_2", name="type_text", result={"error": "fail"}, success=False, error="fail"),
            ],
        )
        content = provider._build_tool_result_content(step)
        assert len(content) == 2
        assert content[0]["type"] == "tool_result"
        assert content[0]["tool_use_id"] == "call_1"
        assert content[0]["is_error"] is False
        assert content[1]["is_error"] is True


# ── Agent Loop Tests ────────────────────────────


class TestAgentLoop:
    """Tests for the agent execution loop."""

    def _make_mock_provider(self, steps: list[AgentStep]):
        """Create a mock provider that returns predefined steps."""
        provider = MagicMock()
        provider.run_step = MagicMock(side_effect=steps)
        return provider

    def _make_mock_backend(self):
        """Create a mock backend."""
        backend = MagicMock()
        backend.capture_screen = MagicMock(return_value=MagicMock(
            path="test.png", width=1920, height=1080
        ))
        backend.get_element_tree = MagicMock(return_value=None)
        backend.click = MagicMock()
        backend.type_text = MagicMock()
        backend.press_key = MagicMock()
        return backend

    def test_agent_completes_on_done(self):
        """Agent should complete when provider returns is_done."""
        done_step = AgentStep(step_number=1, is_done=True, summary="All done")
        done_step.status = StepStatus.SUCCESS
        provider = self._make_mock_provider([done_step])
        backend = self._make_mock_backend()

        result = run_agent("test instruction", provider, backend=backend, max_steps=5)
        assert result.success is True
        assert result.summary == "All done"
        assert result.step_count == 1

    def test_agent_executes_tool_calls(self):
        """Agent should execute tool calls from provider."""
        step1 = AgentStep(step_number=1)
        step1.tool_calls = [ToolCall(name="click", arguments={"x": 100, "y": 200}, call_id="c1")]
        step1.status = StepStatus.SUCCESS

        step2 = AgentStep(step_number=2, is_done=True, summary="Clicked and done")
        step2.status = StepStatus.SUCCESS

        provider = self._make_mock_provider([step1, step2])
        backend = self._make_mock_backend()

        result = run_agent("click something", provider, backend=backend, max_steps=5)
        assert result.success is True
        backend.click.assert_called_once()

    def test_agent_max_steps_limit(self):
        """Agent should stop at max_steps."""
        # Provider never returns done
        steps = []
        for i in range(5):
            s = AgentStep(step_number=i + 1)
            s.tool_calls = [ToolCall(name="capture_screen", arguments={}, call_id=f"c{i}")]
            s.status = StepStatus.SUCCESS
            steps.append(s)

        provider = self._make_mock_provider(steps)
        backend = self._make_mock_backend()

        result = run_agent("forever task", provider, backend=backend, max_steps=3)
        assert result.success is False
        assert "maximum steps" in result.error.lower()
        assert result.step_count == 3

    def test_agent_dry_run_no_execution(self):
        """Dry run should not execute tools."""
        step1 = AgentStep(step_number=1)
        step1.tool_calls = [ToolCall(name="click", arguments={"x": 100, "y": 200}, call_id="c1")]
        step1.status = StepStatus.SUCCESS

        step2 = AgentStep(step_number=2, is_done=True, summary="Done")
        step2.status = StepStatus.SUCCESS

        provider = self._make_mock_provider([step1, step2])
        backend = self._make_mock_backend()

        result = run_agent("click test", provider, backend=backend, max_steps=5, dry_run=True)
        backend.click.assert_not_called()

    def test_agent_handles_provider_error(self):
        """Agent should handle provider errors gracefully."""
        provider = MagicMock()
        provider.run_step = MagicMock(side_effect=Exception("API timeout"))
        backend = self._make_mock_backend()

        result = run_agent("test", provider, backend=backend, max_steps=3)
        assert result.success is False
        assert "API timeout" in result.error

    def test_agent_done_tool_completes(self):
        """Agent should complete when 'done' tool is called."""
        step = AgentStep(step_number=1)
        step.tool_calls = [
            ToolCall(name="done", arguments={"summary": "Task finished"}, call_id="c1"),
        ]
        step.status = StepStatus.SUCCESS

        provider = self._make_mock_provider([step])
        backend = self._make_mock_backend()

        result = run_agent("test", provider, backend=backend, max_steps=5)
        assert result.success is True
        assert result.summary == "Task finished"


# ── Tool Executor Tests ─────────────────────────


class TestToolExecutor:
    """Tests for ToolExecutor."""

    def _make_backend(self):
        backend = MagicMock()
        backend.click = MagicMock()
        backend.type_text = MagicMock()
        backend.press_key = MagicMock()
        backend.hotkey = MagicMock()
        backend.scroll = MagicMock()
        backend.drag = MagicMock()
        backend.move_mouse = MagicMock()
        backend.find_element = MagicMock(return_value=None)
        backend.capture_screen = MagicMock(return_value=MagicMock(path="t.png", width=1920, height=1080))
        backend.list_windows = MagicMock(return_value=[])
        backend.focus_window = MagicMock()
        backend.close_window = MagicMock()
        backend.launch_app = MagicMock()
        backend.quit_app = MagicMock()
        backend.clipboard_get = MagicMock(return_value="test")
        backend.clipboard_set = MagicMock()
        return backend

    def test_execute_click(self):
        backend = self._make_backend()
        executor = ToolExecutor(backend)
        tc = ToolCall(name="click", arguments={"x": 100, "y": 200}, call_id="c1")
        result = executor.execute(tc)
        assert result.success is True
        backend.click.assert_called_once()

    def test_execute_type_text(self):
        backend = self._make_backend()
        executor = ToolExecutor(backend)
        tc = ToolCall(name="type_text", arguments={"text": "hello"}, call_id="c1")
        result = executor.execute(tc)
        assert result.success is True
        backend.type_text.assert_called_once()

    def test_execute_unknown_tool(self):
        backend = self._make_backend()
        executor = ToolExecutor(backend)
        tc = ToolCall(name="nonexistent_tool", arguments={}, call_id="c1")
        result = executor.execute(tc)
        assert result.success is False
        assert "Unknown tool" in result.error

    def test_execute_done(self):
        backend = self._make_backend()
        executor = ToolExecutor(backend)
        tc = ToolCall(name="done", arguments={"summary": "All done"}, call_id="c1")
        result = executor.execute(tc)
        assert result.success is True
        assert result.result["done"] is True

    def test_execute_handles_exception(self):
        backend = self._make_backend()
        backend.click.side_effect = RuntimeError("click failed")
        executor = ToolExecutor(backend)
        tc = ToolCall(name="click", arguments={"x": 0, "y": 0}, call_id="c1")
        result = executor.execute(tc)
        assert result.success is False
        assert "click failed" in result.error

    def test_execute_clipboard_get(self):
        backend = self._make_backend()
        executor = ToolExecutor(backend)
        tc = ToolCall(name="clipboard_get", arguments={}, call_id="c1")
        result = executor.execute(tc)
        assert result.success is True
        assert result.result["text"] == "test"

    def test_execute_list_windows(self):
        backend = self._make_backend()
        executor = ToolExecutor(backend)
        tc = ToolCall(name="list_windows", arguments={}, call_id="c1")
        result = executor.execute(tc)
        assert result.success is True
        assert "windows" in result.result
