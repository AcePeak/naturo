"""Shared recognition-technique CLI options + resolver.

One vocabulary for every command that recognizes UI (`see`, `highlight`, `find`):
composable technique flags whose active set is the UNION of what's given, with
--fast/--deep presets and --fast as the default. This is the single source of
truth so the three surfaces can't drift apart again (see docs/design/
cli-consistency-review.md).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import click

#: Structured (deterministic) techniques — the --fast preset.
FAST_SET = frozenset({"uia", "msaa", "ia2", "jab", "cdp", "com"})


@dataclass(frozen=True)
class TechSelection:
    """Resolved technique gates, ready to thread into ``run_cascade``."""

    enable_uia: bool
    enable_msaa: bool
    enable_ia2: bool
    enable_jab: bool
    enable_cdp: bool
    enable_com: bool
    run_ocr: bool
    fill_gaps_ai: bool
    selected: frozenset

    @property
    def needs_screenshot(self) -> bool:
        """OCR and AI vision both read pixels, so a screenshot must be captured."""
        return self.run_ocr or self.fill_gaps_ai


def resolve_techniques(
    *,
    fast: bool = False,
    deep: bool = False,
    uia: bool = False,
    msaa: bool = False,
    ia2: bool = False,
    jab: bool = False,
    cdp: bool = False,
    com: bool = False,
    ocr: bool = False,
    ai: bool = False,
    cascade: bool = False,
    fill_gaps: bool = False,
) -> TechSelection:
    """Fold the technique flags into a :class:`TechSelection`.

    The active set is the union of every flag given; --fast/--deep expand into
    it; nothing given → --fast. --cascade/--fill-gaps are deprecated aliases for
    --ai. A structured base (UIA) is kept for the window frame that additive
    providers hang off if the caller gates every base away.
    """
    flags = {
        "uia": uia, "msaa": msaa, "ia2": ia2, "jab": jab, "cdp": cdp, "com": com,
        "ocr": ocr, "ai": ai or cascade or fill_gaps,
    }
    selected = {t for t, on in flags.items() if on}
    if fast:
        selected |= set(FAST_SET)
    if deep:
        selected |= (set(FAST_SET) | {"ocr", "ai"})
    if not selected:
        selected = set(FAST_SET)
    bases = selected & {"uia", "msaa", "ia2"}
    if not bases:
        bases = {"uia"}
    return TechSelection(
        enable_uia="uia" in bases,
        enable_msaa="msaa" in bases,
        enable_ia2="ia2" in bases,
        enable_jab="jab" in selected,
        enable_cdp="cdp" in selected,
        enable_com="com" in selected,
        run_ocr="ocr" in selected,
        fill_gaps_ai="ai" in selected,
        selected=frozenset(selected),
    )


def technique_options(func: Callable) -> Callable:
    """Attach the shared recognition-technique flags to a Click command.

    Injects params: want_fast, want_deep, want_uia, want_msaa, want_ia2,
    want_jab, want_cdp, want_com, run_ocr, want_ai, plus the hidden deprecated
    aliases cascade/fill_gaps and the AI provider knobs ai_provider/ai_model/
    ai_api_key. Pass them straight to :func:`resolve_techniques`.
    """
    opts = [
        click.option("--fast", "want_fast", is_flag=True,
                     help="Preset: all fast structured techniques (the DEFAULT "
                          "when no technique is given)."),
        click.option("--deep", "want_deep", is_flag=True,
                     help="Preset: full stack — structured + ocr + ai."),
        click.option("--uia", "want_uia", is_flag=True, help="Technique: UIAutomation."),
        click.option("--msaa", "want_msaa", is_flag=True, help="Technique: MSAA (legacy apps)."),
        click.option("--ia2", "want_ia2", is_flag=True, help="Technique: IAccessible2 (Firefox/LibreOffice)."),
        click.option("--jab", "want_jab", is_flag=True, help="Technique: Java Access Bridge."),
        click.option("--cdp", "want_cdp", is_flag=True, help="Technique: Chrome DevTools DOM (Chromium/Electron)."),
        click.option("--com", "want_com", is_flag=True, help="Technique: COM (Excel/WPS cells)."),
        click.option("--ocr", "run_ocr", is_flag=True,
                     help="Technique: local OCR (rapidocr) — on-screen text (uncertain)."),
        click.option("--ai", "want_ai", is_flag=True,
                     help="Technique: AI vision (needs a provider; slower)."),
        click.option("--cascade", is_flag=True, hidden=True, help="Deprecated alias for --ai."),
        click.option("--fill-gaps", "fill_gaps", is_flag=True, hidden=True, help="Deprecated alias for --ai."),
        click.option("--ai-provider", "ai_provider",
                     type=click.Choice(["auto", "anthropic", "openai", "ollama"]),
                     default="auto", help="AI vision provider for --ai/--deep (default: auto)."),
        click.option("--ai-model", "ai_model", default=None, envvar="NATURO_AI_MODEL",
                     help="AI model override (e.g. claude-opus-4-6, gpt-4o)."),
        click.option("--ai-api-key", "ai_api_key", default=None,
                     help="AI provider API key (overrides env var / credentials file)."),
    ]
    for opt in reversed(opts):
        func = opt(func)
    return func
