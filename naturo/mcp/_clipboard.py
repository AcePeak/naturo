"""MCP tools for clipboard operations."""
from __future__ import annotations


def register_clipboard_tools(server, _get_backend, _safe_tool):
    """Register clipboard MCP tools."""

    @server.tool()
    @_safe_tool
    def clipboard_get() -> dict:
        """Read the current clipboard text content.

        Returns the text from the system clipboard. Useful for reading data
        that was copied from an application.

        Returns:
            text: Current clipboard text content.
            length: Number of characters.
        """
        backend = _get_backend()
        text = backend.clipboard_get()
        return {"success": True, "text": text, "length": len(text)}

    @server.tool()
    @_safe_tool
    def clipboard_set(text: str) -> dict:
        """Write text to the system clipboard.

        Replaces the current clipboard content with the given text.
        Use this to prepare data for pasting into an application.

        Args:
            text: Text to write to the clipboard.

        Returns:
            length: Number of characters written.
        """
        backend = _get_backend()
        backend.clipboard_set(text)
        return {"success": True, "length": len(text)}

    @server.tool()
    @_safe_tool
    def clipboard_clear() -> dict:
        """Clear the system clipboard contents.

        Removes all data from the clipboard.
        """
        backend = _get_backend()
        backend.clipboard_clear()
        return {"success": True}

    @server.tool()
    @_safe_tool
    def clipboard_info() -> dict:
        """Get information about the current clipboard contents.

        Reports the data format, size, and available content types
        (text, image, files).

        Returns:
            format: Primary format (text, image, files, empty).
            size: Data size in bytes.
            has_text: Whether text content is available.
            has_image: Whether image content is available.
            has_files: Whether file references are available.
        """
        backend = _get_backend()
        info = backend.clipboard_info()
        return {"success": True, **info}
