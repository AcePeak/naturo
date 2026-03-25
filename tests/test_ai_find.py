"""Tests for naturo.ai_find — AI-powered natural language element finding.

Covers:
- AIFindResult dataclass
- ai_find_element with mocked vision provider
- UIA refinement matching logic
- CLI: naturo find --ai
- MCP: ai_find_element tool
- Edge cases: no elements found, invalid bounds, non-Windows platform
"""
import json
import os
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from naturo.ai_find import AIFindResult, ai_find_element, _has_valid_coords, _match_uia_element
from naturo.providers.base import VisionResult


# ── Fixtures ────────────────────────────────────


@pytest.fixture
def fake_image(tmp_path):
    """Create a minimal PNG file for testing."""
    png_data = (
        b'\x89PNG\r\n\x1a\n'
        b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx'
        b'\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00'
        b'\x00\x00\x00IEND\xaeB`\x82'
    )
    path = tmp_path / "test_screenshot.png"
    path.write_bytes(png_data)
    return str(path)


@pytest.fixture
def mock_vision_provider():
    """Create a mock vision provider."""
    provider = MagicMock()
    provider.name = "mock"
    provider.is_available = True
    return provider


# ── AIFindResult Tests ──────────────────────────


class TestAIFindResult:
    """Test AIFindResult dataclass."""

    def test_basic_creation(self):
        r = AIFindResult(found=True, description="Save button")
        assert r.found is True
        assert r.description == "Save button"
        assert r.ai_bounds is None
        assert r.element is None
        assert r.confidence == 0.0
        assert r.method == "ai_only"

    def test_full_creation(self):
        r = AIFindResult(
            found=True,
            description="Save button in toolbar",
            ai_bounds={"x": 150, "y": 50, "width": 80, "height": 30},
            element={"id": "el_1", "role": "Button", "name": "Save"},
            confidence=0.95,
            model="claude-sonnet-4-20250514",
            tokens_used=400,
            method="ai+uia",
        )
        assert r.confidence == 0.95
        assert r.method == "ai+uia"
        assert r.element["role"] == "Button"

    def test_not_found(self):
        r = AIFindResult(found=False)
        assert r.found is False
        assert r.description == ""


# ── _has_valid_coords Tests ─────────────────────


class TestHasValidCoords:
    """Test bounds validation helper."""

    def test_valid_coords(self):
        assert _has_valid_coords({"x": 100, "y": 200}) is True

    def test_valid_float_coords(self):
        assert _has_valid_coords({"x": 100.5, "y": 200.3}) is True

    def test_missing_x(self):
        assert _has_valid_coords({"y": 200}) is False

    def test_missing_y(self):
        assert _has_valid_coords({"x": 100}) is False

    def test_empty_dict(self):
        assert _has_valid_coords({}) is False

    def test_none_values(self):
        assert _has_valid_coords({"x": None, "y": None}) is False

    def test_string_values(self):
        assert _has_valid_coords({"x": "100", "y": "200"}) is False

    def test_zero_coords(self):
        assert _has_valid_coords({"x": 0, "y": 0}) is True


# ── ai_find_element Tests ──────────────────────


class TestAiFindElement:
    """Test the main ai_find_element function."""

    def test_element_found(self, mock_vision_provider, fake_image):
        """AI finds the element successfully."""
        mock_vision_provider.identify_element.return_value = VisionResult(
            description='{"found": true, "description": "Save button", "bounds": {"x": 150, "y": 50, "width": 80, "height": 30}, "confidence": 0.95}',
            elements=[{
                "found": True,
                "description": "Save button in toolbar",
                "bounds": {"x": 150, "y": 50, "width": 80, "height": 30},
                "confidence": 0.95,
            }],
            model="claude-sonnet-4-20250514",
            tokens_used=400,
        )

        result = ai_find_element(
            "the Save button",
            provider=mock_vision_provider,
            screenshot_path=fake_image,
            refine_with_uia=False,  # Skip UIA on macOS test
        )

        assert result.found is True
        assert result.confidence == 0.95
        assert result.ai_bounds == {"x": 150, "y": 50, "width": 80, "height": 30}
        assert result.method == "ai_only"

    def test_element_not_found(self, mock_vision_provider, fake_image):
        """AI doesn't find the element."""
        mock_vision_provider.identify_element.return_value = VisionResult(
            description='{"found": false, "description": "Not visible", "bounds": {}, "confidence": 0.1}',
            elements=[{
                "found": False,
                "description": "Element not visible on screen",
                "bounds": {},
                "confidence": 0.1,
            }],
            model="gpt-4o",
            tokens_used=300,
        )

        result = ai_find_element(
            "the delete button",
            provider=mock_vision_provider,
            screenshot_path=fake_image,
        )

        assert result.found is False
        assert result.confidence == 0.1

    def test_no_elements_in_response(self, mock_vision_provider, fake_image):
        """AI returns a response but no structured elements."""
        mock_vision_provider.identify_element.return_value = VisionResult(
            description="I cannot identify any elements in this image.",
            elements=[],
            model="llava",
            tokens_used=100,
        )

        result = ai_find_element(
            "something",
            provider=mock_vision_provider,
            screenshot_path=fake_image,
        )

        assert result.found is False

    def test_auto_provider_selection(self, fake_image):
        """Provider auto-selection is invoked when no provider given."""
        mock_provider = MagicMock()
        mock_provider.identify_element.return_value = VisionResult(
            description="test",
            elements=[{"found": True, "description": "btn", "bounds": {"x": 10, "y": 20}, "confidence": 0.8}],
            model="test",
            tokens_used=50,
        )

        with patch("naturo.ai_find.get_vision_provider", return_value=mock_provider) as mock_get:
            result = ai_find_element(
                "button",
                provider_name="openai",
                screenshot_path=fake_image,
                refine_with_uia=False,
            )
            mock_get.assert_called_once_with("openai")
            assert result.found is True

    def test_uia_refinement_on_windows(self, mock_vision_provider, fake_image):
        """UIA refinement is attempted when refine_with_uia=True."""
        mock_vision_provider.identify_element.return_value = VisionResult(
            description="found",
            elements=[{
                "found": True,
                "description": "OK button",
                "bounds": {"x": 300, "y": 400, "width": 80, "height": 30},
                "confidence": 0.9,
            }],
            model="test",
            tokens_used=200,
        )

        fake_element = {"id": "el_5", "role": "Button", "name": "OK", "bounds": {"x": 290, "y": 395, "width": 80, "height": 30}}

        with patch("naturo.ai_find._match_uia_element", return_value=fake_element):
            result = ai_find_element(
                "OK button",
                provider=mock_vision_provider,
                screenshot_path=fake_image,
                refine_with_uia=True,
            )

        assert result.method == "ai+uia"
        assert result.element is not None
        assert result.element["name"] == "OK"

    def test_uia_refinement_failure_graceful(self, mock_vision_provider, fake_image):
        """UIA refinement failure doesn't break the result."""
        mock_vision_provider.identify_element.return_value = VisionResult(
            description="found",
            elements=[{
                "found": True,
                "description": "Close button",
                "bounds": {"x": 780, "y": 10, "width": 40, "height": 30},
                "confidence": 0.85,
            }],
            model="test",
            tokens_used=200,
        )

        with patch("naturo.ai_find._match_uia_element", side_effect=Exception("UIA failed")):
            result = ai_find_element(
                "close button",
                provider=mock_vision_provider,
                screenshot_path=fake_image,
                refine_with_uia=True,
            )

        # Should still succeed with ai_only
        assert result.found is True
        assert result.method == "ai_only"


# ── _match_uia_element Tests ───────────────────


class TestMatchUIAElement:
    """Test UIA tree matching (mocked on non-Windows)."""

    def test_non_windows_returns_none(self):
        """On non-Windows, always returns None."""
        import platform
        if platform.system() != "Windows":
            result = _match_uia_element({"x": 100, "y": 200})
            assert result is None
        else:
            # On Windows, we'd need a real UIA tree — skip
            pytest.skip("Windows-specific test")


# ── CLI Tests ───────────────────────────────────


class TestFindAICLI:
    """Test the 'naturo find --ai' CLI command."""

    def test_find_ai_help(self):
        from click.testing import CliRunner
        from naturo.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["find", "--help"])
        assert result.exit_code == 0
        assert "--ai" in result.output
        assert "AI vision" in result.output

    def test_find_ai_success_json(self, fake_image):
        from click.testing import CliRunner
        from naturo.cli import main

        mock_result = AIFindResult(
            found=True,
            description="Save button in the toolbar",
            ai_bounds={"x": 150, "y": 50, "width": 80, "height": 30},
            confidence=0.92,
            model="claude-sonnet-4-20250514",
            tokens_used=350,
            method="ai_only",
        )

        with patch("naturo.ai_find.ai_find_element", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(main, [
                "find", "the Save button", "--ai",
                "--screenshot", fake_image, "--json",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["confidence"] == 0.92
        assert data["method"] == "ai_only"
        assert "ai_bounds" in data

    def test_find_ai_not_found_json(self, fake_image):
        from click.testing import CliRunner
        from naturo.cli import main

        mock_result = AIFindResult(
            found=False,
            description="Element not visible on screen",
            confidence=0.1,
            model="gpt-4o",
            tokens_used=200,
            method="ai_only",
        )

        with patch("naturo.ai_find.ai_find_element", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(main, [
                "find", "nonexistent widget", "--ai",
                "--screenshot", fake_image, "--json",
            ])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "ELEMENT_NOT_FOUND"

    def test_find_ai_success_text(self, fake_image):
        from click.testing import CliRunner
        from naturo.cli import main

        mock_result = AIFindResult(
            found=True,
            description="Save button in toolbar",
            ai_bounds={"x": 150, "y": 50, "width": 80, "height": 30},
            confidence=0.95,
            model="claude-sonnet-4-20250514",
            tokens_used=400,
            method="ai_only",
        )

        with patch("naturo.ai_find.ai_find_element", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(main, [
                "find", "the Save button", "--ai",
                "--screenshot", fake_image,
            ])

        assert result.exit_code == 0
        assert "Found:" in result.output
        assert "95%" in result.output

    def test_find_ai_with_uia_match_json(self, fake_image):
        from click.testing import CliRunner
        from naturo.cli import main

        mock_result = AIFindResult(
            found=True,
            description="OK button",
            ai_bounds={"x": 300, "y": 400, "width": 80, "height": 30},
            element={
                "id": "el_5",
                "role": "Button",
                "name": "OK",
                "bounds": {"x": 290, "y": 395, "width": 80, "height": 30},
                "match_distance": 12.1,
            },
            confidence=0.9,
            model="test",
            tokens_used=200,
            method="ai+uia",
        )

        with patch("naturo.ai_find.ai_find_element", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(main, [
                "find", "OK button", "--ai",
                "--screenshot", fake_image, "--json",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["method"] == "ai+uia"
        assert data["element"]["name"] == "OK"

    def test_find_ai_nonexistent_screenshot(self):
        from click.testing import CliRunner
        from naturo.cli import main

        runner = CliRunner()
        result = runner.invoke(main, [
            "find", "something", "--ai",
            "--screenshot", "/nonexistent/image.png", "--json",
        ])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "FILE_NOT_FOUND"

    def test_find_ai_provider_error_json(self, fake_image):
        from click.testing import CliRunner
        from naturo.cli import main

        with patch("naturo.ai_find.ai_find_element",
                    side_effect=Exception("AI provider unavailable: No API key")):
            runner = CliRunner()
            result = runner.invoke(main, [
                "find", "button", "--ai",
                "--screenshot", fake_image, "--json",
            ])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "AI_PROVIDER_UNAVAILABLE"


class TestFindAutoAIMode:
    """Issue #287: --provider or --model should auto-enable AI mode."""

    def test_provider_auto_enables_ai(self, fake_image):
        """When --provider is set to non-auto, AI mode should be auto-enabled."""
        from click.testing import CliRunner
        from naturo.cli import main

        mock_result = AIFindResult(
            found=True,
            description="Found element",
            ai_bounds={"x": 100, "y": 100, "width": 50, "height": 30},
            confidence=0.9,
            model="claude-sonnet-4-20250514",
            tokens_used=200,
            method="ai_only",
        )

        with patch("naturo.ai_find.ai_find_element", return_value=mock_result) as mock_ai:
            runner = CliRunner()
            result = runner.invoke(main, [
                "find", "公众号", "--provider", "anthropic",
                "--screenshot", fake_image, "--json",
            ])

        # AI find should have been called (auto-enabled by --provider)
        mock_ai.assert_called_once()

    def test_model_auto_enables_ai(self, fake_image):
        """When --model is set, AI mode should be auto-enabled."""
        from click.testing import CliRunner
        from naturo.cli import main

        mock_result = AIFindResult(
            found=True,
            description="Found element",
            ai_bounds={"x": 100, "y": 100, "width": 50, "height": 30},
            confidence=0.9,
            model="gpt-4o",
            tokens_used=200,
            method="ai_only",
        )

        with patch("naturo.ai_find.ai_find_element", return_value=mock_result) as mock_ai:
            runner = CliRunner()
            result = runner.invoke(main, [
                "find", "button", "--model", "gpt-4o",
                "--screenshot", fake_image, "--json",
            ])

        mock_ai.assert_called_once()

    def test_api_key_auto_enables_ai(self, fake_image):
        """When --api-key is set, AI mode should be auto-enabled."""
        from click.testing import CliRunner
        from naturo.cli import main

        mock_result = AIFindResult(
            found=True,
            description="Found element",
            ai_bounds={"x": 100, "y": 100, "width": 50, "height": 30},
            confidence=0.9,
            model="claude-sonnet-4-20250514",
            tokens_used=200,
            method="ai_only",
        )

        with patch("naturo.ai_find.ai_find_element", return_value=mock_result) as mock_ai:
            runner = CliRunner()
            result = runner.invoke(main, [
                "find", "button", "--api-key", "sk-test-123",
                "--screenshot", fake_image, "--json",
            ])

        mock_ai.assert_called_once()

    def test_provider_auto_no_false_positive(self):
        """--provider auto (default) should NOT auto-enable AI mode."""
        from click.testing import CliRunner
        from naturo.cli import main

        with patch("naturo.ai_find.ai_find_element") as mock_ai:
            runner = CliRunner()
            # Only --provider auto (the default) — should NOT trigger AI
            result = runner.invoke(main, [
                "find", "Save", "--provider", "auto",
            ])

        mock_ai.assert_not_called()


# ── MCP Tool Tests ──────────────────────────────

