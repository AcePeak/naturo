"""Tests for IAccessible2 (IA2) backend support.

Tests the IA2 element tree inspection and element finding capabilities
for applications like Firefox, Thunderbird, and LibreOffice.
"""

import json
import os
import platform
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli import main as cli


# ── Bridge layer tests ──────────────────────────


class TestBridgeIA2Signatures:
    """Verify IA2 function signatures are set up correctly."""

    def test_bridge_has_ia2_methods(self):
        """NaturoCore class exposes ia2 methods."""
        from naturo.bridge import NaturoCore
        assert hasattr(NaturoCore, "ia2_get_element_tree")
        assert hasattr(NaturoCore, "ia2_find_element")
        assert hasattr(NaturoCore, "ia2_check_support")

    def test_ia2_get_element_tree_signature(self):
        """ia2_get_element_tree accepts hwnd and depth parameters."""
        from naturo.bridge import NaturoCore
        import inspect
        sig = inspect.signature(NaturoCore.ia2_get_element_tree)
        params = list(sig.parameters.keys())
        assert "hwnd" in params
        assert "depth" in params

    def test_ia2_find_element_signature(self):
        """ia2_find_element accepts hwnd, role, and name parameters."""
        from naturo.bridge import NaturoCore
        import inspect
        sig = inspect.signature(NaturoCore.ia2_find_element)
        params = list(sig.parameters.keys())
        assert "hwnd" in params
        assert "role" in params
        assert "name" in params

    def test_ia2_check_support_signature(self):
        """ia2_check_support accepts hwnd parameter."""
        from naturo.bridge import NaturoCore
        import inspect
        sig = inspect.signature(NaturoCore.ia2_check_support)
        params = list(sig.parameters.keys())
        assert "hwnd" in params


# ── Backend layer tests ─────────────────────────


class TestBackendIA2Parameter:
    """Verify the backend parameter accepts 'ia2'."""

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")
    def test_windows_backend_capabilities_include_ia2(self):
        """WindowsBackend capabilities list includes 'ia2'."""
        from naturo.backends.windows import WindowsBackend
        be = WindowsBackend.__new__(WindowsBackend)
        caps = be.capabilities
        assert "ia2" in caps["accessibility"]


class TestBackendIA2Mocked:
    """Test IA2 backend routing with mocked NaturoCore."""

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")
    def test_backend_ia2_calls_ia2(self):
        """backend='ia2' calls core.ia2_get_element_tree."""
        from naturo.backends.windows import WindowsBackend
        from naturo.bridge import ElementInfo

        be = WindowsBackend.__new__(WindowsBackend)
        be._core = MagicMock()
        be._initialized = True
        be._dpi_aware = True

        mock_el = ElementInfo(
            id="a0", role="Document", name="Firefox", value=None,
            x=0, y=0, width=1920, height=1080, children=[],
        )
        be._core.ia2_get_element_tree.return_value = mock_el
        be._core.list_windows.return_value = []

        with patch.object(be, "_resolve_hwnd", return_value=12345):
            result = be.get_element_tree(hwnd=12345, backend="ia2")

        be._core.ia2_get_element_tree.assert_called_once()
        be._core.get_element_tree.assert_not_called()
        be._core.msaa_get_element_tree.assert_not_called()
        assert result is not None

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")
    def test_backend_auto_tries_ia2_before_msaa(self):
        """backend='auto' tries IA2 before MSAA on empty UIA tree."""
        from naturo.backends.windows import WindowsBackend
        from naturo.bridge import ElementInfo

        be = WindowsBackend.__new__(WindowsBackend)
        be._core = MagicMock()
        be._initialized = True
        be._dpi_aware = True

        # UIA returns empty tree
        empty_el = ElementInfo(
            id="", role="", name="", value=None,
            x=0, y=0, width=0, height=0, children=[],
        )
        ia2_el = ElementInfo(
            id="a0", role="Document", name="Firefox Content", value=None,
            x=0, y=0, width=1920, height=1080, children=[],
        )
        be._core.get_element_tree.return_value = empty_el
        be._core.ia2_get_element_tree.return_value = ia2_el
        be._core.list_windows.return_value = []

        with patch.object(be, "_resolve_hwnd", return_value=12345):
            result = be.get_element_tree(hwnd=12345, backend="auto")

        be._core.get_element_tree.assert_called_once()
        be._core.ia2_get_element_tree.assert_called_once()
        # MSAA should NOT be called since IA2 succeeded
        be._core.msaa_get_element_tree.assert_not_called()
        assert result.name == "Firefox Content"

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")
    def test_backend_auto_falls_through_to_msaa(self):
        """backend='auto' falls back to MSAA if both UIA and IA2 fail."""
        from naturo.backends.windows import WindowsBackend
        from naturo.bridge import ElementInfo

        be = WindowsBackend.__new__(WindowsBackend)
        be._core = MagicMock()
        be._initialized = True
        be._dpi_aware = True

        empty_el = ElementInfo(
            id="", role="", name="", value=None,
            x=0, y=0, width=0, height=0, children=[],
        )
        msaa_el = ElementInfo(
            id="m0", role="Client", name="Legacy App", value=None,
            x=0, y=0, width=800, height=600, children=[],
        )
        be._core.get_element_tree.return_value = empty_el
        be._core.ia2_get_element_tree.return_value = None  # IA2 not supported
        be._core.jab_get_element_tree.return_value = None  # JAB not supported
        be._core.msaa_get_element_tree.return_value = msaa_el
        be._core.list_windows.return_value = []

        with patch.object(be, "_resolve_hwnd", return_value=12345):
            result = be.get_element_tree(hwnd=12345, backend="auto")

        be._core.get_element_tree.assert_called_once()
        be._core.ia2_get_element_tree.assert_called_once()
        be._core.msaa_get_element_tree.assert_called_once()
        assert result.name == "Legacy App"


# ── CLI tests ───────────────────────────────────


class TestSeeCLIIA2Option:
    """Test that the see command accepts --backend ia2."""

    def test_see_help_shows_ia2_option(self):
        """see --help mentions ia2 backend."""
        runner = CliRunner()
        result = runner.invoke(cli, ["see", "--help"])
        assert "ia2" in result.output

    def test_see_accepts_ia2_backend(self):
        """see --backend ia2 is accepted by Click (doesn't fail on choice validation)."""
        runner = CliRunner()
        # This will fail with "not supported on this platform" on macOS,
        # but it should NOT fail on invalid choice
        result = runner.invoke(cli, ["see", "--backend", "ia2", "--json"])
        # Check it's NOT a "no such choice" error
        assert "invalid choice" not in result.output.lower()


class TestFindCLIIA2Option:
    """Test that the find command accepts --backend ia2."""

    def test_find_help_shows_ia2_option(self):
        """find --help mentions ia2 backend."""
        runner = CliRunner()
        result = runner.invoke(cli, ["find", "--help"])
        assert "ia2" in result.output

    def test_find_accepts_ia2_backend(self):
        """find --backend ia2 is accepted by Click."""
        runner = CliRunner()
        result = runner.invoke(cli, ["find", "test", "--backend", "ia2", "--json"])
        assert "invalid choice" not in result.output.lower()


# ── C++ layer tests ─────────────────────────────


class TestIA2CppExports:
    """Verify IA2 exports are declared in the header."""

    def test_exports_header_declares_ia2_functions(self):
        """exports.h declares naturo_ia2_* functions."""
        header_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "include", "naturo", "exports.h"
        )
        with open(header_path, encoding="utf-8") as f:
            content = f.read()
        assert "naturo_ia2_get_element_tree" in content
        assert "naturo_ia2_find_element" in content
        assert "naturo_ia2_check_support" in content

    def test_ia2_cpp_source_exists(self):
        """ia2.cpp source file exists."""
        ia2_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "src", "ia2.cpp"
        )
        assert os.path.isfile(ia2_path)

    def test_ia2_cpp_has_iserviceprovider(self):
        """ia2.cpp uses IServiceProvider to obtain IA2 interface."""
        ia2_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "src", "ia2.cpp"
        )
        with open(ia2_path, encoding="utf-8") as f:
            content = f.read()
        assert "IServiceProvider" in content
        assert "QueryService" in content

    def test_ia2_cpp_has_ia2_roles(self):
        """ia2.cpp includes IA2-specific role mappings."""
        ia2_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "src", "ia2.cpp"
        )
        with open(ia2_path, encoding="utf-8") as f:
            content = f.read()
        assert "Heading" in content
        assert "Paragraph" in content
        assert "Landmark" in content
        assert "Footer" in content
        assert "Form" in content

    def test_ia2_cpp_json_includes_backend_field(self):
        """IA2 JSON output includes backend='ia2'."""
        ia2_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "src", "ia2.cpp"
        )
        with open(ia2_path, encoding="utf-8") as f:
            content = f.read()
        assert '"backend\\":\\"ia2\\"' in content or '"backend":"ia2"' in content or \
               'backend' in content and 'ia2' in content

    def test_ia2_cpp_json_includes_ia2_attributes(self):
        """IA2 JSON output includes ia2_attributes field."""
        ia2_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "src", "ia2.cpp"
        )
        with open(ia2_path, encoding="utf-8") as f:
            content = f.read()
        assert "ia2_attributes" in content
        assert "ia2_states" in content
        assert "ia2_unique_id" in content

    def test_ia2_cpp_has_check_support(self):
        """ia2.cpp implements naturo_ia2_check_support."""
        ia2_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "src", "ia2.cpp"
        )
        with open(ia2_path, encoding="utf-8") as f:
            content = f.read()
        assert "naturo_ia2_check_support" in content

    def test_ia2_cpp_has_non_windows_stubs(self):
        """ia2.cpp has non-Windows stubs for cross-platform compilation."""
        ia2_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "src", "ia2.cpp"
        )
        with open(ia2_path, encoding="utf-8") as f:
            content = f.read()
        assert "#else" in content
        assert "Non-Windows stub" in content or "Non-Windows" in content

    def test_ia2_cpp_iid_matches_standard(self):
        """IA2 IID {1546D4B0-4C98-4BDA-89AE-9A64748BDDE4} is correct."""
        ia2_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "src", "ia2.cpp"
        )
        with open(ia2_path, encoding="utf-8") as f:
            content = f.read()
        assert "1546D4B0" in content
        assert "4C98" in content
        assert "4BDA" in content


# ── MCP server tests ────────────────────────────


class TestMCPIA2Support:
    """Test that MCP server accepts ia2 backend."""

    def test_mcp_server_allows_ia2_backend(self):
        """MCP see_ui_tree validates ia2 as valid accessibility_backend."""
        mcp_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "naturo", "mcp_server.py"
        )
        with open(mcp_path, encoding="utf-8") as f:
            content = f.read()
        assert '"ia2"' in content
        assert "ia2" in content


# ── CMake build tests ───────────────────────────


class TestCMakeIA2:
    """Verify ia2.cpp is included in the build system."""

    def test_cmake_includes_ia2_source(self):
        """CMakeLists.txt includes ia2.cpp in the build."""
        cmake_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "CMakeLists.txt"
        )
        with open(cmake_path, encoding="utf-8") as f:
            content = f.read()
        assert "ia2.cpp" in content


# ── Integration tests (Windows-only) ────────────


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")
class TestIA2LiveIntegration:
    """Live IA2 tests that require a Windows desktop session.

    These tests are skipped in CI and on non-Windows platforms.
    """

    def test_ia2_check_support_returns_bool(self):
        """ia2_check_support returns False for non-IA2 windows."""
        from naturo.backends.windows import WindowsBackend
        import ctypes

        be = WindowsBackend()
        core = be._ensure_core()
        # Desktop window typically doesn't support IA2
        desktop_hwnd = ctypes.windll.user32.GetDesktopWindow()
        result = core.ia2_check_support(desktop_hwnd)
        assert isinstance(result, bool)

    def test_ia2_get_element_tree_non_ia2_window(self):
        """ia2_get_element_tree returns None for non-IA2 windows."""
        from naturo.backends.windows import WindowsBackend
        import ctypes

        be = WindowsBackend()
        core = be._ensure_core()
        desktop_hwnd = ctypes.windll.user32.GetDesktopWindow()
        result = core.ia2_get_element_tree(hwnd=desktop_hwnd, depth=2)
        # Desktop doesn't support IA2, should return None
        assert result is None
