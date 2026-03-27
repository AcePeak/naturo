"""Tests for Windows Registry CLI commands and backend.

Tests use mocked winreg module to work on all platforms.
Phase 5C.2.
"""

import json
import platform
import sys
from unittest.mock import MagicMock, patch, call

import pytest
from click.testing import CliRunner

from naturo.cli import main


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_winreg():
    """Mock winreg module for cross-platform testing."""
    winreg = MagicMock()
    winreg.KEY_READ = 0x20019
    winreg.KEY_WRITE = 0x20006
    winreg.HKEY_CURRENT_USER = 0x80000001
    winreg.HKEY_LOCAL_MACHINE = 0x80000002
    winreg.HKEY_CLASSES_ROOT = 0x80000000
    winreg.HKEY_USERS = 0x80000003
    winreg.HKEY_CURRENT_CONFIG = 0x80000005
    winreg.REG_SZ = 1
    winreg.REG_EXPAND_SZ = 2
    winreg.REG_BINARY = 3
    winreg.REG_DWORD = 4
    winreg.REG_MULTI_SZ = 7
    winreg.REG_QWORD = 11
    return winreg


# ── Backend tests ───────────────────────────────────────────────────────────


class TestParseKeyPath:
    """Test _parse_key_path helper."""

    @patch("naturo.registry.platform")
    def test_short_hive_hkcu(self, mock_platform):
        """HKCU is resolved to HKEY_CURRENT_USER."""
        from naturo.registry import _parse_key_path
        hive, subkey = _parse_key_path("HKCU\\Software\\Test")
        assert hive == "HKEY_CURRENT_USER"
        assert subkey == "Software\\Test"

    @patch("naturo.registry.platform")
    def test_short_hive_hklm(self, mock_platform):
        """HKLM is resolved to HKEY_LOCAL_MACHINE."""
        from naturo.registry import _parse_key_path
        hive, subkey = _parse_key_path("HKLM\\SOFTWARE\\Microsoft")
        assert hive == "HKEY_LOCAL_MACHINE"
        assert subkey == "SOFTWARE\\Microsoft"

    @patch("naturo.registry.platform")
    def test_long_hive(self, mock_platform):
        """Long hive names work."""
        from naturo.registry import _parse_key_path
        hive, subkey = _parse_key_path("HKEY_CURRENT_USER\\Software")
        assert hive == "HKEY_CURRENT_USER"
        assert subkey == "Software"

    @patch("naturo.registry.platform")
    def test_forward_slashes(self, mock_platform):
        """Forward slashes are normalised to backslashes."""
        from naturo.registry import _parse_key_path
        hive, subkey = _parse_key_path("HKCU/Software/Test")
        assert hive == "HKEY_CURRENT_USER"
        assert subkey == "Software\\Test"

    @patch("naturo.registry.platform")
    def test_unknown_hive(self, mock_platform):
        """Unknown hive raises NaturoError."""
        from naturo.registry import _parse_key_path
        from naturo.errors import NaturoError
        with pytest.raises(NaturoError, match="Unknown registry hive"):
            _parse_key_path("HKXX\\Software")

    @patch("naturo.registry.platform")
    def test_hive_only(self, mock_platform):
        """Hive with no subkey returns empty subkey."""
        from naturo.registry import _parse_key_path
        hive, subkey = _parse_key_path("HKCU")
        assert hive == "HKEY_CURRENT_USER"
        assert subkey == ""

    @patch("naturo.registry.platform")
    def test_case_insensitive(self, mock_platform):
        """Hive names are case insensitive."""
        from naturo.registry import _parse_key_path
        hive, subkey = _parse_key_path("hkcu\\Software")
        assert hive == "HKEY_CURRENT_USER"


class TestCoerceData:
    """Test _coerce_data helper."""

    def test_reg_sz(self):
        """REG_SZ keeps string as-is."""
        from naturo.registry import _coerce_data
        assert _coerce_data("hello", "REG_SZ") == "hello"

    def test_reg_dword_decimal(self):
        """REG_DWORD parses decimal."""
        from naturo.registry import _coerce_data
        assert _coerce_data("42", "REG_DWORD") == 42

    def test_reg_dword_hex(self):
        """REG_DWORD parses hex."""
        from naturo.registry import _coerce_data
        assert _coerce_data("0xff", "REG_DWORD") == 255

    def test_reg_qword(self):
        """REG_QWORD parses large integers."""
        from naturo.registry import _coerce_data
        assert _coerce_data("999999999999", "REG_QWORD") == 999999999999

    def test_reg_binary(self):
        """REG_BINARY parses hex string to bytes."""
        from naturo.registry import _coerce_data
        assert _coerce_data("deadbeef", "REG_BINARY") == b"\xde\xad\xbe\xef"

    def test_reg_multi_sz(self):
        """REG_MULTI_SZ splits on semicolons."""
        from naturo.registry import _coerce_data
        assert _coerce_data("a;b;c", "REG_MULTI_SZ") == ["a", "b", "c"]

    def test_reg_multi_sz_strips(self):
        """REG_MULTI_SZ strips whitespace and skips empty."""
        from naturo.registry import _coerce_data
        assert _coerce_data(" a ; ; b ", "REG_MULTI_SZ") == ["a", "b"]

    def test_invalid_dword(self):
        """Invalid DWORD value raises NaturoError."""
        from naturo.registry import _coerce_data
        from naturo.errors import NaturoError
        with pytest.raises(NaturoError, match="Cannot convert"):
            _coerce_data("not-a-number", "REG_DWORD")

    def test_reg_expand_sz(self):
        """REG_EXPAND_SZ keeps string as-is."""
        from naturo.registry import _coerce_data
        assert _coerce_data("%PATH%\\bin", "REG_EXPAND_SZ") == "%PATH%\\bin"


class TestTypeName:
    """Test _type_name helper."""

    def test_known_types(self):
        """Known type IDs return correct names."""
        from naturo.registry import _type_name
        assert _type_name(1) == "REG_SZ"
        assert _type_name(4) == "REG_DWORD"
        assert _type_name(11) == "REG_QWORD"

    def test_unknown_type(self):
        """Unknown type ID returns fallback string."""
        from naturo.registry import _type_name
        assert _type_name(99) == "REG_TYPE_99"


class TestFormatValue:
    """Test _format_value helper."""

    def test_bytes_to_hex(self):
        """Bytes are converted to hex string."""
        from naturo.registry import _format_value
        assert _format_value(b"\xde\xad", 3) == "dead"

    def test_string_passthrough(self):
        """Strings pass through unchanged."""
        from naturo.registry import _format_value
        assert _format_value("hello", 1) == "hello"

    def test_int_passthrough(self):
        """Integers pass through unchanged."""
        from naturo.registry import _format_value
        assert _format_value(42, 4) == 42


# ── CLI tests ───────────────────────────────────────────────────────────────


@pytest.mark.skip(reason="CLI command removed in v0.2.0")
class TestRegistryGetCLI:
    """Test 'naturo registry get' CLI command."""

    def test_get_json_success(self, runner, mock_winreg):
        """Successful get outputs JSON with success=true."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock(return_value=mock_key)
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
        mock_winreg.QueryValueEx.return_value = ("test_data", 1)

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, ["registry", "get", "HKCU\\Software\\Test", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"] == "test_data"
        assert data["type_name"] == "REG_SZ"

    def test_get_text_success(self, runner, mock_winreg):
        """Successful get outputs human-readable text."""
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock()
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
        mock_winreg.QueryValueEx.return_value = (42, 4)

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, ["registry", "get", "HKCU\\Software\\Test", "-v", "MyValue"])

        assert result.exit_code == 0
        assert "MyValue" in result.output
        assert "42" in result.output

    def test_get_not_found(self, runner, mock_winreg):
        """Missing value returns REGISTRY_NOT_FOUND."""
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock()
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
        mock_winreg.QueryValueEx.side_effect = FileNotFoundError

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, ["registry", "get", "HKCU\\Software\\NoKey", "--json"])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "REGISTRY_NOT_FOUND"

    def test_get_platform_error(self, runner):
        """Non-Windows platform returns PLATFORM_ERROR."""
        with patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Darwin"
            result = runner.invoke(main, ["registry", "get", "HKCU\\Software", "--json"])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "PLATFORM_ERROR"

    def test_get_permission_denied(self, runner, mock_winreg):
        """Permission denied returns structured error."""
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock()
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
        mock_winreg.QueryValueEx.side_effect = PermissionError

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, ["registry", "get", "HKLM\\SAM", "--json"])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.skip(reason="CLI command removed in v0.2.0")
class TestRegistrySetCLI:
    """Test 'naturo registry set' CLI command."""

    def test_set_json_success(self, runner, mock_winreg):
        """Successful set outputs JSON with success=true."""
        mock_winreg.CreateKeyEx.return_value.__enter__ = MagicMock()
        mock_winreg.CreateKeyEx.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, [
                "registry", "set", "HKCU\\Software\\Test",
                "-v", "MyVal", "-d", "hello", "--json",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["name"] == "MyVal"
        assert data["data"] == "hello"
        assert data["type_name"] == "REG_SZ"

    def test_set_dword(self, runner, mock_winreg):
        """Set DWORD value."""
        mock_winreg.CreateKeyEx.return_value.__enter__ = MagicMock()
        mock_winreg.CreateKeyEx.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, [
                "registry", "set", "HKCU\\Software\\Test",
                "-v", "Count", "-d", "42", "-t", "REG_DWORD", "--json",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"] == 42

    def test_set_text_output(self, runner, mock_winreg):
        """Set in text mode outputs confirmation."""
        mock_winreg.CreateKeyEx.return_value.__enter__ = MagicMock()
        mock_winreg.CreateKeyEx.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, [
                "registry", "set", "HKCU\\Software\\Test",
                "-v", "MyVal", "-d", "hello",
            ])

        assert result.exit_code == 0
        assert "Set MyVal" in result.output

    def test_set_permission_denied(self, runner, mock_winreg):
        """Permission denied writing to HKLM."""
        mock_winreg.CreateKeyEx.return_value.__enter__ = MagicMock()
        mock_winreg.CreateKeyEx.return_value.__exit__ = MagicMock(return_value=False)
        mock_winreg.SetValueEx.side_effect = PermissionError

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, [
                "registry", "set", "HKLM\\SOFTWARE\\Test",
                "-v", "X", "-d", "Y", "--json",
            ])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.skip(reason="CLI command removed in v0.2.0")
class TestRegistryListCLI:
    """Test 'naturo registry list' CLI command."""

    def test_list_json_success(self, runner, mock_winreg):
        """Successful list outputs subkeys and values."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock(return_value=mock_key)
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
        mock_winreg.QueryInfoKey.return_value = (2, 1, 0)
        mock_winreg.EnumKey.side_effect = ["SubKey1", "SubKey2"]
        mock_winreg.EnumValue.side_effect = [("Name", "data", 1)]

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, ["registry", "list", "HKCU\\Software", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert len(data["subkeys"]) == 2
        assert len(data["values"]) == 1

    def test_list_text_output(self, runner, mock_winreg):
        """List in text mode shows subkeys and values."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock(return_value=mock_key)
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
        mock_winreg.QueryInfoKey.return_value = (1, 0, 0)
        mock_winreg.EnumKey.side_effect = ["Child"]

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, ["registry", "list", "HKCU\\Software"])

        assert result.exit_code == 0
        assert "Subkeys:" in result.output
        assert "Child" in result.output

    def test_list_empty_key(self, runner, mock_winreg):
        """Empty key shows message."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock(return_value=mock_key)
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
        mock_winreg.QueryInfoKey.return_value = (0, 0, 0)

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, ["registry", "list", "HKCU\\Software\\Empty"])

        assert result.exit_code == 0
        assert "empty key" in result.output

    def test_list_not_found(self, runner, mock_winreg):
        """Non-existent key returns REGISTRY_NOT_FOUND."""
        mock_winreg.OpenKey.side_effect = FileNotFoundError

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, ["registry", "list", "HKCU\\NoKey", "--json"])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "REGISTRY_NOT_FOUND"


@pytest.mark.skip(reason="CLI command removed in v0.2.0")
class TestRegistryDeleteCLI:
    """Test 'naturo registry delete' CLI command."""

    def test_delete_value_json(self, runner, mock_winreg):
        """Delete a value returns success."""
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock()
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, [
                "registry", "delete", "HKCU\\Software\\Test",
                "-v", "MyVal", "--json",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["deleted"] == "value"

    def test_delete_key_json(self, runner, mock_winreg):
        """Delete a key (no subkeys) returns success."""
        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, [
                "registry", "delete", "HKCU\\Software\\Test", "--json",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["deleted"] == "key"

    def test_delete_text_output(self, runner, mock_winreg):
        """Delete in text mode outputs confirmation."""
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock()
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, [
                "registry", "delete", "HKCU\\Software\\Test", "-v", "X",
            ])

        assert result.exit_code == 0
        assert "Deleted value" in result.output

    def test_delete_value_not_found(self, runner, mock_winreg):
        """Delete non-existent value returns REGISTRY_NOT_FOUND."""
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock()
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
        mock_winreg.DeleteValue.side_effect = FileNotFoundError

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, [
                "registry", "delete", "HKCU\\Software\\Test",
                "-v", "Missing", "--json",
            ])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "REGISTRY_NOT_FOUND"


@pytest.mark.skip(reason="CLI command removed in v0.2.0")
class TestRegistrySearchCLI:
    """Test 'naturo registry search' CLI command."""

    def test_search_json_success(self, runner, mock_winreg):
        """Search returns structured results."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock(return_value=mock_key)
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
        # First call: verify key exists; second call: search
        mock_winreg.QueryInfoKey.return_value = (1, 1, 0)
        mock_winreg.EnumKey.side_effect = ["TestKey", OSError]
        mock_winreg.EnumValue.side_effect = [("TestValue", "data", 1), OSError]

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, [
                "registry", "search", "HKCU\\Software", "Test", "--json",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "results" in data
        assert "count" in data

    def test_search_empty_query(self, runner):
        """Empty query returns INVALID_INPUT."""
        result = runner.invoke(main, [
            "registry", "search", "HKCU\\Software", "   ", "--json",
        ])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_search_invalid_depth(self, runner):
        """Invalid depth returns INVALID_INPUT."""
        result = runner.invoke(main, [
            "registry", "search", "HKCU\\Software", "test",
            "--depth", "0", "--json",
        ])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_search_text_no_results(self, runner, mock_winreg):
        """No results in text mode."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock(return_value=mock_key)
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
        mock_winreg.QueryInfoKey.return_value = (0, 0, 0)

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, [
                "registry", "search", "HKCU\\Software", "nonexistent",
            ])

        assert result.exit_code == 0
        assert "No results" in result.output

    def test_search_invalid_max_results(self, runner):
        """Invalid max-results returns INVALID_INPUT."""
        result = runner.invoke(main, [
            "registry", "search", "HKCU\\Software", "test",
            "--max-results", "0", "--json",
        ])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "INVALID_INPUT"


@pytest.mark.skip(reason="CLI command removed in v0.2.0")
class TestRegistryHelpAndStructure:
    """Test CLI help and command structure."""

    def test_registry_help(self, runner):
        """Registry group shows help."""
        result = runner.invoke(main, ["registry", "--help"])
        assert result.exit_code == 0
        assert "get" in result.output
        assert "set" in result.output
        assert "list" in result.output
        assert "delete" in result.output
        assert "search" in result.output

    def test_registry_get_help(self, runner):
        """Registry get shows help."""
        result = runner.invoke(main, ["registry", "get", "--help"])
        assert result.exit_code == 0
        assert "KEY_PATH" in result.output

    def test_registry_set_help(self, runner):
        """Registry set shows help."""
        result = runner.invoke(main, ["registry", "set", "--help"])
        assert result.exit_code == 0
        assert "REG_SZ" in result.output
        assert "REG_DWORD" in result.output

    def test_registry_search_help(self, runner):
        """Registry search shows help."""
        result = runner.invoke(main, ["registry", "search", "--help"])
        assert result.exit_code == 0
        assert "--depth" in result.output
        assert "--max-results" in result.output

    def test_registry_in_main_help(self, runner):
        """Registry command appears in main help."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "registry" in result.output


@pytest.mark.skip(reason="CLI command removed in v0.2.0")
class TestRegistryJSONConsistency:
    """Test JSON output format consistency."""

    def test_success_has_success_true(self, runner, mock_winreg):
        """All success responses have success=true."""
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock()
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
        mock_winreg.QueryValueEx.return_value = ("val", 1)

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, ["registry", "get", "HKCU\\Test", "--json"])

        data = json.loads(result.output)
        assert "success" in data
        assert data["success"] is True

    def test_error_has_code_and_message(self, runner):
        """All error responses have code and message."""
        with patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Darwin"
            result = runner.invoke(main, ["registry", "get", "HKCU\\Test", "--json"])

        data = json.loads(result.output)
        assert data["success"] is False
        assert "code" in data["error"]
        assert "message" in data["error"]

    def test_error_has_code_message_structure(self, runner, mock_winreg):
        """Error responses always have code and message in error object."""
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock()
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)
        mock_winreg.QueryValueEx.side_effect = FileNotFoundError

        with patch.dict("sys.modules", {"winreg": mock_winreg}), \
             patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = runner.invoke(main, ["registry", "get", "HKCU\\Missing", "--json"])

        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "REGISTRY_NOT_FOUND"
        assert "not found" in data["error"]["message"].lower()


class TestRegistryBackendRequireWindows:
    """Test platform checks."""

    def test_reg_get_requires_windows(self):
        """reg_get raises on non-Windows."""
        from naturo.registry import reg_get
        from naturo.errors import NaturoError
        with patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Linux"
            with pytest.raises(NaturoError, match="Windows"):
                reg_get("HKCU\\Software")

    def test_reg_set_requires_windows(self):
        """reg_set raises on non-Windows."""
        from naturo.registry import reg_set
        from naturo.errors import NaturoError
        with patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Darwin"
            with pytest.raises(NaturoError, match="Windows"):
                reg_set("HKCU\\Software", "v", "d")

    def test_reg_list_requires_windows(self):
        """reg_list raises on non-Windows."""
        from naturo.registry import reg_list
        from naturo.errors import NaturoError
        with patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Darwin"
            with pytest.raises(NaturoError, match="Windows"):
                reg_list("HKCU\\Software")

    def test_reg_delete_requires_windows(self):
        """reg_delete raises on non-Windows."""
        from naturo.registry import reg_delete
        from naturo.errors import NaturoError
        with patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Linux"
            with pytest.raises(NaturoError, match="Windows"):
                reg_delete("HKCU\\Software")

    def test_reg_search_requires_windows(self):
        """reg_search raises on non-Windows."""
        from naturo.registry import reg_search
        from naturo.errors import NaturoError
        with patch("naturo.registry.platform") as mock_platform:
            mock_platform.system.return_value = "Darwin"
            with pytest.raises(NaturoError, match="Windows"):
                reg_search("HKCU\\Software", "test")


class TestRegistryHiveMapping:
    """Test all hive aliases."""

    @pytest.mark.parametrize("alias,expected", [
        ("HKCR", "HKEY_CLASSES_ROOT"),
        ("HKCU", "HKEY_CURRENT_USER"),
        ("HKLM", "HKEY_LOCAL_MACHINE"),
        ("HKU", "HKEY_USERS"),
        ("HKCC", "HKEY_CURRENT_CONFIG"),
    ])
    def test_hive_alias(self, alias, expected):
        """All short hive aliases resolve correctly."""
        from naturo.registry import _parse_key_path
        hive, _ = _parse_key_path(f"{alias}\\Software")
        assert hive == expected
