/**
 * @file minhook_wrapper.cpp
 * @brief RAII wrappers over MinHook (see minhook_wrapper.h).
 */

#include "minhook_wrapper.h"

#ifdef _WIN32
#include <MinHook.h>
#endif

namespace naturo {
namespace hooks {

// ── MinHookLibrary ───────────────────────────────────────────────────────

MinHookLibrary::MinHookLibrary() : ok_(false) {
#ifdef _WIN32
    MH_STATUS status = MH_Initialize();
    // MH_ERROR_ALREADY_INITIALIZED is fine — another component may have
    // initialized MinHook first; we can still create hooks.
    ok_ = (status == MH_OK || status == MH_ERROR_ALREADY_INITIALIZED);
#endif
}

MinHookLibrary::~MinHookLibrary() {
#ifdef _WIN32
    if (ok_) {
        MH_Uninitialize();
    }
#endif
}

MinHookLibrary& MinHookLibrary::instance() {
    // Function-local static: initialized exactly once, thread-safe under C++11,
    // and destroyed at process exit (running MH_Uninitialize).
    static MinHookLibrary lib;
    return lib;
}

// ── ScopedHook ───────────────────────────────────────────────────────────

HookStatus ScopedHook::create(void* target, void* detour, void** out_original) {
#ifdef _WIN32
    if (!MinHookLibrary::instance().ok()) {
        return HookStatus::Unsupported;
    }
    if (MH_CreateHook(target, detour, out_original) != MH_OK) {
        return HookStatus::Unsupported;
    }
    target_ = target;
    created_ = true;
    if (MH_EnableHook(target) != MH_OK) {
        // Roll back the created-but-not-enabled hook so state stays consistent.
        MH_RemoveHook(target);
        created_ = false;
        target_ = nullptr;
        return HookStatus::Unsupported;
    }
    enabled_ = true;
    return HookStatus::Ok;
#else
    (void)target;
    (void)detour;
    (void)out_original;
    return HookStatus::Unsupported;
#endif
}

HookStatus ScopedHook::remove() {
#ifdef _WIN32
    if (!created_) {
        return HookStatus::Ok;
    }
    if (enabled_) {
        MH_DisableHook(target_);
        enabled_ = false;
    }
    MH_STATUS status = MH_RemoveHook(target_);
    created_ = false;
    target_ = nullptr;
    return (status == MH_OK) ? HookStatus::Ok : HookStatus::Unsupported;
#else
    return HookStatus::Ok;
#endif
}

ScopedHook::~ScopedHook() {
    remove();
}

}  // namespace hooks
}  // namespace naturo
