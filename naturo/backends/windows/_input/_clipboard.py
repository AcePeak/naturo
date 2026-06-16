"""Clipboard interaction: get, set, clear, and inspect clipboard contents."""

from __future__ import annotations

from naturo.errors import NaturoError


class ClipboardMixin:
    """Clipboard interaction: get, set, clear, and inspect clipboard contents."""

    def clipboard_get(self) -> str:
        """Get text content from the clipboard.

        Uses the pyperclip library as a portable clipboard interface.

        Returns:
            Clipboard text, or empty string if clipboard is empty.
        """
        try:
            import pyperclip  # type: ignore
            return pyperclip.paste() or ""
        except ImportError:
            # Fallback: use ctypes Win32 API directly
            try:
                import ctypes
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                # Set proper restype/argtypes for 64-bit pointer safety
                user32.GetClipboardData.restype = ctypes.c_void_p
                kernel32.GlobalLock.restype = ctypes.c_void_p
                kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
                kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
                if not user32.OpenClipboard(0):
                    raise NaturoError("Failed to open clipboard")
                try:
                    CF_UNICODETEXT = 13
                    h = user32.GetClipboardData(CF_UNICODETEXT)
                    if not h:
                        return ""
                    ptr = kernel32.GlobalLock(h)
                    if not ptr:
                        raise NaturoError("Failed to lock clipboard memory")
                    try:
                        return ctypes.wstring_at(ptr)
                    finally:
                        kernel32.GlobalUnlock(h)
                finally:
                    user32.CloseClipboard()
            except NaturoError:
                raise
            except Exception as exc:
                raise NaturoError(f"Clipboard read failed: {exc}") from exc

    def clipboard_set(self, text: str = "") -> None:
        """Set the clipboard text content.

        Args:
            text: Text to place on the clipboard.
        """
        try:
            import pyperclip  # type: ignore
            pyperclip.copy(text)
        except ImportError:
            try:
                import ctypes
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                # Set proper restype/argtypes for 64-bit pointer safety
                kernel32.GlobalAlloc.restype = ctypes.c_void_p
                kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
                kernel32.GlobalLock.restype = ctypes.c_void_p
                kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
                kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
                user32.SetClipboardData.restype = ctypes.c_void_p
                user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
                CF_UNICODETEXT = 13
                GMEM_MOVEABLE = 2
                encoded = (text + "\0").encode("utf-16-le")
                h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
                if not h:
                    raise NaturoError("Failed to allocate clipboard memory")
                ptr = kernel32.GlobalLock(h)
                if not ptr:
                    kernel32.GlobalFree = kernel32.GlobalFree  # noqa: E731
                    raise NaturoError("Failed to lock clipboard memory")
                ctypes.memmove(ptr, encoded, len(encoded))
                kernel32.GlobalUnlock(h)
                if not user32.OpenClipboard(0):
                    raise NaturoError("Failed to open clipboard")
                try:
                    user32.EmptyClipboard()
                    user32.SetClipboardData(CF_UNICODETEXT, h)
                finally:
                    user32.CloseClipboard()
            except NaturoError:
                raise
            except Exception as exc:
                raise NaturoError(f"Clipboard write failed: {exc}") from exc

    def clipboard_clear(self) -> None:
        """Clear the clipboard contents."""
        try:
            import pyperclip  # type: ignore
            pyperclip.copy("")
        except ImportError:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                if not user32.OpenClipboard(0):
                    raise NaturoError("Failed to open clipboard")
                try:
                    user32.EmptyClipboard()
                finally:
                    user32.CloseClipboard()
            except NaturoError:
                raise
            except Exception as exc:
                raise NaturoError(f"Clipboard clear failed: {exc}") from exc

    def clipboard_info(self) -> dict:
        """Return information about the current clipboard contents.

        Checks for text, image (CF_DIB/CF_BITMAP), and file (CF_HDROP)
        formats using the Win32 API.

        Returns:
            Dictionary with format, size, has_text, has_image, has_files.
        """
        try:
            import ctypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            user32.GetClipboardData.restype = ctypes.c_void_p
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalSize.restype = ctypes.c_size_t
            kernel32.GlobalSize.argtypes = [ctypes.c_void_p]

            if not user32.OpenClipboard(0):
                raise NaturoError("Failed to open clipboard")
            try:
                CF_UNICODETEXT = 13
                CF_BITMAP = 2
                CF_DIB = 8
                CF_HDROP = 15

                has_text = bool(user32.IsClipboardFormatAvailable(CF_UNICODETEXT))
                has_image = bool(
                    user32.IsClipboardFormatAvailable(CF_BITMAP)
                    or user32.IsClipboardFormatAvailable(CF_DIB)
                )
                has_files = bool(user32.IsClipboardFormatAvailable(CF_HDROP))

                size = 0
                if has_text:
                    fmt = "text"
                    h = user32.GetClipboardData(CF_UNICODETEXT)
                    if h:
                        size = kernel32.GlobalSize(h)
                elif has_image:
                    fmt = "image"
                    h = user32.GetClipboardData(CF_DIB)
                    if h:
                        size = kernel32.GlobalSize(h)
                elif has_files:
                    fmt = "files"
                else:
                    fmt = "empty"

                return {
                    "format": fmt,
                    "size": size,
                    "has_text": has_text,
                    "has_image": has_image,
                    "has_files": has_files,
                }
            finally:
                user32.CloseClipboard()
        except NaturoError:
            raise
        except Exception as exc:
            raise NaturoError(f"Clipboard info failed: {exc}") from exc
