"""Unit tests for naturo._winproc — the resilient Windows process-info layer.

Covers the pure parsers (wmic list/csv + CIM JSON) against captured sample output
and the wmic->CIM fallback dispatch (wmic present = authoritative; wmic absent =
CIM). No live processes are spawned."""
from unittest.mock import patch

from naturo import _winproc


# ── _parse_list_field ───────────────────────────────────────────────────────

def test_parse_list_field_extracts_value():
    out = "\r\nCommandLine=C:\\App\\app.exe --flag\r\n\r\n"
    assert _winproc._parse_list_field(out, "CommandLine") == "C:\\App\\app.exe --flag"


def test_parse_list_field_missing_returns_none():
    assert _winproc._parse_list_field("ExecutablePath=C:\\x.exe", "CommandLine") is None


# ── _parse_bulk_csv ──────────────────────────────────────────────────────────

def test_parse_bulk_csv_maps_pid_to_info():
    out = (
        "Node,CommandLine,ExecutablePath,ProcessId\r\n"
        "HOST,C:\\a.exe --x,C:\\a.exe,1234\r\n"
        "HOST,C:\\b.exe,C:\\b.exe,5678\r\n"
    )
    info = _winproc._parse_bulk_csv(out)
    assert info[1234] == {"command_line": "C:\\a.exe --x", "exe_path": "C:\\a.exe"}
    assert info[5678]["exe_path"] == "C:\\b.exe"


def test_parse_bulk_csv_no_header_returns_empty():
    assert _winproc._parse_bulk_csv("garbage\r\nmore garbage") == {}


# ── _parse_parent_csv ────────────────────────────────────────────────────────

def test_parse_parent_csv_builds_child_to_parent():
    # wmic csv is alphabetical: Node,ParentProcessId,ProcessId
    out = (
        "Node,ParentProcessId,ProcessId\r\n"
        "HOST,100,200\r\n"
        "HOST,200,300\r\n"
    )
    parents = _winproc._parse_parent_csv(out)
    assert parents == {200: 100, 300: 200}


def test_parse_parent_csv_skips_non_numeric():
    out = "Node,ParentProcessId,ProcessId\r\nHOST,x,y\r\nHOST,1,2\r\n"
    assert _winproc._parse_parent_csv(out) == {2: 1}


# ── _parse_cim_json ──────────────────────────────────────────────────────────

def test_parse_cim_json_array():
    rows = _winproc._parse_cim_json('[{"ProcessId":1},{"ProcessId":2}]')
    assert [r["ProcessId"] for r in rows] == [1, 2]


def test_parse_cim_json_single_object_wrapped_to_list():
    # ConvertTo-Json emits a bare object for a single match
    rows = _winproc._parse_cim_json('{"ProcessId":42,"CommandLine":"x"}')
    assert rows == [{"ProcessId": 42, "CommandLine": "x"}]


def test_parse_cim_json_garbage_returns_empty():
    assert _winproc._parse_cim_json("not json") == []
    assert _winproc._parse_cim_json("") == []


# ── fallback dispatch ────────────────────────────────────────────────────────

def test_command_line_uses_wmic_when_available():
    with patch.object(_winproc, "_run_wmic", return_value="CommandLine=C:\\x.exe --a"), \
         patch.object(_winproc, "_cim_query") as mock_cim:
        assert _winproc.command_line(1234) == "C:\\x.exe --a"
        mock_cim.assert_not_called()  # wmic authoritative — no fallback


def test_command_line_falls_back_to_cim_when_wmic_absent():
    with patch.object(_winproc, "_run_wmic", return_value=None), \
         patch.object(_winproc, "_cim_query",
                      return_value=[{"CommandLine": "C:\\y.exe --b"}]):
        assert _winproc.command_line(1234) == "C:\\y.exe --b"


def test_bulk_info_falls_back_to_cim_when_wmic_absent():
    with patch.object(_winproc, "_run_wmic", return_value=None), \
         patch.object(_winproc, "_cim_query", return_value=[
             {"ProcessId": 7, "CommandLine": "c", "ExecutablePath": "e"},
             {"ProcessId": "bad"},  # non-int pid skipped
         ]):
        info = _winproc.bulk_process_info()
        assert info == {7: {"command_line": "c", "exe_path": "e"}}


def test_parent_map_falls_back_to_cim_when_wmic_absent():
    with patch.object(_winproc, "_run_wmic", return_value=None), \
         patch.object(_winproc, "_cim_query", return_value=[
             {"ProcessId": 20, "ParentProcessId": 10},
             {"ProcessId": 30},  # missing ppid skipped
         ]):
        assert _winproc.parent_map() == {20: 10}
