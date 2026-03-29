"""Tests for parse_ai_elements_json — shared AI response JSON parser.

Covers the fix for #611: AI Vision returns elements but JSON parsing fails.
"""
from __future__ import annotations

import pytest

from naturo.providers.base import parse_ai_elements_json


class TestPlainJsonArray:
    """AI returns a clean JSON array."""

    def test_flat_array(self) -> None:
        raw = '[{"role": "Button", "name": "OK", "bounds": {"x": 10, "y": 20, "width": 80, "height": 30}}]'
        result = parse_ai_elements_json(raw)
        assert len(result) == 1
        assert result[0]["role"] == "Button"
        assert result[0]["name"] == "OK"

    def test_multiple_elements(self) -> None:
        raw = '[{"role": "Button", "name": "OK"}, {"role": "Input", "name": "Search"}]'
        result = parse_ai_elements_json(raw)
        assert len(result) == 2

    def test_empty_array(self) -> None:
        assert parse_ai_elements_json("[]") == []


class TestMarkdownCodeFences:
    """AI wraps JSON in markdown code fences."""

    def test_json_fenced(self) -> None:
        raw = '```json\n[{"role": "Button", "name": "Save"}]\n```'
        result = parse_ai_elements_json(raw)
        assert len(result) == 1
        assert result[0]["name"] == "Save"

    def test_plain_fenced(self) -> None:
        raw = '```\n[{"role": "Tab", "name": "Home"}]\n```'
        result = parse_ai_elements_json(raw)
        assert len(result) == 1

    def test_prose_before_fence(self) -> None:
        raw = (
            "Here are the UI elements I found:\n\n"
            '```json\n[{"role": "Link", "name": "Settings"}]\n```\n\n'
            "These elements are interactive."
        )
        result = parse_ai_elements_json(raw)
        assert len(result) == 1
        assert result[0]["role"] == "Link"


class TestProseWithEmbeddedJson:
    """AI returns prose with JSON embedded (no code fences)."""

    def test_prose_then_array(self) -> None:
        raw = (
            'Looking at this interface, I can see:\n'
            '[{"role": "Button", "name": "Submit", "bounds": {"x": 100, "y": 200, "width": 80, "height": 30}}]'
        )
        result = parse_ai_elements_json(raw)
        assert len(result) == 1
        assert result[0]["name"] == "Submit"

    def test_prose_then_object(self) -> None:
        raw = (
            'I found the following element:\n'
            '{"role": "Button", "name": "Close", "bounds": {"x": 50, "y": 10, "width": 30, "height": 30}}'
        )
        result = parse_ai_elements_json(raw)
        assert len(result) == 1
        assert result[0]["name"] == "Close"


class TestWrapperObject:
    """AI returns a wrapper object containing an elements array."""

    def test_elements_key(self) -> None:
        raw = '{"found": true, "elements": [{"role": "Button", "name": "OK"}]}'
        result = parse_ai_elements_json(raw)
        assert len(result) == 1
        assert result[0]["name"] == "OK"

    def test_items_key(self) -> None:
        raw = '{"items": [{"role": "Input", "name": "Email"}]}'
        result = parse_ai_elements_json(raw)
        assert len(result) == 1

    def test_results_key(self) -> None:
        raw = '{"results": [{"role": "Tab", "name": "Home"}, {"role": "Tab", "name": "View"}]}'
        result = parse_ai_elements_json(raw)
        assert len(result) == 2

    def test_single_element_dict(self) -> None:
        raw = '{"role": "Button", "name": "Save", "bounds": {"x": 10, "y": 20, "width": 80, "height": 30}}'
        result = parse_ai_elements_json(raw)
        assert len(result) == 1
        assert result[0]["role"] == "Button"

    def test_unknown_wrapper_returns_empty(self) -> None:
        raw = '{"status": "ok", "count": 5}'
        assert parse_ai_elements_json(raw) == []


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_empty_string(self) -> None:
        assert parse_ai_elements_json("") == []

    def test_whitespace_only(self) -> None:
        assert parse_ai_elements_json("   \n\t  ") == []

    def test_pure_prose_no_json(self) -> None:
        assert parse_ai_elements_json("I cannot identify any elements in this image.") == []

    def test_invalid_json(self) -> None:
        assert parse_ai_elements_json("[{invalid json}]") == []

    def test_non_dict_items_filtered(self) -> None:
        raw = '[{"role": "Button", "name": "OK"}, "not a dict", 42, {"role": "Input", "name": "Search"}]'
        result = parse_ai_elements_json(raw)
        assert len(result) == 2

    def test_wrapper_with_empty_elements(self) -> None:
        raw = '{"elements": []}'
        assert parse_ai_elements_json(raw) == []

    def test_nested_code_fence_with_wrapper(self) -> None:
        raw = (
            "```json\n"
            '{"elements": [{"role": "Button", "name": "Apply"}]}\n'
            "```"
        )
        result = parse_ai_elements_json(raw)
        assert len(result) == 1
        assert result[0]["name"] == "Apply"
