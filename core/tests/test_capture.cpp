/**
 * @file test_capture.cpp
 * @brief Tests for screen and window capture functions.
 */

#include "naturo/exports.h"
#include <cstdio>
#include <cstring>
#include <sys/stat.h>

/**
 * @brief Check if a file exists and has non-zero size.
 */
static bool file_exists_with_size(const char* path) {
    struct stat st;
    if (stat(path, &st) != 0) return false;
    return st.st_size > 0;
}

int main() {
    int failed = 0;

    naturo_init();

    // Test 1: Capture screen to BMP
    {
        const char* path = "test_screen_capture.bmp";
        remove(path);
        int rc = naturo_capture_screen(0, path);
        if (rc != 0) {
            printf("FAIL: naturo_capture_screen returned %d\n", rc);
            failed++;
        } else if (!file_exists_with_size(path)) {
            printf("FAIL: naturo_capture_screen output file missing or empty\n");
            failed++;
        } else {
            printf("PASS: naturo_capture_screen created BMP file\n");
        }
        remove(path);
    }

    // Test 2: Null output_path should return -1
    {
        int rc = naturo_capture_screen(0, NULL);
        if (rc != -1) {
            printf("FAIL: naturo_capture_screen(0, NULL) returned %d, expected -1\n", rc);
            failed++;
        } else {
            printf("PASS: naturo_capture_screen rejects NULL path\n");
        }
    }

    // Test 3: Negative screen index should return -1
    {
        int rc = naturo_capture_screen(-1, "test.bmp");
        if (rc != -1) {
            printf("FAIL: naturo_capture_screen(-1, ...) returned %d, expected -1\n", rc);
            failed++;
        } else {
            printf("PASS: naturo_capture_screen rejects negative index\n");
        }
    }

    // Test 4: Capture window with hwnd=0 (foreground window)
    // Note: May fail in headless CI if no foreground window exists.
    {
        const char* path = "test_window_capture.bmp";
        remove(path);
        int rc = naturo_capture_window(0, path);
        // In CI, there might not be a foreground window, so accept both 0 and -2
        if (rc == 0) {
            if (file_exists_with_size(path)) {
                printf("PASS: naturo_capture_window(0) captured foreground window\n");
            } else {
                printf("FAIL: naturo_capture_window returned 0 but file is missing\n");
                failed++;
            }
        } else if (rc == -2) {
            printf("PASS: naturo_capture_window(0) returned -2 (no foreground window in CI)\n");
        } else {
            printf("FAIL: naturo_capture_window(0) returned unexpected %d\n", rc);
            failed++;
        }
        remove(path);
    }

    // Test 5: Capture window with NULL path
    {
        int rc = naturo_capture_window(0, NULL);
        if (rc != -1) {
            printf("FAIL: naturo_capture_window(0, NULL) returned %d, expected -1\n", rc);
            failed++;
        } else {
            printf("PASS: naturo_capture_window rejects NULL path\n");
        }
    }

    naturo_shutdown();

    printf("\n%s: %d tests failed\n", failed ? "FAILED" : "ALL PASSED", failed);
    return failed;
}
