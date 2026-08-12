"""Tests for #896: UIA accessibility properties in the see/element schema.

Covers the full Python plumbing for the six UIA accessibility properties
(``is_enabled``/IsEnabled, ``is_offscreen``/IsOffscreen, ``help_text``/HelpText,
``localized_control_type``/LocalizedControlType, ``is_keyboard_focusable``/
IsKeyboardFocusable, ``has_keyboard_focus``/HasKeyboardFocus):

* bridge ``ElementInfo`` model + native-JSON parsing,
* ``UIElement`` snapshot model + camelCase to_dict/from_dict round-trip,
* ``assign_stable_refs`` carrying the backend ``properties`` dict → UIElement,
* ``see -j`` serialization emitting each property under a stable snake_case key,
* the ``get_element_a11y_uia`` comtypes reader value mapping.

All hermetic — no live desktop, no native DLL.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.bridge import ElementInfo as BridgeElementInfo
from naturo.bridge._models import _parse_element
from naturo.cli.core._see import see
from naturo.models.snapshot import UIElement
from naturo.refs import assign_stable_refs


# ── Shared fixtures / stubs ────────────────────────────────────────────────


@dataclass
class FakeElementInfo:
    """Lightweight stand-in for backends.base.ElementInfo (has properties)."""
    id: str = "root"
    role: str = "Window"
    name: str = "Test Window"
    value: Optional[str] = None
    x: int = 0
    y: int = 0
    width: int = 1920
    height: int = 1080
    children: list = field(default_factory=list)
    properties: dict = field(default_factory=dict)


@dataclass
class FakeCaptureResult:
    path: str = "/tmp/test.png"
    width: int = 1920
    height: int = 1080
    format: str = "png"
    scale_factor: float = 1.0
    dpi: int = 96


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.capture_screen.return_value = FakeCaptureResult()
    backend.list_monitors.return_value = [MagicMock(scale_factor=1.0, dpi=96)]
    backend.get_dpi_scale.return_value = 1.0
    return backend


def _patch_backend(mock_backend):
    return patch("naturo.cli.core._common._get_backend", return_value=mock_backend)


def _patch_platform(supports=True):
    return patch(
        "naturo.cli.core._common._platform_supports_gui", return_value=supports
    )


# The six props exercised end-to-end, as (backend-props key, camelCase key).
A11Y_PROPS = {
    "is_enabled": "isEnabled",
    "is_offscreen": "isOffscreen",
    "help_text": "helpText",
    "localized_control_type": "localizedControlType",
    "is_keyboard_focusable": "isKeyboardFocusable",
    "has_keyboard_focus": "hasKeyboardFocus",
}


# ── 1. see -j serialization ────────────────────────────────────────────────


class TestSeeJsonSerialization:
    """The see -j element tree emits each a11y prop under a stable key."""

    def _run(self, runner, mock_backend, props):
        tree = FakeElementInfo(
            id="root", role="Window", name="Win",
            x=0, y=0, width=1920, height=1080,
            children=[
                FakeElementInfo(
                    id="btn", role="Button", name="Save",
                    x=10, y=10, width=80, height=30, properties=props,
                ),
            ],
        )
        mock_backend.get_element_tree.return_value = tree
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(
                see, ["--json", "--no-snapshot", "--backend", "uia"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0, result.output
        return json.loads(result.output)["tree"]["children"][0]

    def test_all_props_emitted_under_snake_case_keys(self, runner, mock_backend):
        props = {
            "is_enabled": True,
            "is_offscreen": False,
            "help_text": "Save the document",
            "localized_control_type": "按钮",
            "is_keyboard_focusable": True,
            "has_keyboard_focus": False,
        }
        btn = self._run(runner, mock_backend, props)
        assert btn["is_enabled"] is True
        assert btn["is_offscreen"] is False
        assert btn["help_text"] == "Save the document"
        assert btn["localized_control_type"] == "按钮"
        assert btn["is_keyboard_focusable"] is True
        assert btn["has_keyboard_focus"] is False

    def test_bool_false_is_meaningful_and_emitted(self, runner, mock_backend):
        # is_enabled=False (a disabled control) is a real signal — it MUST be
        # emitted, not dropped like an absent/None property.
        btn = self._run(runner, mock_backend, {"is_enabled": False})
        assert "is_enabled" in btn
        assert btn["is_enabled"] is False

    def test_absent_props_not_emitted(self, runner, mock_backend):
        # A backend that never reads these props (empty dict) adds no keys.
        btn = self._run(runner, mock_backend, {})
        for key in ("is_enabled", "is_offscreen", "help_text",
                    "localized_control_type", "is_keyboard_focusable",
                    "has_keyboard_focus"):
            assert key not in btn

    def test_none_props_not_emitted(self, runner, mock_backend):
        # Explicit None (property queried but unreadable) is also omitted.
        btn = self._run(runner, mock_backend, {"help_text": None,
                                               "is_enabled": None})
        assert "help_text" not in btn
        assert "is_enabled" not in btn


# ── 2. UIElement snapshot model round-trip ─────────────────────────────────


class TestUIElementModel:

    def test_fields_default_to_none(self):
        el = UIElement(id="e1", element_id="element_1", role="Button")
        assert el.is_enabled is None
        assert el.is_offscreen is None
        assert el.help_text is None
        assert el.localized_control_type is None
        assert el.is_keyboard_focusable is None
        assert el.has_keyboard_focus is None

    def test_to_dict_camelcase_keys(self):
        el = UIElement(
            id="e1", element_id="element_1", role="Button",
            is_enabled=False, is_offscreen=True, help_text="tip",
            localized_control_type="按钮",
            is_keyboard_focusable=True, has_keyboard_focus=False,
        )
        d = el.to_dict()
        assert d["isEnabled"] is False
        assert d["isOffscreen"] is True
        assert d["helpText"] == "tip"
        assert d["localizedControlType"] == "按钮"
        assert d["isKeyboardFocusable"] is True
        assert d["hasKeyboardFocus"] is False

    def test_round_trip_preserves_props(self):
        el = UIElement(
            id="e1", element_id="element_1", role="Button",
            is_enabled=True, is_offscreen=False, help_text="tip",
            localized_control_type="Button",
            is_keyboard_focusable=True, has_keyboard_focus=True,
        )
        restored = UIElement.from_dict(el.to_dict())
        assert restored.is_enabled is True
        assert restored.is_offscreen is False
        assert restored.help_text == "tip"
        assert restored.localized_control_type == "Button"
        assert restored.is_keyboard_focusable is True
        assert restored.has_keyboard_focus is True

    def test_from_dict_accepts_snake_case_alias(self):
        restored = UIElement.from_dict({
            "id": "e1", "elementId": "element_1", "role": "Button",
            "is_enabled": True, "help_text": "hi",
        })
        assert restored.is_enabled is True
        assert restored.help_text == "hi"

    def test_from_dict_missing_keys_default_none(self):
        # Older snapshots without the new keys must round-trip unchanged.
        restored = UIElement.from_dict({
            "id": "e1", "elementId": "element_1", "role": "Button",
        })
        assert restored.is_enabled is None
        assert restored.localized_control_type is None


# ── 3. bridge ElementInfo model + native-JSON parsing ──────────────────────


class TestBridgeModel:

    def test_fields_default_to_none(self):
        el = BridgeElementInfo(
            id="e1", role="Button", name="Save", value=None,
            x=0, y=0, width=10, height=10,
        )
        assert el.is_enabled is None
        assert el.is_offscreen is None
        assert el.help_text is None
        assert el.localized_control_type is None
        assert el.is_keyboard_focusable is None
        assert el.has_keyboard_focus is None

    def test_parse_element_reads_native_snake_case_fields(self):
        # Mirrors the JSON the native UIA core emits per element.
        data = {
            "id": "btn", "role": "Button", "name": "Save",
            "x": 1, "y": 2, "width": 3, "height": 4,
            "is_enabled": False,
            "is_offscreen": True,
            "help_text": "Save the document",
            "localized_control_type": "按钮",
            "is_keyboard_focusable": True,
            "has_keyboard_focus": False,
        }
        el = _parse_element(data)
        assert el.is_enabled is False
        assert el.is_offscreen is True
        assert el.help_text == "Save the document"
        assert el.localized_control_type == "按钮"
        assert el.is_keyboard_focusable is True
        assert el.has_keyboard_focus is False

    def test_parse_element_absent_fields_are_none(self):
        el = _parse_element({
            "id": "btn", "role": "Button", "name": "Save",
            "x": 0, "y": 0, "width": 1, "height": 1,
        })
        assert el.is_enabled is None
        assert el.help_text is None


# ── 4. assign_stable_refs carries props → UIElement ────────────────────────


class TestAssignStableRefs:

    def test_props_flow_from_backend_properties_to_uielement(self):
        tree = FakeElementInfo(
            id="btn", role="Button", name="Save",
            x=0, y=0, width=10, height=10,
            properties={
                "is_enabled": False,
                "is_offscreen": True,
                "help_text": "tip",
                "localized_control_type": "按钮",
                "is_keyboard_focusable": True,
                "has_keyboard_focus": False,
            },
        )
        ui_map, _ = assign_stable_refs(tree, UIElement)
        el = next(iter(ui_map.values()))
        assert el.is_enabled is False
        assert el.is_offscreen is True
        assert el.help_text == "tip"
        assert el.localized_control_type == "按钮"
        assert el.is_keyboard_focusable is True
        assert el.has_keyboard_focus is False

    def test_missing_props_default_none(self):
        tree = FakeElementInfo(
            id="btn", role="Button", name="Save",
            x=0, y=0, width=10, height=10, properties={},
        )
        ui_map, _ = assign_stable_refs(tree, UIElement)
        el = next(iter(ui_map.values()))
        assert el.is_enabled is None
        assert el.help_text is None

    def test_stub_uielement_without_new_fields_still_constructs(self):
        # A minimal UIElement stub (predating #896) must not raise TypeError.
        @dataclass
        class StubUIElement:
            id: str = ""
            element_id: str = ""
            role: str = ""
            title: Optional[str] = None
            label: Optional[str] = None
            value: Optional[str] = None
            identifier: Optional[str] = None
            frame: tuple = (0, 0, 0, 0)
            is_actionable: bool = False
            parent_id: Optional[str] = None
            children: list = field(default_factory=list)
            keyboard_shortcut: Optional[str] = None

        tree = FakeElementInfo(
            id="btn", role="Button", name="Save",
            properties={"is_enabled": True},
        )
        ui_map, _ = assign_stable_refs(tree, StubUIElement)
        assert len(ui_map) == 1


# ── 5. comtypes a11y reader value mapping ──────────────────────────────────


class TestGetElementA11yUia:
    """The Python/comtypes single-element reader maps UIA Current* props."""

    def _reader(self, fake_elem):
        from naturo.backends.windows._input._uia_interact import UIAInteractMixin

        class _Backend(UIAInteractMixin):
            pass

        be = _Backend()
        be._init_comtypes_uia = MagicMock(return_value=(MagicMock(), MagicMock()))
        be._resolve_interaction_element = MagicMock(return_value=fake_elem)
        return be

    def test_reads_all_six_current_properties(self):
        elem = MagicMock()
        elem.CurrentIsEnabled = True
        elem.CurrentIsOffscreen = False
        elem.CurrentHelpText = "Save the document"
        elem.CurrentLocalizedControlType = "按钮"
        elem.CurrentIsKeyboardFocusable = True
        elem.CurrentHasKeyboardFocus = False
        be = self._reader(elem)

        result = be.get_element_a11y_uia(hwnd=123, name="Save")
        assert result == {
            "is_enabled": True,
            "is_offscreen": False,
            "help_text": "Save the document",
            "localized_control_type": "按钮",
            "is_keyboard_focusable": True,
            "has_keyboard_focus": False,
        }

    def test_empty_help_text_maps_to_none(self):
        elem = MagicMock()
        elem.CurrentIsEnabled = True
        elem.CurrentIsOffscreen = False
        elem.CurrentHelpText = ""
        elem.CurrentLocalizedControlType = ""
        elem.CurrentIsKeyboardFocusable = False
        elem.CurrentHasKeyboardFocus = False
        be = self._reader(elem)

        result = be.get_element_a11y_uia(hwnd=1, name="x")
        assert result["help_text"] is None
        assert result["localized_control_type"] is None

    def test_no_element_resolved_returns_none(self):
        be = self._reader(None)
        assert be.get_element_a11y_uia(hwnd=1, name="missing") is None

    def test_comtypes_unavailable_returns_none(self):
        from naturo.backends.windows._input._uia_interact import UIAInteractMixin

        class _Backend(UIAInteractMixin):
            pass

        be = _Backend()
        be._init_comtypes_uia = MagicMock(side_effect=ImportError("no comtypes"))
        assert be.get_element_a11y_uia(hwnd=1, name="x") is None
