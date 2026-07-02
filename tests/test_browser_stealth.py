"""Tests for naturo.browser._stealth — anti-detection patches and CLI commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, call

import pytest
from click.testing import CliRunner

from naturo.browser._stealth import (
    ALL_PATCHES,
    STEALTH_FLAGS,
    apply_stealth_patches,
    _PATCH_WEBDRIVER,
    _PATCH_PLUGINS,
    _PATCH_LANGUAGES,
    _PATCH_PERMISSIONS,
    _PATCH_CHROME_RUNTIME,
    _PATCH_WEBGL_VENDOR,
)
from naturo.cli.browser_cmd import browser


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# Patch constants
# ---------------------------------------------------------------------------


class TestStealthConstants:
    """Validate stealth patch definitions."""

    def test_flags_are_strings(self):
        """All stealth flags are non-empty strings."""
        assert len(STEALTH_FLAGS) > 0
        for flag in STEALTH_FLAGS:
            assert isinstance(flag, str)
            assert flag.startswith("--")

    def test_all_patches_count(self):
        """ALL_PATCHES contains all 6 patches."""
        assert len(ALL_PATCHES) == 6

    def test_webdriver_patch_masks_property(self):
        """Webdriver patch overrides navigator.webdriver."""
        assert "navigator" in _PATCH_WEBDRIVER
        assert "webdriver" in _PATCH_WEBDRIVER
        assert "undefined" in _PATCH_WEBDRIVER

    def test_plugins_patch_has_entries(self):
        """Plugins patch provides realistic plugin list."""
        assert "Chrome PDF Plugin" in _PATCH_PLUGINS
        assert "plugins" in _PATCH_PLUGINS

    def test_languages_patch(self):
        """Languages patch sets en-US."""
        assert "en-US" in _PATCH_LANGUAGES

    def test_permissions_patch(self):
        """Permissions patch handles Notification."""
        assert "Notification" in _PATCH_PERMISSIONS

    def test_chrome_runtime_patch(self):
        """Chrome runtime patch creates chrome.runtime stub."""
        assert "chrome.runtime" in _PATCH_CHROME_RUNTIME

    def test_webgl_vendor_patch(self):
        """WebGL vendor patch spoofs Intel."""
        assert "Intel" in _PATCH_WEBGL_VENDOR
        assert "37445" in _PATCH_WEBGL_VENDOR  # UNMASKED_VENDOR


# ---------------------------------------------------------------------------
# apply_stealth_patches
# ---------------------------------------------------------------------------


class TestApplyStealthPatches:
    """Test runtime patch application."""

    def test_applies_all_patches(self):
        """All patches are sent via CDP and evaluated."""
        mock_page = MagicMock()
        mock_page._cdp = MagicMock()

        count = apply_stealth_patches(mock_page)

        assert count == 6
        assert mock_page._cdp.send.call_count == 6
        assert mock_page._cdp.evaluate.call_count == 6

        # Verify addScriptToEvaluateOnNewDocument was used
        for c in mock_page._cdp.send.call_args_list:
            assert c[0][0] == "Page.addScriptToEvaluateOnNewDocument"
            assert "source" in c[0][1]

    def test_handles_partial_failure(self):
        """Continues applying patches even if one fails."""
        mock_page = MagicMock()
        mock_page._cdp = MagicMock()

        # Make the 3rd patch fail
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise RuntimeError("CDP error")

        mock_page._cdp.send.side_effect = side_effect

        count = apply_stealth_patches(mock_page)

        # 5 succeeded, 1 failed
        assert count == 5

    def test_returns_zero_on_total_failure(self):
        """Returns 0 when all patches fail."""
        mock_page = MagicMock()
        mock_page._cdp = MagicMock()
        mock_page._cdp.send.side_effect = RuntimeError("all fail")

        count = apply_stealth_patches(mock_page)
        assert count == 0


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


class TestStealthCLI:
    """Test stealth CLI commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_stealth_flags_text(self, runner):
        """browser stealth-flags prints flags as space-separated string."""
        result = runner.invoke(browser, ["stealth-flags"])
        assert result.exit_code == 0
        assert "--disable-blink-features=AutomationControlled" in result.output

    def test_stealth_flags_json(self, runner):
        """browser stealth-flags --json outputs JSON array."""
        result = runner.invoke(browser, ["stealth-flags", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "flags" in data
        assert isinstance(data["flags"], list)
        assert len(data["flags"]) == len(STEALTH_FLAGS)

    def test_stealth_apply_success(self, runner):
        """browser stealth applies patches and reports count."""
        mock_page = MagicMock()
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page), \
             patch("naturo.browser._stealth.apply_stealth_patches", return_value=6):
            result = runner.invoke(browser, ["stealth"])
        assert result.exit_code == 0
        assert "6" in result.output
        mock_page.close.assert_called_once()

    def test_stealth_apply_json(self, runner):
        """browser stealth --json outputs JSON."""
        mock_page = MagicMock()
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page), \
             patch("naturo.browser._stealth.apply_stealth_patches", return_value=6):
            result = runner.invoke(browser, ["stealth", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["patches_applied"] == 6

    def test_stealth_apply_error(self, runner):
        """browser stealth shows error on failure."""
        mock_page = MagicMock()
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page), \
             patch("naturo.browser._stealth.apply_stealth_patches", side_effect=RuntimeError("connection lost")):
            result = runner.invoke(browser, ["stealth"])
        assert result.exit_code != 0
        assert "connection lost" in result.output

    def test_stealth_help(self, runner):
        """browser stealth --help shows usage."""
        result = runner.invoke(browser, ["stealth", "--help"])
        assert result.exit_code == 0
        assert "anti-detection" in result.output.lower()

    def test_stealth_flags_help(self, runner):
        """browser stealth-flags --help shows usage."""
        result = runner.invoke(browser, ["stealth-flags", "--help"])
        assert result.exit_code == 0
        assert "flag" in result.output.lower()
