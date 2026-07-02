"""Tests for type_text handling of newline characters (#840).

Verifies that newlines in text are converted to Enter keypresses instead
of being silently dropped by the native DLL.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest


@pytest.fixture
def mock_strategy():
    """Create a mock InputStrategy."""
    s = MagicMock()
    s.type_text = MagicMock()
    s.press_key = MagicMock()
    return s


@pytest.fixture
def backend(mock_strategy):
    """Create an InputMixin with a mocked strategy."""
    from naturo.backends.windows._input import InputMixin

    class FakeBackend(InputMixin):
        def _ensure_core(self):
            return MagicMock()

    b = FakeBackend()
    return b


class TestTypeTextNewlines:
    """Newlines should be converted to Enter keypresses (#840)."""

    def test_newline_splits_into_enter(self, backend, mock_strategy):
        """'hello\\nworld' should type 'hello', press Enter, type 'world'."""
        with patch("naturo.backends.windows._input._keyboard.get_input_strategy",
                    return_value=mock_strategy):
            backend.type_text("hello\nworld")

        assert mock_strategy.type_text.call_count == 2
        mock_strategy.type_text.assert_any_call("hello", 5)
        mock_strategy.type_text.assert_any_call("world", 5)
        mock_strategy.press_key.assert_called_once_with("enter")

    def test_multiple_newlines(self, backend, mock_strategy):
        """'a\\nb\\nc' should produce 3 segments with 2 Enter presses."""
        with patch("naturo.backends.windows._input._keyboard.get_input_strategy",
                    return_value=mock_strategy):
            backend.type_text("a\nb\nc")

        assert mock_strategy.type_text.call_count == 3
        assert mock_strategy.press_key.call_count == 2

    def test_trailing_newline(self, backend, mock_strategy):
        """'hello\\n' should type 'hello' then press Enter."""
        with patch("naturo.backends.windows._input._keyboard.get_input_strategy",
                    return_value=mock_strategy):
            backend.type_text("hello\n")

        mock_strategy.type_text.assert_called_once_with("hello", 5)
        mock_strategy.press_key.assert_called_once_with("enter")

    def test_leading_newline(self, backend, mock_strategy):
        """'\\nhello' should press Enter then type 'hello'."""
        with patch("naturo.backends.windows._input._keyboard.get_input_strategy",
                    return_value=mock_strategy):
            backend.type_text("\nhello")

        mock_strategy.type_text.assert_called_once_with("hello", 5)
        mock_strategy.press_key.assert_called_once_with("enter")

    def test_crlf_normalized(self, backend, mock_strategy):
        """Windows-style \\r\\n should be treated as a single newline."""
        with patch("naturo.backends.windows._input._keyboard.get_input_strategy",
                    return_value=mock_strategy):
            backend.type_text("hello\r\nworld")

        assert mock_strategy.type_text.call_count == 2
        mock_strategy.press_key.assert_called_once_with("enter")

    def test_bare_cr_normalized(self, backend, mock_strategy):
        """Bare \\r should be treated as a newline."""
        with patch("naturo.backends.windows._input._keyboard.get_input_strategy",
                    return_value=mock_strategy):
            backend.type_text("hello\rworld")

        assert mock_strategy.type_text.call_count == 2
        mock_strategy.press_key.assert_called_once_with("enter")

    def test_no_newline_passes_through(self, backend, mock_strategy):
        """Text without newlines should be passed directly to strategy."""
        with patch("naturo.backends.windows._input._keyboard.get_input_strategy",
                    return_value=mock_strategy):
            backend.type_text("hello world")

        mock_strategy.type_text.assert_called_once_with("hello world", 5)
        mock_strategy.press_key.assert_not_called()

    def test_only_newlines(self, backend, mock_strategy):
        """'\\n\\n' should press Enter twice with no type_text calls."""
        with patch("naturo.backends.windows._input._keyboard.get_input_strategy",
                    return_value=mock_strategy):
            backend.type_text("\n\n")

        mock_strategy.type_text.assert_not_called()
        assert mock_strategy.press_key.call_count == 2
