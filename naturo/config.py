"""Centralized configuration for naturo.

All file paths, environment variable names, and credential management
in one place. Import from here instead of hardcoding paths/env vars.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── File paths ──
CREDENTIALS_PATH = Path.home() / ".config" / "naturo" / "credentials.json"
SNAPSHOTS_DIR = Path.home() / ".naturo" / "snapshots"

# ── Environment variables ──
ENV_SESSION = "NATURO_SESSION"
ENV_SNAPSHOT_TTL = "NATURO_SNAPSHOT_TTL"
ENV_AI_MODEL = "NATURO_AI_MODEL"
ENV_AI_PROVIDER = "NATURO_AI_PROVIDER"
ENV_LOG_LEVEL = "NATURO_LOG_LEVEL"


def load_credentials() -> dict[str, Any]:
    """Load credentials from ~/.config/naturo/credentials.json."""
    try:
        if CREDENTIALS_PATH.exists():
            return json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("Could not read credentials: %s", exc)
    return {}


def save_credentials(data: dict[str, Any]) -> None:
    """Write credentials atomically."""
    import tempfile
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8",
        dir=CREDENTIALS_PATH.parent,
        prefix=".tmp_", suffix=".json", delete=False,
    ) as tmp:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp_path = tmp.name
    try:
        os.replace(tmp_path, CREDENTIALS_PATH)
    except OSError:
        os.unlink(tmp_path)
        raise
