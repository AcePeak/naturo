"""Tests for naturo.providers.base — VisionResult, parsing, registry, factory."""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from naturo.providers.base import (
    VisionResult,
    _extract_json_text,
    _normalize_parsed,
    detect_media_type,
    encode_image_base64,
    parse_ai_elements_json,
    register_provider,
    _PROVIDER_CLASSES,
    get_vision_provider,
    list_available_providers,
    _auto_detect_provider,
)
from naturo.errors import AIProviderUnavailableError


# ── VisionResult ─────────────────────────────────────────────────────────────


class TestVisionResult:
    def test_defaults(self):
        r = VisionResult(description="A dialog box")
        assert r.description == "A dialog box"
        assert r.elements == []
        assert r.raw_response is None
        assert r.model == ""
        assert r.tokens_used == 0

    def test_with_elements(self):
        elems = [{"role": "Button", "name": "OK"}]
        r = VisionResult(description="test", elements=elems, model="gpt-4o", tokens_used=150)
        assert r.elements == elems
        assert r.model == "gpt-4o"
        assert r.tokens_used == 150


# ── encode_image_base64 ─────────────────────────────────────────────────────


class TestEncodeImageBase64:
    def test_encodes_file(self, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
        result = encode_image_base64(str(img))
        assert isinstance(result, str)
        import base64
        assert base64.b64decode(result) == img.read_bytes()

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="Image not found"):
            encode_image_base64("/nonexistent/image.png")


# ── detect_media_type ────────────────────────────────────────────────────────


class TestDetectMediaType:
    @pytest.mark.parametrize(
        "path,expected",
        [
            ("screen.png", "image/png"),
            ("photo.jpg", "image/jpeg"),
            ("photo.jpeg", "image/jpeg"),
            ("anim.gif", "image/gif"),
            ("modern.webp", "image/webp"),
            ("old.bmp", "image/bmp"),
            ("CAPS.PNG", "image/png"),
            ("unknown.tiff", "image/png"),  # fallback
            ("noext", "image/png"),  # fallback
        ],
    )
    def test_media_types(self, path, expected):
        assert detect_media_type(path) == expected


# ── _extract_json_text ───────────────────────────────────────────────────────


class TestExtractJsonText:
    def test_code_fence_json(self):
        text = 'Some text\n```json\n[{"role": "Button"}]\n```\nMore text'
        assert _extract_json_text(text) == '[{"role": "Button"}]'

    def test_code_fence_no_lang(self):
        text = '```\n{"elements": []}\n```'
        assert _extract_json_text(text) == '{"elements": []}'

    def test_bare_array(self):
        text = 'Here are the elements: [{"name": "OK"}] found on screen.'
        result = _extract_json_text(text)
        assert result == '[{"name": "OK"}]'

    def test_bare_object(self):
        text = 'Result: {"role": "Button", "name": "Cancel"}'
        result = _extract_json_text(text)
        assert result == '{"role": "Button", "name": "Cancel"}'

    def test_plain_text_fallback(self):
        text = "no json here"
        assert _extract_json_text(text) == "no json here"

    def test_empty_string(self):
        assert _extract_json_text("") is None

    def test_whitespace_only(self):
        assert _extract_json_text("   ") is None


# ── _normalize_parsed ────────────────────────────────────────────────────────


class TestNormalizeParsed:
    def test_list_of_dicts(self):
        data = [{"role": "Button"}, {"role": "Edit"}]
        assert _normalize_parsed(data) == data

    def test_list_filters_non_dicts(self):
        data = [{"role": "Button"}, "not a dict", 42, {"role": "Edit"}]
        assert _normalize_parsed(data) == [{"role": "Button"}, {"role": "Edit"}]

    def test_wrapper_elements_key(self):
        data = {"elements": [{"role": "Button"}]}
        assert _normalize_parsed(data) == [{"role": "Button"}]

    def test_wrapper_items_key(self):
        data = {"items": [{"role": "Edit"}]}
        assert _normalize_parsed(data) == [{"role": "Edit"}]

    def test_wrapper_results_key(self):
        data = {"results": [{"name": "OK"}]}
        assert _normalize_parsed(data) == [{"name": "OK"}]

    def test_wrapper_found_elements_key(self):
        data = {"found_elements": [{"label": "Save"}]}
        assert _normalize_parsed(data) == [{"label": "Save"}]

    def test_single_element_dict(self):
        data = {"role": "Button", "name": "OK", "bounds": [0, 0, 100, 50]}
        assert _normalize_parsed(data) == [data]

    def test_unknown_dict(self):
        data = {"foo": "bar", "baz": 42}
        assert _normalize_parsed(data) == []

    def test_non_dict_non_list(self):
        assert _normalize_parsed("string") == []
        assert _normalize_parsed(42) == []
        assert _normalize_parsed(None) == []


# ── parse_ai_elements_json (integration of extract + normalize) ──────────────


class TestParseAiElementsJson:
    def test_empty_input(self):
        assert parse_ai_elements_json("") == []
        assert parse_ai_elements_json("   ") == []

    def test_none_like(self):
        # None is not a valid input type but empty string is
        assert parse_ai_elements_json("") == []

    def test_valid_array(self):
        text = '[{"role": "Button", "name": "OK"}]'
        result = parse_ai_elements_json(text)
        assert len(result) == 1
        assert result[0]["name"] == "OK"

    def test_code_fence_array(self):
        text = '```json\n[{"role": "Edit", "name": "Search"}]\n```'
        result = parse_ai_elements_json(text)
        assert len(result) == 1
        assert result[0]["role"] == "Edit"

    def test_wrapper_object(self):
        text = '{"elements": [{"role": "Button"}]}'
        result = parse_ai_elements_json(text)
        assert len(result) == 1

    def test_invalid_json(self):
        text = "this is not json at all {{{["
        assert parse_ai_elements_json(text) == []

    def test_prose_around_json(self):
        text = 'I found these elements:\n[{"role": "Button", "name": "Submit"}]\nThat is all.'
        result = parse_ai_elements_json(text)
        assert len(result) == 1
        assert result[0]["name"] == "Submit"


# ── Provider Registry ────────────────────────────────────────────────────────


class _FakeProvider:
    """Minimal provider for testing registry."""

    def __init__(self, available=True):
        self._available = available

    @property
    def name(self):
        return "fake"

    @property
    def is_available(self):
        return self._available

    def describe_screenshot(self, image_path, **kwargs):
        return VisionResult(description="fake")

    def identify_element(self, image_path, element_description, **kwargs):
        return VisionResult(description="fake element")


class TestProviderRegistry:
    def setup_method(self):
        self._original = dict(_PROVIDER_CLASSES)

    def teardown_method(self):
        _PROVIDER_CLASSES.clear()
        _PROVIDER_CLASSES.update(self._original)

    def test_register_and_get(self):
        register_provider("fake", _FakeProvider)
        with patch("naturo.providers.base._ensure_providers_registered"):
            provider = get_vision_provider("fake")
        assert provider.name == "fake"

    def test_get_unknown_provider(self):
        with patch("naturo.providers.base._ensure_providers_registered"):
            with pytest.raises(AIProviderUnavailableError):
                get_vision_provider("nonexistent")

    def test_get_unavailable_provider(self):
        register_provider("fake_off", lambda **kw: _FakeProvider(available=False))
        with patch("naturo.providers.base._ensure_providers_registered"):
            with pytest.raises(AIProviderUnavailableError):
                get_vision_provider("fake_off")

    def test_auto_detect_picks_first_available(self):
        register_provider("fake_a", lambda **kw: _FakeProvider(available=False))
        register_provider("fake_b", _FakeProvider)
        # auto_detect tries priority list, but our fakes aren't in it,
        # so test directly
        _PROVIDER_CLASSES.clear()
        _PROVIDER_CLASSES["anthropic"] = lambda **kw: _FakeProvider(available=False)
        _PROVIDER_CLASSES["openai"] = _FakeProvider
        provider = _auto_detect_provider()
        assert provider.is_available

    def test_auto_detect_no_providers(self):
        _PROVIDER_CLASSES.clear()
        with pytest.raises(AIProviderUnavailableError):
            _auto_detect_provider()

    def test_list_available_providers_none(self):
        _PROVIDER_CLASSES.clear()
        with patch("naturo.providers.base._ensure_providers_registered"):
            result = list_available_providers()
        assert result == []

    def test_list_available_providers_mixed(self):
        _PROVIDER_CLASSES.clear()
        _PROVIDER_CLASSES["avail"] = _FakeProvider
        _PROVIDER_CLASSES["unavail"] = lambda: _FakeProvider(available=False)
        with patch("naturo.providers.base._ensure_providers_registered"):
            result = list_available_providers()
        assert "avail" in result
        assert "unavail" not in result
