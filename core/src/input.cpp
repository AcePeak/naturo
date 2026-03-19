/**
 * @file input.cpp
 * @brief Mouse and keyboard input using Win32 SendInput API.
 *
 * Implements Phase 2 "Act" capabilities:
 *   - Mouse move, click (single/double, left/right/middle), scroll
 *   - Keyboard type (UTF-8 text via Unicode SendInput)
 *   - Key press by name (enter, tab, f1-f12, etc.)
 *   - Hotkey combos with modifier bitmask (Ctrl/Alt/Shift/Win)
 *
 * All functions are no-ops on non-Windows builds (return -1).
 */

#ifdef _WIN32

#include "naturo/exports.h"
#include <windows.h>
#include <cstring>
#include <cctype>
#include <string>
#include <vector>

/* ── Helpers ──────────────────────────────────────── */

/**
 * @brief Send a single INPUT event array via SendInput.
 * @param inputs Pointer to INPUT array.
 * @param count  Number of elements.
 * @return 0 on success, -2 on failure.
 */
static int send_inputs(INPUT* inputs, UINT count) {
    UINT sent = SendInput(count, inputs, sizeof(INPUT));
    return (sent == count) ? 0 : -2;
}

/**
 * @brief Build a mouse INPUT for a button event.
 * @param flags MOUSEEVENTF_* flags.
 * @return Filled INPUT struct.
 */
static INPUT make_mouse_input(DWORD flags) {
    INPUT inp = {};
    inp.type = INPUT_MOUSE;
    inp.mi.dwFlags = flags;
    return inp;
}

/**
 * @brief Build a keyboard INPUT for a virtual key event.
 * @param vk    Virtual-key code.
 * @param flags KEYEVENTF_* flags (0 = key down, KEYEVENTF_KEYUP = key up).
 * @return Filled INPUT struct.
 */
static INPUT make_vk_input(WORD vk, DWORD flags = 0) {
    INPUT inp = {};
    inp.type = INPUT_KEYBOARD;
    inp.ki.wVk = vk;
    inp.ki.dwFlags = flags;
    return inp;
}

/**
 * @brief Build a keyboard INPUT for a Unicode character event.
 * @param ch    Unicode character.
 * @param flags KEYEVENTF_* flags.
 * @return Filled INPUT struct.
 */
static INPUT make_unicode_input(WORD ch, DWORD flags = 0) {
    INPUT inp = {};
    inp.type = INPUT_KEYBOARD;
    inp.ki.wScan = ch;
    inp.ki.dwFlags = KEYEVENTF_UNICODE | flags;
    return inp;
}

/**
 * @brief Resolve a named key to a virtual-key code.
 * @param key_name Case-insensitive key name.
 * @return VK_* code, or 0 if unrecognized.
 */
static WORD resolve_key(const char* key_name) {
    if (!key_name) return 0;

    struct KeyMap { const char* name; WORD vk; };
    static const KeyMap TABLE[] = {
        {"enter",    VK_RETURN},
        {"return",   VK_RETURN},
        {"tab",      VK_TAB},
        {"escape",   VK_ESCAPE},
        {"esc",      VK_ESCAPE},
        {"backspace",VK_BACK},
        {"delete",   VK_DELETE},
        {"del",      VK_DELETE},
        {"space",    VK_SPACE},
        {"home",     VK_HOME},
        {"end",      VK_END},
        {"pageup",   VK_PRIOR},
        {"pagedown", VK_NEXT},
        {"pgup",     VK_PRIOR},
        {"pgdn",     VK_NEXT},
        {"left",     VK_LEFT},
        {"right",    VK_RIGHT},
        {"up",       VK_UP},
        {"down",     VK_DOWN},
        {"insert",   VK_INSERT},
        {"ins",      VK_INSERT},
        {"f1",  VK_F1},  {"f2",  VK_F2},  {"f3",  VK_F3},  {"f4",  VK_F4},
        {"f5",  VK_F5},  {"f6",  VK_F6},  {"f7",  VK_F7},  {"f8",  VK_F8},
        {"f9",  VK_F9},  {"f10", VK_F10}, {"f11", VK_F11}, {"f12", VK_F12},
        {"a", 'A'}, {"b", 'B'}, {"c", 'C'}, {"d", 'D'}, {"e", 'E'},
        {"f", 'F'}, {"g", 'G'}, {"h", 'H'}, {"i", 'I'}, {"j", 'J'},
        {"k", 'K'}, {"l", 'L'}, {"m", 'M'}, {"n", 'N'}, {"o", 'O'},
        {"p", 'P'}, {"q", 'Q'}, {"r", 'R'}, {"s", 'S'}, {"t", 'T'},
        {"u", 'U'}, {"v", 'V'}, {"w", 'W'}, {"x", 'X'}, {"y", 'Y'},
        {"z", 'Z'},
        {"0", '0'}, {"1", '1'}, {"2", '2'}, {"3", '3'}, {"4", '4'},
        {"5", '5'}, {"6", '6'}, {"7", '7'}, {"8", '8'}, {"9", '9'},
    };

    // Lowercase the input for comparison
    char lower[64] = {};
    for (int i = 0; i < 63 && key_name[i]; ++i)
        lower[i] = (char)tolower((unsigned char)key_name[i]);

    for (auto& e : TABLE) {
        if (strcmp(e.name, lower) == 0) return e.vk;
    }
    return 0;
}

/* ── naturo_mouse_move ────────────────────────────── */

extern "C" NATURO_API int naturo_mouse_move(int x, int y) {
    // Use SetCursorPos for simplicity; MOUSEEVENTF_MOVE+ABSOLUTE requires
    // scaling to 65535 coords, SetCursorPos is cleaner.
    if (!SetCursorPos(x, y)) return -2;
    return 0;
}

/* ── naturo_mouse_click ───────────────────────────── */

extern "C" NATURO_API int naturo_mouse_click(int button, int double_click) {
    if (button < 0 || button > 2) return -1;

    DWORD down_flag, up_flag;
    switch (button) {
        case 0:  down_flag = MOUSEEVENTF_LEFTDOWN;   up_flag = MOUSEEVENTF_LEFTUP;   break;
        case 1:  down_flag = MOUSEEVENTF_RIGHTDOWN;  up_flag = MOUSEEVENTF_RIGHTUP;  break;
        case 2:  down_flag = MOUSEEVENTF_MIDDLEDOWN; up_flag = MOUSEEVENTF_MIDDLEUP; break;
        default: return -1;
    }

    int clicks = double_click ? 2 : 1;
    for (int i = 0; i < clicks; ++i) {
        INPUT seq[2] = {make_mouse_input(down_flag), make_mouse_input(up_flag)};
        int rc = send_inputs(seq, 2);
        if (rc != 0) return rc;
        if (double_click && i == 0) Sleep(50);  // brief gap between clicks
    }
    return 0;
}

/* ── naturo_mouse_scroll ──────────────────────────── */

extern "C" NATURO_API int naturo_mouse_scroll(int delta, int horizontal) {
    INPUT inp = {};
    inp.type = INPUT_MOUSE;
    inp.mi.mouseData = (DWORD)delta;
    inp.mi.dwFlags = horizontal ? MOUSEEVENTF_HWHEEL : MOUSEEVENTF_WHEEL;
    return send_inputs(&inp, 1);
}

/* ── naturo_key_type ──────────────────────────────── */

extern "C" NATURO_API int naturo_key_type(const char* text, int delay_ms) {
    if (!text) return -1;

    // Convert UTF-8 to UTF-16 for Unicode SendInput
    int wlen = MultiByteToWideChar(CP_UTF8, 0, text, -1, NULL, 0);
    if (wlen <= 0) return -1;

    std::vector<wchar_t> wtext((size_t)wlen);
    MultiByteToWideChar(CP_UTF8, 0, text, -1, wtext.data(), wlen);

    for (int i = 0; i < wlen - 1; ++i) {  // -1 to skip null terminator
        INPUT seq[2] = {
            make_unicode_input((WORD)wtext[i], 0),
            make_unicode_input((WORD)wtext[i], KEYEVENTF_KEYUP),
        };
        if (send_inputs(seq, 2) != 0) return -2;
        if (delay_ms > 0) Sleep((DWORD)delay_ms);
    }
    return 0;
}

/* ── naturo_key_press ─────────────────────────────── */

extern "C" NATURO_API int naturo_key_press(const char* key_name) {
    WORD vk = resolve_key(key_name);
    if (vk == 0) return -1;

    INPUT seq[2] = {make_vk_input(vk, 0), make_vk_input(vk, KEYEVENTF_KEYUP)};
    return send_inputs(seq, 2);
}

/* ── naturo_key_hotkey ────────────────────────────── */

extern "C" NATURO_API int naturo_key_hotkey(int modifiers, const char* key_name) {
    // modifiers: bit0=Ctrl, bit1=Alt, bit2=Shift, bit3=Win
    struct { int bit; WORD vk; } MOD_MAP[] = {
        {0, VK_CONTROL},
        {1, VK_MENU},
        {2, VK_SHIFT},
        {3, VK_LWIN},
    };

    WORD base_vk = 0;
    if (key_name && key_name[0]) {
        base_vk = resolve_key(key_name);
        if (base_vk == 0) return -1;
    }

    // Build: press modifiers down, press base key, release base key,
    //        release modifiers in reverse order.
    std::vector<INPUT> seq;

    for (auto& m : MOD_MAP) {
        if (modifiers & (1 << m.bit)) {
            seq.push_back(make_vk_input(m.vk, 0));
        }
    }

    if (base_vk) {
        seq.push_back(make_vk_input(base_vk, 0));
        seq.push_back(make_vk_input(base_vk, KEYEVENTF_KEYUP));
    }

    // Release modifiers in reverse
    for (int i = 3; i >= 0; --i) {
        if (modifiers & (1 << MOD_MAP[i].bit)) {
            seq.push_back(make_vk_input(MOD_MAP[i].vk, KEYEVENTF_KEYUP));
        }
    }

    if (seq.empty()) return -1;
    return send_inputs(seq.data(), (UINT)seq.size());
}

#else  /* !_WIN32 — stub implementations */

#include "naturo/exports.h"

extern "C" NATURO_API int naturo_mouse_move(int, int)               { return -1; }
extern "C" NATURO_API int naturo_mouse_click(int, int)              { return -1; }
extern "C" NATURO_API int naturo_mouse_scroll(int, int)             { return -1; }
extern "C" NATURO_API int naturo_key_type(const char*, int)         { return -1; }
extern "C" NATURO_API int naturo_key_press(const char*)             { return -1; }
extern "C" NATURO_API int naturo_key_hotkey(int, const char*)       { return -1; }

#endif /* _WIN32 */
