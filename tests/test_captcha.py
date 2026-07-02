"""Tests for naturo.browser._captcha — captcha detection and solving."""

import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest
from click.testing import CliRunner

from naturo.browser._captcha import (
    CaptchaManager,
    CaptchaSolver,
    CaptchaError,
    ManualSolver,
    TokenInjectionSolver,
    _response_check_js,
    _inject_token_js,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_page():
    return MagicMock()


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def recaptcha_v2_info():
    return {
        "type": "recaptcha-v2",
        "sitekey": "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI",
        "element": "div.g-recaptcha",
        "visible": True,
    }


@pytest.fixture
def hcaptcha_info():
    return {
        "type": "hcaptcha",
        "sitekey": "10000000-ffff-ffff-ffff-000000000001",
        "element": "div.h-captcha",
        "visible": True,
    }


@pytest.fixture
def turnstile_info():
    return {
        "type": "turnstile",
        "sitekey": "0x4AAAAAAADnPIDROrmt1Wwj",
        "element": "div.cf-turnstile",
        "visible": True,
    }


# ── CaptchaManager.detect ────────────────────────────────────────────────────


class TestCaptchaDetect:
    """Tests for CaptchaManager.detect()."""

    def test_detect_returns_list(self, mock_page):
        mock_page.evaluate.return_value = [
            {"type": "recaptcha-v2", "sitekey": "abc", "element": "div", "visible": True}
        ]
        manager = CaptchaManager(mock_page)
        result = manager.detect()
        assert len(result) == 1
        assert result[0]["type"] == "recaptcha-v2"

    def test_detect_empty_page(self, mock_page):
        mock_page.evaluate.return_value = []
        manager = CaptchaManager(mock_page)
        assert manager.detect() == []

    def test_detect_js_error_returns_empty(self, mock_page):
        mock_page.evaluate.side_effect = Exception("JS error")
        manager = CaptchaManager(mock_page)
        assert manager.detect() == []

    def test_detect_non_list_returns_empty(self, mock_page):
        mock_page.evaluate.return_value = "not a list"
        manager = CaptchaManager(mock_page)
        assert manager.detect() == []

    def test_detect_multiple_captchas(self, mock_page):
        mock_page.evaluate.return_value = [
            {"type": "recaptcha-v2", "sitekey": "a", "element": "div", "visible": True},
            {"type": "hcaptcha", "sitekey": "b", "element": "div", "visible": True},
        ]
        manager = CaptchaManager(mock_page)
        result = manager.detect()
        assert len(result) == 2


# ── ManualSolver ──────────────────────────────────────────────────────────────


class TestManualSolver:
    """Tests for ManualSolver."""

    def test_solve_returns_token_on_first_poll(self, mock_page, recaptcha_v2_info):
        mock_page.evaluate.return_value = "03AGdBq24PBxt_long_token_string"
        solver = ManualSolver(timeout=5.0, poll_interval=0.1)
        token = solver.solve(recaptcha_v2_info, mock_page)
        assert token == "03AGdBq24PBxt_long_token_string"

    def test_solve_polls_until_found(self, mock_page, recaptcha_v2_info):
        mock_page.evaluate.side_effect = ["", "", "valid_token_12345"]
        solver = ManualSolver(timeout=5.0, poll_interval=0.01)
        token = solver.solve(recaptcha_v2_info, mock_page)
        assert token == "valid_token_12345"

    def test_solve_timeout_raises(self, mock_page, recaptcha_v2_info):
        mock_page.evaluate.return_value = ""
        solver = ManualSolver(timeout=0.1, poll_interval=0.05)
        with pytest.raises(CaptchaError, match="Timeout"):
            solver.solve(recaptcha_v2_info, mock_page)

    def test_solve_ignores_short_tokens(self, mock_page, recaptcha_v2_info):
        """Tokens shorter than 10 chars are likely noise, not real solutions."""
        mock_page.evaluate.return_value = "short"
        solver = ManualSolver(timeout=0.1, poll_interval=0.05)
        with pytest.raises(CaptchaError):
            solver.solve(recaptcha_v2_info, mock_page)


# ── TokenInjectionSolver ─────────────────────────────────────────────────────


class TestTokenInjectionSolver:
    """Tests for TokenInjectionSolver."""

    def test_inject_recaptcha(self, mock_page, recaptcha_v2_info):
        solver = TokenInjectionSolver(token="test_token_abc")
        result = solver.solve(recaptcha_v2_info, mock_page)
        assert result == "test_token_abc"
        mock_page.evaluate.assert_called_once()

    def test_inject_hcaptcha(self, mock_page, hcaptcha_info):
        solver = TokenInjectionSolver(token="hcaptcha_token")
        result = solver.solve(hcaptcha_info, mock_page)
        assert result == "hcaptcha_token"

    def test_inject_turnstile(self, mock_page, turnstile_info):
        solver = TokenInjectionSolver(token="turnstile_token")
        result = solver.solve(turnstile_info, mock_page)
        assert result == "turnstile_token"

    def test_inject_generic(self, mock_page):
        info = {"type": "generic-iframe", "sitekey": "", "element": "iframe"}
        solver = TokenInjectionSolver(token="generic_token")
        result = solver.solve(info, mock_page)
        assert result == "generic_token"

    def test_empty_token_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            TokenInjectionSolver(token="")

    def test_token_with_special_chars(self, mock_page, recaptcha_v2_info):
        """Tokens with quotes and backslashes should be escaped safely."""
        solver = TokenInjectionSolver(token="token'with\\special")
        result = solver.solve(recaptcha_v2_info, mock_page)
        assert result == "token'with\\special"
        # Verify the JS was called (escaping handled internally)
        js_code = mock_page.evaluate.call_args[0][0]
        assert "token\\'with\\\\special" in js_code


# ── CaptchaManager.solve ─────────────────────────────────────────────────────


class TestCaptchaManagerSolve:
    """Tests for CaptchaManager.solve()."""

    def test_solve_with_explicit_info(self, mock_page, recaptcha_v2_info):
        manager = CaptchaManager(mock_page)
        solver = TokenInjectionSolver(token="explicit_token_")
        result = manager.solve(solver=solver, captcha_info=recaptcha_v2_info)
        assert result == "explicit_token_"

    def test_solve_auto_detects_first(self, mock_page):
        mock_page.evaluate.side_effect = [
            [{"type": "hcaptcha", "sitekey": "k", "element": "div", "visible": True}],
            None,  # For the injection JS
        ]
        manager = CaptchaManager(mock_page)
        solver = TokenInjectionSolver(token="auto_detected_tk")
        result = manager.solve(solver=solver)
        assert result == "auto_detected_tk"

    def test_solve_no_captcha_raises(self, mock_page):
        mock_page.evaluate.return_value = []
        manager = CaptchaManager(mock_page)
        solver = TokenInjectionSolver(token="wont_use")
        with pytest.raises(CaptchaError, match="No captcha detected"):
            manager.solve(solver=solver)


# ── JS helper functions ───────────────────────────────────────────────────────


class TestJsHelpers:
    """Tests for JS generation helpers."""

    def test_response_check_recaptcha(self):
        js = _response_check_js("recaptcha-v2")
        assert "grecaptcha" in js

    def test_response_check_recaptcha_v3(self):
        js = _response_check_js("recaptcha-v3")
        assert "grecaptcha" in js

    def test_response_check_hcaptcha(self):
        js = _response_check_js("hcaptcha")
        assert "hcaptcha" in js

    def test_response_check_turnstile(self):
        js = _response_check_js("turnstile")
        assert "turnstile" in js

    def test_response_check_generic(self):
        js = _response_check_js("generic-iframe")
        assert "captcha-response" in js

    def test_inject_token_recaptcha(self):
        js = _inject_token_js("recaptcha-v2", "my_token")
        assert "g-recaptcha-response" in js
        assert "my_token" in js

    def test_inject_token_hcaptcha(self):
        js = _inject_token_js("hcaptcha", "my_token")
        assert "h-captcha-response" in js

    def test_inject_token_turnstile(self):
        js = _inject_token_js("turnstile", "my_token")
        assert "cf-turnstile-response" in js

    def test_inject_token_generic(self):
        js = _inject_token_js("generic-iframe", "my_token")
        assert "captcha-response" in js


# ── CaptchaSolver ABC ────────────────────────────────────────────────────────


class TestCaptchaSolverABC:
    """Tests for the abstract base class."""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            CaptchaSolver()

    def test_subclass_must_implement_solve(self):
        class BadSolver(CaptchaSolver):
            pass

        with pytest.raises(TypeError):
            BadSolver()


# ── CLI commands ──────────────────────────────────────────────────────────────


class TestCaptchaCLI:
    """Tests for browser captcha-detect and captcha-solve CLI commands."""

    def test_captcha_detect_help(self, runner):
        from naturo.cli.browser_cmd import captcha_detect
        result = runner.invoke(captcha_detect, ["--help"])
        assert result.exit_code == 0
        assert "captcha" in result.output.lower()

    def test_captcha_solve_help(self, runner):
        from naturo.cli.browser_cmd import captcha_solve
        result = runner.invoke(captcha_solve, ["--help"])
        assert result.exit_code == 0
        assert "manual" in result.output
        assert "token" in result.output

    @patch("naturo.cli.browser_cmd._get_page")
    def test_captcha_detect_json_output(self, mock_get_page, runner):
        page = MagicMock()
        page.evaluate.return_value = [
            {"type": "recaptcha-v2", "sitekey": "abc", "element": "div", "visible": True}
        ]
        mock_get_page.return_value = page

        from naturo.cli.browser_cmd import captcha_detect
        result = runner.invoke(captcha_detect, ["--json"], obj={"cdp_port": 9222, "cdp_host": "localhost"})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["count"] == 1
        assert data["captchas"][0]["type"] == "recaptcha-v2"

    @patch("naturo.cli.browser_cmd._get_page")
    def test_captcha_detect_no_captchas(self, mock_get_page, runner):
        page = MagicMock()
        page.evaluate.return_value = []
        mock_get_page.return_value = page

        from naturo.cli.browser_cmd import captcha_detect
        result = runner.invoke(captcha_detect, obj={"cdp_port": 9222, "cdp_host": "localhost"})
        assert result.exit_code == 0
        assert "No captchas detected" in result.output

    @patch("naturo.cli.browser_cmd._get_page")
    def test_captcha_detect_text_output(self, mock_get_page, runner):
        page = MagicMock()
        page.evaluate.return_value = [
            {"type": "hcaptcha", "sitekey": "abcdef1234567890abcd", "element": "div", "visible": True}
        ]
        mock_get_page.return_value = page

        from naturo.cli.browser_cmd import captcha_detect
        result = runner.invoke(captcha_detect, obj={"cdp_port": 9222, "cdp_host": "localhost"})
        assert result.exit_code == 0
        assert "1 captcha(s)" in result.output
        assert "hcaptcha" in result.output

    @patch("naturo.cli.browser_cmd._get_page")
    def test_captcha_solve_token_missing(self, mock_get_page, runner):
        mock_get_page.return_value = MagicMock()
        from naturo.cli.browser_cmd import captcha_solve
        result = runner.invoke(captcha_solve, ["--solver", "token"], obj={"cdp_port": 9222, "cdp_host": "localhost"})
        assert result.exit_code != 0
        assert "--token is required" in result.output

    @patch("naturo.cli.browser_cmd._get_page")
    def test_captcha_solve_token_success(self, mock_get_page, runner):
        page = MagicMock()
        page.evaluate.side_effect = [
            [{"type": "recaptcha-v2", "sitekey": "k", "element": "div", "visible": True}],
            None,  # injection
        ]
        mock_get_page.return_value = page

        from naturo.cli.browser_cmd import captcha_solve
        result = runner.invoke(
            captcha_solve,
            ["--solver", "token", "--token", "my_solve_token"],
            obj={"cdp_port": 9222, "cdp_host": "localhost"},
        )
        assert result.exit_code == 0
        assert "solved" in result.output.lower()

    @patch("naturo.cli.browser_cmd._get_page")
    def test_captcha_solve_no_captcha_json(self, mock_get_page, runner):
        page = MagicMock()
        page.evaluate.return_value = []
        mock_get_page.return_value = page

        from naturo.cli.browser_cmd import captcha_solve
        result = runner.invoke(
            captcha_solve,
            ["--solver", "token", "--token", "tok", "--json"],
            obj={"cdp_port": 9222, "cdp_host": "localhost"},
        )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
