"""Dialog detection and interaction engine.

Phase 4.5.1 + 4.5.2 — Detects system dialogs (message boxes, file pickers,
confirmation prompts) and provides structured interaction capabilities.

Dialog types:
- MessageBox: Standard Windows MessageBox (OK, OK/Cancel, Yes/No, etc.)
- FileDialog: Open/Save file pickers (common dialog)
- FolderDialog: Folder browser dialog
- PrintDialog: Print dialog
- ColorDialog: Color picker
- FontDialog: Font picker
- Custom: Application-specific modal dialogs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DialogType(str, Enum):
    """Recognized dialog types."""

    MESSAGE_BOX = "message_box"
    FILE_OPEN = "file_open"
    FILE_SAVE = "file_save"
    FOLDER_BROWSE = "folder_browse"
    PRINT = "print"
    COLOR_PICKER = "color_picker"
    FONT_PICKER = "font_picker"
    CONFIRMATION = "confirmation"
    INPUT = "input"
    CUSTOM = "custom"


@dataclass
class DialogButton:
    """A button found within a dialog.

    Attributes:
        name: Button text (e.g., "OK", "Cancel", "Yes", "No").
        element_id: Backend element identifier for clicking.
        is_default: Whether this is the default/focused button.
        is_cancel: Whether this is the cancel button.
        x: Center X coordinate.
        y: Center Y coordinate.
    """

    name: str
    element_id: str
    is_default: bool = False
    is_cancel: bool = False
    x: int = 0
    y: int = 0


@dataclass
class DialogInfo:
    """Detected dialog information.

    Attributes:
        hwnd: Window handle of the dialog.
        title: Dialog window title.
        dialog_type: Classified dialog type.
        message: Message text (for message boxes/confirmations).
        buttons: Available buttons.
        has_input: Whether the dialog has a text input field.
        input_value: Current value of the input field (if any).
        file_path: Current file path (for file dialogs).
        owner_app: The application that owns this dialog.
        owner_hwnd: Handle of the owner window.
    """

    hwnd: int
    title: str
    dialog_type: DialogType
    message: str = ""
    buttons: list[DialogButton] = field(default_factory=list)
    has_input: bool = False
    input_value: str = ""
    file_path: str = ""
    owner_app: str = ""
    owner_hwnd: int = 0

    def to_dict(self) -> dict:
        """Serialize to dict for JSON output."""
        return {
            "hwnd": self.hwnd,
            "title": self.title,
            "dialog_type": self.dialog_type.value,
            "message": self.message,
            "buttons": [
                {
                    "name": b.name,
                    "is_default": b.is_default,
                    "is_cancel": b.is_cancel,
                }
                for b in self.buttons
            ],
            "has_input": self.has_input,
            "input_value": self.input_value,
            "file_path": self.file_path,
            "owner_app": self.owner_app,
            "owner_hwnd": self.owner_hwnd,
        }


# ── Known dialog class names ────────────────────────────────────────────────

# Standard Win32 dialog class: "#32770"
_DIALOG_CLASS_NAMES = {
    "#32770",  # Standard Windows dialog (MessageBox, common dialogs)
}

# File dialog indicators (UIA roles and class names)
_FILE_DIALOG_INDICATORS = {
    "DUIViewWndClassName",
    "DirectUIHWND",
    "ShellTabWindowClass",
    "SHELLDLL_DefView",
}

# Known button texts for dialog classification
_ACCEPT_BUTTONS = {"ok", "yes", "open", "save", "print", "apply", "continue",
                   "确定", "是", "打开", "保存", "打印", "应用", "继续"}
_DISMISS_BUTTONS = {"cancel", "no", "close", "abort", "取消", "否", "关闭", "中止"}


def classify_dialog(
    title: str,
    class_name: str,
    buttons: list[str],
    has_edit: bool,
    has_file_list: bool,
) -> DialogType:
    """Classify a dialog window by its properties.

    Args:
        title: Dialog window title.
        class_name: Win32 window class name.
        buttons: List of button text labels.
        has_edit: Whether the dialog contains an Edit control.
        has_file_list: Whether the dialog contains a file list view.

    Returns:
        Best-matching DialogType.
    """
    title_lower = title.lower()
    buttons_lower = {b.lower() for b in buttons}

    # File dialogs
    if has_file_list or "shelldll_defview" in class_name.lower():
        if "save" in title_lower or "save" in buttons_lower or "另存" in title_lower:
            return DialogType.FILE_SAVE
        if "open" in title_lower or "打开" in title_lower:
            return DialogType.FILE_OPEN
        if "browse" in title_lower or "浏览" in title_lower:
            return DialogType.FOLDER_BROWSE
        # Default to file open if we see a file list
        return DialogType.FILE_OPEN

    # Print dialog
    if "print" in title_lower or "打印" in title_lower:
        return DialogType.PRINT

    # Color picker
    if "color" in title_lower or "颜色" in title_lower:
        return DialogType.COLOR_PICKER

    # Font picker
    if "font" in title_lower or "字体" in title_lower:
        return DialogType.FONT_PICKER

    # Input dialog (has edit + ok/cancel)
    if has_edit and buttons_lower & _ACCEPT_BUTTONS:
        return DialogType.INPUT

    # Confirmation (Yes/No or OK/Cancel with message)
    yes_no = {"yes", "no", "是", "否"}
    if buttons_lower & yes_no:
        return DialogType.CONFIRMATION

    # Standard message box
    if buttons_lower & _ACCEPT_BUTTONS:
        return DialogType.MESSAGE_BOX

    return DialogType.CUSTOM
