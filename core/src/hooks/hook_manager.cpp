/**
 * @file hook_manager.cpp
 * @brief HookManager implementation, curated detours, and the C ABI exports.
 */

#include "hook_manager.h"

#include "naturo/exports.h"

#include <cctype>
#include <cstdio>
#include <cstring>
#include <sstream>
#include <string>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#include <MinHook.h>
#endif

namespace naturo {
namespace hooks {

namespace {

// ── String helpers ─────────────────────────────────────────────────────────

std::string to_lower(std::string s) {
    for (char& c : s) {
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }
    return s;
}

std::string normalize_module(const std::string& module) {
    std::string s = to_lower(module);
    if (s.size() < 4 || s.compare(s.size() - 4, 4, ".dll") != 0) {
        s += ".dll";
    }
    return s;
}

/// Escape a UTF-8 string for embedding in a JSON string literal.
std::string json_escape(const std::string& in) {
    std::string out;
    out.reserve(in.size() + 8);
    for (unsigned char c : in) {
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (c < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof(buf), "\\u%04x", c);
                    out += buf;
                } else {
                    out += static_cast<char>(c);
                }
        }
    }
    return out;
}

const char* action_name(HookAction a) {
    return a == HookAction::Block ? "block" : "log";
}

#ifdef _WIN32
std::string wide_to_utf8(const wchar_t* w) {
    if (w == nullptr) {
        return std::string();
    }
    int needed = WideCharToMultiByte(CP_UTF8, 0, w, -1, nullptr, 0, nullptr, nullptr);
    if (needed <= 1) {
        return std::string();
    }
    std::vector<char> buf(static_cast<size_t>(needed));
    WideCharToMultiByte(CP_UTF8, 0, w, -1, buf.data(), needed, nullptr, nullptr);
    return std::string(buf.data());  // drops the trailing NUL
}

std::string hex_dword(unsigned long value) {
    char buf[16];
    std::snprintf(buf, sizeof(buf), "0x%lx", value);
    return std::string(buf);
}
#endif  // _WIN32

}  // namespace

// ── Curated supported-API table + detours (Windows only) ───────────────────

#ifdef _WIN32

// Trampolines (original function pointers), populated by MH_CreateHook.
typedef int(WINAPI* MessageBoxW_t)(HWND, LPCWSTR, LPCWSTR, UINT);
typedef int(WINAPI* MessageBoxA_t)(HWND, LPCSTR, LPCSTR, UINT);
typedef HANDLE(WINAPI* CreateFileW_t)(LPCWSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES,
                                      DWORD, DWORD, HANDLE);
typedef HANDLE(WINAPI* CreateFileA_t)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES,
                                      DWORD, DWORD, HANDLE);

static MessageBoxW_t g_orig_MessageBoxW = nullptr;
static MessageBoxA_t g_orig_MessageBoxA = nullptr;
static CreateFileW_t g_orig_CreateFileW = nullptr;
static CreateFileA_t g_orig_CreateFileA = nullptr;

static int WINAPI Detour_MessageBoxW(HWND hWnd, LPCWSTR lpText, LPCWSTR lpCaption,
                                     UINT uType) {
    std::string detail = "caption=\"" + wide_to_utf8(lpCaption) +
                         "\" text=\"" + wide_to_utf8(lpText) + "\"";
    HookAction action =
        HookManager::instance().record_and_action("user32.dll", "MessageBoxW", detail);
    if (action == HookAction::Block) {
        return 0;  // Sentinel: dialog suppressed (not a valid button id).
    }
    return g_orig_MessageBoxW(hWnd, lpText, lpCaption, uType);
}

static int WINAPI Detour_MessageBoxA(HWND hWnd, LPCSTR lpText, LPCSTR lpCaption,
                                     UINT uType) {
    std::string detail = std::string("caption=\"") + (lpCaption ? lpCaption : "") +
                         "\" text=\"" + (lpText ? lpText : "") + "\"";
    HookAction action =
        HookManager::instance().record_and_action("user32.dll", "MessageBoxA", detail);
    if (action == HookAction::Block) {
        return 0;  // Sentinel: dialog suppressed.
    }
    return g_orig_MessageBoxA(hWnd, lpText, lpCaption, uType);
}

static HANDLE WINAPI Detour_CreateFileW(LPCWSTR lpFileName, DWORD dwDesiredAccess,
                                        DWORD dwShareMode,
                                        LPSECURITY_ATTRIBUTES lpSecurityAttributes,
                                        DWORD dwCreationDisposition,
                                        DWORD dwFlagsAndAttributes,
                                        HANDLE hTemplateFile) {
    std::string detail = "path=\"" + wide_to_utf8(lpFileName) +
                         "\" access=" + hex_dword(dwDesiredAccess);
    HookAction action =
        HookManager::instance().record_and_action("kernel32.dll", "CreateFileW", detail);
    if (action == HookAction::Block) {
        SetLastError(ERROR_ACCESS_DENIED);
        return INVALID_HANDLE_VALUE;  // Sentinel: open denied.
    }
    return g_orig_CreateFileW(lpFileName, dwDesiredAccess, dwShareMode,
                              lpSecurityAttributes, dwCreationDisposition,
                              dwFlagsAndAttributes, hTemplateFile);
}

static HANDLE WINAPI Detour_CreateFileA(LPCSTR lpFileName, DWORD dwDesiredAccess,
                                        DWORD dwShareMode,
                                        LPSECURITY_ATTRIBUTES lpSecurityAttributes,
                                        DWORD dwCreationDisposition,
                                        DWORD dwFlagsAndAttributes,
                                        HANDLE hTemplateFile) {
    std::string detail = std::string("path=\"") + (lpFileName ? lpFileName : "") +
                         "\" access=" + hex_dword(dwDesiredAccess);
    HookAction action =
        HookManager::instance().record_and_action("kernel32.dll", "CreateFileA", detail);
    if (action == HookAction::Block) {
        SetLastError(ERROR_ACCESS_DENIED);
        return INVALID_HANDLE_VALUE;  // Sentinel: open denied.
    }
    return g_orig_CreateFileA(lpFileName, dwDesiredAccess, dwShareMode,
                              lpSecurityAttributes, dwCreationDisposition,
                              dwFlagsAndAttributes, hTemplateFile);
}

struct SupportedApi {
    const char* module;    ///< Canonical module name, e.g. "user32.dll".
    const char* function;  ///< Canonical function name, e.g. "MessageBoxW".
    void* detour;          ///< Replacement function.
    void** original;       ///< &g_orig_* — receives the trampoline.
};

static const SupportedApi kSupportedApis[] = {
    {"user32.dll", "MessageBoxW", reinterpret_cast<void*>(&Detour_MessageBoxW),
     reinterpret_cast<void**>(&g_orig_MessageBoxW)},
    {"user32.dll", "MessageBoxA", reinterpret_cast<void*>(&Detour_MessageBoxA),
     reinterpret_cast<void**>(&g_orig_MessageBoxA)},
    {"kernel32.dll", "CreateFileW", reinterpret_cast<void*>(&Detour_CreateFileW),
     reinterpret_cast<void**>(&g_orig_CreateFileW)},
    {"kernel32.dll", "CreateFileA", reinterpret_cast<void*>(&Detour_CreateFileA),
     reinterpret_cast<void**>(&g_orig_CreateFileA)},
};

static const SupportedApi* find_supported_api(const std::string& module,
                                              const std::string& function) {
    std::string want_module = normalize_module(module);
    std::string want_function = to_lower(function);
    for (const SupportedApi& api : kSupportedApis) {
        if (normalize_module(api.module) == want_module &&
            to_lower(api.function) == want_function) {
            return &api;
        }
    }
    return nullptr;
}

#endif  // _WIN32

// ── HookManager ────────────────────────────────────────────────────────────

HookManager::HookManager() : log_capacity_(1000), seq_(0) {}

HookManager& HookManager::instance() {
    static HookManager mgr;
    return mgr;
}

std::string HookManager::make_key(const std::string& module,
                                  const std::string& function) {
    return normalize_module(module) + "!" + to_lower(function);
}

int HookManager::install(const std::string& module, const std::string& function,
                         HookAction action) {
#ifdef _WIN32
    const SupportedApi* api = find_supported_api(module, function);
    if (api == nullptr) {
        return -1;  // Unknown / unsupported API.
    }
    if (!MinHookLibrary::instance().ok()) {
        return -2;  // MinHook failed to initialize.
    }

    std::string key = make_key(api->module, api->function);

    std::lock_guard<std::mutex> lock(mutex_);
    auto it = entries_.find(key);
    if (it != entries_.end()) {
        it->second.action = action;  // Re-arm with a (possibly) new action.
        return 0;
    }

    HMODULE hmod = GetModuleHandleA(api->module);
    if (hmod == nullptr) {
        hmod = LoadLibraryA(api->module);
    }
    if (hmod == nullptr) {
        return -2;
    }
    void* target = reinterpret_cast<void*>(GetProcAddress(hmod, api->function));
    if (target == nullptr) {
        return -2;
    }

    auto hook = std::unique_ptr<ScopedHook>(new ScopedHook());
    if (hook->create(target, api->detour, api->original) != HookStatus::Ok) {
        return -2;
    }

    Entry entry;
    entry.module = api->module;
    entry.function = api->function;
    entry.action = action;
    entry.call_count = 0;
    entry.hook = std::move(hook);
    entries_.emplace(key, std::move(entry));
    return 0;
#else
    (void)module;
    (void)function;
    (void)action;
    return -2;  // Hooking is only available on Windows.
#endif
}

int HookManager::remove(const std::string& module, const std::string& function) {
    std::string key = make_key(module, function);
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = entries_.find(key);
    if (it == entries_.end()) {
        return 1;  // Not installed.
    }
    entries_.erase(it);  // unique_ptr<ScopedHook> dtor disables + removes the hook.
    return 0;
}

void HookManager::clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    entries_.clear();  // Destroys every ScopedHook (disable + remove).
    log_.clear();
}

int HookManager::count() {
    std::lock_guard<std::mutex> lock(mutex_);
    return static_cast<int>(entries_.size());
}

HookAction HookManager::record_and_action(const char* module, const char* function,
                                          const std::string& detail) {
    // A detour runs on arbitrary threads and may fire while another thread holds
    // the lock (e.g. mid-install). Use try_lock so a detour never blocks or
    // deadlocks on the manager: if the lock is contended we simply forward the
    // call (Log) without recording it, which is always safe.
    std::unique_lock<std::mutex> lock(mutex_, std::try_to_lock);
    if (!lock.owns_lock()) {
        return HookAction::Log;
    }

    std::string key = make_key(module, function);
    auto it = entries_.find(key);
    if (it == entries_.end()) {
        return HookAction::Log;  // Hook removed between dispatch and here.
    }
    Entry& entry = it->second;
    entry.call_count += 1;

    LogRecord rec;
    rec.seq = ++seq_;
    rec.module = entry.module;
    rec.function = entry.function;
    rec.action = entry.action;
    rec.detail = detail;
    log_.push_back(std::move(rec));
    while (log_.size() > log_capacity_) {
        log_.pop_front();  // Bounded ring buffer: drop oldest.
    }
    return entry.action;
}

std::string HookManager::list_json() {
    std::lock_guard<std::mutex> lock(mutex_);
    std::ostringstream os;
    os << "[";
    bool first = true;
    for (const auto& kv : entries_) {
        const Entry& e = kv.second;
        if (!first) {
            os << ",";
        }
        first = false;
        os << "{\"module\":\"" << json_escape(e.module) << "\",\"function\":\""
           << json_escape(e.function) << "\",\"action\":\"" << action_name(e.action)
           << "\",\"call_count\":" << e.call_count << "}";
    }
    os << "]";
    return os.str();
}

std::string HookManager::drain_log_json() {
    std::lock_guard<std::mutex> lock(mutex_);
    std::ostringstream os;
    os << "[";
    bool first = true;
    for (const LogRecord& r : log_) {
        if (!first) {
            os << ",";
        }
        first = false;
        os << "{\"seq\":" << r.seq << ",\"module\":\"" << json_escape(r.module)
           << "\",\"function\":\"" << json_escape(r.function) << "\",\"action\":\""
           << action_name(r.action) << "\",\"detail\":\"" << json_escape(r.detail)
           << "\"}";
    }
    os << "]";
    log_.clear();
    return os.str();
}

std::string HookManager::supported_json() {
    std::ostringstream os;
    os << "[";
#ifdef _WIN32
    bool first = true;
    for (const SupportedApi& api : kSupportedApis) {
        if (!first) {
            os << ",";
        }
        first = false;
        os << "{\"module\":\"" << json_escape(api.module) << "\",\"function\":\""
           << json_escape(api.function) << "\"}";
    }
#endif
    os << "]";
    return os.str();
}

}  // namespace hooks
}  // namespace naturo

// ── C ABI exports ──────────────────────────────────────────────────────────

using naturo::hooks::HookAction;
using naturo::hooks::HookManager;

namespace {

/// Copy a JSON string into the caller buffer; return count or -4 if too small.
int emit_json(const std::string& json, char* result_json, int buf_size, int count) {
    if (result_json == nullptr || buf_size <= 0) {
        return -1;
    }
    if (json.size() + 1 > static_cast<size_t>(buf_size)) {
        return -4;
    }
    std::memcpy(result_json, json.c_str(), json.size() + 1);
    return count;
}

int count_json_objects(const std::string& json) {
    // The arrays are flat objects; count top-level '{'. Adequate for our schema
    // (no nested objects), and avoids a JSON parser in the native layer.
    int n = 0;
    for (char c : json) {
        if (c == '{') {
            ++n;
        }
    }
    return n;
}

}  // namespace

extern "C" {

NATURO_API int naturo_hook_install(const char* module, const char* function,
                                   int action) {
    if (module == nullptr || function == nullptr) {
        return -1;
    }
    if (action != 0 && action != 1) {
        return -1;
    }
    HookAction act = (action == 1) ? HookAction::Block : HookAction::Log;
    return HookManager::instance().install(module, function, act);
}

NATURO_API int naturo_hook_list(char* result_json, int buf_size) {
    std::string json = HookManager::instance().list_json();
    return emit_json(json, result_json, buf_size, count_json_objects(json));
}

NATURO_API int naturo_hook_remove(const char* module, const char* function) {
    if (module == nullptr || function == nullptr) {
        return -1;
    }
    return HookManager::instance().remove(module, function);
}

NATURO_API int naturo_hook_drain_log(char* result_json, int buf_size) {
    std::string json = HookManager::instance().drain_log_json();
    return emit_json(json, result_json, buf_size, count_json_objects(json));
}

NATURO_API int naturo_hook_clear(void) {
    HookManager::instance().clear();
    return 0;
}

NATURO_API int naturo_hook_supported(char* result_json, int buf_size) {
    std::string json = HookManager::supported_json();
    return emit_json(json, result_json, buf_size, count_json_objects(json));
}

}  // extern "C"
