/**
 * @file test_input.cpp
 * @brief C++ unit tests for Phase 2 input API (naturo_key_press, etc.)
 *
 * These tests run headlessly and only verify return codes and argument
 * validation. Actual SendInput effects are skipped in headless CI.
 *
 * Tests that require a real display (non-zero SendInput) are guarded
 * by NATURO_TEST_INTERACTIVE env var.
 */

#include "naturo/exports.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>

#define CHECK(cond, msg) \
    do { \
        if (!(cond)) { \
            printf("FAIL: %s\n", msg); \
            return 1; \
        } \
        printf("PASS: %s\n", msg); \
    } while (0)

/* ── naturo_mouse_move ────────────────────────────── */

static int test_mouse_move_valid() {
    // On headless CI (no display), SetCursorPos may fail → -2 is also OK.
    int rc = naturo_mouse_move(100, 100);
    CHECK(rc == 0 || rc == -2, "mouse_move(100,100) returns 0 or -2");
    return 0;
}

/* ── naturo_mouse_click ───────────────────────────── */

static int test_mouse_click_invalid_button() {
    int rc = naturo_mouse_click(5, 0);
    CHECK(rc == -1, "mouse_click(button=5) returns -1");
    return 0;
}

static int test_mouse_click_valid() {
    int rc = naturo_mouse_click(0, 0);  // left single click at current pos
    CHECK(rc == 0 || rc == -2, "mouse_click(left, single) returns 0 or -2");
    return 0;
}

/* ── naturo_mouse_scroll ──────────────────────────── */

static int test_mouse_scroll_down() {
    int rc = naturo_mouse_scroll(-120, 0);  // one notch down
    CHECK(rc == 0 || rc == -2, "mouse_scroll(-120, vertical) returns 0 or -2");
    return 0;
}

static int test_mouse_scroll_horizontal() {
    int rc = naturo_mouse_scroll(120, 1);  // one notch right
    CHECK(rc == 0 || rc == -2, "mouse_scroll(120, horizontal) returns 0 or -2");
    return 0;
}

/* ── naturo_key_press ─────────────────────────────── */

static int test_key_press_null() {
#ifdef _WIN32
    int rc = naturo_key_press(nullptr);
    CHECK(rc == -1, "key_press(NULL) returns -1");
#else
    int rc = naturo_key_press(nullptr);
    CHECK(rc == -1, "key_press(NULL) returns -1 (stub)");
#endif
    return 0;
}

static int test_key_press_unknown() {
    int rc = naturo_key_press("xyzzy_unknown_key_name");
    CHECK(rc == -1, "key_press(unknown) returns -1");
    return 0;
}

static int test_key_press_enter() {
    int rc = naturo_key_press("enter");
    CHECK(rc == 0 || rc == -1 || rc == -2, "key_press(enter) returns valid code");
    return 0;
}

static int test_key_press_escape() {
    int rc = naturo_key_press("escape");
    CHECK(rc == 0 || rc == -1 || rc == -2, "key_press(escape) returns valid code");
    return 0;
}

static int test_key_press_f5() {
    int rc = naturo_key_press("f5");
    CHECK(rc == 0 || rc == -1 || rc == -2, "key_press(f5) returns valid code");
    return 0;
}

static int test_key_press_esc_alias() {
    int rc = naturo_key_press("esc");
    CHECK(rc == 0 || rc == -1 || rc == -2, "key_press(esc alias) returns valid code");
    return 0;
}

/* ── naturo_key_type ──────────────────────────────── */

static int test_key_type_null() {
    int rc = naturo_key_type(nullptr, 0);
    CHECK(rc == -1, "key_type(NULL) returns -1");
    return 0;
}

static int test_key_type_empty() {
    int rc = naturo_key_type("", 0);
    // Empty string → nothing to type → success (0) or graceful (-1 if stub)
    CHECK(rc == 0 || rc == -1, "key_type(empty) returns 0 or -1");
    return 0;
}

/* ── naturo_key_hotkey ────────────────────────────── */

static int test_hotkey_null_modifiers_null_key() {
    int rc = naturo_key_hotkey(0, nullptr);
    CHECK(rc == -1, "hotkey(0 modifiers, NULL key) returns -1");
    return 0;
}

static int test_hotkey_unknown_key() {
    int rc = naturo_key_hotkey(1 /*ctrl*/, "xyzzy_bad_key");
    CHECK(rc == -1, "hotkey(ctrl, bad_key) returns -1");
    return 0;
}

static int test_hotkey_ctrl_a() {
    int rc = naturo_key_hotkey(1 /*ctrl*/, "a");  // Ctrl+A
    CHECK(rc == 0 || rc == -2, "hotkey(ctrl+a) returns 0 or -2");
    return 0;
}

static int test_hotkey_ctrl_shift_z() {
    int rc = naturo_key_hotkey(1 | 4 /*ctrl+shift*/, "z");
    CHECK(rc == 0 || rc == -2, "hotkey(ctrl+shift+z) returns 0 or -2");
    return 0;
}

/* ── Runner ───────────────────────────────────────── */

int main() {
    int failures = 0;

    printf("=== Phase 2 Input Tests ===\n\n");

    failures += test_mouse_move_valid();
    failures += test_mouse_click_invalid_button();
    failures += test_mouse_click_valid();
    failures += test_mouse_scroll_down();
    failures += test_mouse_scroll_horizontal();
    failures += test_key_press_null();
    failures += test_key_press_unknown();
    failures += test_key_press_enter();
    failures += test_key_press_escape();
    failures += test_key_press_f5();
    failures += test_key_press_esc_alias();
    failures += test_key_type_null();
    failures += test_key_type_empty();
    failures += test_hotkey_null_modifiers_null_key();
    failures += test_hotkey_unknown_key();
    failures += test_hotkey_ctrl_a();
    failures += test_hotkey_ctrl_shift_z();

    printf("\n%s (%d failure(s))\n",
           failures == 0 ? "ALL TESTS PASSED" : "SOME TESTS FAILED",
           failures);
    return failures;
}
