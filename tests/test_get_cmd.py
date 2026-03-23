"""Tests for the ``naturo get`` CLI command and backend method.

Covers:
- CLI argument parsing (ref, automation_id, role+name)
- JSON and plain text output modes
- Property filtering (--property)
- Error handling (missing target, element not found)
- Backend get_element_value method (mocked DLL)
"""

import json
import platform
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli import main


# ── Helpers ──────────────────────────────────────────────────────────────────

def _mock_backend_result():
    """Return a mock get_element_value result dict."""
    return {
        "value": "Hello World",
        "pattern": "ValuePattern",
        "role": "Edit",
        "name": "Search",
        "automation_id": "txtSearch",
        "x": 100,
        "y": 200,
        "width": 300,
        "height": 30,
    }


def _make_mock_backend(result=None, not_found=False, error=None):
    """Create a mock backend with get_element_value configured."""
    mock = MagicMock()
    if error:
        from naturo.errors import NaturoError
        mock.get_element_value.side_effect = NaturoError(error)
    elif not_found:
        mock.get_element_value.return_value = None
    else:
        mock.get_element_value.return_value = result or _mock_backend_result()
    return mock


# ── CLI Tests ────────────────────────────────────────────────────────────────

def _patch_get(mock_backend):
    """Context manager to patch both backend and platform check for get_cmd."""
    return (
        patch("naturo.cli.get_cmd._get_backend", return_value=mock_backend),
        patch("naturo.cli.get_cmd.platform") if platform.system() not in ("Windows",) else None,
    )


def _apply_patches(mock_backend):
    """Apply both backend and platform patches for get_cmd tests.

    Returns a combined context manager that patches _get_backend and
    (on non-Windows) fakes platform.system() to return 'Windows'.
    """
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        with patch("naturo.cli.get_cmd._get_backend", return_value=mock_backend):
            if platform.system() not in ("Windows",):
                with patch("naturo.cli.get_cmd.platform") as mock_plat:
                    mock_plat.system.return_value = "Windows"
                    yield
            else:
                yield

    return _ctx()


class TestGetCLI:
    """Tests for the ``naturo get`` CLI command."""

    def test_get_by_ref_plain(self):
        """Get element value by ref in plain text mode."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["get", "e47"])

        assert result.exit_code == 0
        assert "Edit" in result.output
        assert "Search" in result.output
        assert "Hello World" in result.output
        mock.get_element_value.assert_called_once_with(
            ref="e47",
            automation_id=None,
            role=None,
            name=None,
            window_title=None,
            hwnd=None,
        )

    def test_get_by_ref_json(self):
        """Get element value by ref with --json flag."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["--json", "get", "e47"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["value"] == "Hello World"
        assert data["pattern"] == "ValuePattern"
        assert data["role"] == "Edit"
        assert data["ref"] == "e47"

    def test_get_by_automation_id(self):
        """Get element value by AutomationId."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["get", "--aid", "txtSearch"])

        assert result.exit_code == 0
        mock.get_element_value.assert_called_once_with(
            ref=None,
            automation_id="txtSearch",
            role=None,
            name=None,
            window_title=None,
            hwnd=None,
        )

    def test_get_by_role_and_name(self):
        """Get element value by role + name."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["get", "--role", "Edit", "--name", "Search"])

        assert result.exit_code == 0
        mock.get_element_value.assert_called_once_with(
            ref=None,
            automation_id=None,
            role="Edit",
            name="Search",
            window_title=None,
            hwnd=None,
        )

    def test_get_property_filter(self):
        """Get only a specific property with -p."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["get", "e47", "-p", "value"])

        assert result.exit_code == 0
        assert result.output.strip() == "Hello World"

    def test_get_property_filter_role(self):
        """Get role property with -p."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["get", "e47", "-p", "role"])

        assert result.exit_code == 0
        assert result.output.strip() == "Edit"

    def test_get_not_found_plain(self):
        """Element not found shows error in plain mode."""
        mock = _make_mock_backend(not_found=True)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["get", "e99"])

        assert result.exit_code != 0

    def test_get_not_found_json(self):
        """Element not found shows error in JSON mode."""
        mock = _make_mock_backend(not_found=True)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["--json", "get", "e99"])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert "error" in data

    def test_get_no_target_error(self):
        """No target argument shows usage error."""
        runner = CliRunner()
        result = runner.invoke(main, ["get"])
        assert result.exit_code != 0

    def test_get_with_window_title(self):
        """Get element value with --title option."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "get", "e47", "--title", "Notepad"
            ])

        assert result.exit_code == 0
        mock.get_element_value.assert_called_once_with(
            ref="e47",
            automation_id=None,
            role=None,
            name=None,
            window_title="Notepad",
            hwnd=None,
        )

    def test_get_with_hwnd(self):
        """Get element value with --hwnd option."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "get", "e47", "--hwnd", "12345"
            ])

        assert result.exit_code == 0
        mock.get_element_value.assert_called_once_with(
            ref="e47",
            automation_id=None,
            role=None,
            name=None,
            window_title=None,
            hwnd=12345,
        )

    def test_get_target_as_automation_id(self):
        """Non-ref target string treated as automation ID."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["get", "txtSearch"])

        assert result.exit_code == 0
        mock.get_element_value.assert_called_once_with(
            ref=None,
            automation_id="txtSearch",
            role=None,
            name=None,
            window_title=None,
            hwnd=None,
        )

    def test_get_msaa_ref(self):
        """MSAA ref (m3) parsed correctly."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["get", "m3"])

        assert result.exit_code == 0
        mock.get_element_value.assert_called_once_with(
            ref="m3",
            automation_id=None,
            role=None,
            name=None,
            window_title=None,
            hwnd=None,
        )

    def test_get_null_value(self):
        """Element with null value (no pattern support) shows proper message."""
        result_dict = _mock_backend_result()
        result_dict["value"] = None
        result_dict["pattern"] = None
        mock = _make_mock_backend(result=result_dict)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["get", "e47"])

        assert result.exit_code == 0
        assert "none" in result.output.lower()

    def test_get_checkbox_toggle_value(self):
        """Checkbox element returns TogglePattern value."""
        result_dict = {
            "value": "On",
            "pattern": "TogglePattern",
            "role": "CheckBox",
            "name": "Remember me",
            "automation_id": "chkRemember",
            "x": 50, "y": 300, "width": 100, "height": 20,
        }
        mock = _make_mock_backend(result=result_dict)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["get", "e10"])

        assert result.exit_code == 0
        assert "On" in result.output
        assert "CheckBox" in result.output

    def test_get_json_local_flag(self):
        """JSON flag on the get command itself works."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["get", "e47", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["value"] == "Hello World"

    def test_get_no_target_json_error_format(self):
        """No target in JSON mode returns standard error format with code."""
        runner = CliRunner()
        result = runner.invoke(main, ["--json", "get"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "message" in data["error"]

    def test_get_not_found_json_error_format(self):
        """Element not found in JSON mode returns standard error format."""
        mock = _make_mock_backend(not_found=True)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["--json", "get", "e99"])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "ELEMENT_NOT_FOUND"
        assert "suggested_action" in data["error"]

    def test_get_naturo_error_json_format(self):
        """NaturoError in JSON mode returns standard error format."""
        mock = _make_mock_backend(error="backend failure")
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["--json", "get", "e1"])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]


# ── Bridge Tests (unit-level mock) ───────────────────────────────────────────

class TestGetElementValueBridge:
    """Tests for NaturoCore.get_element_value bridge method."""

    def test_bridge_returns_dict(self):
        """Bridge returns parsed JSON dict from DLL."""
        from naturo.bridge import NaturoCore

        mock_lib = MagicMock()
        mock_response = json.dumps({
            "value": "test",
            "pattern": "ValuePattern",
            "role": "Edit",
            "name": "Field",
            "automation_id": "txtField",
            "x": 10, "y": 20, "width": 100, "height": 30,
        }).encode("utf-8")

        def fake_get(hwnd, aid, role, name, buf, size):
            buf.value = mock_response
            return 0

        mock_lib.naturo_get_element_value = MagicMock(side_effect=fake_get)

        core = NaturoCore.__new__(NaturoCore)
        core._lib = mock_lib
        core._initialized = True

        result = core.get_element_value(
            hwnd=0, automation_id="txtField"
        )
        assert result is not None
        assert result["value"] == "test"
        assert result["pattern"] == "ValuePattern"

    def test_bridge_not_found(self):
        """Bridge returns None when element not found (rc=1)."""
        from naturo.bridge import NaturoCore

        mock_lib = MagicMock()
        mock_lib.naturo_get_element_value = MagicMock(return_value=1)

        core = NaturoCore.__new__(NaturoCore)
        core._lib = mock_lib
        core._initialized = True

        result = core.get_element_value(hwnd=0, role="Edit", name="Missing")
        assert result is None

    def test_bridge_error_raises(self):
        """Bridge raises NaturoCoreError on negative return code."""
        from naturo.bridge import NaturoCore, NaturoCoreError

        mock_lib = MagicMock()
        mock_lib.naturo_get_element_value = MagicMock(return_value=-1)

        core = NaturoCore.__new__(NaturoCore)
        core._lib = mock_lib
        core._initialized = True

        with pytest.raises(NaturoCoreError):
            core.get_element_value(hwnd=0, automation_id="test")
