"""Selector resolution for browser automation.

Converts user-facing selector strings into a structured form that can be
dispatched to the appropriate CDP DOM query method.

Selector formats
----------------
* ``css:<selector>``  — explicit CSS selector
* ``xpath:<selector>`` — explicit XPath expression
* ``text:<substring>`` — text content search
* Bare selectors are auto-detected:
  - Starts with ``/`` or ``//`` → XPath
  - Starts with ``#``, ``.``, ``[``, or contains ``:`` / ``>`` / ``~`` / ``+`` → CSS
  - Otherwise → text search
"""

from __future__ import annotations

import re
from enum import Enum
from typing import NamedTuple


class SelectorType(Enum):
    """Selector strategy for DOM queries."""

    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"


class ParsedSelector(NamedTuple):
    """A selector string parsed into type and expression."""

    type: SelectorType
    expression: str


# Characters/patterns that strongly indicate a CSS selector
_CSS_INDICATORS = re.compile(r"[#.\[>~+:=]")


def parse_selector(raw: str) -> ParsedSelector:
    """Parse a raw selector string into type + expression.

    Args:
        raw: User-provided selector string, optionally prefixed with
            ``css:``, ``xpath:``, or ``text:``.

    Returns:
        ParsedSelector with resolved type and cleaned expression.

    Raises:
        ValueError: If *raw* is empty.

    Examples:
        >>> parse_selector("css:div.active")
        ParsedSelector(type=<SelectorType.CSS: 'css'>, expression='div.active')
        >>> parse_selector("//div[@id='main']")
        ParsedSelector(type=<SelectorType.XPATH: 'xpath'>, expression="//div[@id='main']")
        >>> parse_selector("#search-input")
        ParsedSelector(type=<SelectorType.CSS: 'css'>, expression='#search-input')
        >>> parse_selector("Login")
        ParsedSelector(type=<SelectorType.TEXT: 'text'>, expression='Login')
    """
    if not raw or not raw.strip():
        raise ValueError("Selector cannot be empty")

    raw = raw.strip()

    # Explicit prefix detection
    lower = raw.lower()
    if lower.startswith("css:"):
        return ParsedSelector(SelectorType.CSS, raw[4:].strip())
    if lower.startswith("xpath:"):
        return ParsedSelector(SelectorType.XPATH, raw[6:].strip())
    if lower.startswith("text:"):
        return ParsedSelector(SelectorType.TEXT, raw[5:].strip())

    # Auto-detection
    return ParsedSelector(_auto_detect_type(raw), raw)


def _auto_detect_type(selector: str) -> SelectorType:
    """Detect the selector type from its content.

    Args:
        selector: A selector string without an explicit prefix.

    Returns:
        Best-guess SelectorType.
    """
    # XPath: starts with / or //
    if selector.startswith("/"):
        return SelectorType.XPATH

    # CSS: starts with common CSS characters or contains CSS operators
    if selector.startswith(("#", ".", "[")):
        return SelectorType.CSS

    # CSS: contains CSS-specific characters (combinators, pseudo-selectors)
    if _CSS_INDICATORS.search(selector):
        return SelectorType.CSS

    # CSS: looks like a tag name (lowercase, no spaces, common HTML tags)
    if re.fullmatch(r"[a-z][a-z0-9]*", selector) and selector in _HTML_TAGS:
        return SelectorType.CSS

    # Default: text search
    return SelectorType.TEXT


# Common HTML tag names for auto-detection of bare tag selectors
_HTML_TAGS = frozenset({
    "a", "abbr", "article", "aside", "audio", "b", "body", "br", "button",
    "canvas", "caption", "code", "col", "colgroup", "datalist", "dd", "details",
    "dialog", "div", "dl", "dt", "em", "fieldset", "figcaption", "figure",
    "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "head", "header",
    "hr", "html", "i", "iframe", "img", "input", "label", "legend", "li",
    "link", "main", "map", "mark", "menu", "meta", "meter", "nav", "ol",
    "optgroup", "option", "output", "p", "picture", "pre", "progress", "q",
    "script", "section", "select", "small", "source", "span", "strong",
    "style", "sub", "summary", "sup", "svg", "table", "tbody", "td",
    "template", "textarea", "tfoot", "th", "thead", "time", "title", "tr",
    "track", "u", "ul", "var", "video",
})


def _escape_js_string(value: str) -> str:
    """Escape a string for embedding inside a single-quoted JS literal."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def to_cdp_expression(parsed: ParsedSelector) -> str:
    """Convert a parsed selector to a JavaScript expression for CDP evaluation.

    The returned expression can be passed to ``Runtime.evaluate`` and returns
    either a single element or null.

    Args:
        parsed: A parsed selector.

    Returns:
        JavaScript expression string.
    """
    if parsed.type == SelectorType.CSS:
        escaped = _escape_js_string(parsed.expression)
        return f"document.querySelector('{escaped}')"

    if parsed.type == SelectorType.XPATH:
        escaped = _escape_js_string(parsed.expression)
        return (
            f"document.evaluate('{escaped}', document, null, "
            f"XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue"
        )

    # Text search via TreeWalker
    escaped = _escape_js_string(parsed.expression)
    return (
        f"(function() {{"
        f"  var tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);"
        f"  while (tw.nextNode()) {{"
        f"    if (tw.currentNode.textContent.includes('{escaped}')) {{"
        f"      return tw.currentNode.parentElement;"
        f"    }}"
        f"  }}"
        f"  return null;"
        f"}})()"
    )


def to_cdp_expression_all(parsed: ParsedSelector) -> str:
    """Convert a parsed selector to a JS expression returning an array of elements.

    Args:
        parsed: A parsed selector.

    Returns:
        JavaScript expression string returning an Array of elements.
    """
    if parsed.type == SelectorType.CSS:
        escaped = _escape_js_string(parsed.expression)
        return f"Array.from(document.querySelectorAll('{escaped}'))"

    if parsed.type == SelectorType.XPATH:
        escaped = _escape_js_string(parsed.expression)
        return (
            f"(function() {{"
            f"  var r = document.evaluate('{escaped}', document, null, "
            f"XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);"
            f"  var a = []; for (var i = 0; i < r.snapshotLength; i++) a.push(r.snapshotItem(i));"
            f"  return a;"
            f"}})()"
        )

    # Text search — return all matches
    escaped = _escape_js_string(parsed.expression)
    return (
        f"(function() {{"
        f"  var tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);"
        f"  var results = [];"
        f"  while (tw.nextNode()) {{"
        f"    if (tw.currentNode.textContent.includes('{escaped}')) {{"
        f"      var el = tw.currentNode.parentElement;"
        f"      if (el && results.indexOf(el) === -1) results.push(el);"
        f"    }}"
        f"  }}"
        f"  return results;"
        f"}})()"
    )


def to_scoped_function(parsed: ParsedSelector) -> str:
    """Build a JS function that finds the first match *within* a context element.

    The returned source is a function declaration suitable for CDP
    ``Runtime.callFunctionOn`` with ``this`` bound to the parent DOM node, so the
    search is scoped to that node's subtree rather than the whole document. This
    is what makes ``element.find(...)`` honour the parent (e.g. the DrissionPage
    ``item.ele("xpath:.//span")`` per-card scrape pattern), instead of silently
    returning the document's first global match.

    XPath is evaluated with the parent as the context node, so a relative
    expression (``.//span``) resolves against the parent. Text search walks only
    the parent's text nodes. CSS uses the parent's ``querySelector``.

    Args:
        parsed: A parsed selector.

    Returns:
        JavaScript function-declaration source returning the first matching
        element, or ``null``.
    """
    escaped = _escape_js_string(parsed.expression)

    if parsed.type == SelectorType.CSS:
        return f"function() {{ return this.querySelector('{escaped}'); }}"

    if parsed.type == SelectorType.XPATH:
        return (
            f"function() {{"
            f"  return document.evaluate('{escaped}', this, null, "
            f"XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;"
            f"}}"
        )

    # Text search via a TreeWalker rooted at the context element.
    return (
        f"function() {{"
        f"  var tw = document.createTreeWalker(this, NodeFilter.SHOW_TEXT);"
        f"  while (tw.nextNode()) {{"
        f"    if (tw.currentNode.textContent.includes('{escaped}')) {{"
        f"      return tw.currentNode.parentElement;"
        f"    }}"
        f"  }}"
        f"  return null;"
        f"}}"
    )


def to_scoped_function_all(parsed: ParsedSelector) -> str:
    """Build a JS function that finds all matches *within* a context element.

    The array counterpart of :func:`to_scoped_function`: a function declaration
    for CDP ``Runtime.callFunctionOn`` (``this`` = parent node) returning every
    descendant match in document order, scoped to the parent's subtree.

    Args:
        parsed: A parsed selector.

    Returns:
        JavaScript function-declaration source returning an ``Array`` of
        matching elements.
    """
    escaped = _escape_js_string(parsed.expression)

    if parsed.type == SelectorType.CSS:
        return (
            f"function() {{ return Array.from(this.querySelectorAll('{escaped}')); }}"
        )

    if parsed.type == SelectorType.XPATH:
        return (
            f"function() {{"
            f"  var r = document.evaluate('{escaped}', this, null, "
            f"XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);"
            f"  var a = []; for (var i = 0; i < r.snapshotLength; i++) a.push(r.snapshotItem(i));"
            f"  return a;"
            f"}}"
        )

    # Text search via a TreeWalker rooted at the context element.
    return (
        f"function() {{"
        f"  var tw = document.createTreeWalker(this, NodeFilter.SHOW_TEXT);"
        f"  var results = [];"
        f"  while (tw.nextNode()) {{"
        f"    if (tw.currentNode.textContent.includes('{escaped}')) {{"
        f"      var el = tw.currentNode.parentElement;"
        f"      if (el && results.indexOf(el) === -1) results.push(el);"
        f"    }}"
        f"  }}"
        f"  return results;"
        f"}}"
    )
