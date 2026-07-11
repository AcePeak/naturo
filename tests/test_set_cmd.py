"""Tests for the ``naturo set`` CLI command and backend methods.

Covers:
- CLI argument parsing (ref, automation_id, role+name)
- Value setting (ValuePattern)
- Toggle mode (TogglePattern)
- Select mode (SelectionItemPattern)
- Expand/collapse mode (ExpandCollapsePattern)
- JSON and plain text output modes
- Error handling (missing target, missing value, failures)
"""

import json
import platform
import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli import main

# Resolve the *module* (not the Click Command object that shadows it in
# naturo.cli's namespace).  See test_get_cmd.py for detailed explanation.
_set_cmd_mod = sys.modules["naturo.cli.values._set"]


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_mock_backend(
    set_value_result=True,
    toggle_result="On",
    select_result=True,
    expand_result=True,
):
    """Create a mock backend with set/toggle/select/expand methods."""
    mock = MagicMock()
    mock.set_element_value.return_value = set_value_result
    mock.toggle_element.return_value = toggle_result
    mock.select_element.return_value = select_result
    mock.expand_collapse_element.return_value = expand_result
    return mock


def _mock_resolve_identifiers(aid=None, role=None, name=None, coords=None,
                              snap_hwnd=None):
    """Return a mock for _resolve_element_identifiers.

    Mirrors the 5-tuple contract (aid, role, name, coords, window_handle)
    introduced in #1208; ``coords``/``snap_hwnd`` default to ``None`` so
    existing identity-based tests are unaffected.
    """
    def _resolve(ref, automation_id, r, n):
        return (aid or automation_id, role or r, name or n, coords, snap_hwnd)
    return _resolve


@contextmanager
def _apply_patches(mock_backend, resolve_aid=None, resolve_role=None,
                   resolve_name=None):
    """Patch backend, platform, and ref resolution for set_cmd tests."""
    resolver = _mock_resolve_identifiers(
        aid=resolve_aid, role=resolve_role, name=resolve_name,
    )
    with patch.object(_set_cmd_mod, "_get_backend", return_value=mock_backend), \
         patch.object(_set_cmd_mod, "_resolve_element_identifiers",
                      side_effect=resolver):
        if platform.system() not in ("Windows",):
            with patch.object(_set_cmd_mod, "platform") as mock_plat:
                mock_plat.system.return_value = "Windows"
                yield
        else:
            yield


# ── Value Setting Tests ─────────────────────────────────────────────────────


class TestSetValue:
    """Tests for ``naturo set <target> <value>`` (ValuePattern)."""

    def test_set_value_by_ref(self):
        """Set value on element by ref in plain text mode."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["set", "e47", "hello world"])

        assert result.exit_code == 0
        assert "hello world" in result.output
        mock.set_element_value.assert_called_once_with(
            text="hello world",
            hwnd=0,
            name=None,
            automation_id=None,
            role=None,
        )

    def test_set_value_by_ref_json(self):
        """Set value by ref with JSON output."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["--json", "set", "e47", "test"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "set_value"
        assert data["value"] == "test"
        assert data["pattern"] == "ValuePattern"

    def test_set_value_by_automation_id(self):
        """Set value by AutomationId."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "set", "--aid", "txtSearch", "query",
            ])

        assert result.exit_code == 0
        mock.set_element_value.assert_called_once_with(
            text="query",
            hwnd=0,
            name=None,
            automation_id="txtSearch",
            role=None,
        )

    def test_set_value_by_role_and_name(self):
        """Set value by role + name combination."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "set", "--role", "Edit", "--name", "Search", "test",
            ])

        assert result.exit_code == 0
        mock.set_element_value.assert_called_once_with(
            text="test",
            hwnd=0,
            name="Search",
            automation_id=None,
            role="Edit",
        )

    def test_set_value_with_app(self):
        """Set value with --app flag resolves HWND."""
        mock = _make_mock_backend()
        mock._resolve_hwnd.return_value = 12345
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "set", "--aid", "txtField", "--app", "notepad", "hello",
            ])

        assert result.exit_code == 0
        mock._resolve_hwnd.assert_called_once_with(
            app="notepad", window_title=None,
        )
        mock.set_element_value.assert_called_once_with(
            text="hello",
            hwnd=12345,
            name=None,
            automation_id="txtField",
            role=None,
        )

    def test_set_value_with_hwnd(self):
        """Set value with explicit --hwnd."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "set", "--aid", "txtField", "--hwnd", "99999", "data",
            ])

        assert result.exit_code == 0
        mock.set_element_value.assert_called_once_with(
            text="data",
            hwnd=99999,
            name=None,
            automation_id="txtField",
            role=None,
        )

    def test_set_value_failure(self):
        """Set value failure shows error."""
        mock = _make_mock_backend(set_value_result=False)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "set", "--aid", "txtField", "test",
            ])

        assert result.exit_code != 0

    def test_set_value_failure_json(self):
        """Set value failure in JSON mode returns error format."""
        mock = _make_mock_backend(set_value_result=False)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "--json", "set", "--aid", "txtField", "test",
            ])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "SET_VALUE_FAILED"

    def test_set_target_as_automation_id(self):
        """Non-ref target string treated as automation ID."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["set", "txtSearch", "hello"])

        assert result.exit_code == 0
        mock.set_element_value.assert_called_once_with(
            text="hello",
            hwnd=0,
            name=None,
            automation_id="txtSearch",
            role=None,
        )

    def test_set_msaa_ref(self):
        """MSAA ref (m3) parsed correctly as ref."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["set", "m3", "text"])

        assert result.exit_code == 0
        # m3 is a ref, so set_element_value is called without automation_id
        # The ref resolution happens inside the command, but since we mock
        # the backend directly, it passes through
        mock.set_element_value.assert_called_once()


# ── Toggle Tests ────────────────────────────────────────────────────────────


class TestSetToggle:
    """Tests for ``naturo set <target> --toggle`` (TogglePattern)."""

    def test_toggle_by_ref(self):
        """Toggle a checkbox by ref."""
        mock = _make_mock_backend(toggle_result="On")
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["set", "e12", "--toggle"])

        assert result.exit_code == 0
        assert "On" in result.output
        mock.toggle_element.assert_called_once_with(
            hwnd=0,
            automation_id=None,
            role=None,
            name=None,
        )

    def test_toggle_json(self):
        """Toggle with JSON output."""
        mock = _make_mock_backend(toggle_result="Off")
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["--json", "set", "e12", "--toggle"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "toggle"
        assert data["new_state"] == "Off"
        assert data["pattern"] == "TogglePattern"

    def test_toggle_by_automation_id(self):
        """Toggle by AutomationId."""
        mock = _make_mock_backend(toggle_result="On")
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "set", "--aid", "chkRemember", "--toggle",
            ])

        assert result.exit_code == 0
        mock.toggle_element.assert_called_once_with(
            hwnd=0,
            automation_id="chkRemember",
            role=None,
            name=None,
        )

    def test_toggle_failure(self):
        """Toggle failure shows error."""
        mock = _make_mock_backend(toggle_result=None)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["set", "e12", "--toggle"])

        assert result.exit_code != 0

    def test_toggle_failure_json(self):
        """Toggle failure in JSON mode returns error format."""
        mock = _make_mock_backend(toggle_result=None)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "--json", "set", "e12", "--toggle",
            ])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "TOGGLE_FAILED"


# ── Select Tests ────────────────────────────────────────────────────────────


class TestSetSelect:
    """Tests for ``naturo set <target> --select`` (SelectionItemPattern)."""

    def test_select_by_ref(self):
        """Select a list item by ref."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["set", "e8", "--select"])

        assert result.exit_code == 0
        assert "Selected" in result.output
        mock.select_element.assert_called_once_with(
            hwnd=0,
            automation_id=None,
            role=None,
            name=None,
        )

    def test_select_json(self):
        """Select with JSON output."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["--json", "set", "e8", "--select"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "select"
        assert data["pattern"] == "SelectionItemPattern"

    def test_select_failure(self):
        """Select failure shows error."""
        mock = _make_mock_backend(select_result=False)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["set", "e8", "--select"])

        assert result.exit_code != 0

    def test_select_failure_json(self):
        """Select failure in JSON mode returns error format."""
        mock = _make_mock_backend(select_result=False)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "--json", "set", "e8", "--select",
            ])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "SELECT_FAILED"


# ── Expand/Collapse Tests ──────────────────────────────────────────────────


class TestSetExpandCollapse:
    """Tests for ``naturo set <target> --expand/--collapse``."""

    def test_expand_by_ref(self):
        """Expand a combo box by ref."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["set", "e5", "--expand"])

        assert result.exit_code == 0
        assert "Expanded" in result.output
        mock.expand_collapse_element.assert_called_once_with(
            hwnd=0,
            automation_id=None,
            role=None,
            name=None,
            expand=True,
        )

    def test_collapse_by_ref(self):
        """Collapse a combo box by ref."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["set", "e5", "--collapse"])

        assert result.exit_code == 0
        assert "Collapsed" in result.output
        mock.expand_collapse_element.assert_called_once_with(
            hwnd=0,
            automation_id=None,
            role=None,
            name=None,
            expand=False,
        )

    def test_expand_json(self):
        """Expand with JSON output."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["--json", "set", "e5", "--expand"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "expand"
        assert data["pattern"] == "ExpandCollapsePattern"

    def test_collapse_json(self):
        """Collapse with JSON output."""
        mock = _make_mock_backend()
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "--json", "set", "e5", "--collapse",
            ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["action"] == "collapse"

    def test_expand_failure(self):
        """Expand failure shows error."""
        mock = _make_mock_backend(expand_result=False)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, ["set", "e5", "--expand"])

        assert result.exit_code != 0

    def test_expand_failure_json(self):
        """Expand failure in JSON mode returns error format."""
        mock = _make_mock_backend(expand_result=False)
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "--json", "set", "e5", "--expand",
            ])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "EXPAND_FAILED"


# ── Input Validation Tests ──────────────────────────────────────────────────


class TestSetValidation:
    """Tests for input validation in the ``set`` command."""

    def test_no_target_error(self):
        """No target shows usage error."""
        runner = CliRunner()
        result = runner.invoke(main, ["set"])
        assert result.exit_code != 0

    def test_no_value_or_action_error(self):
        """Target without value or action flag shows error."""
        runner = CliRunner()
        with _apply_patches(_make_mock_backend()):
            result = runner.invoke(main, ["set", "--aid", "txtField"])
        assert result.exit_code != 0

    def test_no_value_or_action_json_error(self):
        """Target without value or action in JSON mode returns error."""
        runner = CliRunner()
        with _apply_patches(_make_mock_backend()):
            result = runner.invoke(main, [
                "--json", "set", "--aid", "txtField",
            ])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_multiple_action_flags_error(self):
        """Multiple action flags (--toggle + --select) shows error."""
        runner = CliRunner()
        with _apply_patches(_make_mock_backend()):
            result = runner.invoke(main, [
                "set", "e5", "--toggle", "--select",
            ])
        assert result.exit_code != 0

    def test_toggle_ignores_value_arg(self):
        """--toggle works even if a value argument is provided."""
        mock = _make_mock_backend(toggle_result="On")
        runner = CliRunner()

        with _apply_patches(mock):
            result = runner.invoke(main, [
                "set", "e12", "ignored", "--toggle",
            ])

        # The value "ignored" is technically the VALUE argument but
        # --toggle takes precedence
        assert result.exit_code == 0
        mock.toggle_element.assert_called_once()

    def test_help_output(self):
        """--help shows usage info."""
        runner = CliRunner()
        result = runner.invoke(main, ["set", "--help"])
        assert result.exit_code == 0
        assert "Set element value/state" in result.output
        assert "--toggle" in result.output
        assert "--select" in result.output
        assert "--expand" in result.output
        assert "--collapse" in result.output


# ── App ID Tests (#582) ─────────────────────────────────────────────────────


class TestSetAppId:
    """Tests for the --app-id option on the set command (#582)."""

    def test_app_id_resolves_to_hwnd(self):
        """--app-id resolves to hwnd for element targeting."""
        mock = _make_mock_backend()
        runner = CliRunner()

        mock_entry = MagicMock()
        mock_entry.process_name = "C:\\Program Files\\Calculator.exe"
        mock_entry.handle = 67890
        mock_entry.pid = 1234

        mock_id_map = MagicMock()
        mock_id_map.resolve.return_value = mock_entry

        with _apply_patches(mock, resolve_aid="txtField"):
            with patch("naturo.app_ids.get_app_id_map",
                       return_value=mock_id_map):
                result = runner.invoke(main, [
                    "set", "e47", "hello", "--app-id", "a1",
                ])

        assert result.exit_code == 0
        # hwnd should come from app-id resolution
        mock.set_element_value.assert_called_once_with(
            text="hello",
            hwnd=67890,
            name=None,
            automation_id="txtField",
            role=None,
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
                    "set", "e47", "hello", "--app-id", "a99",
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
                    "--json", "set", "e47", "hello", "--app-id", "a99",
                ])

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert "APP_ID_NOT_FOUND" in data["error"]["code"]

    def test_app_id_does_not_leak_process_name(self):
        """--app-id must not leak process_name as app parameter (#576)."""
        mock = _make_mock_backend()
        runner = CliRunner()

        mock_entry = MagicMock()
        mock_entry.process_name = "C:\\Long\\Path\\app.exe"
        mock_entry.handle = 11111
        mock_entry.pid = 2222

        mock_id_map = MagicMock()
        mock_id_map.resolve.return_value = mock_entry

        with _apply_patches(mock, resolve_aid="txtField"):
            with patch("naturo.app_ids.get_app_id_map",
                       return_value=mock_id_map):
                result = runner.invoke(main, [
                    "set", "e5", "--toggle", "--app-id", "a3",
                ])

        assert result.exit_code == 0
        # toggle_element should get hwnd from app-id, NOT the full path
        mock.toggle_element.assert_called_once_with(
            hwnd=11111,
            automation_id="txtField",
            role=None,
            name=None,
        )

    def test_help_shows_app_id_option(self):
        """--help includes --app-id option."""
        runner = CliRunner()
        result = runner.invoke(main, ["set", "--help"])
        assert result.exit_code == 0
        assert "--app-id" in result.output


# ── RangeValuePattern fallback (Slider/Spinner/ProgressBar) ──────────────────


class TestSetValueRangeValue:
    """set_element_value falls back to RangeValuePattern when a control (e.g. a
    Zoom Slider) has no ValuePattern — and it must not choke on comtypes' NULL
    pointer for the unsupported pattern."""

    @pytest.mark.skipif(platform.system() != "Windows", reason="comtypes/UIA is Windows-only")
    def test_slider_set_via_rangevalue(self):
        from naturo.backends.windows import WindowsBackend

        mod = MagicMock()
        mod.UIA_ValuePatternId = 10002
        mod.UIA_RangeValuePatternId = 10003

        # ValuePattern → a NULL-like (falsy) COM pointer, as comtypes returns for
        # an unsupported pattern. Truthiness must skip it, not QueryInterface it.
        null_vp = MagicMock()
        null_vp.__bool__.return_value = False

        rv_pattern = MagicMock()
        rv_pattern.CurrentIsReadOnly = False
        rv_pattern.CurrentMinimum = 0.0
        rv_pattern.CurrentMaximum = 100.0
        rv_ptr = MagicMock()
        rv_ptr.__bool__.return_value = True
        rv_ptr.QueryInterface.return_value = rv_pattern

        elem = MagicMock()
        elem.GetCurrentPattern.side_effect = (
            lambda pid: rv_ptr if pid == mod.UIA_RangeValuePatternId else null_vp
        )

        b = WindowsBackend.__new__(WindowsBackend)
        with patch.object(b, "_init_comtypes_uia", return_value=(MagicMock(), mod)), \
             patch.object(b, "_resolve_interaction_element", return_value=elem):
            ok = b.set_element_value(text="50", hwnd=1, name="Zoom", role="Slider")

        assert ok is True
        rv_pattern.SetValue.assert_called_once_with(50.0)

    @pytest.mark.skipif(platform.system() != "Windows", reason="comtypes/UIA is Windows-only")
    def test_rangevalue_clamped_to_max(self):
        from naturo.backends.windows import WindowsBackend

        mod = MagicMock()
        mod.UIA_ValuePatternId = 10002
        mod.UIA_RangeValuePatternId = 10003
        null_vp = MagicMock()
        null_vp.__bool__.return_value = False
        rv_pattern = MagicMock()
        rv_pattern.CurrentIsReadOnly = False
        rv_pattern.CurrentMinimum = 0.0
        rv_pattern.CurrentMaximum = 100.0
        rv_ptr = MagicMock()
        rv_ptr.__bool__.return_value = True
        rv_ptr.QueryInterface.return_value = rv_pattern
        elem = MagicMock()
        elem.GetCurrentPattern.side_effect = (
            lambda pid: rv_ptr if pid == mod.UIA_RangeValuePatternId else null_vp
        )
        b = WindowsBackend.__new__(WindowsBackend)
        with patch.object(b, "_init_comtypes_uia", return_value=(MagicMock(), mod)), \
             patch.object(b, "_resolve_interaction_element", return_value=elem):
            ok = b.set_element_value(text="9999", hwnd=1, name="Zoom", role="Slider")
        assert ok is True
        rv_pattern.SetValue.assert_called_once_with(100.0)  # clamped to max
