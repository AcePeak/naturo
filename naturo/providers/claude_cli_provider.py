"""Vision provider backed by the local, already-authenticated Claude Code CLI.

Most vision providers need an API key (``ANTHROPIC_API_KEY`` etc.). This one
instead shells out to the ``claude`` CLI that Claude Code users already have on
PATH and logged in — so naturo's cascade vision-fill works with **zero extra
credentials** wherever Claude Code runs. It is the credential-free fallback in
the auto-detect chain: API-key providers still win when configured.

The CLI reads a local screenshot when its path is named in the prompt, returns
its answer via ``--output-format json``; we parse the element list with the same
``parse_ai_elements_json`` used by the API providers.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from typing import Any, Optional

from naturo.errors import AIProviderUnavailableError
from naturo.providers.base import (
    VisionResult,
    parse_ai_elements_json,
    register_provider,
)

logger = logging.getLogger(__name__)

# Reading UI structure is a fair fallback; forbid shell/web so the CLI answers
# from the image only and never shells out to solve the task another way.
_DISALLOWED = "Bash,BashOutput,KillShell,WebFetch,WebSearch,Task,Agent"


def _salvage_elements(raw: str) -> list[dict[str, Any]]:
    """Best-effort element extraction when the CLI wraps or nests its JSON.

    The agentic CLI sometimes returns ``{"window": {...}}`` or nests elements by
    container instead of the requested flat array. Parse whatever JSON is present
    and recursively collect every dict that looks like a UI element (has a
    role/name/label/text and/or bounds), descending into any child/element lists.
    """
    if not raw:
        return []
    text = raw.strip()
    # isolate the outermost JSON value (array or object)
    for a, b in (("[", "]"), ("{", "}")):
        i, j = text.find(a), text.rfind(b)
        if i != -1 and j > i:
            try:
                data = json.loads(text[i:j + 1])
                break
            except Exception:
                continue
    else:
        return []

    out: list[dict[str, Any]] = []
    _ELEM_KEYS = ("role", "name", "label", "text", "bounds", "bbox", "box")

    def visit(node: Any) -> None:
        if isinstance(node, list):
            for it in node:
                visit(it)
        elif isinstance(node, dict):
            if any(k in node for k in _ELEM_KEYS) and not any(
                isinstance(node.get(k), (list, dict)) for k in ("children", "elements", "items")
            ):
                out.append(node)
            for k, v in node.items():
                if isinstance(v, (list, dict)):
                    visit(v)

    visit(data)
    return out


class ClaudeCliVisionProvider:
    """VisionProvider that calls the local ``claude -p`` CLI with an image."""

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        timeout: int = 180,
        cli_path: Optional[str] = None,
        **_ignored: Any,
    ) -> None:
        self._model = model or ""
        self._timeout = timeout
        self._cli = cli_path or shutil.which("claude")

    @property
    def name(self) -> str:
        return "claude_cli"

    @property
    def is_available(self) -> bool:
        """True when the ``claude`` CLI is on PATH (no API key required)."""
        return bool(self._cli)

    def _run(self, prompt: str, image_path: str, max_tokens: int) -> VisionResult:
        if not self._cli:
            raise AIProviderUnavailableError(
                provider="claude_cli",
                suggested_action="Install the Claude Code CLI (`claude`) on PATH",
            )
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        # The CLI is agentic and defaults to prose — clamp it hard to a FLAT array.
        # Name the exact path so it opens the screenshot itself.
        full = (
            "You are a JSON-only UI element extraction API. Open the image file at "
            f"this exact path and analyze it: {image_path}\n\n"
            + prompt
            + "\n\nCRITICAL OUTPUT CONTRACT:\n"
            "- Respond with ONLY a raw JSON ARRAY, nothing else.\n"
            "- The TOP LEVEL must be a flat array [ ... ]; do NOT wrap it in an "
            "object, do NOT nest by container, do NOT add a 'window' key.\n"
            "- Each array item is ONE element: "
            '{"role": "...", "name": "visible text", "bounds": [x, y, w, h]}.\n'
            "- No prose, no image description, no markdown fences, no preamble.\n"
            "- Your entire reply MUST start with '[' and end with ']'."
        )
        # Trust the screenshot's directory so the CLI can Read it without a
        # permission prompt (headless -p can't answer one). Scoped to that dir
        # only — not a blanket skip — and shell/web/agent tools stay disallowed.
        img_dir = os.path.dirname(os.path.abspath(image_path))
        args = [self._cli, "-p", full, "--output-format", "json",
                "--add-dir", img_dir, "--disallowedTools", _DISALLOWED,
                # System-level clamp is far more reliable than an in-prompt one at
                # stopping the agentic CLI from answering in prose.
                "--append-system-prompt",
                "You are a machine JSON endpoint. Every response is a single raw "
                "JSON array of UI elements and nothing else — never prose, never a "
                "description, never markdown. Start with '[' and end with ']'."]
        if self._model:
            args += ["--model", self._model]

        # The agentic CLI occasionally answers in prose or a nested object; a
        # couple of retries plus a lenient salvage pass reliably land the list.
        raw = ""
        for _attempt in range(3):
            try:
                proc = subprocess.run(
                    args, capture_output=True, text=True, encoding="utf-8",
                    errors="ignore", timeout=self._timeout,
                )
            except Exception as exc:
                logger.debug("claude_cli vision call failed: %s", exc)
                continue
            try:
                raw = json.loads(proc.stdout).get("result", "") or ""
            except Exception:
                raw = proc.stdout or ""
            elements = parse_ai_elements_json(raw) or _salvage_elements(raw)
            if elements:
                return VisionResult(
                    description=raw.strip(), elements=elements,
                    model=self._model or "claude-cli", raw_response=raw,
                )
        return VisionResult(description=raw.strip(), elements=[],
                            model=self._model or "claude-cli", raw_response=raw)

    def describe_screenshot(
        self, image_path: str, *, prompt: Optional[str] = None,
        context: Optional[str] = None, max_tokens: int = 1024,
    ) -> VisionResult:
        p = prompt or "Describe what is on this screen and list the visible UI elements."
        if context:
            p = f"{context}\n\n{p}"
        return self._run(p, image_path, max_tokens)

    def identify_element(
        self, image_path: str, element_description: str, *, max_tokens: int = 4096,
    ) -> VisionResult:
        p = (f"Find '{element_description}' in this screenshot. Reply ONLY a JSON "
             'object {"role": "...", "name": "...", "bounds": [x, y, w, h]}.')
        return self._run(p, image_path, max_tokens)

    def enumerate_elements(
        self, image_path: str, prompt: str, *, max_tokens: int = 16384,
    ) -> VisionResult:
        return self._run(prompt, image_path, max_tokens)


register_provider("claude_cli", ClaudeCliVisionProvider)
