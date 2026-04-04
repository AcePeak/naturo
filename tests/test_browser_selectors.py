"""Tests for naturo.browser._selectors — selector parsing and CDP expression generation."""

from __future__ import annotations

import pytest

from naturo.browser._selectors import (
    ParsedSelector,
    SelectorType,
    parse_selector,
    to_cdp_expression,
    to_cdp_expression_all,
)


# ---------------------------------------------------------------------------
# parse_selector — explicit prefixes
# ---------------------------------------------------------------------------


class TestParseSelectorExplicitPrefix:
    """parse_selector with explicit css:/xpath:/text: prefixes."""

    def test_css_prefix(self) -> None:
        result = parse_selector("css:div.active")
        assert result == ParsedSelector(SelectorType.CSS, "div.active")

    def test_css_prefix_case_insensitive(self) -> None:
        result = parse_selector("CSS:span#id")
        assert result == ParsedSelector(SelectorType.CSS, "span#id")

    def test_xpath_prefix(self) -> None:
        result = parse_selector("xpath://div[@id='main']")
        assert result == ParsedSelector(SelectorType.XPATH, "//div[@id='main']")

    def test_xpath_prefix_case_insensitive(self) -> None:
        result = parse_selector("XPATH://a")
        assert result == ParsedSelector(SelectorType.XPATH, "//a")

    def test_text_prefix(self) -> None:
        result = parse_selector("text:Login")
        assert result == ParsedSelector(SelectorType.TEXT, "Login")

    def test_text_prefix_case_insensitive(self) -> None:
        result = parse_selector("TEXT:Sign Up")
        assert result == ParsedSelector(SelectorType.TEXT, "Sign Up")

    def test_prefix_strips_whitespace(self) -> None:
        result = parse_selector("css:  div.foo  ")
        assert result.expression == "div.foo"


# ---------------------------------------------------------------------------
# parse_selector — auto-detection
# ---------------------------------------------------------------------------


class TestParseSelectorAutoDetect:
    """parse_selector auto-detection without explicit prefix."""

    def test_xpath_starts_with_slash(self) -> None:
        result = parse_selector("/html/body/div")
        assert result.type == SelectorType.XPATH

    def test_xpath_starts_with_double_slash(self) -> None:
        result = parse_selector("//div[@class='main']")
        assert result.type == SelectorType.XPATH

    def test_css_starts_with_hash(self) -> None:
        result = parse_selector("#search-input")
        assert result.type == SelectorType.CSS

    def test_css_starts_with_dot(self) -> None:
        result = parse_selector(".container")
        assert result.type == SelectorType.CSS

    def test_css_starts_with_bracket(self) -> None:
        result = parse_selector("[data-testid='submit']")
        assert result.type == SelectorType.CSS

    def test_css_contains_combinator_gt(self) -> None:
        result = parse_selector("div > span")
        assert result.type == SelectorType.CSS

    def test_css_contains_combinator_tilde(self) -> None:
        result = parse_selector("h1 ~ p")
        assert result.type == SelectorType.CSS

    def test_css_contains_combinator_plus(self) -> None:
        result = parse_selector("h1 + p")
        assert result.type == SelectorType.CSS

    def test_css_contains_pseudo_selector(self) -> None:
        result = parse_selector("li:first-child")
        assert result.type == SelectorType.CSS

    def test_css_bare_html_tag(self) -> None:
        result = parse_selector("div")
        assert result.type == SelectorType.CSS

    def test_css_bare_html_tag_button(self) -> None:
        result = parse_selector("button")
        assert result.type == SelectorType.CSS

    def test_text_plain_string(self) -> None:
        result = parse_selector("Login")
        assert result.type == SelectorType.TEXT

    def test_text_string_with_spaces(self) -> None:
        result = parse_selector("Sign Up Now")
        assert result.type == SelectorType.TEXT

    def test_text_unknown_word(self) -> None:
        result = parse_selector("myCustomElement")
        assert result.type == SelectorType.TEXT

    def test_expression_preserved(self) -> None:
        result = parse_selector("Sign Up")
        assert result.expression == "Sign Up"


# ---------------------------------------------------------------------------
# parse_selector — edge cases
# ---------------------------------------------------------------------------


class TestParseSelectorEdgeCases:
    """Edge cases and error handling for parse_selector."""

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            parse_selector("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            parse_selector("   ")

    def test_leading_trailing_whitespace_stripped(self) -> None:
        result = parse_selector("  #my-id  ")
        assert result == ParsedSelector(SelectorType.CSS, "#my-id")

    def test_css_attribute_selector(self) -> None:
        result = parse_selector("[name=email]")
        assert result.type == SelectorType.CSS


# ---------------------------------------------------------------------------
# to_cdp_expression — single element
# ---------------------------------------------------------------------------


class TestToCdpExpression:
    """to_cdp_expression returns correct JS for each selector type."""

    def test_css_uses_queryselector(self) -> None:
        parsed = ParsedSelector(SelectorType.CSS, "div.active")
        js = to_cdp_expression(parsed)
        assert "document.querySelector(" in js
        assert "div.active" in js

    def test_xpath_uses_evaluate(self) -> None:
        parsed = ParsedSelector(SelectorType.XPATH, "//div[@id='main']")
        js = to_cdp_expression(parsed)
        assert "document.evaluate(" in js
        assert "FIRST_ORDERED_NODE_TYPE" in js

    def test_text_uses_treewalker(self) -> None:
        parsed = ParsedSelector(SelectorType.TEXT, "Login")
        js = to_cdp_expression(parsed)
        assert "createTreeWalker" in js
        assert "Login" in js

    def test_css_escapes_single_quotes(self) -> None:
        parsed = ParsedSelector(SelectorType.CSS, "div[data-name='test']")
        js = to_cdp_expression(parsed)
        assert "\\'" in js

    def test_css_escapes_backslashes(self) -> None:
        parsed = ParsedSelector(SelectorType.CSS, "div\\.class")
        js = to_cdp_expression(parsed)
        assert "\\\\" in js

    def test_xpath_escapes_single_quotes(self) -> None:
        parsed = ParsedSelector(SelectorType.XPATH, "//div[@name='it\\'s']")
        js = to_cdp_expression(parsed)
        assert "document.evaluate(" in js

    def test_text_escapes_single_quotes(self) -> None:
        parsed = ParsedSelector(SelectorType.TEXT, "it's a test")
        js = to_cdp_expression(parsed)
        assert "\\'" in js


# ---------------------------------------------------------------------------
# to_cdp_expression_all — multiple elements
# ---------------------------------------------------------------------------


class TestToCdpExpressionAll:
    """to_cdp_expression_all returns JS that returns an array."""

    def test_css_uses_queryselectorall(self) -> None:
        parsed = ParsedSelector(SelectorType.CSS, "li.item")
        js = to_cdp_expression_all(parsed)
        assert "querySelectorAll(" in js
        assert "Array.from(" in js

    def test_xpath_uses_snapshot(self) -> None:
        parsed = ParsedSelector(SelectorType.XPATH, "//li")
        js = to_cdp_expression_all(parsed)
        assert "ORDERED_NODE_SNAPSHOT_TYPE" in js
        assert "snapshotLength" in js

    def test_text_returns_array(self) -> None:
        parsed = ParsedSelector(SelectorType.TEXT, "Item")
        js = to_cdp_expression_all(parsed)
        assert "createTreeWalker" in js
        assert "results" in js

    def test_text_deduplicates_parents(self) -> None:
        parsed = ParsedSelector(SelectorType.TEXT, "dup")
        js = to_cdp_expression_all(parsed)
        assert "indexOf(el) === -1" in js

    def test_css_escapes_in_all(self) -> None:
        parsed = ParsedSelector(SelectorType.CSS, "a[href='x']")
        js = to_cdp_expression_all(parsed)
        assert "\\'" in js

    def test_xpath_escapes_in_all(self) -> None:
        parsed = ParsedSelector(SelectorType.XPATH, "//a[@href='x']")
        js = to_cdp_expression_all(parsed)
        assert "\\'" in js

    def test_text_escapes_in_all(self) -> None:
        parsed = ParsedSelector(SelectorType.TEXT, "it's")
        js = to_cdp_expression_all(parsed)
        assert "\\'" in js
