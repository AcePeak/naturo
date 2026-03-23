"""Comprehensive tests for the Unified Selector engine.

Tests cover:
  - URI parsing (valid, edge cases, errors)
  - XML parsing (valid, edge cases, errors)
  - Simple/legacy selector parsing
  - Auto-detection of format
  - SelectorNode matching (exact, wildcard, fuzzy)
  - SelectorBuilder (URI and XML output)
  - SelectorResolver (exact, relaxed, fuzzy, resolve_all, exists)
  - String utilities (wildcard, fuzzy, Levenshtein)
  - Round-trip: build → parse → resolve
"""

from __future__ import annotations

import pytest
from naturo.selector import (
    SelectorAST,
    SelectorBuilder,
    SelectorNode,
    SelectorParseError,
    SelectorResolver,
    ResolvedElement,
    parse,
    parse_uri,
    parse_xml,
    _fuzzy_match,
    _levenshtein_similarity,
    _wildcard_match,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_tree():
    """A realistic UI element tree for testing resolution."""
    return [
        {
            "role": "Window",
            "name": "Untitled - Notepad",
            "automationid": "",
            "cls": "Notepad",
            "children": [
                {
                    "role": "MenuBar",
                    "name": "Application",
                    "automationid": "MenuBar",
                    "cls": "",
                    "children": [
                        {
                            "role": "MenuItem",
                            "name": "File",
                            "automationid": "File",
                            "cls": "",
                            "children": [],
                        },
                        {
                            "role": "MenuItem",
                            "name": "Edit",
                            "automationid": "Edit",
                            "cls": "",
                            "children": [],
                        },
                    ],
                },
                {
                    "role": "Edit",
                    "name": "",
                    "automationid": "15",
                    "cls": "Edit",
                    "value": "Hello World",
                    "children": [],
                },
                {
                    "role": "StatusBar",
                    "name": "Status Bar",
                    "automationid": "StatusBar",
                    "cls": "",
                    "children": [
                        {
                            "role": "Text",
                            "name": "Ln 1, Col 1",
                            "automationid": "",
                            "cls": "",
                            "children": [],
                        },
                    ],
                },
            ],
        },
    ]


@pytest.fixture
def multi_button_tree():
    """Tree with multiple buttons for idx testing."""
    return [
        {
            "role": "Window",
            "name": "Dialog",
            "automationid": "",
            "cls": "",
            "children": [
                {
                    "role": "Button",
                    "name": "OK",
                    "automationid": "btn_ok",
                    "cls": "Button",
                    "children": [],
                },
                {
                    "role": "Button",
                    "name": "Cancel",
                    "automationid": "btn_cancel",
                    "cls": "Button",
                    "children": [],
                },
                {
                    "role": "Button",
                    "name": "Apply",
                    "automationid": "btn_apply",
                    "cls": "Button",
                    "children": [],
                },
            ],
        },
    ]


@pytest.fixture
def builder():
    return SelectorBuilder()


@pytest.fixture
def resolver():
    return SelectorResolver()


# ══════════════════════════════════════════════════════════════════════════════
# URI Parsing
# ══════════════════════════════════════════════════════════════════════════════


class TestURIParsing:
    """URI-format selector parsing."""

    def test_simple_uri(self):
        """Parse basic URI with one node."""
        ast = parse_uri('app://notepad.exe/Button[@name="Save"]')
        assert ast.app == "notepad.exe"
        assert len(ast.nodes) == 1
        assert ast.nodes[0].role == "Button"
        assert ast.nodes[0].name == "Save"

    def test_multi_node_uri(self):
        """Parse URI with multiple path segments."""
        ast = parse_uri(
            'app://notepad.exe/Window[@name="Untitled"]/Edit[@automationid="15"]'
        )
        assert ast.app == "notepad.exe"
        assert len(ast.nodes) == 2
        assert ast.nodes[0].role == "Window"
        assert ast.nodes[0].name == "Untitled"
        assert ast.nodes[1].role == "Edit"
        assert ast.nodes[1].automationid == "15"

    def test_wildcard_app(self):
        """Parse URI with wildcard app."""
        ast = parse_uri('app://*/Button[@name="OK"]')
        assert ast.app == "*"
        assert ast.nodes[0].name == "OK"

    def test_multiple_attributes(self):
        """Parse node with multiple attributes."""
        ast = parse_uri(
            'app://calc.exe/Button[@name="7", @automationid="num7"]'
        )
        assert ast.nodes[0].name == "7"
        assert ast.nodes[0].automationid == "num7"

    def test_single_quote_attributes(self):
        """Parse attributes with single quotes."""
        ast = parse_uri("app://app.exe/Edit[@name='Username']")
        assert ast.nodes[0].name == "Username"

    def test_role_only_node(self):
        """Parse node with no attributes (role only)."""
        ast = parse_uri("app://app.exe/Window/Button")
        assert len(ast.nodes) == 2
        assert ast.nodes[0].role == "Window"
        assert ast.nodes[0].attributes == {}
        assert ast.nodes[1].role == "Button"

    def test_wildcard_in_name(self):
        """Parse wildcard characters in attribute values."""
        ast = parse_uri('app://*/Button[@name="Save*"]')
        assert ast.nodes[0].name == "Save*"

    def test_idx_attribute(self):
        """Parse idx attribute."""
        ast = parse_uri('app://app.exe/Button[@name="OK", @idx="2"]')
        assert ast.nodes[0].idx == 2

    def test_cls_attribute(self):
        """Parse cls attribute."""
        ast = parse_uri('app://app.exe/*[@cls="TButton"]')
        assert ast.nodes[0].role == "*"
        assert ast.nodes[0].cls == "TButton"

    def test_empty_uri_raises(self):
        """Empty URI body should raise."""
        with pytest.raises(SelectorParseError, match="Empty"):
            parse_uri("app://")

    def test_no_nodes_raises(self):
        """URI with only app and no nodes should raise."""
        with pytest.raises(SelectorParseError, match="at least one node"):
            parse_uri("app://notepad.exe")

    def test_wrong_scheme_raises(self):
        """Non-app:// scheme should raise."""
        with pytest.raises(SelectorParseError, match="app://"):
            parse_uri("http://example.com")

    def test_unclosed_bracket_raises(self):
        """Unclosed bracket should raise."""
        with pytest.raises(SelectorParseError, match="Unclosed"):
            parse_uri('app://app.exe/Button[@name="OK"')


# ══════════════════════════════════════════════════════════════════════════════
# XML Parsing
# ══════════════════════════════════════════════════════════════════════════════


class TestXMLParsing:
    """XML-format selector parsing."""

    def test_simple_xml(self):
        """Parse basic XML selector."""
        xml = '<selector app="notepad.exe"><node role="Button" name="Save"/></selector>'
        ast = parse_xml(xml)
        assert ast.app == "notepad.exe"
        assert len(ast.nodes) == 1
        assert ast.nodes[0].role == "Button"
        assert ast.nodes[0].name == "Save"

    def test_multi_node_xml(self):
        """Parse XML with multiple nodes."""
        xml = """<selector app="notepad.exe">
            <node role="Window" name="Untitled"/>
            <node role="Edit" automationid="15"/>
        </selector>"""
        ast = parse_xml(xml)
        assert len(ast.nodes) == 2
        assert ast.nodes[1].automationid == "15"

    def test_default_app(self):
        """XML without app attribute defaults to '*'."""
        xml = '<selector><node role="Button" name="OK"/></selector>'
        ast = parse_xml(xml)
        assert ast.app == "*"

    def test_wildcard_role(self):
        """XML node with role='*'."""
        xml = '<selector><node role="*" name="OK"/></selector>'
        ast = parse_xml(xml)
        assert ast.nodes[0].role == "*"

    def test_invalid_xml_raises(self):
        """Malformed XML should raise."""
        with pytest.raises(SelectorParseError, match="Invalid XML"):
            parse_xml("<selector><broken>")

    def test_wrong_root_raises(self):
        """Non-<selector> root should raise."""
        with pytest.raises(SelectorParseError, match="<selector>"):
            parse_xml('<query><node role="Button"/></query>')

    def test_no_nodes_raises(self):
        """Empty selector should raise."""
        with pytest.raises(SelectorParseError, match="at least one"):
            parse_xml("<selector></selector>")


# ══════════════════════════════════════════════════════════════════════════════
# Auto-Detection & Simple Parsing
# ══════════════════════════════════════════════════════════════════════════════


class TestAutoDetection:
    """Auto-detection of selector format and simple selectors."""

    def test_detect_uri(self):
        """Auto-detect URI format."""
        ast = parse('app://app.exe/Button[@name="OK"]')
        assert ast.app == "app.exe"

    def test_detect_xml(self):
        """Auto-detect XML format."""
        ast = parse('<selector><node role="Button" name="OK"/></selector>')
        assert ast.nodes[0].name == "OK"

    def test_simple_role_name(self):
        """Parse simple 'role:name' format."""
        ast = parse("Button:OK")
        assert ast.nodes[0].role == "Button"
        assert ast.nodes[0].name == "OK"

    def test_simple_name_only(self):
        """Parse bare name (no role)."""
        ast = parse("Save")
        assert ast.nodes[0].role == "*"
        assert ast.nodes[0].name == "Save"

    def test_simple_role_only(self):
        """Parse 'role:' with empty name."""
        ast = parse("Button:")
        assert ast.nodes[0].role == "Button"
        assert ast.nodes[0].name is None

    def test_empty_raises(self):
        """Empty string should raise."""
        with pytest.raises(SelectorParseError, match="Empty"):
            parse("")

    def test_whitespace_only_raises(self):
        """Whitespace-only should raise."""
        with pytest.raises(SelectorParseError, match="Empty"):
            parse("   ")


# ══════════════════════════════════════════════════════════════════════════════
# SelectorNode Matching
# ══════════════════════════════════════════════════════════════════════════════


class TestSelectorNodeMatching:
    """SelectorNode.matches() behavior."""

    def test_exact_match(self):
        """Exact role and name match."""
        node = SelectorNode(role="Button", attributes={"name": "OK"})
        assert node.matches("Button", {"name": "OK"})

    def test_role_mismatch(self):
        """Wrong role should not match."""
        node = SelectorNode(role="Button", attributes={"name": "OK"})
        assert not node.matches("Edit", {"name": "OK"})

    def test_wildcard_role(self):
        """Wildcard role matches any."""
        node = SelectorNode(role="*", attributes={"name": "OK"})
        assert node.matches("Button", {"name": "OK"})
        assert node.matches("Edit", {"name": "OK"})

    def test_wildcard_name(self):
        """Wildcard in name attribute."""
        node = SelectorNode(role="Button", attributes={"name": "Save*"})
        assert node.matches("Button", {"name": "Save As..."})
        assert not node.matches("Button", {"name": "Open"})

    def test_automationid_match(self):
        """Match by automationid."""
        node = SelectorNode(role="Edit", attributes={"automationid": "15"})
        assert node.matches("Edit", {"automationid": "15"})
        assert not node.matches("Edit", {"automationid": "16"})

    def test_multiple_attrs(self):
        """All attributes must match."""
        node = SelectorNode(
            role="Button", attributes={"name": "OK", "automationid": "btn_ok"}
        )
        assert node.matches("Button", {"name": "OK", "automationid": "btn_ok"})
        assert not node.matches("Button", {"name": "OK", "automationid": "btn_cancel"})

    def test_fuzzy_name(self):
        """Fuzzy matching on name."""
        node = SelectorNode(role="Button", attributes={"name": "Save"})
        assert node.matches("Button", {"name": "Sav"}, fuzzy=True)

    def test_case_insensitive_role(self):
        """Role matching is case-insensitive via wildcard."""
        node = SelectorNode(role="button", attributes={})
        assert node.matches("Button", {})

    def test_idx_skipped_in_matches(self):
        """idx is positional — should be skipped in matches()."""
        node = SelectorNode(role="Button", attributes={"name": "OK", "idx": "2"})
        # idx doesn't affect matches — it's handled by resolver
        assert node.matches("Button", {"name": "OK"})


# ══════════════════════════════════════════════════════════════════════════════
# SelectorBuilder
# ══════════════════════════════════════════════════════════════════════════════


class TestSelectorBuilder:
    """SelectorBuilder generates selectors from element dicts."""

    def test_build_uri_basic(self, builder):
        """Build URI for element with name."""
        element = {"role": "Button", "name": "OK", "automationid": ""}
        uri = builder.build_uri(element, app="calc.exe")
        assert uri.startswith("app://calc.exe/")
        assert "Button" in uri
        assert "OK" in uri

    def test_build_uri_automationid_priority(self, builder):
        """automationid is included when present."""
        element = {"role": "Edit", "name": "Input", "automationid": "txtSearch"}
        uri = builder.build_uri(element, app="app.exe")
        assert "automationid" in uri
        assert "txtSearch" in uri

    def test_build_uri_cls_fallback(self, builder):
        """cls used when no automationid or name."""
        element = {"role": "Pane", "name": "", "automationid": "", "cls": "SysListView32"}
        uri = builder.build_uri(element, app="explorer.exe")
        assert "cls" in uri
        assert "SysListView32" in uri

    def test_build_uri_with_ancestors(self, builder):
        """Ancestors with discriminating attributes are included."""
        ancestors = [
            {"role": "Window", "name": "Settings", "automationid": ""},
        ]
        element = {"role": "Button", "name": "Apply", "automationid": ""}
        uri = builder.build_uri(element, ancestors=ancestors, app="app.exe")
        assert "Window" in uri
        assert "Settings" in uri
        assert "Button" in uri
        assert "Apply" in uri

    def test_build_uri_skips_empty_ancestors(self, builder):
        """Ancestors without name or automationid are skipped."""
        ancestors = [
            {"role": "Pane", "name": "", "automationid": ""},
        ]
        element = {"role": "Button", "name": "OK", "automationid": ""}
        uri = builder.build_uri(element, ancestors=ancestors, app="app.exe")
        # Pane with no attrs should be skipped
        assert "Pane" not in uri

    def test_build_xml_basic(self, builder):
        """Build XML for element."""
        element = {"role": "Button", "name": "Save", "automationid": ""}
        xml = builder.build_xml(element, app="notepad.exe")
        assert '<selector app="notepad.exe">' in xml
        assert '<node' in xml
        assert 'role="Button"' in xml
        assert 'name="Save"' in xml
        assert "</selector>" in xml

    def test_build_xml_with_ancestors(self, builder):
        """XML includes ancestor nodes."""
        ancestors = [
            {"role": "Window", "name": "Dialog", "automationid": ""},
        ]
        element = {"role": "Button", "name": "OK", "automationid": ""}
        xml = builder.build_xml(element, ancestors=ancestors, app="app.exe")
        assert xml.count("<node") == 2

    def test_build_xml_escapes_special_chars(self, builder):
        """XML output escapes special characters."""
        element = {"role": "Button", "name": 'Save & "Close"', "automationid": ""}
        xml = builder.build_xml(element, app="app.exe")
        assert "&amp;" in xml
        assert "&quot;" in xml


# ══════════════════════════════════════════════════════════════════════════════
# SelectorResolver
# ══════════════════════════════════════════════════════════════════════════════


class TestSelectorResolver:
    """SelectorResolver finds elements in UI trees."""

    def test_resolve_by_name(self, resolver, sample_tree):
        """Resolve element by name."""
        ast = parse('app://*/MenuItem[@name="File"]')
        result = resolver.resolve(ast, sample_tree)
        assert result is not None
        assert result.element["name"] == "File"
        assert result.match_quality == "exact"

    def test_resolve_by_automationid(self, resolver, sample_tree):
        """Resolve element by automationid."""
        ast = parse('app://*/Edit[@automationid="15"]')
        result = resolver.resolve(ast, sample_tree)
        assert result is not None
        assert result.element["automationid"] == "15"

    def test_resolve_multi_node(self, resolver, sample_tree):
        """Resolve with multi-node path."""
        ast = parse(
            'app://*/Window[@name="Untitled - Notepad"]/MenuBar[@name="Application"]/MenuItem[@name="Edit"]'
        )
        result = resolver.resolve(ast, sample_tree)
        assert result is not None
        assert result.element["name"] == "Edit"
        assert result.element["role"] == "MenuItem"

    def test_resolve_not_found(self, resolver, sample_tree):
        """Resolve returns None for non-existent element."""
        ast = parse('app://*/Button[@name="Nonexistent"]')
        result = resolver.resolve(ast, sample_tree)
        assert result is None

    def test_resolve_wildcard_role(self, resolver, sample_tree):
        """Resolve with wildcard role."""
        ast = parse('app://*/*[@automationid="15"]')
        result = resolver.resolve(ast, sample_tree)
        assert result is not None
        assert result.element["role"] == "Edit"

    def test_resolve_relaxed_fallback(self, resolver, multi_button_tree):
        """Relaxed match drops idx and still finds element."""
        ast = SelectorAST(
            app="*",
            nodes=[SelectorNode(role="Button", attributes={"name": "OK", "idx": "5"})],
        )
        result = resolver.resolve(ast, multi_button_tree)
        assert result is not None
        assert result.element["name"] == "OK"
        assert result.match_quality == "relaxed"

    def test_resolve_fuzzy_fallback(self, resolver, multi_button_tree):
        """Fuzzy match finds element with approximate name."""
        ast = SelectorAST(
            app="*",
            nodes=[SelectorNode(role="Button", attributes={"name": "Cancle"})],  # typo
        )
        result = resolver.resolve(ast, multi_button_tree)
        assert result is not None
        assert result.element["name"] == "Cancel"
        assert result.match_quality == "fuzzy"

    def test_resolve_all(self, resolver, multi_button_tree):
        """resolve_all returns all matching buttons."""
        ast = SelectorAST(
            app="*",
            nodes=[SelectorNode(role="Button", attributes={})],
        )
        results = resolver.resolve_all(ast, multi_button_tree)
        assert len(results) == 3
        names = {r.element["name"] for r in results}
        assert names == {"OK", "Cancel", "Apply"}

    def test_exists_true(self, resolver, sample_tree):
        """exists() returns True for matching selector."""
        ast = parse('app://*/MenuItem[@name="File"]')
        assert resolver.exists(ast, sample_tree)

    def test_exists_false(self, resolver, sample_tree):
        """exists() returns False for non-matching selector."""
        ast = parse('app://*/Button[@name="Missing"]')
        assert not resolver.exists(ast, sample_tree)

    def test_resolve_nested_deep(self, resolver, sample_tree):
        """Resolve deeply nested element."""
        ast = parse('app://*/Text[@name="Ln 1, Col 1"]')
        result = resolver.resolve(ast, sample_tree)
        assert result is not None
        assert result.element["name"] == "Ln 1, Col 1"

    def test_resolve_simple_selector(self, resolver, sample_tree):
        """Resolve with simple 'role:name' selector."""
        ast = parse("MenuItem:File")
        result = resolver.resolve(ast, sample_tree)
        assert result is not None
        assert result.element["name"] == "File"

    def test_resolve_bare_name(self, resolver, sample_tree):
        """Resolve with bare name selector."""
        ast = parse("Status Bar")
        result = resolver.resolve(ast, sample_tree)
        assert result is not None
        assert result.element["role"] == "StatusBar"


# ══════════════════════════════════════════════════════════════════════════════
# String Utilities
# ══════════════════════════════════════════════════════════════════════════════


class TestStringUtilities:
    """Wildcard and fuzzy matching utilities."""

    def test_wildcard_exact(self):
        assert _wildcard_match("OK", "OK")

    def test_wildcard_star(self):
        assert _wildcard_match("Save*", "Save As...")
        assert not _wildcard_match("Save*", "Open")

    def test_wildcard_question(self):
        assert _wildcard_match("O?", "OK")
        assert not _wildcard_match("O?", "OKK")

    def test_wildcard_case_insensitive(self):
        assert _wildcard_match("button", "Button")
        assert _wildcard_match("BUTTON", "button")

    def test_fuzzy_exact(self):
        assert _fuzzy_match("Save", "Save")

    def test_fuzzy_close(self):
        assert _fuzzy_match("Cancel", "Cancle", threshold=0.6)

    def test_fuzzy_too_different(self):
        assert not _fuzzy_match("Save", "Delete", threshold=0.7)

    def test_fuzzy_empty(self):
        assert _fuzzy_match("", "")
        assert not _fuzzy_match("Save", "")
        assert not _fuzzy_match("", "Save")

    def test_levenshtein_identical(self):
        assert _levenshtein_similarity("hello", "hello") == 1.0

    def test_levenshtein_one_edit(self):
        sim = _levenshtein_similarity("hello", "helo")
        assert sim > 0.7

    def test_levenshtein_empty(self):
        assert _levenshtein_similarity("", "") == 1.0


# ══════════════════════════════════════════════════════════════════════════════
# Round-Trip Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestRoundTrip:
    """Build a selector, parse it back, resolve against the tree."""

    def test_uri_round_trip(self, builder, resolver, sample_tree):
        """Build URI → parse → resolve finds original element."""
        element = {"role": "Edit", "name": "", "automationid": "15", "cls": "Edit"}
        uri = builder.build_uri(element, app="notepad.exe")
        ast = parse(uri)
        result = resolver.resolve(ast, sample_tree)
        assert result is not None
        assert result.element["automationid"] == "15"

    def test_xml_round_trip(self, builder, resolver, multi_button_tree):
        """Build XML → parse → resolve finds original element."""
        element = {"role": "Button", "name": "Cancel", "automationid": "btn_cancel"}
        xml = builder.build_xml(element, app="dialog.exe")
        ast = parse(xml)
        result = resolver.resolve(ast, multi_button_tree)
        assert result is not None
        assert result.element["name"] == "Cancel"

    def test_uri_round_trip_with_ancestors(self, builder, resolver, sample_tree):
        """Build URI with ancestors → parse → resolve."""
        ancestors = [
            {"role": "Window", "name": "Untitled - Notepad", "automationid": ""},
        ]
        element = {"role": "MenuItem", "name": "File", "automationid": "File"}
        uri = builder.build_uri(element, ancestors=ancestors, app="notepad.exe")
        ast = parse(uri)
        result = resolver.resolve(ast, sample_tree)
        assert result is not None
        assert result.element["name"] == "File"
