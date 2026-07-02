"""Tests for naturo.browser package — selector parsing, CLI structure.

Selector auto-detection is pure logic and runs on all platforms.
BrowserPage/BrowserElement tests mock the CDP layer.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.browser._selectors import (
    SelectorType,
    ParsedSelector,
    parse_selector,
    _auto_detect_type,
    to_cdp_expression,
    to_cdp_expression_all,
)
from naturo.cli import main


# ═══════════════════════════════════════════════════════════════════════════════
# Selector Parsing
# ═══════════════════════════════════════════════════════════════════════════════


class TestParseSelector:
    """Test selector string parsing and auto-detection."""

    # ── Explicit prefix ───────────────────────────────────────────────────

    def test_explicit_css_prefix(self):
        result = parse_selector("css:div.active")
        assert result.type == SelectorType.CSS
        assert result.expression == "div.active"

    def test_explicit_css_prefix_case_insensitive(self):
        result = parse_selector("CSS:#main")
        assert result.type == SelectorType.CSS
        assert result.expression == "#main"

    def test_explicit_xpath_prefix(self):
        result = parse_selector("xpath://div[@id='main']")
        assert result.type == SelectorType.XPATH
        assert result.expression == "//div[@id='main']"

    def test_explicit_text_prefix(self):
        result = parse_selector("text:Login")
        assert result.type == SelectorType.TEXT
        assert result.expression == "Login"

    def test_explicit_text_prefix_with_spaces(self):
        result = parse_selector("text: Sign In ")
        assert result.type == SelectorType.TEXT
        assert result.expression == "Sign In"

    # ── Auto-detect CSS ───────────────────────────────────────────────────

    def test_auto_detect_css_id_selector(self):
        result = parse_selector("#search-input")
        assert result.type == SelectorType.CSS
        assert result.expression == "#search-input"

    def test_auto_detect_css_class_selector(self):
        result = parse_selector(".active")
        assert result.type == SelectorType.CSS

    def test_auto_detect_css_attribute_selector(self):
        result = parse_selector("[data-testid='submit']")
        assert result.type == SelectorType.CSS

    def test_auto_detect_css_combinator(self):
        result = parse_selector("div > span")
        assert result.type == SelectorType.CSS

    def test_auto_detect_css_pseudo_selector(self):
        result = parse_selector("button:first-child")
        assert result.type == SelectorType.CSS

    def test_auto_detect_css_sibling(self):
        result = parse_selector("h1 + p")
        assert result.type == SelectorType.CSS

    def test_auto_detect_css_tag_name(self):
        result = parse_selector("button")
        assert result.type == SelectorType.CSS

    def test_auto_detect_css_div(self):
        result = parse_selector("div")
        assert result.type == SelectorType.CSS

    # ── Auto-detect XPath ─────────────────────────────────────────────────

    def test_auto_detect_xpath_double_slash(self):
        result = parse_selector("//div[@class='item']")
        assert result.type == SelectorType.XPATH

    def test_auto_detect_xpath_single_slash(self):
        result = parse_selector("/html/body/div")
        assert result.type == SelectorType.XPATH

    # ── Auto-detect text ──────────────────────────────────────────────────

    def test_auto_detect_text_plain_string(self):
        result = parse_selector("Login")
        assert result.type == SelectorType.TEXT
        assert result.expression == "Login"

    def test_auto_detect_text_with_spaces(self):
        result = parse_selector("Sign In Now")
        assert result.type == SelectorType.TEXT

    def test_auto_detect_text_non_html_word(self):
        result = parse_selector("Submit Order")
        assert result.type == SelectorType.TEXT

    # ── Edge cases ────────────────────────────────────────────────────────

    def test_empty_selector_raises_error(self):
        with pytest.raises(ValueError, match="empty"):
            parse_selector("")

    def test_whitespace_only_raises_error(self):
        with pytest.raises(ValueError, match="empty"):
            parse_selector("   ")

    def test_selector_is_trimmed(self):
        result = parse_selector("  #foo  ")
        assert result.expression == "#foo"

    def test_input_tag_detected_as_css(self):
        result = parse_selector("input")
        assert result.type == SelectorType.CSS


class TestAutoDetectType:
    """Focused tests for _auto_detect_type."""

    @pytest.mark.parametrize("sel,expected", [
        ("#id", SelectorType.CSS),
        (".class", SelectorType.CSS),
        ("[attr]", SelectorType.CSS),
        ("div", SelectorType.CSS),
        ("span", SelectorType.CSS),
        ("a", SelectorType.CSS),
        ("input", SelectorType.CSS),
        ("div.foo", SelectorType.CSS),
        ("div > p", SelectorType.CSS),
        ("//div", SelectorType.XPATH),
        ("/html", SelectorType.XPATH),
        ("Login", SelectorType.TEXT),
        ("Click here", SelectorType.TEXT),
        ("some random text", SelectorType.TEXT),
    ])
    def test_parametrized(self, sel, expected):
        assert _auto_detect_type(sel) == expected


# ═══════════════════════════════════════════════════════════════════════════════
# CDP Expression Generation
# ═══════════════════════════════════════════════════════════════════════════════


class TestCDPExpressions:
    """Test JavaScript expression generation for CDP."""

    def test_css_querySelector(self):
        parsed = ParsedSelector(SelectorType.CSS, "#foo")
        expr = to_cdp_expression(parsed)
        assert "querySelector" in expr
        assert "#foo" in expr

    def test_css_querySelectorAll(self):
        parsed = ParsedSelector(SelectorType.CSS, ".bar")
        expr = to_cdp_expression_all(parsed)
        assert "querySelectorAll" in expr
        assert ".bar" in expr

    def test_xpath_evaluate(self):
        parsed = ParsedSelector(SelectorType.XPATH, "//div[@id='main']")
        expr = to_cdp_expression(parsed)
        assert "document.evaluate" in expr
        assert "//div[@id=\\'main\\']" in expr

    def test_xpath_evaluate_all(self):
        parsed = ParsedSelector(SelectorType.XPATH, "//li")
        expr = to_cdp_expression_all(parsed)
        assert "ORDERED_NODE_SNAPSHOT_TYPE" in expr

    def test_text_treewalker(self):
        parsed = ParsedSelector(SelectorType.TEXT, "Login")
        expr = to_cdp_expression(parsed)
        assert "TreeWalker" in expr
        assert "Login" in expr

    def test_text_treewalker_all(self):
        parsed = ParsedSelector(SelectorType.TEXT, "Login")
        expr = to_cdp_expression_all(parsed)
        assert "TreeWalker" in expr
        assert "results" in expr

    def test_css_escapes_single_quotes(self):
        parsed = ParsedSelector(SelectorType.CSS, "[data-name='test']")
        expr = to_cdp_expression(parsed)
        assert "\\'" in expr


# ═══════════════════════════════════════════════════════════════════════════════
# BrowserElement (mocked CDP)
# ═══════════════════════════════════════════════════════════════════════════════


class TestBrowserElement:
    """Test BrowserElement with mocked CDPClient."""

    def _make_element(self):
        from naturo.browser._element import BrowserElement
        page = MagicMock()
        page._cdp = MagicMock()
        return BrowserElement(page, "obj-123", description="div#test")

    def test_text_calls_function_on(self):
        el = self._make_element()
        el._page._cdp.send.return_value = {
            "result": {"value": "Hello World"}
        }
        assert el.text == "Hello World"
        el._page._cdp.send.assert_called_once()
        args = el._page._cdp.send.call_args
        assert args[0][0] == "Runtime.callFunctionOn"

    def test_attr_returns_value(self):
        el = self._make_element()
        el._page._cdp.send.return_value = {
            "result": {"value": "https://example.com"}
        }
        assert el.attr("href") == "https://example.com"

    def test_attr_returns_none_when_missing(self):
        el = self._make_element()
        el._page._cdp.send.return_value = {"result": {"value": None}}
        assert el.attr("nonexistent") is None

    def test_click_dispatches_mouse_events(self):
        el = self._make_element()
        # Mock DOM.getContentQuads (top-document coords, #1080)
        el._page._cdp.send.side_effect = [
            # scroll_into_view (callFunctionOn)
            {"result": {"value": None}},
            # getContentQuads -> one quad: TL,TR,BR,BL
            {"quads": [[100, 200, 180, 200, 180, 230, 100, 230]]},
            # mousePressed
            {},
            # mouseReleased
            {},
        ]
        el.click()
        calls = el._page._cdp.send.call_args_list
        # Should have 4 calls: scrollIntoView, getContentQuads, mousePressed, mouseReleased
        assert len(calls) == 4
        # Params are passed as dict in second positional arg
        assert calls[2][0][1]["type"] == "mousePressed"
        assert calls[3][0][1]["type"] == "mouseReleased"

    def test_type_dispatches_key_events(self):
        el = self._make_element()
        el._page._cdp.send.return_value = {"result": {"value": None}}
        el.type("ab", clear_first=False)
        # focus + 2 chars * (keyDown + keyUp) = 1 + 4 = 5 calls
        assert el._page._cdp.send.call_count == 5

    def test_type_with_clear_first(self):
        el = self._make_element()
        el._page._cdp.send.return_value = {"result": {"value": None}}
        el.type("x", clear_first=True)
        # focus + clear + 1 char * (keyDown + keyUp) = 1 + 1 + 2 = 4 calls
        assert el._page._cdp.send.call_count == 4

    def test_repr(self):
        el = self._make_element()
        assert "div#test" in repr(el)

    def test_find_delegates_to_querySelector(self):
        el = self._make_element()
        el._page._cdp.send.return_value = {
            "result": {"objectId": "child-obj-1", "description": "span"}
        }
        child = el.find("css:.child")
        assert child is not None
        assert child.object_id == "child-obj-1"

    def test_find_all_returns_list(self):
        el = self._make_element()
        # First call: querySelectorAll → returns array objectId
        el._page._cdp.send.side_effect = [
            {"result": {"objectId": "arr-1"}},
            # getProperties → array items
            {"result": [
                {"name": "0", "value": {"objectId": "el-0", "description": "li"}},
                {"name": "1", "value": {"objectId": "el-1", "description": "li"}},
                {"name": "length", "value": {"value": 2}},
            ]},
        ]
        children = el.find_all("css:li")
        assert len(children) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestBrowserCLI:
    """Test browser CLI subcommand structure."""

    def test_browser_group_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert result.exit_code == 0
        assert "Browser automation" in result.output

    def test_browser_navigate_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "navigate" in result.output

    def test_browser_find_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "find" in result.output

    def test_browser_click_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "click" in result.output

    def test_browser_type_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "type" in result.output

    def test_browser_screenshot_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "screenshot" in result.output

    def test_browser_wait_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "wait" in result.output

    def test_browser_scroll_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "scroll" in result.output

    def test_browser_hover_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "hover" in result.output

    def test_browser_tabs_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "tabs" in result.output

    def test_browser_eval_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "eval" in result.output

    def test_browser_text_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "text" in result.output

    def test_browser_attr_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "attr" in result.output

    def test_browser_html_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "html" in result.output

    def test_browser_close_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "close" in result.output

    def test_browser_port_option(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "--help"])
        assert "--port" in result.output

    def test_browser_navigate_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "navigate", "--help"])
        assert result.exit_code == 0
        assert "--wait-until" in result.output

    def test_browser_find_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "find", "--help"])
        assert result.exit_code == 0
        assert "--all" in result.output
        assert "--timeout" in result.output
        assert "--by" in result.output

    def test_browser_click_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "click", "--help"])
        assert result.exit_code == 0
        assert "--offset-x" in result.output
        assert "--offset-y" in result.output

    def test_browser_type_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "type", "--help"])
        assert result.exit_code == 0
        assert "--clear-first" in result.output

    def test_browser_wait_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "wait", "--help"])
        assert result.exit_code == 0
        assert "--state" in result.output
        assert "visible" in result.output
        assert "hidden" in result.output

    def test_browser_scroll_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["browser", "scroll", "--help"])
        assert result.exit_code == 0
        assert "--to-bottom" in result.output
        assert "--to-top" in result.output
        assert "--to-element" in result.output

    def test_naturo_help_shows_browser(self):
        """The 'browser' subcommand appears in naturo --help."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "browser" in result.output
