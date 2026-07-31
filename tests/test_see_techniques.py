"""`naturo see` recognition-technique flags → run_cascade gate mapping.

Composable technique flags (--uia/--msaa/--ia2/--jab/--cdp/--com/--ocr/--ai) and
presets (--fast/--deep) select the active set as a UNION; nothing given → --fast.
These tests assert each flag combination threads the right enable_*/fill_gaps_ai/
run_ocr into run_cascade.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.backends.base import ElementInfo


def _tree() -> ElementInfo:
    return ElementInfo(
        id="w", role="Window", name="App", value=None,
        x=0, y=0, width=400, height=300,
        children=[
            ElementInfo(id="b", role="Button", name="OK", value=None,
                        x=10, y=10, width=80, height=30, children=[], properties={}),
            ElementInfo(id="e", role="Edit", name="Field", value=None,
                        x=10, y=50, width=200, height=30, children=[], properties={}),
        ],
        properties={},
    )


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.get_element_tree.return_value = _tree()
    backend.list_monitors.return_value = []
    backend.get_dpi_scale.return_value = 1.0
    return backend


def _capture_cascade_kwargs(runner, mock_backend, args):
    """Invoke `see` with run_cascade mocked; return (result, captured_kwargs)."""
    captured: dict = {}

    def _fake_cascade(_be, **kw):
        captured.update(kw)
        result = MagicMock()
        result.tree = _tree()
        result.stats = MagicMock(providers=[])
        return result

    from naturo.cli.core import see
    with patch("naturo.cli.core._common._get_backend", return_value=mock_backend), \
         patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
         patch("naturo.cascade.run_cascade", side_effect=_fake_cascade):
        result = runner.invoke(see, args + ["--no-snapshot"])
    return result, captured


class TestSeeTechniqueGates:

    def test_default_is_fast_all_structured(self, runner, mock_backend):
        result, kw = _capture_cascade_kwargs(runner, mock_backend, [])
        assert result.exit_code == 0, result.output
        assert kw["enable_uia"] and kw["enable_msaa"]
        assert kw["enable_jab"] and kw["enable_cdp"] and kw["enable_com"]
        assert kw["fill_gaps_ai"] is False and kw["run_ocr"] is False

    def test_uia_only_disables_the_rest(self, runner, mock_backend):
        _result, kw = _capture_cascade_kwargs(runner, mock_backend, ["--uia"])
        assert kw["enable_uia"] is True
        assert kw["enable_jab"] is False
        assert kw["enable_cdp"] is False
        assert kw["enable_com"] is False
        assert kw["fill_gaps_ai"] is False and kw["run_ocr"] is False

    def test_uia_plus_cdp_union(self, runner, mock_backend):
        _result, kw = _capture_cascade_kwargs(runner, mock_backend, ["--uia", "--cdp"])
        assert kw["enable_uia"] is True and kw["enable_cdp"] is True
        assert kw["enable_jab"] is False and kw["enable_com"] is False

    def test_ocr_enables_ocr_only(self, runner, mock_backend):
        _result, kw = _capture_cascade_kwargs(runner, mock_backend, ["--ocr"])
        assert kw["run_ocr"] is True
        assert kw["fill_gaps_ai"] is False

    def test_ai_enables_ai(self, runner, mock_backend):
        _result, kw = _capture_cascade_kwargs(runner, mock_backend, ["--ai"])
        assert kw["fill_gaps_ai"] is True

    def test_deep_enables_full_stack(self, runner, mock_backend):
        _result, kw = _capture_cascade_kwargs(runner, mock_backend, ["--deep"])
        assert kw["enable_jab"] and kw["enable_cdp"] and kw["enable_com"]
        assert kw["fill_gaps_ai"] is True and kw["run_ocr"] is True

    def test_com_only_needs_uia_base_for_bounds(self, runner, mock_backend):
        # No structured a11y base selected → UIA base is kept for the frame,
        # COM grafts on, JAB/CDP stay off.
        _result, kw = _capture_cascade_kwargs(runner, mock_backend, ["--com"])
        assert kw["enable_com"] is True
        assert kw["enable_uia"] is True   # fallback base for bounds
        assert kw["enable_jab"] is False and kw["enable_cdp"] is False

    def test_cascade_alias_maps_to_ai(self, runner, mock_backend):
        _result, kw = _capture_cascade_kwargs(runner, mock_backend, ["--cascade"])
        assert kw["fill_gaps_ai"] is True
