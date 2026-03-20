"""Tests for naturo.vision and naturo.providers.

Covers:
- Provider base: registry, factory, auto-detection, helper functions
- AnthropicVisionProvider: describe_screenshot, identify_element
- OpenAIVisionProvider: describe_screenshot, identify_element
- OllamaVisionProvider: describe_screenshot, identify_element
- Vision API: describe_screen, identify_element orchestration
- CLI: naturo describe command
- MCP: describe_screen, identify_element tools
"""
import json
import os
import tempfile
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from naturo.providers.base import (
    VisionResult,
    encode_image_base64,
    detect_media_type,
    get_vision_provider,
    list_available_providers,
    register_provider,
    _PROVIDER_CLASSES,
)
from naturo.errors import AIProviderUnavailableError, AIAnalysisFailedError


# ── Fixtures ────────────────────────────────────


@pytest.fixture
def fake_image(tmp_path):
    """Create a minimal PNG file for testing."""
    # Minimal valid PNG (1x1 transparent pixel)
    png_data = (
        b'\x89PNG\r\n\x1a\n'  # PNG signature
        b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx'
        b'\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00'
        b'\x00\x00\x00IEND\xaeB`\x82'
    )
    path = tmp_path / "test_screenshot.png"
    path.write_bytes(png_data)
    return str(path)


@pytest.fixture
def fake_jpg(tmp_path):
    """Create a minimal JPEG file for testing."""
    # Minimal valid JPEG
    jpg_data = (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01'
        b'\x00\x01\x00\x00\xff\xd9'
    )
    path = tmp_path / "test_screenshot.jpg"
    path.write_bytes(jpg_data)
    return str(path)


# ── Provider Base Tests ─────────────────────────


class TestDetectMediaType:
    """Test MIME type detection."""

    def test_png(self):
        assert detect_media_type("test.png") == "image/png"

    def test_jpg(self):
        assert detect_media_type("test.jpg") == "image/jpeg"

    def test_jpeg(self):
        assert detect_media_type("test.jpeg") == "image/jpeg"

    def test_webp(self):
        assert detect_media_type("test.webp") == "image/webp"

    def test_bmp(self):
        assert detect_media_type("test.bmp") == "image/bmp"

    def test_gif(self):
        assert detect_media_type("test.gif") == "image/gif"

    def test_unknown_defaults_to_png(self):
        assert detect_media_type("test.tiff") == "image/png"


class TestEncodeImageBase64:
    """Test image base64 encoding."""

    def test_encode_existing_file(self, fake_image):
        result = encode_image_base64(fake_image)
        assert isinstance(result, str)
        assert len(result) > 0
        # Should be valid base64
        import base64
        decoded = base64.b64decode(result)
        assert decoded[:4] == b'\x89PNG'

    def test_encode_nonexistent_file(self):
        with pytest.raises(FileNotFoundError, match="Image not found"):
            encode_image_base64("/nonexistent/path/image.png")


class TestProviderRegistry:
    """Test provider registration and factory."""

    def test_register_and_get(self):
        """Register a mock provider and retrieve it."""
        class MockProvider:
            def __init__(self, **kw):
                pass
            @property
            def name(self):
                return "mock_test"
            @property
            def is_available(self):
                return True
            def describe_screenshot(self, *a, **kw):
                return VisionResult(description="mock")
            def identify_element(self, *a, **kw):
                return VisionResult(description="mock")

        register_provider("mock_test", MockProvider)
        try:
            provider = get_vision_provider("mock_test")
            assert provider.name == "mock_test"
            assert provider.is_available
        finally:
            _PROVIDER_CLASSES.pop("mock_test", None)

    def test_get_nonexistent_provider(self):
        with pytest.raises(AIProviderUnavailableError):
            get_vision_provider("nonexistent_provider_xyz")

    def test_get_unavailable_provider(self):
        """Provider exists but is_available returns False."""
        class UnavailableProvider:
            def __init__(self, **kw):
                pass
            @property
            def name(self):
                return "unavail"
            @property
            def is_available(self):
                return False
            def describe_screenshot(self, *a, **kw):
                pass
            def identify_element(self, *a, **kw):
                pass

        register_provider("unavail_test", UnavailableProvider)
        try:
            with pytest.raises(AIProviderUnavailableError):
                get_vision_provider("unavail_test")
        finally:
            _PROVIDER_CLASSES.pop("unavail_test", None)


class TestListAvailableProviders:
    """Test listing available providers."""

    def test_returns_list(self):
        result = list_available_providers()
        assert isinstance(result, list)


# ── Anthropic Provider Tests ────────────────────


class TestAnthropicProvider:
    """Test AnthropicVisionProvider with mocked API."""

    def test_name(self):
        from naturo.providers.anthropic_provider import AnthropicVisionProvider
        p = AnthropicVisionProvider(api_key="test-key")
        assert p.name == "anthropic"

    def test_is_available_with_key(self):
        from naturo.providers.anthropic_provider import AnthropicVisionProvider
        p = AnthropicVisionProvider(api_key="test-key")
        assert p.is_available is True

    def test_is_unavailable_without_key(self):
        from naturo.providers.anthropic_provider import AnthropicVisionProvider
        with patch.dict(os.environ, {}, clear=True):
            # Remove env var if present
            env = dict(os.environ)
            env.pop("ANTHROPIC_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                p = AnthropicVisionProvider(api_key="")
                assert p.is_available is False

    def test_describe_screenshot_no_key(self, fake_image):
        from naturo.providers.anthropic_provider import AnthropicVisionProvider
        p = AnthropicVisionProvider(api_key="")
        with pytest.raises(AIProviderUnavailableError):
            p.describe_screenshot(fake_image)

    def test_describe_screenshot_success(self, fake_image):
        from naturo.providers.anthropic_provider import AnthropicVisionProvider

        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.text = "This is a Notepad window with an empty document."
        mock_response.content = [mock_block]
        mock_response.usage = MagicMock(input_tokens=500, output_tokens=50)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        p = AnthropicVisionProvider(api_key="test-key")
        with patch.object(p, "_get_client", return_value=mock_client):
            result = p.describe_screenshot(fake_image)

        assert isinstance(result, VisionResult)
        assert "Notepad" in result.description
        assert result.tokens_used == 550
        assert result.model

    def test_describe_screenshot_with_context(self, fake_image):
        from naturo.providers.anthropic_provider import AnthropicVisionProvider

        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.text = "Analysis with context."
        mock_response.content = [mock_block]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=20)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        p = AnthropicVisionProvider(api_key="test-key")
        with patch.object(p, "_get_client", return_value=mock_client):
            result = p.describe_screenshot(fake_image, context="Testing context")

        # Verify context was included in the prompt
        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        text_content = [c for c in messages[0]["content"] if c["type"] == "text"]
        assert "Testing context" in text_content[0]["text"]

    def test_describe_screenshot_api_error(self, fake_image):
        from naturo.providers.anthropic_provider import AnthropicVisionProvider

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API rate limit")

        p = AnthropicVisionProvider(api_key="test-key")
        with patch.object(p, "_get_client", return_value=mock_client):
            with pytest.raises(AIAnalysisFailedError, match="API rate limit"):
                p.describe_screenshot(fake_image)

    def test_identify_element_success(self, fake_image):
        from naturo.providers.anthropic_provider import AnthropicVisionProvider

        json_response = json.dumps({
            "found": True,
            "description": "Save button in toolbar",
            "bounds": {"x": 150, "y": 50, "width": 80, "height": 30},
            "confidence": 0.95,
        })

        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.text = json_response
        mock_response.content = [mock_block]
        mock_response.usage = MagicMock(input_tokens=500, output_tokens=80)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        p = AnthropicVisionProvider(api_key="test-key")
        with patch.object(p, "_get_client", return_value=mock_client):
            result = p.identify_element(fake_image, "the Save button")

        assert len(result.elements) == 1
        assert result.elements[0]["found"] is True
        assert result.elements[0]["confidence"] == 0.95

    def test_identify_element_json_in_code_fence(self, fake_image):
        from naturo.providers.anthropic_provider import AnthropicVisionProvider

        response_text = '```json\n{"found": false, "description": "Not visible", "bounds": {}, "confidence": 0.1}\n```'

        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.text = response_text
        mock_response.content = [mock_block]
        mock_response.usage = MagicMock(input_tokens=500, output_tokens=80)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        p = AnthropicVisionProvider(api_key="test-key")
        with patch.object(p, "_get_client", return_value=mock_client):
            result = p.identify_element(fake_image, "nonexistent element")

        assert len(result.elements) == 1
        assert result.elements[0]["found"] is False


# ── OpenAI Provider Tests ───────────────────────


class TestOpenAIProvider:
    """Test OpenAIVisionProvider with mocked API."""

    def test_name(self):
        from naturo.providers.openai_provider import OpenAIVisionProvider
        p = OpenAIVisionProvider(api_key="test-key")
        assert p.name == "openai"

    def test_is_available_with_key(self):
        from naturo.providers.openai_provider import OpenAIVisionProvider
        p = OpenAIVisionProvider(api_key="test-key")
        assert p.is_available is True

    def test_is_unavailable_without_key(self):
        from naturo.providers.openai_provider import OpenAIVisionProvider
        with patch.dict(os.environ, {}, clear=True):
            env = dict(os.environ)
            env.pop("OPENAI_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                p = OpenAIVisionProvider(api_key="")
                assert p.is_available is False

    def test_describe_screenshot_success(self, fake_image):
        from naturo.providers.openai_provider import OpenAIVisionProvider

        mock_message = MagicMock()
        mock_message.content = "This is a calculator application."
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(prompt_tokens=400, completion_tokens=30)

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        p = OpenAIVisionProvider(api_key="test-key")
        with patch.object(p, "_get_client", return_value=mock_client):
            result = p.describe_screenshot(fake_image)

        assert "calculator" in result.description.lower()
        assert result.tokens_used == 430

    def test_describe_screenshot_no_key(self, fake_image):
        from naturo.providers.openai_provider import OpenAIVisionProvider
        p = OpenAIVisionProvider(api_key="")
        with pytest.raises(AIProviderUnavailableError):
            p.describe_screenshot(fake_image)

    def test_identify_element_success(self, fake_image):
        from naturo.providers.openai_provider import OpenAIVisionProvider

        json_response = json.dumps({
            "found": True,
            "description": "Close button (X)",
            "bounds": {"x": 780, "y": 10, "width": 40, "height": 30},
            "confidence": 0.9,
        })

        mock_message = MagicMock()
        mock_message.content = json_response
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(prompt_tokens=400, completion_tokens=60)

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        p = OpenAIVisionProvider(api_key="test-key")
        with patch.object(p, "_get_client", return_value=mock_client):
            result = p.identify_element(fake_image, "the close button")

        assert len(result.elements) == 1
        assert result.elements[0]["found"] is True


# ── Ollama Provider Tests ───────────────────────


class TestOllamaProvider:
    """Test OllamaVisionProvider with mocked HTTP."""

    def test_name(self):
        from naturo.providers.ollama_provider import OllamaVisionProvider
        p = OllamaVisionProvider()
        assert p.name == "ollama"

    def test_is_available_mock_running(self):
        from naturo.providers.ollama_provider import OllamaVisionProvider
        p = OllamaVisionProvider()

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert p.is_available is True

    def test_is_unavailable_not_running(self):
        from naturo.providers.ollama_provider import OllamaVisionProvider
        p = OllamaVisionProvider()

        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            assert p.is_available is False

    def test_describe_screenshot_success(self, fake_image):
        from naturo.providers.ollama_provider import OllamaVisionProvider

        response_data = json.dumps({
            "response": "This shows a text editor with some code.",
            "eval_count": 30,
            "prompt_eval_count": 200,
        }).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        p = OllamaVisionProvider()
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = p.describe_screenshot(fake_image)

        assert "text editor" in result.description.lower()
        assert result.tokens_used == 230


# ── Vision API Tests ────────────────────────────


class TestDescribeScreen:
    """Test the high-level describe_screen function."""

    def test_with_existing_screenshot(self, fake_image):
        """describe_screen with screenshot_path should not capture."""
        from naturo.vision import describe_screen

        mock_provider = MagicMock()
        mock_provider.describe_screenshot.return_value = VisionResult(
            description="Test description",
            model="test-model",
            tokens_used=100,
        )

        result = describe_screen(
            provider=mock_provider,
            screenshot_path=fake_image,
        )

        assert result.description == "Test description"
        mock_provider.describe_screenshot.assert_called_once()
        # Verify it passed the screenshot path
        call_args = mock_provider.describe_screenshot.call_args
        assert call_args[0][0] == fake_image

    def test_with_custom_prompt(self, fake_image):
        """Custom prompt is forwarded to provider."""
        from naturo.vision import describe_screen

        mock_provider = MagicMock()
        mock_provider.describe_screenshot.return_value = VisionResult(
            description="Custom analysis",
            model="test-model",
            tokens_used=100,
        )

        describe_screen(
            provider=mock_provider,
            screenshot_path=fake_image,
            prompt="Count the buttons",
        )

        call_kwargs = mock_provider.describe_screenshot.call_args.kwargs
        assert call_kwargs["prompt"] == "Count the buttons"


class TestIdentifyElement:
    """Test the high-level identify_element function."""

    def test_with_existing_screenshot(self, fake_image):
        from naturo.vision import identify_element

        mock_provider = MagicMock()
        mock_provider.identify_element.return_value = VisionResult(
            description='{"found": true}',
            elements=[{"found": True, "bounds": {"x": 100, "y": 50}}],
            model="test-model",
            tokens_used=80,
        )

        result = identify_element(
            "the Save button",
            provider=mock_provider,
            screenshot_path=fake_image,
        )

        assert len(result.elements) == 1
        assert result.elements[0]["found"] is True


# ── CLI Tests ───────────────────────────────────


class TestDescribeCLI:
    """Test the 'naturo describe' CLI command."""

    def test_describe_help(self):
        from click.testing import CliRunner
        from naturo.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["describe", "--help"])
        assert result.exit_code == 0
        assert "Describe the screen" in result.output
        assert "--provider" in result.output
        assert "--screenshot" in result.output

    def test_describe_nonexistent_screenshot(self):
        from click.testing import CliRunner
        from naturo.cli import main

        runner = CliRunner()
        result = runner.invoke(main, [
            "describe", "--screenshot", "/nonexistent/image.png",
            "--provider", "anthropic",
        ])
        assert result.exit_code != 0

    def test_describe_nonexistent_screenshot_json(self):
        from click.testing import CliRunner
        from naturo.cli import main

        mock_provider = MagicMock()
        mock_provider.is_available = True

        with patch("naturo.providers.base.get_vision_provider", return_value=mock_provider):
            runner = CliRunner()
            result = runner.invoke(main, [
                "describe", "--screenshot", "/nonexistent/image.png",
                "--provider", "anthropic", "--json",
            ])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert "FILE_NOT_FOUND" in data["error"]["code"]

    def test_describe_no_provider_available_json(self):
        from click.testing import CliRunner
        from naturo.cli import main

        runner = CliRunner()
        # auto-detect with no API keys set should fail
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
        }, clear=False):
            result = runner.invoke(main, [
                "describe", "--screenshot", "dummy.png",
                "--provider", "anthropic", "--json",
            ])
        # Should fail with provider unavailable
        assert result.exit_code != 0

    def test_describe_success_json(self, fake_image):
        from click.testing import CliRunner
        from naturo.cli import main

        mock_result = VisionResult(
            description="A calculator window showing 42.",
            model="claude-sonnet-4-20250514",
            tokens_used=200,
        )

        mock_provider = MagicMock()

        with patch("naturo.providers.base.get_vision_provider", return_value=mock_provider), \
             patch("naturo.vision.describe_screen", return_value=mock_result) as mock_describe:

            runner = CliRunner()
            result = runner.invoke(main, [
                "describe", "--screenshot", fake_image, "--json",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "calculator" in data["description"].lower()
        assert data["model"] == "claude-sonnet-4-20250514"
        assert data["tokens_used"] == 200

    def test_describe_success_text(self, fake_image):
        from click.testing import CliRunner
        from naturo.cli import main

        mock_result = VisionResult(
            description="A Notepad window with hello world.",
            model="gpt-4o",
            tokens_used=150,
        )

        mock_provider = MagicMock()

        with patch("naturo.providers.base.get_vision_provider", return_value=mock_provider), \
             patch("naturo.vision.describe_screen", return_value=mock_result):

            runner = CliRunner()
            result = runner.invoke(main, [
                "describe", "--screenshot", fake_image,
            ])

        assert result.exit_code == 0
        assert "Notepad" in result.output


# ── VisionResult Tests ──────────────────────────


class TestVisionResult:
    """Test VisionResult dataclass."""

    def test_basic_creation(self):
        r = VisionResult(description="test")
        assert r.description == "test"
        assert r.elements == []
        assert r.model == ""
        assert r.tokens_used == 0

    def test_with_elements(self):
        r = VisionResult(
            description="Found it",
            elements=[{"found": True, "bounds": {"x": 10, "y": 20}}],
            model="claude-sonnet-4-20250514",
            tokens_used=100,
        )
        assert len(r.elements) == 1
        assert r.elements[0]["found"] is True
        assert r.model == "claude-sonnet-4-20250514"
