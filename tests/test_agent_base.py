"""Tests for naturo.providers.agent_base — shared agent provider base class.

Covers: AGENT_TOOLS definitions, get_system_prompt, BaseAgentProvider
shared logic (is_available, _build_user_content, run_step delegation).
"""
from __future__ import annotations

import json
import os
import struct
import zlib
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

from naturo.agent import AgentStep, StepStatus, ToolCall, ToolResult
from naturo.errors import AIProviderUnavailableError
from naturo.providers.agent_base import (
    AGENT_TOOLS,
    BaseAgentProvider,
    get_system_prompt,
)


# ---------------------------------------------------------------------------
# Concrete test subclass
# ---------------------------------------------------------------------------


class _StubProvider(BaseAgentProvider):
    """Minimal concrete subclass for testing the base class logic."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            default_model="stub-model-v1",
            api_key_env="STUB_API_KEY",
        )
        self.call_api_called = False
        self.last_conversation: list[dict[str, Any]] = []
        self.mock_response: Any = None

    @property
    def name(self) -> str:
        return "stub"

    def _get_client(self) -> Any:
        return MagicMock()

    def _format_screenshot_content(
        self, image_data: str, media_type: str,
    ) -> dict[str, Any]:
        return {"type": "image", "data": image_data, "media_type": media_type}

    def _get_tool_definitions(self) -> list[dict[str, Any]]:
        return [{"name": t["name"]} for t in AGENT_TOOLS]

    def _call_api(
        self,
        client: Any,
        conversation: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> Any:
        self.call_api_called = True
        self.last_conversation = list(conversation)
        return self.mock_response

    def _parse_response(self, response: Any, step_num: int) -> AgentStep:
        step = AgentStep(step_number=step_num, status=StepStatus.SUCCESS)
        if response and response.get("done"):
            step.is_done = True
            step.summary = response.get("summary", "Done")
        if response and response.get("tool_calls"):
            for tc_data in response["tool_calls"]:
                step.tool_calls.append(
                    ToolCall(name=tc_data["name"], arguments=tc_data.get("args", {}))
                )
        return step

    def _append_history_messages(self, prev_step: AgentStep) -> None:
        if prev_step.reasoning:
            self._conversation.append(
                {"role": "assistant", "content": prev_step.reasoning}
            )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STUB_API_KEY", raising=False)
    monkeypatch.delenv("NATURO_AGENT_MODEL", raising=False)


@pytest.fixture()
def fake_image(tmp_path: Path) -> str:
    """Create a minimal valid 1x1 PNG."""
    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b"\x00\xff\x00\x00"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw))
        + _chunk(b"IEND", b"")
    )
    p = tmp_path / "test.png"
    p.write_bytes(png)
    return str(p)


# ---------------------------------------------------------------------------
# AGENT_TOOLS
# ---------------------------------------------------------------------------


class TestAgentTools:
    def test_tool_count(self) -> None:
        assert len(AGENT_TOOLS) == 18

    def test_all_tools_have_required_keys(self) -> None:
        for tool in AGENT_TOOLS:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool {tool['name']} missing 'description'"
            assert "parameters" in tool, f"Tool {tool['name']} missing 'parameters'"
            assert tool["parameters"]["type"] == "object"

    def test_tool_names_unique(self) -> None:
        names = [t["name"] for t in AGENT_TOOLS]
        assert len(names) == len(set(names))

    def test_expected_tools_present(self) -> None:
        names = {t["name"] for t in AGENT_TOOLS}
        expected = {
            "click", "type_text", "press_key", "hotkey", "scroll", "drag",
            "move_mouse", "find_element", "capture_screen", "list_windows",
            "focus_window", "close_window", "launch_app", "quit_app",
            "clipboard_get", "clipboard_set", "wait_for_element", "done",
        }
        assert names == expected


# ---------------------------------------------------------------------------
# get_system_prompt
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_default_tool_noun(self) -> None:
        prompt = get_system_prompt()
        assert "tool calls" in prompt
        assert "function calls" not in prompt

    def test_function_noun(self) -> None:
        prompt = get_system_prompt(tool_noun="function")
        assert "function calls" in prompt
        assert "tool calls" not in prompt

    def test_contains_naturo(self) -> None:
        assert "Naturo" in get_system_prompt()

    def test_contains_done(self) -> None:
        assert "`done`" in get_system_prompt()


# ---------------------------------------------------------------------------
# BaseAgentProvider — construction
# ---------------------------------------------------------------------------


class TestBaseProviderInit:
    def test_explicit_key(self) -> None:
        p = _StubProvider(api_key="sk-test")
        assert p.is_available is True
        assert p.name == "stub"

    def test_env_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUB_API_KEY", "sk-env")
        p = _StubProvider()
        assert p.is_available is True

    def test_no_key(self) -> None:
        p = _StubProvider()
        assert p.is_available is False

    def test_default_model(self) -> None:
        p = _StubProvider(api_key="sk-test")
        assert p._model == "stub-model-v1"

    def test_custom_model(self) -> None:
        p = _StubProvider(api_key="sk-test", model="custom-v2")
        assert p._model == "custom-v2"

    def test_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NATURO_AGENT_MODEL", "env-model")
        p = _StubProvider(api_key="sk-test")
        assert p._model == "env-model"

    def test_empty_conversation(self) -> None:
        p = _StubProvider(api_key="sk-test")
        assert p._conversation == []


# ---------------------------------------------------------------------------
# BaseAgentProvider — _build_user_content
# ---------------------------------------------------------------------------


class TestBuildUserContent:
    def test_first_step_text(self) -> None:
        p = _StubProvider(api_key="sk-test")
        content = p._build_user_content("Click the button", None, None, 1, [])
        text_blocks = [c for c in content if c.get("type") == "text"]
        assert len(text_blocks) == 1
        assert "## Instruction" in text_blocks[0]["text"]
        assert "Click the button" in text_blocks[0]["text"]

    def test_subsequent_step_text(self) -> None:
        prev = AgentStep(step_number=1, status=StepStatus.SUCCESS)
        prev.tool_results = [
            ToolResult(call_id="c1", name="click", result={"ok": True}, success=True),
        ]
        p = _StubProvider(api_key="sk-test")
        content = p._build_user_content("Do stuff", None, None, 2, [prev])
        text = content[-1]["text"]
        assert "## Step 2" in text
        assert "click" in text

    def test_screenshot_included(self, fake_image: str) -> None:
        p = _StubProvider(api_key="sk-test")
        content = p._build_user_content("Look", fake_image, None, 1, [])
        image_blocks = [c for c in content if c.get("type") == "image"]
        assert len(image_blocks) == 1

    def test_no_screenshot(self) -> None:
        p = _StubProvider(api_key="sk-test")
        content = p._build_user_content("Look", None, None, 1, [])
        image_blocks = [c for c in content if c.get("type") == "image"]
        assert len(image_blocks) == 0

    def test_ui_tree_included(self) -> None:
        tree = {"role": "Window", "name": "Notepad"}
        p = _StubProvider(api_key="sk-test")
        content = p._build_user_content("See", None, tree, 1, [])
        text = content[-1]["text"]
        assert "Notepad" in text
        assert "UI Accessibility Tree" in text

    def test_ui_tree_truncation(self) -> None:
        big_tree = {"elements": [{"name": f"el_{i}"} for i in range(500)]}
        p = _StubProvider(api_key="sk-test")
        content = p._build_user_content("See", None, big_tree, 1, [])
        text = content[-1]["text"]
        assert "truncated" in text


# ---------------------------------------------------------------------------
# BaseAgentProvider — run_step
# ---------------------------------------------------------------------------


class TestBaseRunStep:
    def test_unavailable_raises(self) -> None:
        p = _StubProvider()
        with pytest.raises(AIProviderUnavailableError):
            p.run_step("Do thing", None, None, [])

    def test_first_step_calls_api(self) -> None:
        p = _StubProvider(api_key="sk-test")
        p.mock_response = {"tool_calls": [{"name": "click", "args": {"x": 1, "y": 2}}]}
        step = p.run_step("Click", None, None, [])

        assert p.call_api_called
        assert step.step_number == 1
        assert step.status == StepStatus.SUCCESS
        assert len(step.tool_calls) == 1

    def test_done_response(self) -> None:
        p = _StubProvider(api_key="sk-test")
        p.mock_response = {"done": True, "summary": "All done"}
        step = p.run_step("Finish", None, None, [])

        assert step.is_done is True
        assert step.summary == "All done"

    def test_api_error_returns_error_step(self) -> None:
        p = _StubProvider(api_key="sk-test")

        # Override _call_api to raise
        def _raise(*_a: Any, **_kw: Any) -> None:
            raise RuntimeError("network failure")

        p._call_api = _raise  # type: ignore[assignment]
        step = p.run_step("Click", None, None, [])

        assert step.status == StepStatus.ERROR
        assert "network failure" in step.summary

    def test_second_step_appends_history(self) -> None:
        p = _StubProvider(api_key="sk-test")
        p.mock_response = {"tool_calls": [{"name": "type_text", "args": {"text": "hi"}}]}

        prev = AgentStep(step_number=1, status=StepStatus.SUCCESS)
        prev.reasoning = "Clicked field"
        prev.tool_calls = [ToolCall(name="click", arguments={"x": 1}, call_id="c1")]
        prev.tool_results = [
            ToolResult(call_id="c1", name="click", result={"ok": True}, success=True),
        ]

        step = p.run_step("Type hi", None, None, [prev])
        assert step.step_number == 2

        # Verify assistant message was appended via _append_history_messages
        roles = [m["role"] for m in p.last_conversation]
        assert "assistant" in roles

    def test_conversation_reset_on_step_1(self) -> None:
        p = _StubProvider(api_key="sk-test")
        p._conversation = [{"role": "user", "content": "old"}]
        p.mock_response = {"tool_calls": []}

        p.run_step("New task", None, None, [])
        # Conversation should have been reset to just the new message
        assert len(p._conversation) == 1
        assert p._conversation[0]["role"] == "user"
