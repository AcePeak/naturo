"""Tests for naturo.selector — parsing, building, matching, and utility functions.

Covers the pure-logic portions of the selector engine:
- SelectorNode / SelectorAST dataclasses
- URI, XML, and simple parsers
- SelectorBuilder (URI + XML generation)
- Wildcard matching, fuzzy matching, Levenshtein similarity
- App name normalization and matching
- XML escaping
"""

from __future__ import annotations

import pytest

from naturo.selector import (
    SelectorAST,
    SelectorBuilder,
    SelectorNode,
    SelectorParseError,
    _fuzzy_match,
    _levenshtein_similarity,
    _parse_simple,
    _parse_uri_node,
    _split_uri_path,
    _wildcard_match,
    _xml_escape,
    app_names_match,
    normalize_app_name,
    parse,
    parse_uri,
    parse_xml,
)


# ── SelectorNode ─────────────────────────────────────────────────────────────


class TestSelectorNode:
    def test_defaults(self):
        node = SelectorNode()
        assert node.role == "*"
        assert node.attributes == {}
        assert node.name is None
        assert node.automationid is None
        assert node.cls is None
        assert node.idx is None

    def test_shortcut_properties(self):
        node = SelectorNode(
            role="Button",
            attributes={"name": "OK", "automationid": "btn1", "cls": "Win32", "idx": "3"},
        )
        assert node.name == "OK"
        assert node.automationid == "btn1"
        assert node.cls == "Win32"
        assert node.idx == 3

    def test_idx_invalid_returns_none(self):
        node = SelectorNode(attributes={"idx": "abc"})
        assert node.idx is None

    def test_matches_any_role(self):
        node = SelectorNode(role="*", attributes={"name": "OK"})
        assert node.matches("Button", {"name": "OK"})
        assert node.matches("Edit", {"name": "OK"})

    def test_matches_specific_role(self):
        node = SelectorNode(role="Button")
        assert node.matches("Button", {})
        assert not node.matches("Edit", {})

    def test_matches_wildcard_role(self):
        node = SelectorNode(role="But*")
        assert node.matches("Button", {})
        assert not node.matches("Edit", {})

    def test_matches_attribute(self):
        node = SelectorNode(role="Button", attributes={"name": "Save"})
        assert node.matches("Button", {"name": "Save"})
        assert not node.matches("Button", {"name": "Cancel"})

    def test_matches_wildcard_attribute(self):
        node = SelectorNode(role="*", attributes={"name": "Save*"})
        assert node.matches("Button", {"name": "Save As..."})
        assert not node.matches("Button", {"name": "Cancel"})

    def test_matches_fuzzy(self):
        node = SelectorNode(role="Button", attributes={"name": "Save"})
        assert node.matches("Button", {"name": "Sav"}, fuzzy=True, fuzzy_threshold=0.6)

    def test_matches_idx_skipped(self):
        """idx is positional and handled by resolver, not by matches()."""
        node = SelectorNode(role="Button", attributes={"idx": "0", "name": "OK"})
        assert node.matches("Button", {"name": "OK"})

    def test_matches_missing_attribute(self):
        node = SelectorNode(attributes={"name": "OK"})
        assert not node.matches("Button", {})


# ── SelectorAST ──────────────────────────────────────────────────────────────


class TestSelectorAST:
    def test_empty_nodes(self):
        ast = SelectorAST()
        assert ast.app == "*"
        assert ast.nodes == []
        assert ast.target is None

    def test_target_returns_last_node(self):
        n1 = SelectorNode(role="Window")
        n2 = SelectorNode(role="Button")
        ast = SelectorAST(app="notepad.exe", nodes=[n1, n2])
        assert ast.target is n2

    def test_repr(self):
        ast = SelectorAST(
            app="notepad.exe",
            nodes=[SelectorNode(role="Button", attributes={"name": "OK"})],
        )
        r = repr(ast)
        assert "notepad.exe" in r
        assert "Button" in r


# ── URI Parser ───────────────────────────────────────────────────────────────


class TestParseUri:
    def test_basic(self):
        ast = parse_uri('app://notepad.exe/Button[@name="OK"]')
        assert ast.app == "notepad.exe"
        assert len(ast.nodes) == 1
        assert ast.nodes[0].role == "Button"
        assert ast.nodes[0].name == "OK"

    def test_wildcard_app(self):
        ast = parse_uri('app://*/Edit[@automationid="15"]')
        assert ast.app == "*"
        assert ast.nodes[0].automationid == "15"

    def test_multi_node(self):
        ast = parse_uri('app://chrome.exe/Window[@name="Tab"]/Button[@name="Close"]')
        assert len(ast.nodes) == 2
        assert ast.nodes[0].role == "Window"
        assert ast.nodes[1].role == "Button"

    def test_no_attributes(self):
        ast = parse_uri("app://app.exe/Button")
        assert ast.nodes[0].role == "Button"
        assert ast.nodes[0].attributes == {}

    def test_single_quotes(self):
        ast = parse_uri("app://app.exe/Button[@name='OK']")
        assert ast.nodes[0].name == "OK"

    def test_error_no_prefix(self):
        with pytest.raises(SelectorParseError, match="app://"):
            parse_uri("notepad.exe/Button")

    def test_error_empty_body(self):
        with pytest.raises(SelectorParseError, match="Empty URI"):
            parse_uri("app://")

    def test_error_no_nodes(self):
        with pytest.raises(SelectorParseError, match="at least one node"):
            parse_uri("app://notepad.exe")


# ── XML Parser ───────────────────────────────────────────────────────────────


class TestParseXml:
    def test_basic(self):
        xml = '<selector app="notepad.exe"><node role="Button" name="OK"/></selector>'
        ast = parse_xml(xml)
        assert ast.app == "notepad.exe"
        assert len(ast.nodes) == 1
        assert ast.nodes[0].role == "Button"
        assert ast.nodes[0].attributes["name"] == "OK"

    def test_wildcard_app(self):
        xml = '<selector><node role="Edit"/></selector>'
        ast = parse_xml(xml)
        assert ast.app == "*"

    def test_multi_node(self):
        xml = """<selector app="app.exe">
            <node role="Window" name="Main"/>
            <node role="Button" name="OK"/>
        </selector>"""
        ast = parse_xml(xml)
        assert len(ast.nodes) == 2

    def test_error_invalid_xml(self):
        with pytest.raises(SelectorParseError, match="Invalid XML"):
            parse_xml("<not valid xml>>>")

    def test_error_wrong_root(self):
        with pytest.raises(SelectorParseError, match="<selector>"):
            parse_xml('<window><node role="Button"/></window>')

    def test_error_no_nodes(self):
        with pytest.raises(SelectorParseError, match="at least one"):
            parse_xml('<selector app="x"></selector>')


# ── Simple Parser ────────────────────────────────────────────────────────────


class TestParseSimple:
    def test_role_colon_name(self):
        ast = _parse_simple("Button:OK")
        assert ast.nodes[0].role == "Button"
        assert ast.nodes[0].name == "OK"

    def test_bare_name(self):
        ast = _parse_simple("Save")
        assert ast.nodes[0].role == "*"
        assert ast.nodes[0].name == "Save"

    def test_role_only(self):
        ast = _parse_simple("Button:")
        assert ast.nodes[0].role == "Button"
        assert ast.nodes[0].name is None

    def test_colon_name_only(self):
        ast = _parse_simple(":OK")
        assert ast.nodes[0].role == "*"
        assert ast.nodes[0].name == "OK"


# ── Auto-detect Parser ──────────────────────────────────────────────────────


class TestParse:
    def test_uri_format(self):
        ast = parse('app://app.exe/Button[@name="OK"]')
        assert ast.app == "app.exe"

    def test_xml_format(self):
        ast = parse('<selector><node role="Button" name="OK"/></selector>')
        assert ast.nodes[0].role == "Button"

    def test_descendant_shorthand(self):
        ast = parse('//Button[@name="OK"]')
        assert ast.app == "*"
        assert ast.nodes[0].role == "Button"

    def test_simple_format(self):
        ast = parse("Button:OK")
        assert ast.nodes[0].role == "Button"

    def test_empty_raises(self):
        with pytest.raises(SelectorParseError, match="Empty"):
            parse("")

    def test_whitespace_stripped(self):
        ast = parse('  app://app.exe/Button[@name="OK"]  ')
        assert ast.app == "app.exe"


# ── URI Helpers ──────────────────────────────────────────────────────────────


class TestSplitUriPath:
    def test_simple(self):
        assert _split_uri_path("app.exe/Button/Edit") == ["app.exe", "Button", "Edit"]

    def test_brackets_preserved(self):
        result = _split_uri_path('app.exe/Button[@name="a/b"]')
        assert len(result) == 2
        assert result[0] == "app.exe"
        assert "a/b" in result[1]

    def test_empty(self):
        assert _split_uri_path("") == []

    def test_single_segment(self):
        assert _split_uri_path("app.exe") == ["app.exe"]


class TestParseUriNode:
    def test_role_only(self):
        node = _parse_uri_node("Button")
        assert node.role == "Button"
        assert node.attributes == {}

    def test_role_with_attrs(self):
        node = _parse_uri_node('Button[@name="OK", @automationid="btn1"]')
        assert node.role == "Button"
        assert node.attributes["name"] == "OK"
        assert node.attributes["automationid"] == "btn1"

    def test_empty_role_defaults_star(self):
        node = _parse_uri_node('[@name="OK"]')
        assert node.role == "*"

    def test_unclosed_bracket_error(self):
        with pytest.raises(SelectorParseError, match="Unclosed bracket"):
            _parse_uri_node("Button[@name")

    def test_unparseable_attrs_error(self):
        with pytest.raises(SelectorParseError, match="Could not parse"):
            _parse_uri_node("Button[garbage]")


# ── SelectorBuilder ──────────────────────────────────────────────────────────


class TestSelectorBuilder:
    def setup_method(self):
        self.builder = SelectorBuilder()

    def test_build_uri_simple(self):
        elem = {"role": "Button", "name": "OK"}
        uri = self.builder.build_uri(elem, app="notepad.exe")
        assert uri.startswith("app://notepad.exe/")
        assert "Button" in uri
        assert "OK" in uri

    def test_build_uri_automationid_priority(self):
        elem = {"role": "Button", "name": "OK", "automationid": "btn1"}
        uri = self.builder.build_uri(elem)
        assert "automationid" in uri
        assert "name" in uri

    def test_build_uri_cls_fallback(self):
        elem = {"role": "Pane", "cls": "MyClass", "idx": 2}
        uri = self.builder.build_uri(elem)
        assert "cls" in uri
        assert "idx" in uri

    def test_build_uri_with_ancestors(self):
        elem = {"role": "Button", "name": "OK"}
        ancestors = [{"role": "Window", "name": "Dialog"}]
        uri = self.builder.build_uri(elem, ancestors=ancestors, app="app.exe")
        assert "Window" in uri
        assert "Button" in uri

    def test_build_uri_ancestors_without_name_skipped(self):
        elem = {"role": "Button", "name": "OK"}
        ancestors = [{"role": "Pane"}]  # no name or automationid
        uri = self.builder.build_uri(elem, ancestors=ancestors)
        # Should only have the target node, not the ancestor
        # URI: app://*/Button[@name="OK"] — no Pane segment
        assert "Pane" not in uri
        assert "Button" in uri

    def test_build_xml(self):
        elem = {"role": "Button", "name": "OK"}
        xml = self.builder.build_xml(elem, app="app.exe")
        assert '<selector app="app.exe">' in xml
        assert 'role="Button"' in xml
        assert "</selector>" in xml

    def test_build_xml_escapes_special(self):
        elem = {"role": "Button", "name": 'Save & "Exit"'}
        xml = self.builder.build_xml(elem)
        assert "&amp;" in xml
        assert "&quot;" in xml

    def test_node_to_uri_no_attrs(self):
        node = SelectorNode(role="Button")
        assert SelectorBuilder._node_to_uri_segment(node) == "Button"

    def test_node_to_uri_with_attrs(self):
        node = SelectorNode(role="Edit", attributes={"name": "Search"})
        segment = SelectorBuilder._node_to_uri_segment(node)
        assert segment == 'Edit[@name="Search"]'


# ── Wildcard Matching ────────────────────────────────────────────────────────


class TestWildcardMatch:
    def test_exact(self):
        assert _wildcard_match("Button", "Button")

    def test_case_insensitive(self):
        assert _wildcard_match("button", "BUTTON")

    def test_star_wildcard(self):
        assert _wildcard_match("But*", "Button")
        assert _wildcard_match("*ton", "Button")
        assert not _wildcard_match("But*", "Edit")

    def test_question_mark(self):
        assert _wildcard_match("Butto?", "Button")
        assert not _wildcard_match("Butto?", "Buttons")


# ── Fuzzy Matching ───────────────────────────────────────────────────────────


class TestFuzzyMatch:
    def test_exact_match(self):
        assert _fuzzy_match("Save", "Save")

    def test_close_match(self):
        assert _fuzzy_match("Save", "Sav", threshold=0.6)

    def test_no_match(self):
        assert not _fuzzy_match("Save", "Delete", threshold=0.8)

    def test_both_empty(self):
        assert _fuzzy_match("", "")

    def test_one_empty(self):
        assert not _fuzzy_match("Save", "")
        assert not _fuzzy_match("", "Save")

    def test_wildcard_checked_first(self):
        assert _fuzzy_match("Sav*", "Save", threshold=0.99)


# ── Levenshtein Similarity ───────────────────────────────────────────────────


class TestLevenshteinSimilarity:
    def test_identical(self):
        assert _levenshtein_similarity("abc", "abc") == 1.0

    def test_both_empty(self):
        assert _levenshtein_similarity("", "") == 1.0

    def test_completely_different(self):
        sim = _levenshtein_similarity("abc", "xyz")
        assert sim == 0.0

    def test_one_edit(self):
        sim = _levenshtein_similarity("cat", "bat")
        assert sim == pytest.approx(2 / 3)

    def test_addition(self):
        sim = _levenshtein_similarity("abc", "abcd")
        assert sim == pytest.approx(3 / 4)


# ── App Name Utilities ───────────────────────────────────────────────────────


class TestNormalizeAppName:
    def test_lowercase(self):
        assert normalize_app_name("Chrome") == "chrome"

    def test_strip_exe(self):
        assert normalize_app_name("notepad.exe") == "notepad"

    def test_strip_whitespace(self):
        assert normalize_app_name("  Chrome.exe  ") == "chrome"

    def test_no_exe(self):
        assert normalize_app_name("firefox") == "firefox"


class TestAppNamesMatch:
    def test_same(self):
        assert app_names_match("chrome", "chrome")

    def test_case_insensitive(self):
        assert app_names_match("Chrome", "chrome")

    def test_exe_suffix(self):
        assert app_names_match("notepad.exe", "notepad")

    def test_wildcard(self):
        assert app_names_match("*", "anything")
        assert app_names_match("something", "*")

    def test_different(self):
        assert not app_names_match("chrome", "firefox")


# ── XML Escape ────────────────────────────────────��──────────────────────────


class TestXmlEscape:
    def test_ampersand(self):
        assert "&amp;" in _xml_escape("a & b")

    def test_quotes(self):
        assert "&quot;" in _xml_escape('say "hello"')

    def test_angle_brackets(self):
        assert "&lt;" in _xml_escape("<tag>")
        assert "&gt;" in _xml_escape("</tag>")

    def test_apostrophe(self):
        assert "&apos;" in _xml_escape("it's")

    def test_no_escaping_needed(self):
        assert _xml_escape("plain text") == "plain text"
