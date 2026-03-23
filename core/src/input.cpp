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
 * Phase 5B.5 adds hardware-level (scancode) keyboard input:
 *   - naturo_phys_key_type: Type text using hardware scan codes
 *   - naturo_phys_key_press: Press a key using hardware scan codes
 *   - naturo_phys_key_hotkey: Hotkey combos using hardware scan codes
 *   These bypass SendInput virtual-key detection used by games and
 *   anti-cheat software, sending raw keyboard scan codes instead.
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

/* ── naturo_mouse_down ─────────────────────────────── */

extern "C" NATURO_API int naturo_mouse_down(int button) {
    if (button < 0 || button > 2) return -1;

    DWORD down_flag;
    switch (button) {
        case 0:  down_flag = MOUSEEVENTF_LEFTDOWN;   break;
        case 1:  down_flag = MOUSEEVENTF_RIGHTDOWN;  break;
        case 2:  down_flag = MOUSEEVENTF_MIDDLEDOWN; break;
        default: return -1;
    }

    INPUT inp = make_mouse_input(down_flag);
    return send_inputs(&inp, 1);
}

/* ── naturo_mouse_up ──────────────────────────────── */

extern "C" NATURO_API int naturo_mouse_up(int button) {
    if (button < 0 || button > 2) return -1;

    DWORD up_flag;
    switch (button) {
        case 0:  up_flag = MOUSEEVENTF_LEFTUP;   break;
        case 1:  up_flag = MOUSEEVENTF_RIGHTUP;  break;
        case 2:  up_flag = MOUSEEVENTF_MIDDLEUP; break;
        default: return -1;
    }

    INPUT inp = make_mouse_input(up_flag);
    return send_inputs(&inp, 1);
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

/* ══════════════════════════════════════════════════════
 * Phase 5B.5 — Hardware-level keyboard input (Phys32)
 *
 * Uses KEYEVENTF_SCANCODE to send raw hardware scan codes via
 * SendInput. Unlike virtual-key input, scan code events are
 * processed at a lower level by the keyboard driver stack,
 * making them harder for applications to distinguish from
 * real hardware keypresses.
 *
 * This is useful for:
 *   - Games that block virtual-key SendInput
 *   - Anti-cheat software that filters KEYEVENTF_UNICODE
 *   - Applications that only respond to hardware interrupts
 *   - DirectInput-based applications
 * ══════════════════════════════════════════════════════ */

/**
 * @brief Build a scancode-based keyboard INPUT struct.
 * @param scancode Hardware scan code value.
 * @param flags    Additional flags (KEYEVENTF_KEYUP, KEYEVENTF_EXTENDEDKEY).
 * @return Filled INPUT struct with KEYEVENTF_SCANCODE.
 */
static INPUT make_scancode_input(WORD scancode, DWORD flags = 0) {
    INPUT inp = {};
    inp.type = INPUT_KEYBOARD;
    inp.ki.wScan = scancode;
    inp.ki.dwFlags = KEYEVENTF_SCANCODE | flags;
    return inp;
}

/**
 * @brief Scan code lookup table.
 *
 * Maps named keys to their PS/2 Set 1 hardware scan codes.
 * Extended keys (arrows, home, end, etc.) use the E0 prefix
 * and must include KEYEVENTF_EXTENDEDKEY in flags.
 */
struct ScanEntry {
    const char* name;
    WORD scancode;
    bool extended;  // true if key requires E0 prefix (KEYEVENTF_EXTENDEDKEY)
};

static const ScanEntry SCAN_TABLE[] = {
    // Row 1 — Function keys
    {"escape",   0x01, false}, {"esc",       0x01, false},
    {"f1",       0x3B, false}, {"f2",        0x3C, false},
    {"f3",       0x3D, false}, {"f4",        0x3E, false},
    {"f5",       0x3F, false}, {"f6",        0x40, false},
    {"f7",       0x41, false}, {"f8",        0x42, false},
    {"f9",       0x43, false}, {"f10",       0x44, false},
    {"f11",      0x57, false}, {"f12",       0x58, false},

    // Row 2 — Number row
    {"1",        0x02, false}, {"2",         0x03, false},
    {"3",        0x04, false}, {"4",         0x05, false},
    {"5",        0x06, false}, {"6",         0x07, false},
    {"7",        0x08, false}, {"8",         0x09, false},
    {"9",        0x0A, false}, {"0",         0x0B, false},

    // Row 3 — QWERTY
    {"q",        0x10, false}, {"w",         0x11, false},
    {"e",        0x12, false}, {"r",         0x13, false},
    {"t",        0x14, false}, {"y",         0x15, false},
    {"u",        0x16, false}, {"i",         0x17, false},
    {"o",        0x18, false}, {"p",         0x19, false},

    // Row 4 — ASDF
    {"a",        0x1E, false}, {"s",         0x1F, false},
    {"d",        0x20, false}, {"f",         0x21, false},
    {"g",        0x22, false}, {"h",         0x23, false},
    {"j",        0x24, false}, {"k",         0x25, false},
    {"l",        0x26, false},

    // Row 5 — ZXCV
    {"z",        0x2C, false}, {"x",         0x2D, false},
    {"c",        0x2E, false}, {"v",         0x2F, false},
    {"b",        0x30, false}, {"n",         0x31, false},
    {"m",        0x32, false},

    // Special keys — main block
    {"backspace", 0x0E, false}, {"tab",      0x0F, false},
    {"enter",     0x1C, false}, {"return",   0x1C, false},
    {"space",     0x39, false},

    // Modifier keys
    {"lshift",    0x2A, false}, {"rshift",   0x36, false},
    {"lctrl",     0x1D, false}, {"rctrl",    0x1D, true},
    {"lalt",      0x38, false}, {"ralt",     0x38, true},

    // Extended keys (E0 prefix)
    {"insert",    0x52, true},  {"ins",      0x52, true},
    {"delete",    0x53, true},  {"del",      0x53, true},
    {"home",      0x47, true},  {"end",      0x4F, true},
    {"pageup",    0x49, true},  {"pgup",     0x49, true},
    {"pagedown",  0x51, true},  {"pgdn",     0x51, true},
    {"up",        0x48, true},  {"down",     0x50, true},
    {"left",      0x4B, true},  {"right",    0x4D, true},

    // Windows keys
    {"lwin",      0x5B, true},  {"rwin",     0x5C, true},
    {"apps",      0x5D, true},  // context menu key
};

static const int SCAN_TABLE_SIZE = sizeof(SCAN_TABLE) / sizeof(SCAN_TABLE[0]);

/**
 * @brief Resolve a named key to a hardware scan code entry.
 * @param key_name Case-insensitive key name.
 * @return Pointer to ScanEntry, or nullptr if not found.
 */
static const ScanEntry* resolve_scancode(const char* key_name) {
    if (!key_name) return nullptr;

    char lower[64] = {};
    for (int i = 0; i < 63 && key_name[i]; ++i)
        lower[i] = (char)tolower((unsigned char)key_name[i]);

    for (int i = 0; i < SCAN_TABLE_SIZE; ++i) {
        if (strcmp(SCAN_TABLE[i].name, lower) == 0)
            return &SCAN_TABLE[i];
    }
    return nullptr;
}

/**
 * @brief Map a VK code to its PS/2 scan code (for typing characters).
 *
 * Uses MapVirtualKeyA(vk, MAPVK_VK_TO_VSC) which returns the scan code
 * corresponding to the virtual key. Falls back to 0 if unmapped.
 */
static WORD vk_to_scancode(WORD vk) {
    UINT sc = MapVirtualKeyA(vk, MAPVK_VK_TO_VSC);
    return (WORD)sc;
}

/* ── naturo_phys_key_type ─────────────────────────── */

extern "C" NATURO_API int naturo_phys_key_type(const char* text, int delay_ms) {
    if (!text) return -1;

    // Convert UTF-8 to UTF-16
    int wlen = MultiByteToWideChar(CP_UTF8, 0, text, -1, NULL, 0);
    if (wlen <= 0) return -1;

    std::vector<wchar_t> wtext((size_t)wlen);
    MultiByteToWideChar(CP_UTF8, 0, text, -1, wtext.data(), wlen);

    for (int i = 0; i < wlen - 1; ++i) {
        wchar_t ch = wtext[i];

        // Use VkKeyScanW to find VK + shift state for this character
        SHORT vk_result = VkKeyScanW(ch);
        if (vk_result == -1) {
            // Character has no keyboard mapping; fall back to Unicode input
            INPUT seq[2] = {
                make_unicode_input((WORD)ch, 0),
                make_unicode_input((WORD)ch, KEYEVENTF_KEYUP),
            };
            if (send_inputs(seq, 2) != 0) return -2;
        } else {
            BYTE vk = LOBYTE(vk_result);
            BYTE shift_state = HIBYTE(vk_result);

            WORD sc = vk_to_scancode(vk);
            if (sc == 0) {
                // No scan code mapping; fall back to Unicode
                INPUT seq[2] = {
                    make_unicode_input((WORD)ch, 0),
                    make_unicode_input((WORD)ch, KEYEVENTF_KEYUP),
                };
                if (send_inputs(seq, 2) != 0) return -2;
            } else {
                std::vector<INPUT> seq;

                // Press required modifiers
                if (shift_state & 1) {  // Shift
                    seq.push_back(make_scancode_input(0x2A));  // LShift down
                }
                if (shift_state & 2) {  // Ctrl
                    seq.push_back(make_scancode_input(0x1D));  // LCtrl down
                }
                if (shift_state & 4) {  // Alt
                    seq.push_back(make_scancode_input(0x38));  // LAlt down
                }

                // Press and release the key
                seq.push_back(make_scancode_input(sc));
                seq.push_back(make_scancode_input(sc, KEYEVENTF_KEYUP));

                // Release modifiers in reverse
                if (shift_state & 4) {
                    seq.push_back(make_scancode_input(0x38, KEYEVENTF_KEYUP));
                }
                if (shift_state & 2) {
                    seq.push_back(make_scancode_input(0x1D, KEYEVENTF_KEYUP));
                }
                if (shift_state & 1) {
                    seq.push_back(make_scancode_input(0x2A, KEYEVENTF_KEYUP));
                }

                if (send_inputs(seq.data(), (UINT)seq.size()) != 0) return -2;
            }
        }

        if (delay_ms > 0) Sleep((DWORD)delay_ms);
    }
    return 0;
}

/* ── naturo_phys_key_press ────────────────────────── */

extern "C" NATURO_API int naturo_phys_key_press(const char* key_name) {
    const ScanEntry* entry = resolve_scancode(key_name);
    if (!entry) {
        // Try resolving via VK → scan code as fallback
        WORD vk = resolve_key(key_name);
        if (vk == 0) return -1;
        WORD sc = vk_to_scancode(vk);
        if (sc == 0) return -1;

        INPUT seq[2] = {
            make_scancode_input(sc),
            make_scancode_input(sc, KEYEVENTF_KEYUP),
        };
        return send_inputs(seq, 2);
    }

    DWORD ext = entry->extended ? KEYEVENTF_EXTENDEDKEY : 0;
    INPUT seq[2] = {
        make_scancode_input(entry->scancode, ext),
        make_scancode_input(entry->scancode, ext | KEYEVENTF_KEYUP),
    };
    return send_inputs(seq, 2);
}

/* ── naturo_phys_key_hotkey ───────────────────────── */

extern "C" NATURO_API int naturo_phys_key_hotkey(int modifiers, const char* key_name) {
    // modifiers: bit0=Ctrl, bit1=Alt, bit2=Shift, bit3=Win
    struct { int bit; WORD scancode; DWORD ext; } MOD_SC[] = {
        {0, 0x1D, 0},                       // LCtrl
        {1, 0x38, 0},                       // LAlt
        {2, 0x2A, 0},                       // LShift
        {3, 0x5B, KEYEVENTF_EXTENDEDKEY},  // LWin
    };

    // Resolve base key
    WORD base_sc = 0;
    DWORD base_ext = 0;
    if (key_name && key_name[0]) {
        const ScanEntry* entry = resolve_scancode(key_name);
        if (entry) {
            base_sc = entry->scancode;
            base_ext = entry->extended ? KEYEVENTF_EXTENDEDKEY : 0;
        } else {
            // Fallback: VK → scancode
            WORD vk = resolve_key(key_name);
            if (vk == 0) return -1;
            base_sc = vk_to_scancode(vk);
            if (base_sc == 0) return -1;
        }
    }

    std::vector<INPUT> seq;

    // Press modifiers
    for (auto& m : MOD_SC) {
        if (modifiers & (1 << m.bit)) {
            seq.push_back(make_scancode_input(m.scancode, m.ext));
        }
    }

    // Press and release base key
    if (base_sc) {
        seq.push_back(make_scancode_input(base_sc, base_ext));
        seq.push_back(make_scancode_input(base_sc, base_ext | KEYEVENTF_KEYUP));
    }

    // Release modifiers in reverse
    for (int i = 3; i >= 0; --i) {
        if (modifiers & (1 << MOD_SC[i].bit)) {
            seq.push_back(make_scancode_input(MOD_SC[i].scancode,
                                               MOD_SC[i].ext | KEYEVENTF_KEYUP));
        }
    }

    if (seq.empty()) return -1;
    return send_inputs(seq.data(), (UINT)seq.size());
}

#else  /* !_WIN32 — stub implementations */

#include "naturo/exports.h"

extern "C" NATURO_API int naturo_mouse_move(int, int)               { return -1; }
extern "C" NATURO_API int naturo_mouse_click(int, int)              { return -1; }
extern "C" NATURO_API int naturo_mouse_down(int)                    { return -1; }
extern "C" NATURO_API int naturo_mouse_up(int)                      { return -1; }
extern "C" NATURO_API int naturo_mouse_scroll(int, int)             { return -1; }
extern "C" NATURO_API int naturo_key_type(const char*, int)         { return -1; }
extern "C" NATURO_API int naturo_key_press(const char*)             { return -1; }
extern "C" NATURO_API int naturo_key_hotkey(int, const char*)       { return -1; }
extern "C" NATURO_API int naturo_phys_key_type(const char*, int)    { return -1; }
extern "C" NATURO_API int naturo_phys_key_press(const char*)        { return -1; }
extern "C" NATURO_API int naturo_phys_key_hotkey(int, const char*)  { return -1; }

#endif /* _WIN32 */
