"""Unit tests for the AI-vision coordinate helpers extracted from
``_fetch_ai_elements`` (bounds-format detection, downscale recovery, and
raw-dict -> ElementInfo conversion). These lock the subtle coordinate math that
used to be buried inside a 215-line function."""
from naturo.cascade._providers import (
    _ai_raw_to_element,
    _detect_ai_scale,
    _detect_xyxy_bounds,
    _raw_bounds,
)


# ── _raw_bounds ────────────────────────────────────────────────────────────

def test_raw_bounds_list_form():
    assert _raw_bounds([10, 20, 30, 40]) == (10.0, 20.0, 30.0, 40.0)


def test_raw_bounds_dict_form_uses_defaults():
    assert _raw_bounds({"x": 5, "y": 6}, default_w=50.0, default_h=20.0) == (
        5.0, 6.0, 50.0, 20.0)


def test_raw_bounds_rejects_garbage():
    assert _raw_bounds(None) is None
    assert _raw_bounds([1, 2]) is None
    assert _raw_bounds("nope") is None


# ── _detect_xyxy_bounds ────────────────────────────────────────────────────

def test_detects_xyxy_when_corners_dominate():
    # x2>=x1 and y2>=y1 for every element → corner form
    els = [{"bounds": [10, 10, 100, 80]}, {"bounds": [200, 50, 260, 90]}]
    assert _detect_xyxy_bounds(els) is True


def test_keeps_xywh_when_widths_are_small():
    # width/height much smaller than x/y for right-side elements → not corners
    els = [{"bounds": [500, 400, 30, 12]}, {"bounds": [600, 300, 20, 10]}]
    assert _detect_xyxy_bounds(els) is False


def test_detect_xyxy_empty_is_false():
    assert _detect_xyxy_bounds([]) is False


# ── _detect_ai_scale ───────────────────────────────────────────────────────

def test_scale_recovers_downscaled_space():
    # AI answered in a ~1024-wide space; real screenshot is 2048 → 2x correction
    els = [{"bounds": [0, 0, 1024, 512]}]
    sx, sy = _detect_ai_scale(els, img_w=2048, img_h=1024, is_xyxy=False)
    assert round(sx, 3) == 2.0
    assert round(sy, 3) == 2.0


def test_scale_noise_below_threshold_is_ignored():
    # AI max only ~1.1x smaller than the image → below the 1.5x guard → no scale
    els = [{"bounds": [0, 0, 900, 900]}]
    assert _detect_ai_scale(els, img_w=1000, img_h=1000, is_xyxy=False) == (1.0, 1.0)


def test_scale_uses_corner_coords_when_xyxy():
    els = [{"bounds": [0, 0, 1000, 500]}]  # x2,y2 are the max corner
    sx, sy = _detect_ai_scale(els, img_w=2000, img_h=1000, is_xyxy=True)
    assert round(sx, 3) == 2.0 and round(sy, 3) == 2.0


def test_scale_noop_without_image_dims():
    assert _detect_ai_scale([{"bounds": [0, 0, 10, 10]}], 0, 0, False) == (1.0, 1.0)


# ── _ai_raw_to_element ─────────────────────────────────────────────────────

def test_converts_xywh_with_window_offset():
    el = _ai_raw_to_element(
        0, {"role": "button", "name": "OK", "bounds": [10, 20, 30, 40]},
        is_xyxy=False, ai_scale_x=1.0, ai_scale_y=1.0, win_x=100, win_y=200)
    assert el is not None
    assert (el.x, el.y, el.width, el.height) == (110, 220, 30, 40)
    assert el.role == "Button"  # capitalized
    assert el.name == "OK"
    assert el.properties["source"] == "vision"


def test_converts_corner_form_to_width_height():
    el = _ai_raw_to_element(
        1, {"bounds": [10, 20, 60, 80]},  # x1,y1,x2,y2
        is_xyxy=True, ai_scale_x=1.0, ai_scale_y=1.0, win_x=0, win_y=0)
    assert el is not None
    assert (el.width, el.height) == (50, 60)  # 60-10, 80-20


def test_applies_scale_then_offset_and_clamps():
    el = _ai_raw_to_element(
        2, {"bounds": [10, 10, 5, 5]},
        is_xyxy=False, ai_scale_x=2.0, ai_scale_y=2.0, win_x=0, win_y=0)
    assert el is not None
    assert (el.x, el.y, el.width, el.height) == (20, 20, 10, 10)


def test_skips_non_dict_and_bad_bounds():
    assert _ai_raw_to_element(0, "nope", False, 1.0, 1.0, 0, 0) is None
    assert _ai_raw_to_element(1, {"bounds": "x"}, False, 1.0, 1.0, 0, 0) is None
