/**
 * @file test_element.cpp
 * @brief Tests for UI element tree inspection functions.
 */

#include "naturo/exports.h"
#include <cstdio>
#include <cstring>

int main() {
    int failed = 0;

    naturo_init();

    // Test 1: Get element tree of desktop (hwnd=0 uses foreground window).
    // In CI there may be no foreground window, so -2 is acceptable.
    {
        char buf[65536];
        int count = naturo_get_element_tree(0, 2, buf, sizeof(buf));
        if (count > 0) {
            printf("PASS: naturo_get_element_tree returned %d elements\n", count);
            // Verify JSON starts with '{'
            if (buf[0] != '{') {
                printf("FAIL: element tree JSON does not start with '{': %.20s\n", buf);
                failed++;
            } else {
                printf("PASS: naturo_get_element_tree returned valid JSON\n");
            }
        } else if (count == -2) {
            printf("PASS: naturo_get_element_tree returned -2 (no foreground window in CI)\n");
        } else {
            printf("FAIL: naturo_get_element_tree returned unexpected %d\n", count);
            failed++;
        }
    }

    // Test 2: NULL buffer should return -1
    {
        int rc = naturo_get_element_tree(0, 2, NULL, 100);
        if (rc != -1) {
            printf("FAIL: naturo_get_element_tree(NULL buffer) returned %d, expected -1\n", rc);
            failed++;
        } else {
            printf("PASS: naturo_get_element_tree rejects NULL buffer\n");
        }
    }

    // Test 3: find_element with NULL buffer should return -1
    {
        int rc = naturo_find_element(0, "Button", NULL, NULL, 100);
        if (rc != -1) {
            printf("FAIL: naturo_find_element(NULL buffer) returned %d, expected -1\n", rc);
            failed++;
        } else {
            printf("PASS: naturo_find_element rejects NULL buffer\n");
        }
    }

    // Test 4: find_element with both role and name NULL should return -1
    {
        char buf[1024];
        int rc = naturo_find_element(0, NULL, NULL, buf, sizeof(buf));
        if (rc != -1) {
            printf("FAIL: naturo_find_element(NULL role, NULL name) returned %d, expected -1\n", rc);
            failed++;
        } else {
            printf("PASS: naturo_find_element rejects NULL role + NULL name\n");
        }
    }

    // Test 5: find_element for a non-existent element name
    {
        char buf[4096];
        int rc = naturo_find_element(0, NULL, "NonExistentElement12345", buf, sizeof(buf));
        // Should return 1 (not found) or -2 (no foreground window)
        if (rc == 1 || rc == -2) {
            printf("PASS: naturo_find_element correctly reports not found / no window (rc=%d)\n", rc);
        } else if (rc == 0) {
            // Extremely unlikely but technically possible
            printf("PASS: naturo_find_element found something (unexpected but not wrong)\n");
        } else {
            printf("FAIL: naturo_find_element returned unexpected %d\n", rc);
            failed++;
        }
    }

    naturo_shutdown();

    printf("\n%s: %d tests failed\n", failed ? "FAILED" : "ALL PASSED", failed);
    return failed;
}
