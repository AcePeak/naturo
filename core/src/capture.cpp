/**
 * @file capture.cpp
 * @brief Screen and window capture using GDI (BitBlt / PrintWindow).
 *
 * Saves screenshots as BMP files. The Python layer can convert to PNG
 * with Pillow if needed.
 */

#ifdef _WIN32

#include "naturo/exports.h"
#include <windows.h>
#include <cstdio>
#include <cstring>
#include <new>

/**
 * @brief Write pixel data to a BMP file.
 * @param path Output file path.
 * @param pixels Pointer to raw pixel data (BGR, bottom-up).
 * @param width Image width in pixels.
 * @param height Image height in pixels.
 * @return 0 on success, -3 on file error.
 */
static int write_bmp(const char* path, const void* pixels, int width, int height) {
    int row_size = ((width * 3 + 3) & ~3);  // Each row padded to 4-byte boundary
    int data_size = row_size * height;

    BITMAPFILEHEADER file_header = {};
    file_header.bfType = 0x4D42;  // "BM"
    file_header.bfSize = sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER) + data_size;
    file_header.bfOffBits = sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER);

    BITMAPINFOHEADER info_header = {};
    info_header.biSize = sizeof(BITMAPINFOHEADER);
    info_header.biWidth = width;
    info_header.biHeight = height;  // Positive = bottom-up
    info_header.biPlanes = 1;
    info_header.biBitCount = 24;
    info_header.biCompression = BI_RGB;
    info_header.biSizeImage = data_size;

    FILE* f = fopen(path, "wb");
    if (!f) return -3;

    fwrite(&file_header, sizeof(file_header), 1, f);
    fwrite(&info_header, sizeof(info_header), 1, f);
    fwrite(pixels, 1, data_size, f);
    fclose(f);
    return 0;
}

extern "C" {

NATURO_API int naturo_capture_screen(int screen_index, const char* output_path) {
    if (!output_path) return -1;
    if (screen_index < 0) return -1;

    // Get the screen DC. For screen_index 0, use the primary display.
    // Multi-monitor support: enumerate monitors for index > 0.
    HDC hdc_screen = GetDC(NULL);
    if (!hdc_screen) return -2;

    int width = GetSystemMetrics(SM_CXSCREEN);
    int height = GetSystemMetrics(SM_CYSCREEN);
    int x_offset = 0;
    int y_offset = 0;

    // For multi-monitor: use virtual screen if index > 0
    if (screen_index > 0) {
        // Use virtual screen dimensions (all monitors combined)
        // For a more precise per-monitor capture, EnumDisplayMonitors would be needed.
        width = GetSystemMetrics(SM_CXVIRTUALSCREEN);
        height = GetSystemMetrics(SM_CYVIRTUALSCREEN);
        x_offset = GetSystemMetrics(SM_XVIRTUALSCREEN);
        y_offset = GetSystemMetrics(SM_YVIRTUALSCREEN);
    }

    HDC hdc_mem = CreateCompatibleDC(hdc_screen);
    if (!hdc_mem) {
        ReleaseDC(NULL, hdc_screen);
        return -2;
    }

    HBITMAP hbm = CreateCompatibleBitmap(hdc_screen, width, height);
    if (!hbm) {
        DeleteDC(hdc_mem);
        ReleaseDC(NULL, hdc_screen);
        return -2;
    }

    HGDIOBJ old_bm = SelectObject(hdc_mem, hbm);
    BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, x_offset, y_offset, SRCCOPY);
    SelectObject(hdc_mem, old_bm);

    // Extract pixel data
    BITMAPINFO bmi = {};
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = width;
    bmi.bmiHeader.biHeight = height;
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 24;
    bmi.bmiHeader.biCompression = BI_RGB;

    int row_size = ((width * 3 + 3) & ~3);
    int data_size = row_size * height;
    unsigned char* pixels = new (std::nothrow) unsigned char[data_size];
    if (!pixels) {
        DeleteObject(hbm);
        DeleteDC(hdc_mem);
        ReleaseDC(NULL, hdc_screen);
        return -2;
    }

    GetDIBits(hdc_mem, hbm, 0, height, pixels, &bmi, DIB_RGB_COLORS);

    int rc = write_bmp(output_path, pixels, width, height);

    delete[] pixels;
    DeleteObject(hbm);
    DeleteDC(hdc_mem);
    ReleaseDC(NULL, hdc_screen);
    return rc;
}

NATURO_API int naturo_capture_window(uintptr_t hwnd, const char* output_path) {
    if (!output_path) return -1;

    HWND target = (HWND)hwnd;
    if (!target) {
        target = GetForegroundWindow();
        if (!target) return -2;
    }

    if (!IsWindow(target)) return -1;

    RECT rect;
    if (!GetWindowRect(target, &rect)) return -2;

    int width = rect.right - rect.left;
    int height = rect.bottom - rect.top;
    if (width <= 0 || height <= 0) return -2;

    HDC hdc_screen = GetDC(NULL);
    if (!hdc_screen) return -2;

    HDC hdc_mem = CreateCompatibleDC(hdc_screen);
    if (!hdc_mem) {
        ReleaseDC(NULL, hdc_screen);
        return -2;
    }

    HBITMAP hbm = CreateCompatibleBitmap(hdc_screen, width, height);
    if (!hbm) {
        DeleteDC(hdc_mem);
        ReleaseDC(NULL, hdc_screen);
        return -2;
    }

    HGDIOBJ old_bm = SelectObject(hdc_mem, hbm);

    // PrintWindow captures the window content even if partially occluded.
    // PW_RENDERFULLCONTENT (0x2) for better rendering on newer Windows.
    if (!PrintWindow(target, hdc_mem, 0x2)) {
        // Fallback: try without PW_RENDERFULLCONTENT
        if (!PrintWindow(target, hdc_mem, 0)) {
            SelectObject(hdc_mem, old_bm);
            DeleteObject(hbm);
            DeleteDC(hdc_mem);
            ReleaseDC(NULL, hdc_screen);
            return -2;
        }
    }

    SelectObject(hdc_mem, old_bm);

    // Extract pixel data
    BITMAPINFO bmi = {};
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = width;
    bmi.bmiHeader.biHeight = height;
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 24;
    bmi.bmiHeader.biCompression = BI_RGB;

    int row_size = ((width * 3 + 3) & ~3);
    int data_size = row_size * height;
    unsigned char* pixels = new (std::nothrow) unsigned char[data_size];
    if (!pixels) {
        DeleteObject(hbm);
        DeleteDC(hdc_mem);
        ReleaseDC(NULL, hdc_screen);
        return -2;
    }

    GetDIBits(hdc_mem, hbm, 0, height, pixels, &bmi, DIB_RGB_COLORS);

    int rc = write_bmp(output_path, pixels, width, height);

    delete[] pixels;
    DeleteObject(hbm);
    DeleteDC(hdc_mem);
    ReleaseDC(NULL, hdc_screen);
    return rc;
}

} // extern "C"

#else
// Non-Windows stub implementations

#include "naturo/exports.h"

extern "C" {

NATURO_API int naturo_capture_screen(int screen_index, const char* output_path) {
    (void)screen_index;
    (void)output_path;
    return -2;  // Not supported on this platform
}

NATURO_API int naturo_capture_window(uintptr_t hwnd, const char* output_path) {
    (void)hwnd;
    (void)output_path;
    return -2;  // Not supported on this platform
}

} // extern "C"

#endif // _WIN32
