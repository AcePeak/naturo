"""Tests for naturo.deps — optional dependency auto-installer."""

import json
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from naturo.deps import ensure_package, requires_package, _detect_installer, _is_interactive
from naturo.errors import NaturoError


class TestDetectInstaller:
    """Tests for installer detection."""

    def test_returns_list(self):
        result = _detect_installer()
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_default_uses_python_pip(self):
        result = _detect_installer()
        # Should end with "pip", "install" or "-m", "pip", "install"
        assert "pip" in result
        assert "install" in result


class TestIsInteractive:
    def test_returns_bool(self):
        result = _is_interactive()
        assert isinstance(result, bool)


class TestEnsurePackage:
    """Tests for ensure_package."""

    def test_already_installed(self):
        """No error when package is already importable."""
        # 'json' is always available
        ensure_package("json")

    def test_missing_non_interactive_raises(self):
        """Raises NaturoError in non-interactive mode."""
        with patch("naturo.deps._is_interactive", return_value=False):
            with pytest.raises(NaturoError) as exc_info:
                ensure_package(
                    "nonexistent_pkg_xyz_test",
                    feature="Test",
                    auto_install=False,
                )
            assert "MISSING_DEPENDENCY" in str(exc_info.value.code)

    def test_auto_install_false_raises(self):
        """auto_install=False always raises without prompting."""
        with pytest.raises(NaturoError):
            ensure_package("nonexistent_pkg_xyz_test", auto_install=False)

    def test_auto_install_true_attempts_install(self):
        """auto_install=True attempts pip install."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="not found")
            with pytest.raises(NaturoError) as exc_info:
                ensure_package(
                    "nonexistent_pkg_xyz_test",
                    auto_install=True,
                )
            # Should have tried to install
            mock_run.assert_called_once()
            assert "INSTALL_FAILED" in str(exc_info.value.code)

    def test_auto_install_success(self):
        """Successful install + import works."""
        with patch("subprocess.run") as mock_run, \
             patch("importlib.import_module") as mock_import:
            mock_run.return_value = MagicMock(returncode=0)
            # First call: ImportError (not installed yet)
            # Second call: success (after install)
            mock_import.side_effect = [ImportError("no module"), MagicMock()]

            ensure_package("fakepkg", auto_install=True)
            mock_run.assert_called_once()

    def test_install_extra_in_error_message(self):
        """Error message includes the extras hint."""
        with pytest.raises(NaturoError) as exc_info:
            ensure_package(
                "nonexistent_pkg",
                feature="Desktop",
                install_extra="desktop",
                auto_install=False,
            )
        assert "naturo[desktop]" in exc_info.value.message

    def test_custom_import_name(self):
        """import_name overrides the import module name."""
        # 'os' is always available, so this should pass
        ensure_package("some-pypi-name", import_name="os")

    def test_timeout_raises(self):
        """Timeout during install raises NaturoError."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 120)):
            with pytest.raises(NaturoError) as exc_info:
                ensure_package("fakepkg", auto_install=True)
            assert "INSTALL_TIMEOUT" in str(exc_info.value.code)

    def test_interactive_prompt_yes(self):
        """Interactive prompt with 'y' triggers install."""
        with patch("naturo.deps._is_interactive", return_value=True), \
             patch("builtins.input", return_value="y"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="fail")
            with pytest.raises(NaturoError):
                ensure_package("nonexistent_pkg_xyz", feature="Test")
            mock_run.assert_called_once()

    def test_interactive_prompt_no(self):
        """Interactive prompt with 'n' raises without install."""
        with patch("naturo.deps._is_interactive", return_value=True), \
             patch("builtins.input", return_value="n"), \
             patch("subprocess.run") as mock_run:
            with pytest.raises(NaturoError):
                ensure_package("nonexistent_pkg_xyz", feature="Test")
            mock_run.assert_not_called()


class TestRequiresPackageDecorator:
    """Tests for @requires_package decorator."""

    def test_passes_when_available(self):
        """Decorated function runs normally when package is available."""

        @requires_package("json", feature="JSON")
        def my_func():
            return 42

        assert my_func() == 42

    def test_raises_when_missing(self):
        """Decorated function raises when package is missing."""

        @requires_package("nonexistent_pkg_xyz_test", feature="Test", install_extra="test")
        def my_func():
            return 42

        with patch("naturo.deps._is_interactive", return_value=False):
            with pytest.raises(NaturoError):
                my_func()

    def test_preserves_function_name(self):
        """Decorator preserves the original function name."""

        @requires_package("json")
        def my_special_func():
            """My docstring."""
            pass

        assert my_special_func.__name__ == "my_special_func"
        assert my_special_func.__doc__ == "My docstring."
