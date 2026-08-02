"""Lock the safe JSON shape of the MCP see_ui_tree serializer.

The old _mcp_serialize dumped the raw backend property bag and the full value
for every node — unbounded, and able to carry non-JSON values that broke the
MCP encoder on large trees. These tests pin the bounded/filtered shape.
"""
import json
import types

from naturo.mcp import _inspect


def _el(**kw):
    d = dict(id="s1", role="Edit", name="msg", value=None, x=1, y=2,
             width=3, height=4, properties={}, children=[])
    d.update(kw)
    return types.SimpleNamespace(**d)


def _ctx():
    return _inspect._McpTreeCtx(
        element_obj_to_ref={}, display_ref_map={}, counter=[1],
        annotate=lambda _p: None, full_text=False,
    )


def test_serialize_drops_raw_property_bag_and_stays_json_safe():
    # A non-JSON object in the raw bag would have crashed the old encoder.
    el = _el(properties={"readable": True, "actionable": True,
                         "source": "uia", "bad_rect": object()})
    out = _inspect._mcp_serialize(el, _ctx())
    assert "properties" not in out          # raw bag not dumped
    assert out["source"] == "uia"           # useful key surfaced
    assert out["caps"] == "ra"              # readable+actionable
    json.dumps(out)                          # must be serialisable


def test_serialize_bounds_long_value():
    big = "x" * 100_000
    out = _inspect._mcp_serialize(_el(value=big), _ctx())
    assert len(out["value"]) < len(big)      # preview, not the whole blob
    assert out["value_length"] == 100_000


def test_serialize_keeps_short_value_and_recurses():
    parent = _el(name="p", value="hi", children=[_el(name="c", value=None)])
    out = _inspect._mcp_serialize(parent, _ctx())
    assert out["value"] == "hi"
    assert "value_length" not in out
    assert [c["name"] for c in out["children"]] == ["c"]
