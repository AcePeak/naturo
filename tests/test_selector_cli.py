"""Tests for --selector flag on interaction commands (click, type, press, scroll, move).

The --selector flag resolves unified selectors (URI/XML format) to UI
elements before performing the action. These tests mock the backend to
verify the CLI wiring works correctly on all platforms.
"""
from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    return CliRunner()


def _make_mock_backend():
    """Create a mock backend with a simple element tree."""
    backend = MagicMock()

    # Build a minimal element tree
    button = MagicMock()
    button.id = "btnSave"
    button.role = "Button"
    button.name = "Save"
    button.value = ""
    button.x, button.y, button.width, button.height = 100, 200, 80, 30
    button.children = []
    button.properties = {"className": "Button"}

    edit = MagicMock()
    edit.id = "txtContent"
    edit.role = "Edit"
    edit.name = ""
    edit.value = "Hello"
    edit.x, edit.y, edit.width, edit.height = 10, 50, 400, 300
    edit.children = []
    edit.properties = {"className": "Edit"}

    root = MagicMock()
    root.id = "root"
    root.role = "Window"
    root.name = "Untitled - Notepad"
    root.value = ""
    root.x, root.y, root.width, root.height = 0, 0, 800, 600
    root.children = [button, edit]
    root.properties = {"className": "Notepad"}

    backend.get_element_tree.return_value = root

    # Mock click to succeed
    backend.click.return_value = {"x": 0, "y": 0, "button": "left"}
    return backend


def _get_click_xy(mock_call):
    """Extract x, y from a mock backend.click() call (positional or keyword)."""
    args, kwargs = mock_call
    x = kwargs.get("x", args[0] if args else None)
    y = kwargs.get("y", args[1] if len(args) > 1 else None)
    return x, y


def _patch_backend(mock_backend):
    """Return patch objects for _get_backend, _check_desktop_session, _auto_route."""
    return [
        patch("naturo.cli.interaction._get_backend", return_value=mock_backend),
        patch("naturo.cli.interaction._check_desktop_session"),
        patch("naturo.cli.interaction._auto_route", return_value={}),
    ]


class TestClickSelector:
    """Tests for 'naturo click --selector'."""

    def test_click_selector_resolves_button(self, runner):
        """--selector with a URI selector should resolve and click the element."""
        mock_be = _make_mock_backend()
        patches = _patch_backend(mock_be)
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import click_cmd
            result = runner.invoke(click_cmd, [
                "--selector", 'app://*/Button[@name="Save"]',
                "--json", "--no-verify",
            ])
            assert result.exit_code == 0, f"output: {result.output}"
            mock_be.click.assert_called_once()
            x, y = _get_click_xy(mock_be.click.call_args)
            assert x == 140, f"Expected x=140, got {x}"  # 100 + 80//2
            assert y == 215, f"Expected y=215, got {y}"  # 200 + 30//2
        finally:
            for p in patches:
                p.stop()

    def test_click_selector_not_found(self, runner):
        """--selector that matches nothing should emit SELECTOR_NOT_FOUND error."""
        mock_be = _make_mock_backend()
        patches = _patch_backend(mock_be)
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import click_cmd
            result = runner.invoke(click_cmd, [
                "--selector", 'app://*/CheckBox[@name="Nonexistent"]',
                "--json",
            ])
            assert result.exit_code != 0
            assert "SELECTOR_NOT_FOUND" in result.output
        finally:
            for p in patches:
                p.stop()

    def test_click_selector_invalid_syntax(self, runner):
        """Malformed selector should emit an error."""
        mock_be = _make_mock_backend()
        patches = _patch_backend(mock_be)
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import click_cmd
            result = runner.invoke(click_cmd, [
                "--selector", "not a valid selector ][",
                "--json",
            ])
            assert result.exit_code != 0
        finally:
            for p in patches:
                p.stop()

    def test_click_selector_takes_priority_over_query(self, runner):
        """--selector should take priority over positional QUERY argument."""
        mock_be = _make_mock_backend()
        patches = _patch_backend(mock_be)
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import click_cmd
            result = runner.invoke(click_cmd, [
                "some-text-query",
                "--selector", 'app://*/Button[@name="Save"]',
                "--json", "--no-verify",
            ])
            assert result.exit_code == 0, f"output: {result.output}"
            mock_be.click.assert_called_once()
            x, _ = _get_click_xy(mock_be.click.call_args)
            assert x == 140  # center of Save button, not text query
        finally:
            for p in patches:
                p.stop()

    def test_click_selector_by_automationid(self, runner):
        """--selector with automationid should resolve correctly."""
        mock_be = _make_mock_backend()
        patches = _patch_backend(mock_be)
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import click_cmd
            result = runner.invoke(click_cmd, [
                "--selector", 'app://*/Edit[@automationid="txtContent"]',
                "--json", "--no-verify",
            ])
            assert result.exit_code == 0, f"output: {result.output}"
            mock_be.click.assert_called_once()
            x, y = _get_click_xy(mock_be.click.call_args)
            assert x == 210  # 10 + 400//2
            assert y == 200  # 50 + 300//2
        finally:
            for p in patches:
                p.stop()


class TestTypeSelectorFlag:
    """Tests for 'naturo type --selector'."""

    def test_type_selector_clicks_to_focus(self, runner):
        """--selector on type should click the resolved element to focus it."""
        mock_be = _make_mock_backend()
        patches = _patch_backend(mock_be)
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import type_cmd
            result = runner.invoke(type_cmd, [
                "Hello",
                "--selector", 'app://*/Edit[@automationid="txtContent"]',
                "--json", "--no-verify",
            ])
            assert result.exit_code == 0, f"output: {result.output}"
            assert mock_be.click.call_count >= 1
            x, _ = _get_click_xy(mock_be.click.call_args_list[0])
            assert x == 210  # center of edit field
        finally:
            for p in patches:
                p.stop()


class TestPressSelectorFlag:
    """Tests for 'naturo press --selector'."""

    def test_press_selector_clicks_to_focus(self, runner):
        """--selector on press should click the resolved element to focus it."""
        mock_be = _make_mock_backend()
        patches = _patch_backend(mock_be)
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import press
            result = runner.invoke(press, [
                "enter",
                "--selector", 'app://*/Button[@name="Save"]',
                "--json", "--no-verify",
            ])
            assert result.exit_code == 0, f"output: {result.output}"
            assert mock_be.click.call_count >= 1
            x, _ = _get_click_xy(mock_be.click.call_args_list[0])
            assert x == 140  # center of Save button
        finally:
            for p in patches:
                p.stop()


class TestElementInfoToDict:
    """Tests for _elementinfo_to_dict conversion."""

    def test_converts_basic_element(self):
        """ElementInfo with standard fields should convert correctly."""
        from naturo.cli.interaction import _elementinfo_to_dict

        el = MagicMock()
        el.role = "Button"
        el.name = "OK"
        el.id = "btn1"
        el.value = ""
        el.x, el.y, el.width, el.height = 10, 20, 60, 25
        el.children = []
        el.properties = {}

        result = _elementinfo_to_dict(el)
        assert result["role"] == "Button"
        assert result["name"] == "OK"
        assert result["automationid"] == "btn1"
        assert result["x"] == 10
        assert result["width"] == 60
        assert result["children"] == []

    def test_converts_with_children(self):
        """Element with children should convert recursively."""
        from naturo.cli.interaction import _elementinfo_to_dict

        child = MagicMock()
        child.role = "Text"
        child.name = "Label"
        child.id = ""
        child.value = None
        child.x, child.y, child.width, child.height = 5, 5, 50, 15
        child.children = []
        child.properties = {}

        parent = MagicMock()
        parent.role = "Pane"
        parent.name = "Container"
        parent.id = "pane1"
        parent.value = None
        parent.x, parent.y, parent.width, parent.height = 0, 0, 200, 100
        parent.children = [child]
        parent.properties = {}

        result = _elementinfo_to_dict(parent)
        assert len(result["children"]) == 1
        assert result["children"][0]["role"] == "Text"
        assert result["children"][0]["name"] == "Label"


class TestScrollSelectorFlag:
    """Tests for 'naturo scroll --selector'."""

    def test_scroll_selector_resolves_to_coords(self, runner):
        """--selector on scroll should resolve element and scroll at its center."""
        mock_be = _make_mock_backend()
        patches = _patch_backend(mock_be)
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import scroll
            result = runner.invoke(scroll, [
                "down",
                "--selector", 'app://*/Edit[@automationid="txtContent"]',
                "--json",
            ])
            assert result.exit_code == 0, f"output: {result.output}"
            mock_be.scroll.assert_called_once()
            call_kwargs = mock_be.scroll.call_args[1]
            assert call_kwargs["x"] == 210  # 10 + 400//2
            assert call_kwargs["y"] == 200  # 50 + 300//2
            assert call_kwargs["direction"] == "down"
        finally:
            for p in patches:
                p.stop()

    def test_scroll_selector_not_found(self, runner):
        """--selector that matches nothing should emit error."""
        mock_be = _make_mock_backend()
        patches = _patch_backend(mock_be)
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import scroll
            result = runner.invoke(scroll, [
                "down",
                "--selector", 'app://*/CheckBox[@name="Nonexistent"]',
                "--json",
            ])
            assert result.exit_code != 0
            assert "SELECTOR_NOT_FOUND" in result.output
        finally:
            for p in patches:
                p.stop()

    def test_scroll_selector_takes_priority_over_coords(self, runner):
        """--selector should take priority over --coords."""
        mock_be = _make_mock_backend()
        patches = _patch_backend(mock_be)
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import scroll
            result = runner.invoke(scroll, [
                "down",
                "--selector", 'app://*/Button[@name="Save"]',
                "--coords", "999", "999",
                "--json",
            ])
            assert result.exit_code == 0, f"output: {result.output}"
            call_kwargs = mock_be.scroll.call_args[1]
            assert call_kwargs["x"] == 140  # Save button center, not 999
        finally:
            for p in patches:
                p.stop()

    def test_scroll_selector_help(self, runner):
        """scroll --help should document --selector."""
        from naturo.cli.interaction import scroll
        result = runner.invoke(scroll, ["--help"])
        assert "--selector" in result.output


class TestMoveSelectorFlag:
    """Tests for 'naturo move --selector'."""

    def test_move_selector_resolves_to_coords(self, runner):
        """--selector on move should resolve element and move to its center."""
        mock_be = _make_mock_backend()
        patches = _patch_backend(mock_be)
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import move
            result = runner.invoke(move, [
                "--selector", 'app://*/Button[@name="Save"]',
                "--json",
            ])
            assert result.exit_code == 0, f"output: {result.output}"
            mock_be.move_mouse.assert_called_once_with(140, 215)
        finally:
            for p in patches:
                p.stop()

    def test_move_selector_not_found(self, runner):
        """--selector that matches nothing should emit error."""
        mock_be = _make_mock_backend()
        patches = _patch_backend(mock_be)
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import move
            result = runner.invoke(move, [
                "--selector", 'app://*/CheckBox[@name="Nonexistent"]',
                "--json",
            ])
            assert result.exit_code != 0
            assert "SELECTOR_NOT_FOUND" in result.output
        finally:
            for p in patches:
                p.stop()

    def test_move_selector_help(self, runner):
        """move --help should document --selector."""
        from naturo.cli.interaction import move
        result = runner.invoke(move, ["--help"])
        assert "--selector" in result.output
