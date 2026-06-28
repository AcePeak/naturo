/**
 * @file window.cpp
 * @brief Window enumeration and info using Win32 API.
 *
 * Uses EnumWindows, GetWindowText, GetWindowRect, etc.
 * Outputs JSON without any external JSON library.
 */

#ifdef _WIN32

#include "naturo/exports.h"
#include <windows.h>
#include <psapi.h>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

/**
 * @brief Escape a string for safe JSON embedding.
 * @param s Input string.
 * @return Escaped string (backslash, quotes, control chars handled).
 */
static std::string json_escape(const char* s) {
    if (!s) return "";
    std::string out;
    out.reserve(strlen(s) + 16);
    for (const char* p = s; *p; ++p) {
        switch (*p) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b";  break;
            case '\f': out += "\\f";  break;
            case '\n': out += "\\n";  break;
            case '\r': out += "\\r";  break;
            case '\t': out += "\\t";  break;
            default:
                if (static_cast<unsigned char>(*p) < 0x20) {
                    char buf[8];
                    snprintf(buf, sizeof(buf), "\\u%04x", (unsigned char)*p);
                    out += buf;
                } else {
                    out += *p;
                }
                break;
        }
    }
    return out;
}

/**
 * @brief Convert a UTF-16 (wide) Win32 string to a UTF-8 narrow buffer.
 *
 * The narrow ``...A`` Win32 read APIs (``GetWindowTextA`` etc.) encode their
 * result in the active ANSI codepage, which silently replaces every character
 * outside that codepage (emoji, cross-script text) with ``'?'`` — irreversible
 * data loss (#1159). Reading via the wide ``...W`` APIs and converting with
 * ``WideCharToMultiByte(CP_UTF8)`` preserves the full Unicode title; the Python
 * bridge already decodes core strings as UTF-8 first (``_decode_native``), so
 * the round-trip is lossless.
 *
 * The output is always NUL-terminated. If the UTF-8 encoding does not fit in
 * @p out_size, it is truncated on a UTF-8 character boundary (never mid
 * multi-byte sequence) so the emitted JSON stays valid.
 *
 * @param wide     Source wide string (may be null or empty).
 * @param out      Destination narrow buffer.
 * @param out_size Size of @p out in bytes (including the NUL terminator).
 */
static void wide_to_utf8(const wchar_t* wide, char* out, size_t out_size) {
    if (out_size == 0) return;
    out[0] = '\0';
    if (!wide || !wide[0]) return;

    int needed = WideCharToMultiByte(CP_UTF8, 0, wide, -1, nullptr, 0, nullptr, nullptr);
    if (needed <= 0) return;  // conversion failure — leave the empty string

    std::string utf8(static_cast<size_t>(needed), '\0');
    WideCharToMultiByte(CP_UTF8, 0, wide, -1, &utf8[0], needed, nullptr, nullptr);

    size_t len = static_cast<size_t>(needed) - 1;  // exclude the NUL terminator
    if (len >= out_size) {
        len = out_size - 1;
        // Back off so we never cut in the middle of a UTF-8 sequence:
        // continuation bytes match 0b10xxxxxx (0x80..0xBF).
        while (len > 0 && (static_cast<unsigned char>(utf8[len]) & 0xC0) == 0x80) {
            --len;
        }
    }
    memcpy(out, utf8.data(), len);
    out[len] = '\0';
}

/** @brief Internal struct for collecting window data. */
struct WindowData {
    uintptr_t hwnd;
    char title[512];
    char process_name[512];
    DWORD pid;
    RECT rect;
    bool is_visible;
    bool is_minimized;
};

/**
 * @brief Format a WindowData as a JSON object string.
 */
static std::string window_to_json(const WindowData& w) {
    char buf[2048];
    snprintf(buf, sizeof(buf),
        "{\"hwnd\":%llu,\"title\":\"%s\",\"process_name\":\"%s\","
        "\"pid\":%lu,\"x\":%ld,\"y\":%ld,\"width\":%ld,\"height\":%ld,"
        "\"is_visible\":%s,\"is_minimized\":%s}",
        (unsigned long long)w.hwnd,
        json_escape(w.title).c_str(),
        json_escape(w.process_name).c_str(),
        (unsigned long)w.pid,
        w.rect.left, w.rect.top,
        w.rect.right - w.rect.left,
        w.rect.bottom - w.rect.top,
        w.is_visible ? "true" : "false",
        w.is_minimized ? "true" : "false");
    return buf;
}

/**
 * @brief Populate a WindowData struct from an HWND.
 */
static void fill_window_data(HWND hwnd, WindowData& wd) {
    wd.hwnd = (uintptr_t)hwnd;

    wchar_t wtitle[512];
    wtitle[0] = L'\0';
    GetWindowTextW(hwnd, wtitle, static_cast<int>(ARRAYSIZE(wtitle)));
    wide_to_utf8(wtitle, wd.title, sizeof(wd.title));

    GetWindowRect(hwnd, &wd.rect);
    wd.is_visible = IsWindowVisible(hwnd) != 0;
    wd.is_minimized = IsIconic(hwnd) != 0;

    wd.pid = 0;
    wd.process_name[0] = '\0';
    GetWindowThreadProcessId(hwnd, &wd.pid);

    if (wd.pid) {
        HANDLE hproc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, wd.pid);
        if (hproc) {
            wchar_t wname[512];
            wname[0] = L'\0';
            DWORD name_len = static_cast<DWORD>(ARRAYSIZE(wname));
            if (QueryFullProcessImageNameW(hproc, 0, wname, &name_len)) {
                wide_to_utf8(wname, wd.process_name, sizeof(wd.process_name));
            } else {
                wd.process_name[0] = '\0';
            }
            CloseHandle(hproc);
        }
    }
}

/** @brief Callback context for EnumWindows. */
struct EnumContext {
    std::vector<WindowData> windows;
};

/**
 * @brief EnumWindows callback — collects visible top-level windows.
 */
static BOOL CALLBACK enum_windows_cb(HWND hwnd, LPARAM lparam) {
    if (!IsWindowVisible(hwnd)) return TRUE;

    // Skip windows with empty titles
    wchar_t title[4];
    title[0] = L'\0';
    if (GetWindowTextW(hwnd, title, static_cast<int>(ARRAYSIZE(title))) == 0) return TRUE;

    auto* ctx = reinterpret_cast<EnumContext*>(lparam);
    WindowData wd = {};
    fill_window_data(hwnd, wd);
    ctx->windows.push_back(wd);
    return TRUE;
}

extern "C" {

NATURO_API int naturo_list_windows(char* result_json, int buf_size) {
    if (!result_json || buf_size <= 0) return -1;

    EnumContext ctx;
    EnumWindows(enum_windows_cb, reinterpret_cast<LPARAM>(&ctx));

    // Build JSON array
    std::string json = "[";
    for (size_t i = 0; i < ctx.windows.size(); ++i) {
        if (i > 0) json += ",";
        json += window_to_json(ctx.windows[i]);
    }
    json += "]";

    if ((int)json.size() + 1 > buf_size) {
        // Write required size as hint in first 4 bytes if possible
        if (buf_size >= 4) {
            int needed = (int)json.size() + 1;
            memcpy(result_json, &needed, 4);
        }
        return -4;
    }

    memcpy(result_json, json.c_str(), json.size() + 1);
    return (int)ctx.windows.size();
}

NATURO_API int naturo_get_window_info(uintptr_t hwnd, char* result_json, int buf_size) {
    if (!result_json || buf_size <= 0) return -1;

    HWND target = (HWND)hwnd;
    if (!IsWindow(target)) return -1;

    WindowData wd = {};
    fill_window_data(target, wd);

    std::string json = window_to_json(wd);

    if ((int)json.size() + 1 > buf_size) {
        if (buf_size >= 4) {
            int needed = (int)json.size() + 1;
            memcpy(result_json, &needed, 4);
        }
        return -4;
    }

    memcpy(result_json, json.c_str(), json.size() + 1);
    return 0;
}

} // extern "C"

#else
// Non-Windows stubs

#include "naturo/exports.h"
#include <cstring>

extern "C" {

NATURO_API int naturo_list_windows(char* result_json, int buf_size) {
    if (!result_json || buf_size < 3) return -1;
    memcpy(result_json, "[]", 3);
    return 0;
}

NATURO_API int naturo_get_window_info(uintptr_t hwnd, char* result_json, int buf_size) {
    (void)hwnd;
    (void)result_json;
    (void)buf_size;
    return -2;  // Not supported on this platform
}

} // extern "C"

#endif // _WIN32
