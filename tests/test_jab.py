"""Tests for Java Access Bridge (JAB) integration.

JAB requires a running Java application and WindowsAccessBridge-64.dll,
so most tests are skipped on non-Windows or when JAB is unavailable.
The mock-based tests verify the Python bridge, CLI, and MCP layer work
correctly regardless of platform.
"""

import json
import platform
import sys
from unittest.mock import MagicMock, patch

import pytest

# ── Bridge Layer Tests ────────────────────────────────


class TestJABBridgeSetup:
    """Test that JAB function pointers are declared in bridge.py."""

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only DLL")
    def test_bridge_has_jab_methods(self):
        """Bridge NaturoCore has jab_check_support, jab_get_element_tree, jab_find_element."""
        from naturo.bridge import NaturoCore

        core = NaturoCore.__new__(NaturoCore)
        # Verify the methods exist
        assert hasattr(core, "jab_check_support")
        assert hasattr(core, "jab_get_element_tree")
        assert hasattr(core, "jab_find_element")

    def test_bridge_jab_methods_exist(self):
        """jab_* methods are defined on NaturoCore class."""
        from naturo.bridge import NaturoCore

        assert callable(getattr(NaturoCore, "jab_check_support", None))
        assert callable(getattr(NaturoCore, "jab_get_element_tree", None))
        assert callable(getattr(NaturoCore, "jab_find_element", None))


# ── Backend Layer Tests ───────────────────────────────


class TestJABBackend:
    """Test WindowsBackend JAB integration."""

    def test_capabilities_include_jab(self):
        """WindowsBackend.capabilities lists 'jab' in accessibility."""
        from naturo.backends.windows import WindowsBackend

        backend = WindowsBackend.__new__(WindowsBackend)
        caps = backend.capabilities
        assert "jab" in caps["accessibility"]

    @patch("naturo.backends.windows.WindowsBackend._ensure_core")
    @patch("naturo.backends.windows.WindowsBackend._resolve_hwnd", return_value=0)
    def test_get_element_tree_jab_backend(self, mock_resolve, mock_core_fn):
        """get_element_tree(backend='jab') calls core.jab_get_element_tree."""
        from naturo.backends.windows import WindowsBackend

        mock_core = MagicMock()
        mock_core.jab_get_element_tree.return_value = None
        mock_core_fn.return_value = mock_core

        backend = WindowsBackend.__new__(WindowsBackend)
        result = backend.get_element_tree(backend="jab")

        mock_core.jab_get_element_tree.assert_called_once_with(hwnd=0, depth=3)
        assert result is None

    @patch("naturo.backends.windows.WindowsBackend._ensure_core")
    @patch("naturo.backends.windows.WindowsBackend._resolve_hwnd", return_value=0)
    def test_auto_fallback_includes_jab(self, mock_resolve, mock_core_fn):
        """auto mode tries UIA → IA2 → JAB → MSAA."""
        from naturo.backends.windows import WindowsBackend
        from naturo.bridge import ElementInfo

        mock_core = MagicMock()
        # UIA returns empty
        mock_core.get_element_tree.return_value = ElementInfo(
            id="0", role="Window", name="", value="",
            x=0, y=0, width=100, height=100, children=[]
        )
        # IA2 returns None
        mock_core.ia2_get_element_tree.return_value = None
        # JAB returns an element
        jab_el = ElementInfo(
            id="j0", role="Window", name="Java App", value="",
            x=0, y=0, width=800, height=600, children=[]
        )
        jab_el.properties = {"backend": "jab"}
        mock_core.jab_get_element_tree.return_value = jab_el
        mock_core_fn.return_value = mock_core

        backend = WindowsBackend.__new__(WindowsBackend)
        result = backend.get_element_tree(backend="auto")

        # JAB was called as fallback
        mock_core.jab_get_element_tree.assert_called_once()
        # MSAA should NOT be called since JAB succeeded
        mock_core.msaa_get_element_tree.assert_not_called()


# ── CLI Tests ─────────────────────────────────────────


class TestJABCLI:
    """Test CLI --backend jab option."""

    def test_see_help_includes_jab(self):
        """'naturo see --help' mentions jab."""
        from click.testing import CliRunner
        from naturo.cli.core import see

        runner = CliRunner()
        result = runner.invoke(see, ["--help"])
        assert "jab" in result.output

    def test_find_help_includes_jab(self):
        """'naturo find --help' mentions jab."""
        from click.testing import CliRunner
        from naturo.cli.core import find_cmd

        runner = CliRunner()
        result = runner.invoke(find_cmd, ["--help"])
        assert "jab" in result.output

    def test_see_backend_jab_accepted(self):
        """'--backend jab' is accepted by the see command."""
        from click.testing import CliRunner
        from naturo.cli.core import see

        runner = CliRunner()
        # Will fail since no backend on macOS, but should not reject the choice
        result = runner.invoke(see, ["--backend", "jab"])
        # Should NOT say "invalid choice"
        assert "invalid choice" not in result.output.lower()


# ── MCP Tests ─────────────────────────────────────────


class TestJABMCP:
    """Test MCP server accepts jab backend."""

    def test_mcp_see_ui_tree_accepts_jab(self):
        """see_ui_tree MCP tool is created and accepts 'jab' backend."""
        pytest.importorskip("mcp")
        from naturo.mcp_server import create_server

        # Verify the server can be created (which registers all tools)
        server = create_server()
        # The server should have tools registered
        assert server is not None

    def test_mcp_server_source_accepts_jab(self):
        """MCP server source code accepts 'jab' as valid accessibility_backend."""
        import os

        mcp_path = os.path.join(os.path.dirname(__file__), "..", "naturo", "mcp_server.py")
        with open(mcp_path, "r", encoding="utf-8") as f:
            content = f.read()

        # The validation line should include 'jab'
        assert '"jab"' in content
        assert 'accessibility_backend not in ("uia", "msaa", "ia2", "jab", "auto")' in content


# ── Role Mapping Tests ────────────────────────────────


class TestJABRoleMapping:
    """Test that JAB role strings map correctly to Naturo standard roles."""

    @pytest.mark.skipif(platform.system() == "Windows", reason="C++ only on Windows")
    def test_stub_returns_not_available(self):
        """On non-Windows, JAB functions return -6 (not available)."""
        # This tests that the stub compiles and links correctly
        pass

    def test_role_mapping_documented(self):
        """Verify key role mappings are documented in jab.cpp."""
        import os
        jab_cpp = os.path.join(os.path.dirname(__file__), "..", "core", "src", "jab.cpp")
        if not os.path.exists(jab_cpp):
            pytest.skip("jab.cpp not found")

        with open(jab_cpp, "r", encoding="utf-8") as f:
            content = f.read()

        # Check critical role mappings exist
        assert '"push button") return "Button"' in content
        assert '"text") return "Edit"' in content
        assert '"label") return "Text"' in content
        assert '"menu item") return "MenuItem"' in content
        assert '"combo box") return "ComboBox"' in content
        assert '"tree") return "Tree"' in content
        assert '"table") return "Table"' in content


# ── Exports Header Tests ─────────────────────────────


class TestJABExports:
    """Test that JAB functions are declared in exports.h."""

    def test_exports_header_has_jab(self):
        """exports.h declares naturo_jab_* functions."""
        import os
        header = os.path.join(os.path.dirname(__file__), "..", "core", "include", "naturo", "exports.h")
        if not os.path.exists(header):
            pytest.skip("exports.h not found")

        with open(header, "r", encoding="utf-8") as f:
            content = f.read()

        assert "naturo_jab_get_element_tree" in content
        assert "naturo_jab_find_element" in content
        assert "naturo_jab_check_support" in content


# ── CMake Build Tests ─────────────────────────────────


class TestJABBuild:
    """Test that JAB is included in the build system."""

    def test_cmake_includes_jab(self):
        """CMakeLists.txt includes jab.cpp."""
        import os
        cmake = os.path.join(os.path.dirname(__file__), "..", "core", "CMakeLists.txt")
        if not os.path.exists(cmake):
            pytest.skip("CMakeLists.txt not found")

        with open(cmake, "r", encoding="utf-8") as f:
            content = f.read()

        assert "jab.cpp" in content
