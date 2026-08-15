"""Tests for naturo.word — Word COM automation (mock-based, Linux-collectable)."""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _inject_win32com(app):
    """Return a patch.dict context injecting a fake win32com whose DispatchEx
    returns *app*."""
    win32com = types.ModuleType("win32com")
    client = types.ModuleType("win32com.client")
    client.DispatchEx = MagicMock(return_value=app)
    win32com.client = client  # type: ignore[attr-defined]
    return {"win32com": win32com, "win32com.client": client}, client


class TestWordCom:

    def test_get_word_uses_dispatchex(self):
        import naturo.word as W
        app = MagicMock()
        mods, client = _inject_win32com(app)
        with patch("naturo.word.platform.system", return_value="Windows"), \
             patch.dict(sys.modules, mods):
            W._get_word()
        assert client.DispatchEx.called
        assert app.Visible is False

    def test_word_write_new_doc_sets_content_saves_and_quits(self):
        import naturo.word as W
        app = MagicMock()
        doc = MagicMock()
        app.Documents.Add.return_value = doc
        doc.Content.Text = ""
        mods, _ = _inject_win32com(app)
        with patch("naturo.word.platform.system", return_value="Windows"), \
             patch("naturo.word.os.path.isfile", return_value=False), \
             patch.dict(sys.modules, mods):
            result = W.word_write(r"C:\x\a.docx", "hello world", create=True)
        assert doc.Content.Text == "hello world"  # whole-document replace
        assert doc.SaveAs.called                   # new file → SaveAs
        assert app.Quit.called                     # cleanup in finally
        assert result["path"].endswith("a.docx")

    def test_word_read_returns_document_text(self):
        import naturo.word as W
        app = MagicMock()
        doc = MagicMock()
        doc.Content.Text = "the document body"
        app.Documents.Open.return_value = doc
        mods, _ = _inject_win32com(app)
        with patch("naturo.word.platform.system", return_value="Windows"), \
             patch("naturo.word.os.path.isfile", return_value=True), \
             patch.dict(sys.modules, mods):
            result = W.word_read(r"C:\x\a.docx")
        assert result["text"] == "the document body"
        assert result["chars"] == len("the document body")
        assert app.Quit.called

    def test_word_read_missing_file_raises(self):
        import naturo.word as W
        with patch("naturo.word.platform.system", return_value="Windows"), \
             patch("naturo.word.os.path.isfile", return_value=False):
            with pytest.raises(W.WordError):
                W.word_read(r"C:\x\nope.docx")
