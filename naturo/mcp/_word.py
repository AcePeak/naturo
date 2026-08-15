"""MCP tools for Word COM automation."""
from __future__ import annotations


def register_word_tools(server, _get_backend, _safe_tool):
    """Register Word COM MCP tools."""

    @server.tool()
    @_safe_tool
    def word_write(
        path: str,
        text: str,
        create: bool = True,
        append: bool = False,
    ) -> dict:
        """Write text to a Word document programmatically (COM) — no UI needed.

        The direct way to put text in a .docx: no start-screen click, no typing
        into the window, no clipboard round-trip. Uses a dedicated Word instance
        (DispatchEx) so it never stalls on the Backstage start screen, and works
        from the MCP worker thread. For reading a document back, use word_read.

        Args:
            path: Path to the .docx file.
            text: Text to write.
            create: Create the document if it does not exist (default True).
            append: Append to the end instead of replacing the whole document.

        Returns:
            Dict with path and chars (document length after write).
        """
        from naturo.word import word_write as _word_write
        result = _word_write(path, text, create=create, append=append)
        return {"success": True, **result}

    @server.tool()
    @_safe_tool
    def word_read(path: str) -> dict:
        """Read the full text of a Word document programmatically (COM).

        Returns the document body text directly — far cleaner than opening the
        window and doing select-all / copy / read-clipboard. Uses a dedicated
        Word instance (DispatchEx), works from the MCP worker thread.

        Args:
            path: Path to the .docx/.doc file.

        Returns:
            Dict with path, text (full document text), and chars.
        """
        from naturo.word import word_read as _word_read
        result = _word_read(path)
        return {"success": True, **result}
