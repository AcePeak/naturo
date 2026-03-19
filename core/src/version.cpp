/**
 * @file version.cpp
 * @brief Library version, initialization, and shutdown.
 */

#include "naturo/exports.h"

#ifdef _WIN32
#include <windows.h>
#endif

static const char* NATURO_VERSION = "0.1.0";
static bool g_initialized = false;

extern "C" {

NATURO_API const char* naturo_version(void) {
    return NATURO_VERSION;
}

NATURO_API int naturo_init(void) {
    if (g_initialized) return 0;

#ifdef _WIN32
    // Initialize COM for UIAutomation (multithreaded apartment).
    HRESULT hr = CoInitializeEx(NULL, COINIT_MULTITHREADED);
    if (FAILED(hr) && hr != RPC_E_CHANGED_MODE) {
        // RPC_E_CHANGED_MODE means COM is already initialized with a
        // different threading model — that is acceptable.
        return -2;
    }
#endif

    g_initialized = true;
    return 0;
}

NATURO_API int naturo_shutdown(void) {
    if (!g_initialized) return 0;

#ifdef _WIN32
    CoUninitialize();
#endif

    g_initialized = false;
    return 0;
}

} // extern "C"
