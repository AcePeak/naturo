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
import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli import main

# Resolve the *module* (not the Click Command object that shadows it in
# naturo.cli's namespace).  On Python 3.9 ``mock.patch()`` uses the old
# ``_importer`` which walks ``getattr`` and finds the Command; on 3.11+
# it uses ``pkgutil.resolve_name`` which finds the module.  Using
# ``patch.object`` with the real module works on every Python version.
_get_cmd_mod = sys.modules["naturo.cli.values._get"]


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

def _apply_patches(mock_backend):
    """Apply both backend and platform patches for get_cmd tests.

    Returns a combined context manager that patches _get_backend and
    (on non-Windows) fakes platform.system() to return 'Windows'.
    """
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        with patch.object(_get_cmd_mod, "_get_backend", return_value=mock_backend):
            if platform.system() not in ("Windows",):
                with patch.object(_get_cmd_mod, "platform") as mock_plat:
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
            app=None,
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
            app=None,
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
            app=None,
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
            app=None,
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
            app=None,
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
            app=None,
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
            app=None,
            window_title=None,
            hwnd=None,
        )

    def test_get_null_value_no_name(self):
        """Element with null value and empty name shows 'no readable pattern'."""
        result_dict = _mock_backend_result()
        result_dict["value"] = None
        result_dict["pattern"] = None
        result_dict["name"] = ""
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


class TestRoleAliasFallback:
    """Tests for role alias fallback in get_element_value (#352)."""

    def test_edit_falls_back_to_document(self):
        """When role='Edit' fails, should try 'Document' as alias (#352).

        Win11 Notepad's text editor uses role 'Document', not 'Edit'.
        """
        from unittest.mock import patch, MagicMock, call

        mock_core = MagicMock()
        # First call with role='Edit' returns None (not found)
        # Second call with role='Document' returns a result
        mock_core.get_element_value.side_effect = [
            None,  # role='Edit' → not found
            {"value": "Hello", "role": "Document", "name": "Text Editor",
             "pattern": "TextPattern", "automation_id": "", "x": 0, "y": 0,
             "width": 800, "height": 600},  # role='Document' → found
        ]

        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = mock_core

        with patch.object(backend, '_ensure_core', return_value=mock_core):
            result = backend.get_element_value(role="Edit", hwnd=12345)

        assert result is not None
        assert result["role"] == "Document"
        assert result["value"] == "Hello"
        # Should have been called twice: once with Edit, once with Document
        assert mock_core.get_element_value.call_count == 2

    def test_no_fallback_when_first_role_succeeds(self):
        """When the initial role lookup succeeds, no alias fallback needed."""
        from unittest.mock import patch, MagicMock

        mock_core = MagicMock()
        mock_core.get_element_value.return_value = {
            "value": "Hello", "role": "Edit", "name": "Search",
            "pattern": "ValuePattern", "automation_id": "txtSearch",
            "x": 0, "y": 0, "width": 200, "height": 30,
        }

        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = mock_core

        with patch.object(backend, '_ensure_core', return_value=mock_core):
            result = backend.get_element_value(role="Edit", hwnd=12345)

        assert result is not None
        assert result["role"] == "Edit"
        # Only called once — no fallback needed
        assert mock_core.get_element_value.call_count == 1

    def test_no_alias_fallback_with_automation_id(self):
        """Role alias fallback should not trigger when automation_id is set."""
        from unittest.mock import patch, MagicMock

        mock_core = MagicMock()
        mock_core.get_element_value.return_value = None  # Not found

        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = mock_core

        with patch.object(backend, '_ensure_core', return_value=mock_core):
            result = backend.get_element_value(
                role="Edit", automation_id="txtMissing", hwnd=12345,
            )

        assert result is None
        # Only one call — no alias fallback because automation_id is set
        assert mock_core.get_element_value.call_count == 1


class TestNamePropertyFallback:
    """Tests for NameProperty fallback when no UIA pattern returns a value (#521)."""

    def test_name_fallback_when_value_is_null(self):
        """When C++ core returns value=null but name is set, use name as value."""
        from unittest.mock import patch, MagicMock

        mock_core = MagicMock()
        mock_core.get_element_value.return_value = {
            "value": None,
            "pattern": None,
            "role": "Text",
            "name": "\u663e\u793a\u4e3a 579",
            "automation_id": "CalculatorResults",
            "x": 10, "y": 20, "width": 200, "height": 40,
        }

        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = mock_core

        with patch.object(backend, '_ensure_core', return_value=mock_core):
            result = backend.get_element_value(
                automation_id="CalculatorResults", hwnd=12345,
            )

        assert result is not None
        assert result["value"] == "\u663e\u793a\u4e3a 579"
        assert result["pattern"] == "NameProperty"

    def test_no_name_fallback_when_value_is_set(self):
        """When C++ core returns a real value, name fallback does not override."""
        from unittest.mock import patch, MagicMock

        mock_core = MagicMock()
        mock_core.get_element_value.return_value = {
            "value": "42",
            "pattern": "ValuePattern",
            "role": "Edit",
            "name": "Amount",
            "automation_id": "txtAmount",
            "x": 10, "y": 20, "width": 200, "height": 30,
        }

        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = mock_core

        with patch.object(backend, '_ensure_core', return_value=mock_core):
            result = backend.get_element_value(
                automation_id="txtAmount", hwnd=12345,
            )

        assert result["value"] == "42"
        assert result["pattern"] == "ValuePattern"

    def test_no_name_fallback_when_name_is_empty(self):
        """When both value and name are empty, no fallback occurs."""
        from unittest.mock import patch, MagicMock

        mock_core = MagicMock()
        mock_core.get_element_value.return_value = {
            "value": None,
            "pattern": None,
            "role": "Pane",
            "name": "",
            "automation_id": "",
            "x": 0, "y": 0, "width": 100, "height": 100,
        }

        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = mock_core

        with patch.object(backend, '_ensure_core', return_value=mock_core):
            result = backend.get_element_value(
                role="Pane", hwnd=12345,
            )

        assert result["value"] is None
        assert result["pattern"] is None

    def test_name_fallback_in_cli_plain_output(self):
        """CLI shows the name-based value instead of 'no readable pattern'."""
        result_dict = {
            "value": "\u663e\u793a\u4e3a 579",
            "pattern": "NameProperty",
            "role": "Text",
            "name": "\u663e\u793a\u4e3a 579",
            "automation_id": "CalculatorResults",
            "x": 10, "y": 20, "width": 200, "height": 40,
        }
        mock = _make_mock_backend(result=result_dict)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["get", "e15"])

        assert result.exit_code == 0
        assert "\u663e\u793a\u4e3a 579" in result.output
        assert "NameProperty" in result.output
        assert "no readable pattern" not in result.output


class TestAppIdOption:
    """Tests for the --app-id option on the get command (#522)."""

    def test_app_id_resolves_to_hwnd_only(self):
        """--app-id resolves to hwnd only, not process_name (#582)."""
        mock = _make_mock_backend()
        runner = CliRunner()

        mock_entry = MagicMock()
        mock_entry.process_name = "C:\\Program Files\\Calculator.exe"
        mock_entry.handle = 67890
        mock_entry.pid = 1234

        mock_id_map = MagicMock()
        mock_id_map.resolve.return_value = mock_entry

        with _apply_patches(mock):
            with patch("naturo.app_ids.get_app_id_map",
                       return_value=mock_id_map):
                result = runner.invoke(main, [
                    "get", "e15", "--app-id", "a1",
                ])

        assert result.exit_code == 0
        # (#582) process_name must NOT leak as app — it may be a full path
        mock.get_element_value.assert_called_once_with(
            ref="e15",
            automation_id=None,
            role=None,
            name=None,
            app=None,
            window_title=None,
            hwnd=67890,
        )

    def test_app_id_not_found_error(self):
        """--app-id with invalid ID shows error."""
        mock = _make_mock_backend()
        runner = CliRunner()

        mock_id_map = MagicMock()
        mock_id_map.resolve.return_value = None

        with _apply_patches(mock):
            with patch("naturo.app_ids.get_app_id_map",
                       return_value=mock_id_map):
                result = runner.invoke(main, [
                    "get", "e15", "--app-id", "a99",
                ])

        assert result.exit_code != 0

    def test_app_id_not_found_json_error(self):
        """--app-id with invalid ID in JSON mode shows structured error."""
        mock = _make_mock_backend()
        runner = CliRunner()

        mock_id_map = MagicMock()
        mock_id_map.resolve.return_value = None

        with _apply_patches(mock):
            with patch("naturo.app_ids.get_app_id_map",
                       return_value=mock_id_map):
                result = runner.invoke(main, [
                    "--json", "get", "e15", "--app-id", "a99",
                ])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert "APP_ID_NOT_FOUND" in data["error"]["code"]


# ── --all flag tests (issue #382) ────────────────────────────────────────────

class TestGetAllFlag:
    """Tests for the ``naturo get --all`` flag."""

    def _make_tree(self):
        """Build a mock element tree with multiple buttons and edits."""
        from naturo.backends.base import ElementInfo
        return ElementInfo(
            id="e0", role="Window", name="Test App", value=None,
            x=0, y=0, width=800, height=600,
            children=[
                ElementInfo(
                    id="e1", role="Button", name="Save", value=None,
                    x=10, y=10, width=80, height=30, children=[], properties={},
                ),
                ElementInfo(
                    id="e2", role="Edit", name="Username", value="alice",
                    x=10, y=50, width=200, height=25, children=[], properties={},
                ),
                ElementInfo(
                    id="e3", role="Button", name="Cancel", value=None,
                    x=100, y=10, width=80, height=30, children=[], properties={},
                ),
                ElementInfo(
                    id="e4", role="Edit", name="Password", value="***",
                    x=10, y=80, width=200, height=25, children=[], properties={},
                ),
                ElementInfo(
                    id="e5", role="Button", name="Help", value=None,
                    x=200, y=10, width=80, height=30, children=[], properties={},
                ),
            ],
            properties={},
        )

    def test_all_buttons_json(self):
        """--all --role Button returns array of all buttons."""
        tree = self._make_tree()
        mock = MagicMock()
        mock.get_element_tree.return_value = tree
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "--json", "get", "--role", "Button", "--all",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 3
        names = [el["name"] for el in data]
        assert "Save" in names
        assert "Cancel" in names
        assert "Help" in names

    def test_all_edits_json(self):
        """--all --role Edit returns array of all edit fields."""
        tree = self._make_tree()
        mock = MagicMock()
        mock.get_element_tree.return_value = tree
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "--json", "get", "--role", "Edit", "--all",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert data[0]["value"] == "alice"
        assert data[1]["value"] == "***"

    def test_all_by_name_json(self):
        """--all --name with substring match."""
        tree = self._make_tree()
        mock = MagicMock()
        mock.get_element_tree.return_value = tree
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "--json", "get", "--name", "Save", "--all",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["name"] == "Save"
        assert data[0]["role"] == "Button"

    def test_all_plain_text(self):
        """--all in plain text mode shows numbered list."""
        tree = self._make_tree()
        mock = MagicMock()
        mock.get_element_tree.return_value = tree
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "get", "--role", "Button", "--all",
            ])

        assert result.exit_code == 0
        assert "3 matching element(s)" in result.output
        assert "Save" in result.output
        assert "Cancel" in result.output
        assert "Help" in result.output

    def test_all_no_matches_json(self):
        """--all with no matching role returns empty array."""
        tree = self._make_tree()
        mock = MagicMock()
        mock.get_element_tree.return_value = tree
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "--json", "get", "--role", "ComboBox", "--all",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data == []

    def test_all_no_matches_plain(self):
        """--all with no matches exits with error in plain mode."""
        tree = self._make_tree()
        mock = MagicMock()
        mock.get_element_tree.return_value = tree
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "get", "--role", "ComboBox", "--all",
            ])

        assert result.exit_code != 0
        assert "No elements found" in result.output

    def test_all_requires_role_or_name(self):
        """--all without --role or --name shows error."""
        runner = CliRunner()
        result = runner.invoke(main, ["get", "--all"])
        assert result.exit_code != 0

    def test_all_with_app_filter(self):
        """--all --app passes app to get_element_tree."""
        tree = self._make_tree()
        mock = MagicMock()
        mock.get_element_tree.return_value = tree
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "--json", "get", "--role", "Button", "--all",
                "--app", "notepad",
            ])

        assert result.exit_code == 0
        mock.get_element_tree.assert_called_once_with(
            app="notepad", window_title=None, hwnd=None,
            depth=20, backend="auto",
        )

    def test_all_includes_bounds(self):
        """--all JSON output includes bounding rect."""
        tree = self._make_tree()
        mock = MagicMock()
        mock.get_element_tree.return_value = tree
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "--json", "get", "--role", "Button", "--all",
            ])

        data = json.loads(result.output)
        first = data[0]
        assert "x" in first
        assert "y" in first
        assert "width" in first
        assert "height" in first
