"""Tests for naturo.cli.table — shared CLI table output utility."""

import json

import pytest
from click.testing import CliRunner

import click
from naturo.cli.table import print_table


@pytest.fixture
def runner():
    return CliRunner()


def _invoke_print_table(runner, **kwargs):
    """Helper: invoke print_table inside a Click context and capture output."""

    @click.command()
    def cmd():
        print_table(**kwargs)

    return runner.invoke(cmd)


class TestTextOutput:
    """Text-mode table rendering."""

    def test_basic_table(self, runner):
        result = _invoke_print_table(
            runner,
            headers=["NAME", "AGE"],
            rows=[["Alice", "30"], ["Bob", "25"]],
        )
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert "NAME" in lines[0]
        assert "AGE" in lines[0]
        assert "---" in lines[1]
        assert "Alice" in lines[2]
        assert "Bob" in lines[3]
        assert "2 rows." in lines[-1]

    def test_empty_rows(self, runner):
        result = _invoke_print_table(
            runner,
            headers=["NAME"],
            rows=[],
        )
        assert result.exit_code == 0
        assert "No items found." in result.output

    def test_custom_count_label(self, runner):
        result = _invoke_print_table(
            runner,
            headers=["PID"],
            rows=[["123"], ["456"]],
            count_label="2 processes",
        )
        assert result.exit_code == 0
        assert "2 processes" in result.output
        assert "2 rows." not in result.output

    def test_column_width_adapts_to_long_values(self, runner):
        result = _invoke_print_table(
            runner,
            headers=["X"],
            rows=[["a very long cell value"]],
        )
        assert result.exit_code == 0
        assert "a very long cell value" in result.output

    def test_short_row_pads_missing_cells(self, runner):
        result = _invoke_print_table(
            runner,
            headers=["A", "B", "C"],
            rows=[["only_one"]],
        )
        assert result.exit_code == 0
        assert "only_one" in result.output


class TestJsonOutput:
    """JSON-mode table rendering."""

    def test_json_basic(self, runner):
        result = _invoke_print_table(
            runner,
            headers=["NAME", "PID"],
            rows=[["calc", "100"], ["notepad", "200"]],
            json_output=True,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 2
        assert data["items"][0] == {"name": "calc", "pid": "100"}
        assert data["items"][1] == {"name": "notepad", "pid": "200"}

    def test_json_custom_key(self, runner):
        result = _invoke_print_table(
            runner,
            headers=["TITLE"],
            rows=[["My Window"]],
            json_output=True,
            json_key="windows",
        )
        data = json.loads(result.output)
        assert "windows" in data
        assert data["windows"][0]["title"] == "My Window"

    def test_json_extra_fields(self, runner):
        result = _invoke_print_table(
            runner,
            headers=["A"],
            rows=[["1"]],
            json_output=True,
            json_extra={"app": "notepad", "pid": 42},
        )
        data = json.loads(result.output)
        assert data["app"] == "notepad"
        assert data["pid"] == 42

    def test_json_empty_rows(self, runner):
        result = _invoke_print_table(
            runner,
            headers=["NAME"],
            rows=[],
            json_output=True,
        )
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 0
        assert data["items"] == []

    def test_json_header_normalization(self, runner):
        result = _invoke_print_table(
            runner,
            headers=["Process Name", "Window Handle"],
            rows=[["calc", "0x1234"]],
            json_output=True,
        )
        data = json.loads(result.output)
        item = data["items"][0]
        assert "process_name" in item
        assert "window_handle" in item

    def test_json_short_row(self, runner):
        result = _invoke_print_table(
            runner,
            headers=["A", "B"],
            rows=[["only_a"]],
            json_output=True,
        )
        data = json.loads(result.output)
        assert data["items"][0] == {"a": "only_a", "b": ""}
