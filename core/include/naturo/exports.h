/**
 * @file exports.h
 * @brief Public API for the naturo_core native library.
 *
 * All functions use C linkage for cross-language compatibility.
 * Error codes: 0 = success, -1 = invalid argument, -2 = COM/system error,
 *              -3 = file I/O error, -4 = buffer too small.
 */

#ifndef NATURO_EXPORTS_H
#define NATURO_EXPORTS_H

#include <stdint.h>

#ifdef _WIN32
    #ifdef NATURO_BUILDING
        #define NATURO_API __declspec(dllexport)
    #else
        #define NATURO_API __declspec(dllimport)
    #endif
#else
    #define NATURO_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

/* ── Lifecycle ────────────────────────────────────── */

/**
 * @brief Get the library version string.
 * @return Null-terminated version string (e.g., "0.1.0"). Never NULL.
 */
NATURO_API const char* naturo_version(void);

/**
 * @brief Initialize the naturo_core library.
 *
 * Must be called before any other API function (except naturo_version).
 * Safe to call multiple times (idempotent).
 * On Windows, initializes COM for UIAutomation.
 *
 * @return 0 on success, -2 on COM initialization failure.
 */
NATURO_API int naturo_init(void);

/**
 * @brief Shut down the naturo_core library and release resources.
 *
 * Safe to call multiple times (idempotent).
 *
 * @return 0 on success.
 */
NATURO_API int naturo_shutdown(void);

/* ── Screen Capture ───────────────────────────────── */

/**
 * @brief Capture a screenshot of the entire screen or a specific monitor.
 * @param screen_index Zero-based monitor index. Use 0 for primary screen.
 * @param output_path File path to save the screenshot (BMP format).
 * @return 0 on success, -1 on invalid argument, -2 on capture error, -3 on file error.
 */
NATURO_API int naturo_capture_screen(int screen_index, const char* output_path);

/**
 * @brief Capture a screenshot of a specific window.
 * @param hwnd Window handle (HWND cast to uintptr_t). Pass 0 to capture the foreground window.
 * @param output_path File path to save the screenshot (BMP format).
 * @return 0 on success, -1 on invalid argument, -2 on capture error, -3 on file error.
 */
NATURO_API int naturo_capture_window(uintptr_t hwnd, const char* output_path);

/* ── Window Listing ───────────────────────────────── */

/**
 * @brief List all visible top-level windows.
 * @param result_json Buffer to receive a JSON array of window info objects.
 *        Each object: {"hwnd":N,"title":"...","process_name":"...","pid":N,
 *        "x":N,"y":N,"width":N,"height":N,"is_visible":B,"is_minimized":B}
 * @param buf_size Size of the result_json buffer in bytes.
 * @return Number of windows found (>= 0), or negative error code.
 *         Returns -4 if buffer too small.
 */
NATURO_API int naturo_list_windows(char* result_json, int buf_size);

/**
 * @brief Get information about a specific window.
 * @param hwnd Window handle.
 * @param result_json Buffer to receive a JSON object with window info.
 * @param buf_size Size of the buffer in bytes.
 * @return 0 on success, -1 if window not found, -4 if buffer too small.
 */
NATURO_API int naturo_get_window_info(uintptr_t hwnd, char* result_json, int buf_size);

/* ── UI Element Tree ──────────────────────────────── */

/**
 * @brief Inspect the UI Automation element tree of a window.
 * @param hwnd Window handle. Pass 0 for the focused/foreground window.
 * @param depth Maximum tree depth to traverse (clamped to 1-10).
 * @param result_json Buffer to receive a JSON tree of UI elements.
 *        Each element: {"id":"...","role":"...","name":"...","value":"...",
 *        "x":N,"y":N,"width":N,"height":N,"children":[...]}
 * @param buf_size Size of the buffer in bytes.
 * @return Number of elements found (>= 0), or negative error code.
 *         Returns -2 on UIAutomation error, -4 if buffer too small.
 */
NATURO_API int naturo_get_element_tree(uintptr_t hwnd, int depth,
                                       char* result_json, int buf_size);

/**
 * @brief Find a UI element by role and/or name within a window.
 * @param hwnd Window handle. Pass 0 for the focused/foreground window.
 * @param role Element role filter (e.g., "Button", "Edit"). NULL for any role.
 * @param name Element name filter. NULL for any name.
 * @param result_json Buffer to receive a JSON object of the found element.
 * @param buf_size Size of the buffer in bytes.
 * @return 0 if found, 1 if not found, -1 on invalid argument,
 *         -2 on UIAutomation error, -4 if buffer too small.
 */
NATURO_API int naturo_find_element(uintptr_t hwnd, const char* role,
                                    const char* name, char* result_json,
                                    int buf_size);

/* ── Input — Mouse ────────────────────────────────── */

/**
 * @brief Move the mouse cursor to absolute screen coordinates.
 * @param x Target X coordinate (screen pixels, top-left origin).
 * @param y Target Y coordinate.
 * @return 0 on success, -1 on invalid argument.
 */
NATURO_API int naturo_mouse_move(int x, int y);

/**
 * @brief Click the mouse at the current cursor position.
 * @param button Mouse button: 0 = left, 1 = right, 2 = middle.
 * @param double_click Non-zero for double-click, 0 for single.
 * @return 0 on success, -1 on invalid argument, -2 on system error.
 */
NATURO_API int naturo_mouse_click(int button, int double_click);

/**
 * @brief Press a mouse button down (without releasing).
 * @param button Mouse button: 0 = left, 1 = right, 2 = middle.
 * @return 0 on success, -1 on invalid argument, -2 on system error.
 */
NATURO_API int naturo_mouse_down(int button);

/**
 * @brief Release a mouse button.
 * @param button Mouse button: 0 = left, 1 = right, 2 = middle.
 * @return 0 on success, -1 on invalid argument, -2 on system error.
 */
NATURO_API int naturo_mouse_up(int button);

/**
 * @brief Scroll the mouse wheel.
 * @param delta Positive = scroll up/forward, negative = scroll down/backward.
 *              Typically ±120 per notch (Windows WHEEL_DELTA).
 * @param horizontal Non-zero for horizontal scroll, 0 for vertical.
 * @return 0 on success, -2 on system error.
 */
NATURO_API int naturo_mouse_scroll(int delta, int horizontal);

/* ── Input — Keyboard ─────────────────────────────── */

/**
 * @brief Type a UTF-8 string using SendInput.
 * @param text Null-terminated UTF-8 string to type.
 * @param delay_ms Delay between keystrokes in milliseconds.
 * @return 0 on success, -1 on invalid argument, -2 on system error.
 */
NATURO_API int naturo_key_type(const char* text, int delay_ms);

/**
 * @brief Press and release a named key.
 * @param key_name Null-terminated key name string. Supported:
 *        enter, tab, escape, esc, backspace, delete, del,
 *        space, home, end, pageup, pagedown,
 *        left, right, up, down,
 *        f1..f12, a..z, 0..9.
 * @return 0 on success, -1 if key name unrecognized, -2 on system error.
 */
NATURO_API int naturo_key_press(const char* key_name);

/**
 * @brief Press a key combination (hotkey) with optional modifiers.
 * @param modifiers Bitmask: bit 0 = Ctrl, bit 1 = Alt, bit 2 = Shift,
 *                  bit 3 = Win.
 * @param key_name The base key name (same set as naturo_key_press).
 *                 May be NULL to press modifier keys alone.
 * @return 0 on success, -1 on invalid argument, -2 on system error.
 */
NATURO_API int naturo_key_hotkey(int modifiers, const char* key_name);

/* ── MSAA / IAccessible ───────────────────────────── */

/**
 * @brief Inspect the MSAA (IAccessible) element tree of a window.
 *
 * Provides element inspection for legacy applications that lack
 * UIAutomation support (MFC, VB6, Delphi, native Win32, etc.).
 *
 * @param hwnd Window handle. Pass 0 for the foreground window.
 * @param depth Maximum tree depth to traverse (clamped to 1-10).
 * @param result_json Buffer to receive a JSON tree of MSAA elements.
 *        Each element: {"id":"mN","role":"...","role_id":N,"name":"...",
 *        "value":"...","x":N,"y":N,"width":N,"height":N,"state":N,
 *        "keyboard_shortcut":"...","backend":"msaa","children":[...]}
 * @param buf_size Size of the buffer in bytes.
 * @return Number of elements found (>= 0), or negative error code.
 *         Returns -2 on MSAA/COM error, -4 if buffer too small.
 */
NATURO_API int naturo_msaa_get_element_tree(uintptr_t hwnd, int depth,
                                             char* result_json, int buf_size);

/**
 * @brief Find an MSAA element by role and/or name within a window.
 *
 * Uses BFS traversal of the IAccessible tree. Role matching uses
 * the same human-readable names as the tree output (e.g., "Button",
 * "Edit", "MenuItem").
 *
 * @param hwnd Window handle. Pass 0 for the foreground window.
 * @param role Element role filter (case-insensitive). NULL for any role.
 * @param name Element name filter (case-insensitive). NULL for any name.
 * @param result_json Buffer to receive a JSON object of the found element.
 * @param buf_size Size of the buffer in bytes.
 * @return 0 if found, 1 if not found, -1 on invalid argument,
 *         -2 on MSAA/COM error, -4 if buffer too small.
 */
NATURO_API int naturo_msaa_find_element(uintptr_t hwnd, const char* role,
                                         const char* name,
                                         char* result_json, int buf_size);

/* ── IAccessible2 ─────────────────────────────────── */

/**
 * @brief Inspect the IAccessible2 element tree of a window.
 *
 * Provides extended accessibility info for IA2-enabled applications
 * (Firefox, Thunderbird, LibreOffice, etc.). Includes IA2-specific
 * properties like object attributes, extended roles, and states.
 *
 * @param hwnd Window handle. Pass 0 for the foreground window.
 * @param depth Maximum tree depth to traverse (clamped to 1-10).
 * @param result_json Buffer to receive a JSON tree of IA2 elements.
 *        Each element: {"id":"aN","role":"...","role_id":N,"name":"...",
 *        "value":"...","x":N,"y":N,"width":N,"height":N,"state":N,
 *        "keyboard_shortcut":"...","backend":"ia2","ia2":true|false,
 *        "ia2_states":N,"ia2_unique_id":N,"ia2_attributes":"...",
 *        "children":[...]}
 * @param buf_size Size of the buffer in bytes.
 * @return Number of elements found (>= 0), -2 on COM error,
 *         -4 if buffer too small, -5 if IA2 not supported by application.
 */
NATURO_API int naturo_ia2_get_element_tree(uintptr_t hwnd, int depth,
                                            char* result_json, int buf_size);

/**
 * @brief Find an IA2 element by role and/or name within a window.
 *
 * Uses BFS traversal of the IAccessible2 tree. Role matching uses
 * both MSAA and IA2-extended role names (e.g., "Heading", "Paragraph",
 * "Landmark" for IA2-specific roles).
 *
 * @param hwnd Window handle. Pass 0 for the foreground window.
 * @param role Element role filter (case-insensitive). NULL for any role.
 * @param name Element name filter (case-insensitive). NULL for any name.
 * @param result_json Buffer to receive a JSON object of the found element.
 * @param buf_size Size of the buffer in bytes.
 * @return 0 if found, 1 if not found, -1 on invalid argument,
 *         -2 on COM error, -4 if buffer too small, -5 if IA2 not supported.
 */
NATURO_API int naturo_ia2_find_element(uintptr_t hwnd, const char* role,
                                        const char* name,
                                        char* result_json, int buf_size);

/**
 * @brief Check if a window supports IAccessible2.
 *
 * @param hwnd Window handle. Pass 0 for the foreground window.
 * @return 1 if IA2 supported, 0 if not supported, -2 on COM error.
 */
NATURO_API int naturo_ia2_check_support(uintptr_t hwnd);

/* ── Element Value Reading ─────────────────────────── */

/**
 * @brief Read the current value of a UI element using UIA patterns.
 *
 * Queries multiple UIA patterns in priority order to retrieve the
 * element's current value:
 *   1. ValuePattern.Value — text fields, dropdowns
 *   2. TextPattern.DocumentRange.GetText() — rich text controls
 *   3. TogglePattern.ToggleState — checkboxes (On/Off/Indeterminate)
 *   4. SelectionPattern — selected items in lists/combos
 *   5. RangeValuePattern.Value — sliders, progress bars
 *
 * The element is located by its AutomationId within the given window.
 * If automation_id is NULL and role+name are provided, the element is
 * found by role/name matching (same logic as naturo_find_element).
 *
 * @param hwnd Window handle. Pass 0 for the foreground window.
 * @param automation_id AutomationId of the target element. NULL to use role/name.
 * @param role Element role filter (used when automation_id is NULL).
 * @param name Element name filter (used when automation_id is NULL).
 * @param result_json Buffer to receive a JSON object:
 *        {"value":"...","pattern":"ValuePattern","role":"Edit","name":"Search",
 *         "automation_id":"txtSearch","states":["focusable","focused"],
 *         "x":N,"y":N,"width":N,"height":N}
 *        If no value pattern is supported: {"value":null,"pattern":null,...}
 * @param buf_size Size of the buffer in bytes.
 * @return 0 on success, 1 if element not found, -1 on invalid argument,
 *         -2 on UIAutomation error, -4 if buffer too small.
 */
NATURO_API int naturo_get_element_value(uintptr_t hwnd,
                                         const char* automation_id,
                                         const char* role,
                                         const char* name,
                                         char* result_json, int buf_size);

/* ── Hardware-level Keyboard (Phys32) ─────────────── */

/**
 * @brief Type a UTF-8 string using hardware scan codes.
 *
 * Similar to naturo_key_type but uses KEYEVENTF_SCANCODE instead of
 * virtual keys or Unicode events. Characters without a direct keyboard
 * mapping fall back to Unicode input transparently.
 *
 * @param text Null-terminated UTF-8 string to type.
 * @param delay_ms Delay between keystrokes in milliseconds.
 * @return 0 on success, -1 on invalid argument, -2 on system error.
 */
NATURO_API int naturo_phys_key_type(const char* text, int delay_ms);

/**
 * @brief Press and release a named key using hardware scan codes.
 *
 * Uses PS/2 Set 1 scan codes with KEYEVENTF_SCANCODE. Extended keys
 * (arrows, home, end, etc.) include the E0 prefix automatically.
 *
 * @param key_name Null-terminated key name (same set as naturo_key_press).
 * @return 0 on success, -1 if key unrecognized, -2 on system error.
 */
NATURO_API int naturo_phys_key_press(const char* key_name);

/**
 * @brief Press a hotkey combination using hardware scan codes.
 *
 * @param modifiers Bitmask: bit 0 = Ctrl, bit 1 = Alt, bit 2 = Shift,
 *                  bit 3 = Win.
 * @param key_name The base key name. May be NULL for modifier-only combos.
 * @return 0 on success, -1 on invalid argument, -2 on system error.
 */
NATURO_API int naturo_phys_key_hotkey(int modifiers, const char* key_name);

/* ── Java Access Bridge (JAB) ─────────────────────── */

/**
 * @brief Inspect the Java Access Bridge element tree of a window.
 *
 * Provides element inspection for Java/Swing/AWT applications via
 * the Windows Java Access Bridge API. Requires a JRE/JDK with
 * accessibility enabled and WindowsAccessBridge-64.dll available.
 *
 * @param hwnd Window handle. Pass 0 for the foreground window.
 * @param depth Maximum tree depth to traverse (clamped to 1-10).
 * @param result_json Buffer to receive a JSON tree of JAB elements.
 *        Each element: {"id":"jN","role":"...","name":"...","value":"...",
 *        "x":N,"y":N,"width":N,"height":N,"states":"...","jab_role":"...",
 *        "backend":"jab","children":[...]}
 * @param buf_size Size of the buffer in bytes.
 * @return Number of elements found (>= 0), -2 on JAB error,
 *         -4 if buffer too small, -6 if JAB not available.
 */
NATURO_API int naturo_jab_get_element_tree(uintptr_t hwnd, int depth,
                                            char* result_json, int buf_size);

/**
 * @brief Find a JAB element by role and/or name within a window.
 *
 * Uses BFS traversal of the Java accessibility tree. Role matching
 * uses normalized role names (e.g., "Button", "Edit", "MenuItem").
 *
 * @param hwnd Window handle. Pass 0 for the foreground window.
 * @param role Element role filter (case-insensitive). NULL for any role.
 * @param name Element name filter (case-insensitive). NULL for any name.
 * @param result_json Buffer to receive a JSON object of the found element.
 * @param buf_size Size of the buffer in bytes.
 * @return 0 if found, 1 if not found, -1 on invalid argument,
 *         -2 on JAB error, -4 if buffer too small, -6 if JAB not available.
 */
NATURO_API int naturo_jab_find_element(uintptr_t hwnd, const char* role,
                                        const char* name,
                                        char* result_json, int buf_size);

/**
 * @brief Check if a window supports Java Access Bridge.
 *
 * @param hwnd Window handle. Pass 0 to check for any Java window.
 * @return 1 if JAB supported, 0 if not supported.
 */
NATURO_API int naturo_jab_check_support(uintptr_t hwnd);

#ifdef __cplusplus
}
#endif

#endif /* NATURO_EXPORTS_H */
