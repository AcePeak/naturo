"""Tests for naturo.wait — wait polling, timeout, found/not-found, and CLI duration."""
import json
import time
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from click.testing import CliRunner
from naturo.cli.wait_cmd import wait as wait_cmd
from naturo.wait import wait_for_element, wait_until_gone, wait_for_window, WaitResult
from naturo.backends.base import ElementInfo, WindowInfo


def _make_element(name="Save", role="Button"):
    return ElementInfo(
        id="e1", role=role, name=name, value=None,
        x=10, y=20, width=100, height=30, children=[], properties={},
    )


def _make_window(title="Notepad"):
    return WindowInfo(
        handle=123, title=title, process_name="notepad.exe",
        pid=1000, x=0, y=0, width=800, height=600,
        is_visible=True, is_minimized=False,
    )


class TestWaitResult:
    def test_default(self):
        r = WaitResult(found=True)
        assert r.found is True
        assert r.element is None
        assert r.wait_time == 0.0
        assert r.warnings == []

    def test_with_element(self):
        el = _make_element()
        r = WaitResult(found=True, element=el, wait_time=1.5)
        assert r.element.name == "Save"
        assert r.wait_time == 1.5


class TestWaitForElement:
    def test_found_immediately(self):
        backend = MagicMock()
        backend.find_element.return_value = _make_element()

        result = wait_for_element("Button:Save", timeout=2.0, backend=backend)
        assert result.found is True
        assert result.element is not None
        assert result.element.name == "Save"
        assert result.wait_time < 1.0

    def test_found_after_delay(self):
        backend = MagicMock()
        call_count = [0]

        def find_side_effect(selector, window_title=None):
            call_count[0] += 1
            if call_count[0] >= 3:
                return _make_element()
            return None

        backend.find_element.side_effect = find_side_effect

        result = wait_for_element(
            "Button:Save", timeout=5.0, poll_interval=0.05, backend=backend,
        )
        assert result.found is True
        assert result.element is not None
        assert call_count[0] >= 3

    def test_timeout(self):
        backend = MagicMock()
        backend.find_element.return_value = None

        result = wait_for_element(
            "Button:Save", timeout=0.2, poll_interval=0.05, backend=backend,
        )
        assert result.found is False
        assert result.element is None
        assert result.wait_time >= 0.15

    def test_with_window_title(self):
        backend = MagicMock()
        backend.find_element.return_value = _make_element()

        result = wait_for_element(
            "Button:Save", window_title="Notepad", timeout=2.0, backend=backend,
        )
        assert result.found is True
        backend.find_element.assert_called_with("Button:Save", window_title="Notepad")

    def test_handles_poll_errors(self):
        backend = MagicMock()
        call_count = [0]

        def find_side_effect(selector, window_title=None):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("COM error")
            return _make_element()

        backend.find_element.side_effect = find_side_effect

        result = wait_for_element(
            "Button:Save", timeout=2.0, poll_interval=0.05, backend=backend,
        )
        assert result.found is True
        assert len(result.warnings) >= 1
        assert "COM error" in result.warnings[0]


class TestWaitUntilGone:
    def test_gone_immediately(self):
        backend = MagicMock()
        backend.find_element.return_value = None

        result = wait_until_gone("Dialog:Loading", timeout=2.0, backend=backend)
        assert result.found is True
        assert result.element is None

    def test_gone_after_delay(self):
        backend = MagicMock()
        call_count = [0]

        def find_side_effect(selector, window_title=None):
            call_count[0] += 1
            if call_count[0] >= 3:
                return None
            return _make_element(name="Loading", role="Dialog")

        backend.find_element.side_effect = find_side_effect

        result = wait_until_gone(
            "Dialog:Loading", timeout=5.0, poll_interval=0.05, backend=backend,
        )
        assert result.found is True

    def test_timeout_still_present(self):
        backend = MagicMock()
        backend.find_element.return_value = _make_element(name="Loading")

        result = wait_until_gone(
            "Dialog:Loading", timeout=0.2, poll_interval=0.05, backend=backend,
        )
        assert result.found is False

    def test_error_treated_as_gone(self):
        backend = MagicMock()
        backend.find_element.side_effect = RuntimeError("Window closed")

        result = wait_until_gone(
            "Dialog:Loading", timeout=2.0, backend=backend,
        )
        assert result.found is True
        assert len(result.warnings) >= 1


class TestWaitForWindow:
    def test_found_immediately(self):
        backend = MagicMock()
        backend.list_windows.return_value = [_make_window("Notepad")]

        result = wait_for_window("Notepad", timeout=2.0, backend=backend)
        assert result.found is True
        assert result.element is not None
        assert result.element.name == "Notepad"

    def test_case_insensitive_match(self):
        backend = MagicMock()
        backend.list_windows.return_value = [_make_window("NOTEPAD - Untitled")]

        result = wait_for_window("notepad", timeout=2.0, backend=backend)
        assert result.found is True

    def test_timeout(self):
        backend = MagicMock()
        backend.list_windows.return_value = []

        result = wait_for_window("Notepad", timeout=0.2, poll_interval=0.05, backend=backend)
        assert result.found is False

    def test_found_after_delay(self):
        backend = MagicMock()
        call_count = [0]

        def list_side_effect():
            call_count[0] += 1
            if call_count[0] >= 3:
                return [_make_window("Notepad")]
            return []

        backend.list_windows.side_effect = list_side_effect

        result = wait_for_window(
            "Notepad", timeout=5.0, poll_interval=0.05, backend=backend,
        )
        assert result.found is True


class TestWaitDurationCLI:
    """Tests for the simple duration mode: naturo wait <seconds>."""

    def test_wait_duration_basic(self):
        runner = CliRunner()
        start = time.monotonic()
        result = runner.invoke(wait_cmd, ["0.1"])
        elapsed = time.monotonic() - start
        assert result.exit_code == 0
        assert "Waited" in result.output
        assert elapsed >= 0.09

    def test_wait_duration_json(self):
        runner = CliRunner()
        result = runner.invoke(wait_cmd, ["0.1", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["mode"] == "duration"
        assert data["wait_time"] == 0.1

    def test_wait_duration_zero(self):
        runner = CliRunner()
        result = runner.invoke(wait_cmd, ["0"])
        assert result.exit_code == 0
        assert "Waited" in result.output

    def test_wait_duration_negative_error(self):
        runner = CliRunner()
        result = runner.invoke(wait_cmd, ["-1"])
        # Click may interpret -1 as an option; either way should not succeed silently
        assert result.exit_code != 0 or "Error" in (result.output + (result.output or ""))

    def test_wait_duration_with_condition_error(self):
        runner = CliRunner()
        result = runner.invoke(wait_cmd, ["3", "--element", "Button:Save"])
        assert result.exit_code != 0
        assert "Cannot combine" in result.output

    def test_wait_no_args_error(self):
        runner = CliRunner()
        result = runner.invoke(wait_cmd, [])
        assert result.exit_code != 0
        assert "Specify a duration" in result.output or "Error" in result.output

    def test_wait_no_args_json_error(self):
        runner = CliRunner()
        result = runner.invoke(wait_cmd, ["--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert "error" in data or "code" in data
