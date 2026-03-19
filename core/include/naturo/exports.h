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

#ifdef __cplusplus
}
#endif

#endif /* NATURO_EXPORTS_H */
