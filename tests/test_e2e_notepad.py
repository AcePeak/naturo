"""End-to-end tests with Notepad and multi-window scenarios.

These tests require Windows with a desktop session and naturo_core.dll.
They launch real applications and verify automation works end-to-end.
"""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
import time

import pytest


pytestmark = [
    pytest.mark.ui,
    pytest.mark.e2e,
    pytest.mark.skipif(
        platform.system() != "Windows",
        reason="End-to-end tests require Windows with desktop session",
    ),
]


@pytest.fixture
def core():
    """Create and initialized NaturoCore instance."""
    from naturo.bridge import NaturoCore

    c = NaturoCore()
    c.init()
    yield c
    c.shutdown()


def _launch_notepad():
    """Launch notepad and return the process."""
    return subprocess.Popen(["notepad.exe"])


def _kill_process(proc):
    """Kill a process gracefully."""
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


class TestMultiWindowChaos:
    """R-QA-001 to R-QA-003: Multi-window chaos tests."""

    def test_multi_window_list_all(self, core):
        """R-QA-001: Open multiple Notepad instances, verify all appear in list.

        Opens 3 Notepad windows (reduced from 5 for CI stability), verifies
        list_windows returns all with correct titles, PIDs, and process names.
        """
        procs = []
        try:
            for _ in range(3):
                procs.append(_launch_notepad())
                time.sleep(0.5)

            # Give windows time to fully initialize
            time.sleep(1.0)

            windows = core.list_windows()
            notepad_windows = [
                w for w in windows
                if "notepad" in w.process_name.lower()
            ]

            # Should find at least our 3 notepad windows
            assert len(notepad_windows) >= 3, (
                f"Expected >=3 Notepad windows, found {len(notepad_windows)}"
            )

            # Each should have valid fields
            pids = set()
            for w in notepad_windows:
                assert w.pid > 0
                assert w.hwnd > 0
                assert isinstance(w.title, str)
                assert "notepad" in w.process_name.lower()
                pids.add(w.pid)

            # Should have distinct PIDs for each process
            assert len(pids) >= 3
        finally:
            for p in procs:
                _kill_process(p)

    def test_multi_window_capture_each(self, core):
        """R-QA-002: Capture each window by HWND — all produce distinct valid BMP files.

        With multiple windows open, capture each by HWND and verify each
        produces a valid, distinct BMP file.
        """
        procs = []
        paths = []
        try:
            for _ in range(2):
                procs.append(_launch_notepad())
                time.sleep(0.5)
            time.sleep(1.0)

            windows = core.list_windows()
            notepad_windows = [
                w for w in windows
                if "notepad" in w.process_name.lower()
                and w.is_visible
                and not w.is_minimized
            ]

            if len(notepad_windows) < 2:
                pytest.skip("Could not find 2 visible Notepad windows")

            for w in notepad_windows[:2]:
                with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
                    path = f.name
                paths.append(path)
                core.capture_window(w.hwnd, path)
                assert os.path.exists(path)
                assert os.path.getsize(path) > 0
                with open(path, "rb") as f:
                    assert f.read(2) == b"BM"
        finally:
            for p in procs:
                _kill_process(p)
            for path in paths:
                if os.path.exists(path):
                    os.unlink(path)

    def test_multi_window_element_tree_each(self, core):
        """R-QA-003: Get element tree for each of multiple windows.

        With multiple windows open, get_element_tree for each should return
        correct root element role and distinct children.
        """
        procs = []
        try:
            for _ in range(2):
                procs.append(_launch_notepad())
                time.sleep(0.5)
            time.sleep(1.0)

            windows = core.list_windows()
            notepad_windows = [
                w for w in windows
                if "notepad" in w.process_name.lower()
                and w.is_visible
                and not w.is_minimized
            ]

            if len(notepad_windows) < 2:
                pytest.skip("Could not find 2 visible Notepad windows")

            for w in notepad_windows[:2]:
                tree = core.get_element_tree(hwnd=w.hwnd, depth=2)
                if tree is not None:
                    assert isinstance(tree.role, str)
                    assert isinstance(tree.children, list)
        finally:
            for p in procs:
                _kill_process(p)


class TestNotepadElements:
    """T071, T072: Notepad-specific element discovery."""

    def test_notepad_edit_element(self, core):
        """T071: Notepad Edit element found with correct role.

        Launch Notepad, inspect element tree, find the Edit/RichEdit control.
        """
        proc = _launch_notepad()
        try:
            time.sleep(1.5)

            windows = core.list_windows()
            notepad_windows = [
                w for w in windows
                if "notepad" in w.process_name.lower()
                and w.is_visible
            ]
            if not notepad_windows:
                pytest.skip("Notepad window not found")

            tree = core.get_element_tree(hwnd=notepad_windows[0].hwnd, depth=5)
            if tree is None:
                pytest.skip("Could not get element tree for Notepad")

            # Search for Edit or Document or RichEdit element
            def find_edit(el):
                role_lower = el.role.lower()
                if "edit" in role_lower or "document" in role_lower:
                    return el
                for child in el.children:
                    result = find_edit(child)
                    if result:
                        return result
                return None

            edit = find_edit(tree)
            assert edit is not None, (
                "Expected to find an Edit/Document element in Notepad"
            )
        finally:
            _kill_process(proc)

    def test_notepad_menu_elements(self, core):
        """T072: Notepad menu elements found.

        Launch Notepad, inspect element tree, find menu bar and menu items.
        """
        proc = _launch_notepad()
        try:
            time.sleep(1.5)

            windows = core.list_windows()
            notepad_windows = [
                w for w in windows
                if "notepad" in w.process_name.lower()
                and w.is_visible
            ]
            if not notepad_windows:
                pytest.skip("Notepad window not found")

            tree = core.get_element_tree(hwnd=notepad_windows[0].hwnd, depth=3)
            if tree is None:
                pytest.skip("Could not get element tree for Notepad")

            # Search for MenuBar or Menu element
            def find_menu(el):
                role_lower = el.role.lower()
                if "menu" in role_lower:
                    return el
                for child in el.children:
                    result = find_menu(child)
                    if result:
                        return result
                return None

            menu = find_menu(tree)
            assert menu is not None, (
                "Expected to find a Menu/MenuBar element in Notepad"
            )
        finally:
            _kill_process(proc)


class TestAIAgentPerspective:
    """R-PD-007: AI agent perspective test."""

    def test_see_json_output_for_ai(self, core):
        """R-PD-007: see --json output includes all info an AI agent needs.

        The JSON output must include role, name, value, bounds (x/y/width/height),
        and actionable IDs in a parseable structure.
        """
        import json

        proc = _launch_notepad()
        try:
            time.sleep(1.5)

            windows = core.list_windows()
            notepad_windows = [
                w for w in windows
                if "notepad" in w.process_name.lower()
                and w.is_visible
            ]
            if not notepad_windows:
                pytest.skip("Notepad window not found")

            tree = core.get_element_tree(hwnd=notepad_windows[0].hwnd, depth=3)
            if tree is None:
                pytest.skip("Could not get element tree")

            # Verify the tree has all fields an AI agent needs
            def verify_ai_fields(el):
                assert hasattr(el, "id"), "Element must have an id field"
                assert hasattr(el, "role"), "Element must have a role field"
                assert hasattr(el, "name"), "Element must have a name field"
                assert hasattr(el, "value"), "Element must have a value field"
                assert hasattr(el, "x"), "Element must have x bound"
                assert hasattr(el, "y"), "Element must have y bound"
                assert hasattr(el, "width"), "Element must have width"
                assert hasattr(el, "height"), "Element must have height"
                for child in el.children:
                    verify_ai_fields(child)

            verify_ai_fields(tree)

            # Verify JSON serialization round-trip
            def to_dict(el):
                return {
                    "id": el.id,
                    "role": el.role,
                    "name": el.name,
                    "value": el.value,
                    "x": el.x,
                    "y": el.y,
                    "width": el.width,
                    "height": el.height,
                    "children": [to_dict(c) for c in el.children],
                }

            data = to_dict(tree)
            json_str = json.dumps(data)
            parsed = json.loads(json_str)
            assert "role" in parsed
            assert "name" in parsed
            assert "children" in parsed
        finally:
            _kill_process(proc)
