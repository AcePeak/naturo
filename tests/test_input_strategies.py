"""Tests for the pluggable input strategy pattern (issue #412).

Validates:
  - InputStrategy ABC cannot be instantiated directly
  - SendInputStrategy delegates to NaturoCore virtual-key methods
  - Phys32Strategy delegates to NaturoCore scan-code methods
  - get_input_strategy factory returns correct strategy for each mode
  - InputMixin.type_text/press_key/hotkey dispatch through strategies
  - Unknown input_mode raises ValueError
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from naturo.backends.windows._strategies import (
    InputStrategy,
    Phys32Strategy,
    SendInputStrategy,
    get_input_strategy,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_core() -> MagicMock:
    """Create a mock NaturoCore with all input methods."""
    core = MagicMock()
    core.key_type.return_value = None
    core.key_press.return_value = None
    core.key_hotkey.return_value = None
    core.mouse_move.return_value = None
    core.mouse_click.return_value = None
    core.mouse_scroll.return_value = None
    core.phys_key_type.return_value = None
    core.phys_key_press.return_value = None
    core.phys_key_hotkey.return_value = None
    return core


# ── ABC Tests ────────────────────────────────────────────────────────────────


class TestInputStrategyABC:
    """InputStrategy is abstract and cannot be instantiated."""

    def test_cannot_instantiate(self):
        """Attempting to create InputStrategy directly raises TypeError."""
        with pytest.raises(TypeError):
            InputStrategy()  # type: ignore[abstract]

    def test_has_required_methods(self):
        """InputStrategy declares all five abstract methods."""
        abstracts = InputStrategy.__abstractmethods__
        assert "type_text" in abstracts
        assert "press_key" in abstracts
        assert "hotkey" in abstracts
        assert "click" in abstracts
        assert "scroll" in abstracts


# ── SendInputStrategy Tests ──────────────────────────────────────────────────


class TestSendInputStrategy:
    """SendInputStrategy delegates to NaturoCore virtual-key methods."""

    def test_type_text(self):
        core = _make_core()
        s = SendInputStrategy(core)
        s.type_text("hello", 10)
        core.key_type.assert_called_once_with("hello", 10)

    def test_type_text_default_delay(self):
        core = _make_core()
        s = SendInputStrategy(core)
        s.type_text("x")
        core.key_type.assert_called_once_with("x", 5)

    def test_press_key(self):
        core = _make_core()
        s = SendInputStrategy(core)
        s.press_key("enter")
        core.key_press.assert_called_once_with("enter")

    def test_hotkey(self):
        core = _make_core()
        s = SendInputStrategy(core)
        s.hotkey("ctrl", "c")
        core.key_hotkey.assert_called_once_with("ctrl", "c")

    def test_click(self):
        core = _make_core()
        s = SendInputStrategy(core)
        s.click(100, 200, button=1, double=True)
        core.mouse_move.assert_called_once_with(100, 200)
        core.mouse_click.assert_called_once_with(1, True)

    def test_click_defaults(self):
        core = _make_core()
        s = SendInputStrategy(core)
        s.click(50, 60)
        core.mouse_move.assert_called_once_with(50, 60)
        core.mouse_click.assert_called_once_with(0, False)

    def test_scroll(self):
        core = _make_core()
        s = SendInputStrategy(core)
        s.scroll(360, horizontal=True)
        core.mouse_scroll.assert_called_once_with(360, True)


# ── Phys32Strategy Tests ────────────────────────────────────────────────────


class TestPhys32Strategy:
    """Phys32Strategy delegates keyboard to scan-code methods, mouse to SendInput."""

    def test_type_text(self):
        core = _make_core()
        s = Phys32Strategy(core)
        s.type_text("world", 20)
        core.phys_key_type.assert_called_once_with("world", 20)
        core.key_type.assert_not_called()

    def test_press_key(self):
        core = _make_core()
        s = Phys32Strategy(core)
        s.press_key("tab")
        core.phys_key_press.assert_called_once_with("tab")
        core.key_press.assert_not_called()

    def test_hotkey(self):
        core = _make_core()
        s = Phys32Strategy(core)
        s.hotkey("ctrl", "a")
        core.phys_key_hotkey.assert_called_once_with("ctrl", "a")
        core.key_hotkey.assert_not_called()

    def test_click_uses_sendinput(self):
        """Phys32 only covers keyboard; mouse is still SendInput."""
        core = _make_core()
        s = Phys32Strategy(core)
        s.click(300, 400)
        core.mouse_move.assert_called_once_with(300, 400)
        core.mouse_click.assert_called_once_with(0, False)

    def test_scroll_uses_sendinput(self):
        """Phys32 only covers keyboard; scroll is still SendInput."""
        core = _make_core()
        s = Phys32Strategy(core)
        s.scroll(-240)
        core.mouse_scroll.assert_called_once_with(-240, False)


# ── Factory Tests ────────────────────────────────────────────────────────────


class TestGetInputStrategy:
    """get_input_strategy returns the correct strategy for each mode."""

    def test_normal_returns_sendinput(self):
        core = _make_core()
        s = get_input_strategy(core, "normal")
        assert isinstance(s, SendInputStrategy)

    def test_hardware_returns_phys32(self):
        core = _make_core()
        s = get_input_strategy(core, "hardware")
        assert isinstance(s, Phys32Strategy)

    def test_default_is_normal(self):
        core = _make_core()
        s = get_input_strategy(core)
        assert isinstance(s, SendInputStrategy)

    def test_unknown_mode_raises(self):
        core = _make_core()
        with pytest.raises(ValueError, match="Unknown input_mode"):
            get_input_strategy(core, "telekinesis")


# ── InputMixin Integration Tests ─────────────────────────────────────────────


class TestInputMixinUsesStrategy:
    """InputMixin methods dispatch through get_input_strategy."""

    def _make_backend(self) -> MagicMock:
        """Create a mock backend with _ensure_core returning a mock core."""
        from naturo.backends.windows._input import InputMixin
        backend = MagicMock(spec=InputMixin)
        backend._ensure_core = MagicMock(return_value=_make_core())
        return backend

    def test_type_text_normal_delegates_to_sendinput(self):
        core = _make_core()
        with patch(
            "naturo.backends.windows._input._keyboard.get_input_strategy"
        ) as mock_factory:
            mock_strategy = MagicMock()
            mock_factory.return_value = mock_strategy

            from naturo.backends.windows._input import InputMixin
            mixin = InputMixin.__new__(InputMixin)
            mixin._ensure_core = MagicMock(return_value=core)

            mixin.type_text("test", input_mode="normal")

            mock_factory.assert_called_once_with(core, "normal")
            mock_strategy.type_text.assert_called_once_with("test", 5)

    def test_type_text_hardware_delegates_to_phys32(self):
        core = _make_core()
        with patch(
            "naturo.backends.windows._input._keyboard.get_input_strategy"
        ) as mock_factory:
            mock_strategy = MagicMock()
            mock_factory.return_value = mock_strategy

            from naturo.backends.windows._input import InputMixin
            mixin = InputMixin.__new__(InputMixin)
            mixin._ensure_core = MagicMock(return_value=core)

            mixin.type_text("test", input_mode="hardware")

            mock_factory.assert_called_once_with(core, "hardware")
            mock_strategy.type_text.assert_called_once()

    def test_press_key_delegates_through_strategy(self):
        core = _make_core()
        with patch(
            "naturo.backends.windows._input._keyboard.get_input_strategy"
        ) as mock_factory:
            mock_strategy = MagicMock()
            mock_factory.return_value = mock_strategy

            from naturo.backends.windows._input import InputMixin
            mixin = InputMixin.__new__(InputMixin)
            mixin._ensure_core = MagicMock(return_value=core)

            mixin.press_key("enter", input_mode="normal")

            mock_factory.assert_called_once_with(core, "normal")
            mock_strategy.press_key.assert_called_once_with("enter")

    def test_hotkey_delegates_through_strategy(self):
        core = _make_core()
        with patch(
            "naturo.backends.windows._input._keyboard.get_input_strategy"
        ) as mock_factory:
            mock_strategy = MagicMock()
            mock_factory.return_value = mock_strategy

            from naturo.backends.windows._input import InputMixin
            mixin = InputMixin.__new__(InputMixin)
            mixin._ensure_core = MagicMock(return_value=core)

            mixin.hotkey("ctrl", "z", input_mode="hardware")

            mock_factory.assert_called_once_with(core, "hardware")
            mock_strategy.hotkey.assert_called_once_with("ctrl", "z")

    def test_type_text_human_profile_calculates_delay(self):
        """Human typing profile converts WPM to ms-per-char before delegating."""
        core = _make_core()
        with patch(
            "naturo.backends.windows._input._keyboard.get_input_strategy"
        ) as mock_factory:
            mock_strategy = MagicMock()
            mock_factory.return_value = mock_strategy

            from naturo.backends.windows._input import InputMixin
            mixin = InputMixin.__new__(InputMixin)
            mixin._ensure_core = MagicMock(return_value=core)

            # 60 WPM = 60000 / (60*5) = 200ms per char
            mixin.type_text("abc", profile="human", wpm=60)

            mock_strategy.type_text.assert_called_once_with("abc", 200)


# ── Newline handling (#840) ──────────────────────────────────────────────────


class TestTypeTextNewlines:
    """#840: type_text splits on newlines and presses Enter between segments."""

    @staticmethod
    def _make_mixin(mock_strategy):
        """Create an InputMixin wired to a mock strategy."""
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            core = _make_core()
            with patch(
                "naturo.backends.windows._input._keyboard.get_input_strategy",
                return_value=mock_strategy,
            ):
                from naturo.backends.windows._input import InputMixin
                mixin = InputMixin.__new__(InputMixin)
                mixin._ensure_core = MagicMock(return_value=core)
                yield mixin
        return _ctx()

    def test_no_newlines_single_call(self):
        """Text without newlines is typed in a single call."""
        mock_strategy = MagicMock()
        with self._make_mixin(mock_strategy) as mixin:
            mixin.type_text("hello world")
        mock_strategy.type_text.assert_called_once_with("hello world", 5)
        mock_strategy.press_key.assert_not_called()

    def test_lf_newline_splits_and_presses_enter(self):
        """Unix \\n is split into two type_text calls with Enter between."""
        mock_strategy = MagicMock()
        with self._make_mixin(mock_strategy) as mixin:
            mixin.type_text("line1\nline2")
        assert mock_strategy.type_text.call_count == 2
        mock_strategy.type_text.assert_any_call("line1", 5)
        mock_strategy.type_text.assert_any_call("line2", 5)
        mock_strategy.press_key.assert_called_once_with("enter")

    def test_crlf_newline(self):
        """Windows \\r\\n is treated as a single newline."""
        mock_strategy = MagicMock()
        with self._make_mixin(mock_strategy) as mixin:
            mixin.type_text("a\r\nb")
        assert mock_strategy.type_text.call_count == 2
        mock_strategy.press_key.assert_called_once_with("enter")

    def test_cr_newline(self):
        """Old Mac \\r is treated as a newline."""
        mock_strategy = MagicMock()
        with self._make_mixin(mock_strategy) as mixin:
            mixin.type_text("a\rb")
        assert mock_strategy.type_text.call_count == 2
        mock_strategy.press_key.assert_called_once_with("enter")

    def test_multiple_newlines(self):
        """Multiple newlines produce multiple Enter presses."""
        mock_strategy = MagicMock()
        with self._make_mixin(mock_strategy) as mixin:
            mixin.type_text("a\nb\nc")
        assert mock_strategy.type_text.call_count == 3
        assert mock_strategy.press_key.call_count == 2

    def test_trailing_newline(self):
        """Trailing newline produces Enter after the text."""
        mock_strategy = MagicMock()
        with self._make_mixin(mock_strategy) as mixin:
            mixin.type_text("hello\n")
        mock_strategy.type_text.assert_called_once_with("hello", 5)
        mock_strategy.press_key.assert_called_once_with("enter")

    def test_leading_newline(self):
        """Leading newline produces Enter before the text."""
        mock_strategy = MagicMock()
        with self._make_mixin(mock_strategy) as mixin:
            mixin.type_text("\nhello")
        mock_strategy.type_text.assert_called_once_with("hello", 5)
        mock_strategy.press_key.assert_called_once_with("enter")

    def test_only_newlines(self):
        """Text of only newlines produces Enter presses with no type_text calls."""
        mock_strategy = MagicMock()
        with self._make_mixin(mock_strategy) as mixin:
            mixin.type_text("\n\n")
        mock_strategy.type_text.assert_not_called()
        assert mock_strategy.press_key.call_count == 2


# ── Extensibility Tests ──────────────────────────────────────────────────────


class TestStrategyExtensibility:
    """New strategies can be created by subclassing InputStrategy."""

    def test_custom_strategy_subclass(self):
        """A third-party input strategy can be created."""

        class HookStrategy(InputStrategy):
            """Hypothetical MinHook injection strategy."""

            def __init__(self) -> None:
                self.calls: list[str] = []

            def type_text(self, text: str, delay_ms: int = 5) -> None:
                self.calls.append(f"type:{text}")

            def press_key(self, key: str) -> None:
                self.calls.append(f"press:{key}")

            def hotkey(self, *keys: str) -> None:
                self.calls.append(f"hotkey:{'+'.join(keys)}")

            def click(self, x: int, y: int, button: int = 0,
                      double: bool = False) -> None:
                self.calls.append(f"click:{x},{y}")

            def scroll(self, delta: int, horizontal: bool = False) -> None:
                self.calls.append(f"scroll:{delta}")

        s = HookStrategy()
        s.type_text("hi")
        s.press_key("enter")
        s.hotkey("ctrl", "s")
        s.click(10, 20)
        s.scroll(-120)

        assert s.calls == [
            "type:hi",
            "press:enter",
            "hotkey:ctrl+s",
            "click:10,20",
            "scroll:-120",
        ]
