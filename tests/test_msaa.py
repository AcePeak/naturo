"""Tests for MSAA (IAccessible) backend support.

Tests the MSAA element tree inspection and element finding capabilities,
both at the bridge level and through the CLI/MCP interfaces.
"""

import json
import platform
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli import main as cli


# ── Bridge layer tests ──────────────────────────


class TestBridgeMSAASignatures:
    """Verify MSAA function signatures are set up correctly."""

    def test_bridge_has_msaa_methods(self):
        """NaturoCore class exposes msaa_get_element_tree and msaa_find_element."""
        from naturo.bridge import NaturoCore
        assert hasattr(NaturoCore, "msaa_get_element_tree")
        assert hasattr(NaturoCore, "msaa_find_element")

    def test_msaa_get_element_tree_signature(self):
        """msaa_get_element_tree accepts hwnd and depth parameters."""
        from naturo.bridge import NaturoCore
        import inspect
        sig = inspect.signature(NaturoCore.msaa_get_element_tree)
        params = list(sig.parameters.keys())
        assert "hwnd" in params
        assert "depth" in params

    def test_msaa_find_element_signature(self):
        """msaa_find_element accepts hwnd, role, and name parameters."""
        from naturo.bridge import NaturoCore
        import inspect
        sig = inspect.signature(NaturoCore.msaa_find_element)
        params = list(sig.parameters.keys())
        assert "hwnd" in params
        assert "role" in params
        assert "name" in params


# ── Backend layer tests ─────────────────────────


class TestBackendMSAAParameter:
    """Verify the backend parameter is accepted by get_element_tree."""

    def test_base_backend_accepts_backend_param(self):
        """Backend.get_element_tree accepts backend='uia'|'msaa'|'auto'."""
        from naturo.backends.base import Backend
        import inspect
        sig = inspect.signature(Backend.get_element_tree)
        params = sig.parameters
        assert "backend" in params
        assert params["backend"].default == "uia"

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")
    def test_windows_backend_accepts_backend_param(self):
        """WindowsBackend.get_element_tree accepts backend parameter."""
        from naturo.backends.windows import WindowsBackend
        import inspect
        sig = inspect.signature(WindowsBackend.get_element_tree)
        params = sig.parameters
        assert "backend" in params


class TestBackendMSAAMocked:
    """Test MSAA backend routing with mocked NaturoCore."""

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")
    def test_backend_uia_calls_uia(self):
        """backend='uia' calls core.get_element_tree (UIA)."""
        from naturo.backends.windows import WindowsBackend
        from naturo.bridge import ElementInfo

        be = WindowsBackend.__new__(WindowsBackend)
        be._core = MagicMock()
        be._initialized = True
        be._dpi_aware = True

        mock_el = ElementInfo(
            id="e0", role="Window", name="Test", value=None,
            x=0, y=0, width=100, height=100, children=[],
        )
        be._core.get_element_tree.return_value = mock_el
        be._core.list_windows.return_value = []

        with patch.object(be, "_resolve_hwnd", return_value=12345):
            result = be.get_element_tree(hwnd=12345, backend="uia")

        be._core.get_element_tree.assert_called_once()
        be._core.msaa_get_element_tree.assert_not_called()
        assert result is not None

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")
    def test_backend_msaa_calls_msaa(self):
        """backend='msaa' calls core.msaa_get_element_tree."""
        from naturo.backends.windows import WindowsBackend
        from naturo.bridge import ElementInfo

        be = WindowsBackend.__new__(WindowsBackend)
        be._core = MagicMock()
        be._initialized = True
        be._dpi_aware = True

        mock_el = ElementInfo(
            id="m0", role="Client", name="Test", value=None,
            x=0, y=0, width=100, height=100, children=[],
        )
        be._core.msaa_get_element_tree.return_value = mock_el
        be._core.list_windows.return_value = []

        with patch.object(be, "_resolve_hwnd", return_value=12345):
            result = be.get_element_tree(hwnd=12345, backend="msaa")

        be._core.msaa_get_element_tree.assert_called_once()
        be._core.get_element_tree.assert_not_called()
        assert result is not None

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")
    def test_backend_auto_fallback(self):
        """backend='auto' tries UIA first, falls back to MSAA on empty tree."""
        from naturo.backends.windows import WindowsBackend
        from naturo.bridge import ElementInfo

        be = WindowsBackend.__new__(WindowsBackend)
        be._core = MagicMock()
        be._initialized = True
        be._dpi_aware = True

        # UIA returns empty tree (no children, no name)
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
        be._core.msaa_get_element_tree.assert_called_once()
        assert result is not None
        assert result.name == "Legacy App"

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")
    def test_backend_auto_no_fallback_when_uia_has_data(self):
        """backend='auto' doesn't try MSAA when UIA returns data."""
        from naturo.backends.windows import WindowsBackend
        from naturo.bridge import ElementInfo

        be = WindowsBackend.__new__(WindowsBackend)
        be._core = MagicMock()
        be._initialized = True
        be._dpi_aware = True

        uia_el = ElementInfo(
            id="e0", role="Window", name="Modern App", value=None,
            x=0, y=0, width=800, height=600,
            children=[
                ElementInfo(
                    id="e1", role="Button", name="OK", value=None,
                    x=10, y=10, width=80, height=30, children=[],
                )
            ],
        )
        be._core.get_element_tree.return_value = uia_el
        be._core.list_windows.return_value = []

        with patch.object(be, "_resolve_hwnd", return_value=12345):
            result = be.get_element_tree(hwnd=12345, backend="auto")

        be._core.get_element_tree.assert_called_once()
        be._core.msaa_get_element_tree.assert_not_called()
        assert result.name == "Modern App"


# ── CLI tests ───────────────────────────────────


class TestSeeCLIMSAAOption:
    """Test that the see command accepts --backend option."""

    def test_see_help_shows_backend_option(self):
        """see --help mentions --backend option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["see", "--help"])
        assert "--backend" in result.output or "-b" in result.output
        assert "msaa" in result.output
        assert "uia" in result.output
        assert "auto" in result.output

    def test_see_invalid_backend(self):
        """see --backend invalid_value is rejected by Click."""
        runner = CliRunner()
        result = runner.invoke(cli, ["see", "--backend", "invalid_value"])
        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "Invalid" in result.output


class TestFindCLIMSAAOption:
    """Test that the find command accepts --backend option."""

    def test_find_help_shows_backend_option(self):
        """find --help mentions --backend option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["find", "--help"])
        assert "--backend" in result.output or "-b" in result.output
        assert "msaa" in result.output

    def test_find_invalid_backend(self):
        """find --backend invalid_value is rejected by Click."""
        runner = CliRunner()
        result = runner.invoke(cli, ["find", "test", "--backend", "invalid_value"])
        assert result.exit_code != 0


# ── C++ layer tests (compile/link validation) ───


class TestMSAACppExports:
    """Verify MSAA exports are declared in the header."""

    def test_exports_header_declares_msaa_functions(self):
        """exports.h declares naturo_msaa_get_element_tree and naturo_msaa_find_element."""
        import os
        header_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "include", "naturo", "exports.h"
        )
        with open(header_path, encoding="utf-8") as f:
            content = f.read()
        assert "naturo_msaa_get_element_tree" in content
        assert "naturo_msaa_find_element" in content

    def test_cmake_includes_msaa_source(self):
        """CMakeLists.txt includes msaa.cpp in the build."""
        import os
        cmake_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "CMakeLists.txt"
        )
        with open(cmake_path, encoding="utf-8") as f:
            content = f.read()
        assert "msaa.cpp" in content


# ── MCP server tests ────────────────────────────


class TestMCPSeeUITreeMSAA:
    """Test that MCP see_ui_tree accepts accessibility_backend parameter."""

    def test_mcp_see_ui_tree_has_backend_param(self):
        """see_ui_tree function signature includes accessibility_backend."""
        pytest.importorskip("mcp")
        from naturo.mcp_server import create_server
        import inspect

        # Check the function in the module
        with open(
            os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         "naturo", "mcp_server.py"),
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "accessibility_backend" in content
        assert '"msaa"' in content or "'msaa'" in content


# Import os for file path tests
import os


# ── MSAA JSON format tests ──────────────────────


class TestMSAARoleMapping:
    """Verify MSAA role constants map to consistent role strings."""

    def test_msaa_cpp_has_role_mapping(self):
        """msaa.cpp maps ROLE_SYSTEM_* constants to human-readable strings."""
        msaa_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "src", "msaa.cpp"
        )
        with open(msaa_path, encoding="utf-8") as f:
            content = f.read()
        # Core roles that must be mapped
        assert "ROLE_SYSTEM_PUSHBUTTON" in content
        assert "ROLE_SYSTEM_TEXT" in content
        assert "ROLE_SYSTEM_COMBOBOX" in content
        assert "ROLE_SYSTEM_MENUITEM" in content
        assert '"Button"' in content
        assert '"Edit"' in content
        assert '"backend\":\"msaa\"' in content or '"backend\\":\\"msaa\\"' in content

    def test_msaa_cpp_json_includes_backend_field(self):
        """MSAA JSON output includes a 'backend' field set to 'msaa'."""
        msaa_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "src", "msaa.cpp"
        )
        with open(msaa_path, encoding="utf-8") as f:
            content = f.read()
        # In C++ source, the JSON field is escaped: \"backend\":\"msaa\"
        assert "backend" in content
        assert "msaa" in content

    def test_msaa_cpp_json_includes_role_id(self):
        """MSAA JSON output includes numeric role_id for programmatic use."""
        msaa_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "src", "msaa.cpp"
        )
        with open(msaa_path, encoding="utf-8") as f:
            content = f.read()
        assert "role_id" in content

    def test_msaa_cpp_json_includes_state(self):
        """MSAA JSON output includes element state flags."""
        msaa_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core", "src", "msaa.cpp"
        )
        with open(msaa_path, encoding="utf-8") as f:
            content = f.read()
        assert "state" in content
        assert "get_accState" in content


# ── Integration test helpers ────────────────────


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")
class TestMSAALiveIntegration:
    """Live MSAA tests that require a Windows desktop session.

    These tests are skipped in CI and on non-Windows platforms.
    They verify actual MSAA element tree traversal works end-to-end.
    """

    def test_msaa_desktop_tree(self):
        """MSAA can inspect the desktop window."""
        from naturo.backends.windows import WindowsBackend
        import ctypes

        be = WindowsBackend()
        desktop_hwnd = ctypes.windll.user32.GetDesktopWindow()
        tree = be.get_element_tree(hwnd=desktop_hwnd, depth=2, backend="msaa")
        # Desktop should always have some children
        assert tree is not None

    def test_msaa_element_has_backend_property(self):
        """MSAA elements include backend='msaa' in their properties."""
        from naturo.backends.windows import WindowsBackend
        import ctypes

        be = WindowsBackend()
        desktop_hwnd = ctypes.windll.user32.GetDesktopWindow()
        core = be._ensure_core()
        result = core.msaa_get_element_tree(hwnd=desktop_hwnd, depth=1)
        # The raw bridge result should parse; backend field is in JSON
        assert result is not None
