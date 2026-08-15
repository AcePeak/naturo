"""Windows Word COM Automation backend.

Read/write Word document text via ``win32com.client`` (pywin32), mirroring
:mod:`naturo.excel`:

* **DispatchEx** — a dedicated, automation-ready Word instance (never attaches to
  an interactively-launched Word stuck on the Backstage start screen, where COM
  operations fail with OLE 0x800a01a8).
* **CoInitialize** (via the shared ``_com_apartment`` decorator) — works from the
  FastMCP worker thread that dispatches synchronous MCP tools.
* **Quit in a finally** — nothing leaks.

Requires: Windows, Microsoft Word, pywin32.
"""
from __future__ import annotations

import logging
import os
import platform
from typing import Any

from naturo.errors import NaturoError, ErrorCode, ErrorCategory
from naturo.excel import _com_apartment  # shared COM-apartment (CoInitialize) helper

logger = logging.getLogger(__name__)

# Word constants (avoid the makepy type library).
_WD_COLLAPSE_END = 0
_WD_FORMAT_DOCX = 16


class WordError(NaturoError):
    """Word COM automation error."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("category", ErrorCategory.AUTOMATION)
        super().__init__(message, code=kwargs.pop("code", "WORD_ERROR"), **kwargs)


class WordNotAvailableError(WordError):
    """Word or pywin32 is not available."""

    def __init__(self, detail: str = "") -> None:
        msg = "Microsoft Word is not available"
        if detail:
            msg += f": {detail}"
        super().__init__(
            msg,
            code="WORD_NOT_AVAILABLE",
            suggested_action="Install Microsoft Word and pywin32 (pip install pywin32).",
        )


def _require_windows() -> None:
    if platform.system() != "Windows":
        raise WordError(
            "Word COM automation requires Windows",
            code=ErrorCode.PERMISSION_DENIED,
        )


def _normalize_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def _get_word():  # type: ignore[no-untyped-def]
    """Return a dedicated Word.Application COM instance (DispatchEx)."""
    _require_windows()
    try:
        import win32com.client  # type: ignore[import-untyped]
    except ImportError:
        raise WordNotAvailableError("pywin32 is not installed (pip install pywin32)")
    try:
        app = win32com.client.DispatchEx("Word.Application")
    except Exception as exc:
        raise WordNotAvailableError(str(exc))
    app.Visible = False
    app.DisplayAlerts = 0
    return app


_COM_HINT = (
    "Word COM automation failed. Ensure Microsoft Word is installed and "
    "activated — an un-activated or first-run Office can block COM automation. "
    "Try opening the document in Word once, and verify the path."
)


@_com_apartment
def word_write(
    path: str,
    text: str,
    create: bool = True,
    append: bool = False,
) -> dict[str, Any]:
    """Write text to a Word document.

    Args:
        path: Path to the .docx file.
        text: Text to write.
        create: Create the document if it does not exist.
        append: Append to the end instead of replacing the whole document.

    Returns:
        Dict with path, chars (document length after write).
    """
    _require_windows()
    abs_path = _normalize_path(path)
    if not os.path.isfile(abs_path) and not create:
        raise WordError(
            f"Document not found: {path}",
            code=ErrorCode.FILE_NOT_FOUND,
            context={"path": abs_path},
        )

    app = _get_word()
    try:
        existed = os.path.isfile(abs_path)
        doc = app.Documents.Open(abs_path) if existed else app.Documents.Add()

        if append:
            rng = doc.Content
            rng.Collapse(_WD_COLLAPSE_END)
            rng.InsertAfter(text)
        else:
            doc.Content.Text = text

        if existed:
            doc.Save()
        else:
            doc.SaveAs(abs_path, FileFormat=_WD_FORMAT_DOCX)

        chars = len(doc.Content.Text)
        doc.Close(SaveChanges=False)
        return {"path": abs_path, "chars": chars, "appended": append}
    except WordError:
        raise
    except Exception as exc:
        raise WordError(
            f"Failed to write document: {exc}",
            context={"path": abs_path},
            suggested_action=_COM_HINT,
        )
    finally:
        try:
            app.Quit()
        except Exception as exc:
            logger.debug("Word COM cleanup failed: %s", exc)


@_com_apartment
def word_read(path: str) -> dict[str, Any]:
    """Read the full text of a Word document.

    Args:
        path: Path to the .docx/.doc file.

    Returns:
        Dict with path, text (full document text), chars.
    """
    _require_windows()
    abs_path = _normalize_path(path)
    if not os.path.isfile(abs_path):
        raise WordError(
            f"Document not found: {path}",
            code=ErrorCode.FILE_NOT_FOUND,
            context={"path": abs_path},
        )

    app = _get_word()
    try:
        doc = app.Documents.Open(abs_path, ReadOnly=True)
        text = doc.Content.Text
        doc.Close(SaveChanges=False)
        return {"path": abs_path, "text": text, "chars": len(text)}
    except WordError:
        raise
    except Exception as exc:
        raise WordError(
            f"Failed to read document: {exc}",
            context={"path": abs_path},
            suggested_action=_COM_HINT,
        )
    finally:
        try:
            app.Quit()
        except Exception as exc:
            logger.debug("Word COM cleanup failed: %s", exc)
