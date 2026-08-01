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

// ── Windows.Graphics.Capture (WGC) — GPU/DirectComposition surface capture ──
// PrintWindow and screen BitBlt both return a blank frame for windows whose
// content is composited via a DXGI swap-chain / hardware overlay (Chromium/CEF
// message panes, DirectComposition, some Electron/Qt surfaces). WGC captures the
// window through the DWM's real composition path, so it sees that content. Used
// only as the last-resort fallback when the GDI paths come back blank.
#include <d3d11.h>
#include <dxgi.h>
#include <inspectable.h>
#include <roapi.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Graphics.h>
#include <winrt/Windows.Graphics.Capture.h>
#include <winrt/Windows.Graphics.DirectX.h>
#include <winrt/Windows.Graphics.DirectX.Direct3D11.h>
#include <windows.graphics.capture.interop.h>
#include <windows.graphics.directx.direct3d11.interop.h>

/**
 * @brief Convert a UTF-8 string to a wide (UTF-16) string.
 * @param utf8 Null-terminated UTF-8 string.
 * @param wbuf Output buffer for wide characters.
 * @param wbuf_len Size of wbuf in wchar_t units.
 * @return Number of wide characters written (excluding null), or 0 on error.
 */
static int utf8_to_wide(const char* utf8, wchar_t* wbuf, int wbuf_len) {
    if (!utf8 || !wbuf || wbuf_len <= 0) return 0;
    int result = MultiByteToWideChar(CP_UTF8, 0, utf8, -1, wbuf, wbuf_len);
    return result > 0 ? result - 1 : 0;  // Exclude null terminator from count
}

/**
 * @brief Write pixel data to a BMP file.
 * @param path Output file path (UTF-8 encoded).
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

    // (#693) Use _wfopen with UTF-16 path to support Unicode file paths
    // (Chinese characters, etc.). The path arrives as UTF-8 from Python.
    wchar_t wpath[MAX_PATH];
    if (utf8_to_wide(path, wpath, MAX_PATH) == 0) return -3;

    FILE* f = _wfopen(wpath, L"wb");
    if (!f) return -3;

    fwrite(&file_header, sizeof(file_header), 1, f);
    fwrite(&info_header, sizeof(info_header), 1, f);
    fwrite(pixels, 1, data_size, f);
    fclose(f);
    return 0;
}

// ── WGC capture implementation ──────────────────────────────────────────────

namespace {

namespace wgc = winrt::Windows::Graphics::Capture;
namespace wgd = winrt::Windows::Graphics::DirectX;
namespace wgd3d = winrt::Windows::Graphics::DirectX::Direct3D11;

// Pull the underlying ID3D11Texture2D out of a WinRT IDirect3DSurface.
static winrt::com_ptr<ID3D11Texture2D> texture_from_surface(
        wgd3d::IDirect3DSurface const& surface) {
    auto access = surface.as<::Windows::Graphics::DirectX::Direct3D11::IDirect3DDxgiInterfaceAccess>();
    winrt::com_ptr<ID3D11Texture2D> tex;
    winrt::check_hresult(access->GetInterface(winrt::guid_of<ID3D11Texture2D>(), tex.put_void()));
    return tex;
}

// Capture *target* via WGC into a BMP at *output_path*. Returns 0 on success,
// -5 if WGC is unsupported on this OS, -4 on frame timeout, -2 on other failure.
static int capture_window_wgc_impl(HWND target, const char* output_path) {
    if (!wgc::GraphicsCaptureSession::IsSupported()) return -5;

    // D3D11 device (hardware, then WARP fallback). BGRA needed for WGC.
    winrt::com_ptr<ID3D11Device> d3dDevice;
    winrt::com_ptr<ID3D11DeviceContext> d3dContext;
    UINT flags = D3D11_CREATE_DEVICE_BGRA_SUPPORT;
    HRESULT hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, flags,
                                   nullptr, 0, D3D11_SDK_VERSION,
                                   d3dDevice.put(), nullptr, d3dContext.put());
    if (FAILED(hr)) {
        hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, flags,
                               nullptr, 0, D3D11_SDK_VERSION,
                               d3dDevice.put(), nullptr, d3dContext.put());
        if (FAILED(hr)) return -2;
    }
    auto dxgiDevice = d3dDevice.as<IDXGIDevice>();
    winrt::com_ptr<::IInspectable> inspectable;
    winrt::check_hresult(CreateDirect3D11DeviceFromDXGIDevice(dxgiDevice.get(), inspectable.put()));
    auto device = inspectable.as<wgd3d::IDirect3DDevice>();

    // GraphicsCaptureItem for the target window.
    auto interop = winrt::get_activation_factory<wgc::GraphicsCaptureItem,
                                                 ::IGraphicsCaptureItemInterop>();
    wgc::GraphicsCaptureItem item{ nullptr };
    hr = interop->CreateForWindow(target, winrt::guid_of<wgc::GraphicsCaptureItem>(),
                                  winrt::put_abi(item));
    if (FAILED(hr) || !item) return -2;
    auto size = item.Size();
    if (size.Width <= 0 || size.Height <= 0) return -2;

    // Free-threaded pool: no DispatcherQueue needed, poll for the frame.
    auto framePool = wgc::Direct3D11CaptureFramePool::CreateFreeThreaded(
        device, wgd::DirectXPixelFormat::B8G8R8A8UIntNormalized, 2, size);
    auto session = framePool.CreateCaptureSession(item);
    try { session.IsBorderRequired(false); } catch (...) {}  // hide yellow border (Win11)
    session.StartCapture();

    wgc::Direct3D11CaptureFrame frame{ nullptr };
    for (int i = 0; i < 60 && !frame; ++i) {   // ~1.2s max wait for first frame
        frame = framePool.TryGetNextFrame();
        if (!frame) Sleep(20);
    }
    if (!frame) { session.Close(); framePool.Close(); return -4; }

    auto surfaceTex = texture_from_surface(frame.Surface());
    D3D11_TEXTURE2D_DESC desc{};
    surfaceTex->GetDesc(&desc);

    D3D11_TEXTURE2D_DESC sdesc = desc;
    sdesc.Usage = D3D11_USAGE_STAGING;
    sdesc.BindFlags = 0;
    sdesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    sdesc.MiscFlags = 0;
    winrt::com_ptr<ID3D11Texture2D> staging;
    if (FAILED(d3dDevice->CreateTexture2D(&sdesc, nullptr, staging.put()))) {
        frame.Close(); session.Close(); framePool.Close(); return -2;
    }
    d3dContext->CopyResource(staging.get(), surfaceTex.get());

    D3D11_MAPPED_SUBRESOURCE mapped{};
    if (FAILED(d3dContext->Map(staging.get(), 0, D3D11_MAP_READ, 0, &mapped))) {
        frame.Close(); session.Close(); framePool.Close(); return -2;
    }

    int width = (int)desc.Width;
    int height = (int)desc.Height;
    int row_size = ((width * 3 + 3) & ~3);
    int data_size = row_size * height;
    unsigned char* pixels = new (std::nothrow) unsigned char[data_size];
    int rc = -2;
    if (pixels) {
        // WGC gives top-down BGRA; BMP wants bottom-up BGR.
        const unsigned char* src = (const unsigned char*)mapped.pData;
        for (int y = 0; y < height; ++y) {
            const unsigned char* srow = src + (size_t)y * mapped.RowPitch;
            unsigned char* drow = pixels + (size_t)(height - 1 - y) * row_size;
            for (int x = 0; x < width; ++x) {
                drow[x * 3 + 0] = srow[x * 4 + 0];  // B
                drow[x * 3 + 1] = srow[x * 4 + 1];  // G
                drow[x * 3 + 2] = srow[x * 4 + 2];  // R
            }
        }
        rc = write_bmp(output_path, pixels, width, height);
        delete[] pixels;
    }
    d3dContext->Unmap(staging.get(), 0);
    frame.Close(); session.Close(); framePool.Close();
    return rc;
}

}  // namespace

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

NATURO_API int naturo_capture_window_wgc(uintptr_t hwnd, const char* output_path) {
    if (!output_path) return -1;
    HWND target = (HWND)hwnd;
    if (!target) target = GetForegroundWindow();
    if (!target || !IsWindow(target)) return -1;

    // WGC needs a WinRT apartment on the calling thread. Init MTA; tolerate the
    // thread already being STA (RPC_E_CHANGED_MODE) — the free-threaded frame
    // pool works from either. Only uninitialize what we initialized.
    HRESULT hrInit = RoInitialize(RO_INIT_MULTITHREADED);
    bool didInit = SUCCEEDED(hrInit);
    if (FAILED(hrInit) && hrInit != RPC_E_CHANGED_MODE) return -2;

    int rc;
    try {
        rc = capture_window_wgc_impl(target, output_path);
    } catch (...) {
        rc = -2;
    }
    if (didInit) RoUninitialize();
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

NATURO_API int naturo_capture_window_wgc(uintptr_t hwnd, const char* output_path) {
    (void)hwnd;
    (void)output_path;
    return -2;  // Not supported on this platform
}

} // extern "C"

#endif // _WIN32
