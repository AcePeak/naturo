"""Shared recognition-technique resolver (see/highlight/find single source)."""
from __future__ import annotations

from naturo.cli._techniques import FAST_SET, resolve_techniques


def test_default_is_fast_all_structured():
    t = resolve_techniques()
    assert t.enable_uia and t.enable_msaa and t.enable_ia2
    assert t.enable_jab and t.enable_cdp and t.enable_com
    assert not t.run_ocr and not t.fill_gaps_ai
    assert t.selected == FAST_SET
    assert t.needs_screenshot is False


def test_uia_only():
    t = resolve_techniques(uia=True)
    assert t.enable_uia
    assert not (t.enable_jab or t.enable_cdp or t.enable_com)
    assert not t.run_ocr and not t.fill_gaps_ai


def test_union_of_flags():
    t = resolve_techniques(uia=True, cdp=True)
    assert t.enable_uia and t.enable_cdp
    assert not (t.enable_jab or t.enable_com)


def test_ocr_and_ai_flags():
    t = resolve_techniques(ocr=True)
    assert t.run_ocr and not t.fill_gaps_ai and t.needs_screenshot
    t2 = resolve_techniques(ai=True)
    assert t2.fill_gaps_ai and not t2.run_ocr and t2.needs_screenshot


def test_deep_is_everything():
    t = resolve_techniques(deep=True)
    assert t.enable_jab and t.enable_cdp and t.enable_com
    assert t.run_ocr and t.fill_gaps_ai


def test_cascade_and_fill_gaps_alias_ai():
    assert resolve_techniques(cascade=True).fill_gaps_ai is True
    assert resolve_techniques(fill_gaps=True).fill_gaps_ai is True


def test_base_kept_for_bounds_when_only_additive_selected():
    # Selecting only COM (or only ai/ocr) still keeps a UIA base for the frame.
    t = resolve_techniques(com=True)
    assert t.enable_com and t.enable_uia
    assert not (t.enable_jab or t.enable_cdp)
    t2 = resolve_techniques(ai=True)
    assert t2.enable_uia  # base for bounds


def test_msaa_only_base_switches_off_uia():
    t = resolve_techniques(msaa=True)
    assert t.enable_msaa and not t.enable_uia
