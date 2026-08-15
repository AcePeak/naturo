"""Fast, locale-independent regressions for the CJK/UTF-8 test-harness fixes.

Guards two host-locale bugs whose only exercised code paths otherwise live in
markers excluded from the default gate (``integration``) or in a single module:

* #1232 — the integration helper ``_run_naturo`` decoded the CLI's UTF-8 stdout
  with the host locale codec (GBK on Chinese Windows), raising ``UnicodeDecodeError``
  on CJK output. The fix pins ``encoding="utf-8"`` on the ``subprocess.run`` call,
  and the CLI genuinely emits UTF-8 (``naturo.cli`` reconfigures stdout to UTF-8 and
  ``naturo.cli._jsonio.json_dumps`` emits literal, non-ASCII-escaped text). These
  tests assert that alignment so a revert to a locale-dependent decode is caught in
  the fast suite, without needing a live desktop.

* #1192 — ``tests/test_cost_guardrails.py`` read the guardrails YAML with a bare
  ``open()``; on a non-UTF-8 locale the non-ASCII bytes raised ``UnicodeDecodeError``.
  Here we assert the file actually contains non-ASCII bytes, proving the explicit
  ``encoding="utf-8"`` is load-bearing rather than incidental.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from naturo.cli._jsonio import json_dumps

_REPO_ROOT = Path(__file__).resolve().parent.parent
_INTEGRATION_HELPER = _REPO_ROOT / "tests" / "integration" / "test_unified_app_model.py"

# A CJK payload that is illegal as GBK for at least one byte, so a locale-codec
# decode on a Chinese-Windows host would raise (that is the #1232 crash).
_CJK_TITLE = "记事本 — 你好, 世界 🌏"


def _load_run_naturo() -> Any:
    """Import the ``_run_naturo`` helper from the integration module by path.

    Loaded via ``importlib`` under a synthetic name so pytest does not re-collect
    the ``integration``-marked module here, and so ``tests`` needing to be a
    package is irrelevant.
    """
    spec = importlib.util.spec_from_file_location(
        "_regression_unified_app_model", _INTEGRATION_HELPER
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRunNaturoDecodesUtf8:
    """#1232 — the CLI-output helper must decode as UTF-8, not the host locale."""

    def test_helper_passes_utf8_encoding_to_subprocess(self, monkeypatch):
        module = _load_run_naturo()

        captured: dict[str, Any] = {}

        def fake_run(cmd, **kwargs):  # noqa: ANN001 - test stub
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            result = MagicMock()
            result.stdout = json_dumps({"title": _CJK_TITLE})
            return result

        monkeypatch.setattr(module.subprocess, "run", fake_run)

        parsed = module._run_naturo("see", "--app", "notepad")

        # Decode is pinned to UTF-8 (would be the locale codec if reverted to
        # text=True alone) and CJK output round-trips intact.
        assert captured["kwargs"].get("encoding") == "utf-8"
        assert parsed["title"] == _CJK_TITLE

    def test_cli_utf8_bytes_roundtrip_through_helper_decode(self):
        # The CLI reconfigures stdout to UTF-8 and json_dumps emits literal
        # (non-\uXXXX) text, so its stdout bytes are UTF-8. Decoding those bytes
        # as UTF-8 (what the helper now does) restores the CJK exactly.
        emitted = json_dumps({"title": _CJK_TITLE})
        assert "\\u" not in emitted  # literal CJK, not ASCII escapes
        stdout_bytes = emitted.encode("utf-8")
        assert json.loads(stdout_bytes.decode("utf-8"))["title"] == _CJK_TITLE

    def test_locale_codec_would_have_crashed(self):
        # Documents *why* utf-8 is required: the same bytes are not decodable as
        # GBK, i.e. the pre-fix locale-default decode raised on this input.
        stdout_bytes = json_dumps({"title": _CJK_TITLE}).encode("utf-8")
        try:
            stdout_bytes.decode("gbk")
        except UnicodeDecodeError:
            return  # expected on the emoji / mixed bytes
        # If a given build's GBK tables happen to decode it, it must at least be
        # mangled — never equal to the original UTF-8 text.
        assert stdout_bytes.decode("gbk") != _CJK_TITLE


class TestGuardrailsYamlIsNonAscii:
    """#1192 — the explicit encoding= on the YAML read must be load-bearing."""

    def test_guardrails_yaml_contains_non_ascii_bytes(self):
        path = _REPO_ROOT / "agents" / "config" / "cost-guardrails.yaml"
        assert path.exists(), f"Missing {path}"
        raw = path.read_bytes()
        assert any(b > 0x7F for b in raw), (
            "expected non-ASCII bytes so the explicit encoding='utf-8' read "
            "actually guards against a locale-default (GBK) decode crash"
        )
