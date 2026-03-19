/**
 * @file test_window.cpp
 * @brief Tests for window listing and info functions.
 */

#include "naturo/exports.h"
#include <cstdio>
#include <cstring>

int main() {
    int failed = 0;

    naturo_init();

    // Test 1: List windows — should return at least one on a desktop session
    {
        char buf[65536];
        int count = naturo_list_windows(buf, sizeof(buf));
        if (count < 0) {
            printf("FAIL: naturo_list_windows returned error %d\n", count);
            failed++;
        } else {
            printf("PASS: naturo_list_windows found %d windows\n", count);
            // Verify JSON starts with '['
            if (buf[0] != '[') {
                printf("FAIL: JSON does not start with '[': %.20s\n", buf);
                failed++;
            } else {
                printf("PASS: naturo_list_windows returned valid JSON array\n");
            }
        }
    }

    // Test 2: List windows with NULL buffer should return -1
    {
        int rc = naturo_list_windows(NULL, 100);
        if (rc != -1) {
            printf("FAIL: naturo_list_windows(NULL, 100) returned %d, expected -1\n", rc);
            failed++;
        } else {
            printf("PASS: naturo_list_windows rejects NULL buffer\n");
        }
    }

    // Test 3: List windows with tiny buffer should return -4
    {
        char buf[4] = {};
        int rc = naturo_list_windows(buf, sizeof(buf));
        if (rc != -4) {
            // If there are very few windows, the JSON might fit in 4 bytes
            // (unlikely, but possible: "[]" = 2 chars + null = 3)
            if (rc >= 0) {
                printf("PASS: naturo_list_windows fit in tiny buffer (unlikely but valid)\n");
            } else {
                printf("FAIL: naturo_list_windows with tiny buffer returned %d, expected -4\n", rc);
                failed++;
            }
        } else {
            printf("PASS: naturo_list_windows returns -4 on small buffer\n");
        }
    }

    // Test 4: Get window info with invalid HWND
    {
        char buf[1024];
        int rc = naturo_get_window_info(0xDEADBEEF, buf, sizeof(buf));
        if (rc != -1) {
            printf("FAIL: naturo_get_window_info(invalid) returned %d, expected -1\n", rc);
            failed++;
        } else {
            printf("PASS: naturo_get_window_info rejects invalid HWND\n");
        }
    }

    naturo_shutdown();

    printf("\n%s: %d tests failed\n", failed ? "FAILED" : "ALL PASSED", failed);
    return failed;
}
