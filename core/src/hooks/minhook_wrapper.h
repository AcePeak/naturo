/**
 * @file minhook_wrapper.h
 * @brief Thin RAII wrappers over the MinHook trampoline library.
 *
 * Two small helpers isolate the raw MinHook C API from the rest of the core:
 *
 *   - MinHookLibrary: a process-wide RAII singleton that calls MH_Initialize
 *     once (lazily, on first use) and MH_Uninitialize at process teardown.
 *   - ScopedHook: an RAII handle for a single (target -> detour) hook that
 *     create+enables on request and guarantees disable+remove on destruction,
 *     so a leaked ScopedHook can never leave a live detour dangling on a freed
 *     target.
 *
 * All Windows-specific behavior is compiled only on _WIN32; on other platforms
 * the members are inert stubs returning a generic failure so the surrounding
 * C ABI still links.
 */

#ifndef NATURO_HOOKS_MINHOOK_WRAPPER_H
#define NATURO_HOOKS_MINHOOK_WRAPPER_H

namespace naturo {
namespace hooks {

/// Result of a wrapper operation. 0 == success; negative values mirror the
/// naturo_core convention (-2 == system/library error).
enum class HookStatus : int {
    Ok = 0,
    Unsupported = -2,  ///< MinHook unavailable (non-Windows) or MH_* failure.
};

/**
 * @brief Process-wide RAII owner of MinHook global initialization.
 *
 * The first call to instance() runs MH_Initialize; the singleton's destructor
 * runs MH_Uninitialize at process exit. ok() reports whether MinHook is usable
 * in this process (always false off Windows).
 */
class MinHookLibrary {
public:
    /// Return the process-wide instance, initializing MinHook on first call.
    static MinHookLibrary& instance();

    /// True when MH_Initialize succeeded and hooks may be created.
    bool ok() const { return ok_; }

    MinHookLibrary(const MinHookLibrary&) = delete;
    MinHookLibrary& operator=(const MinHookLibrary&) = delete;

private:
    MinHookLibrary();
    ~MinHookLibrary();
    bool ok_;
};

/**
 * @brief RAII handle for a single MinHook hook.
 *
 * create() installs and enables the hook; the destructor (or an explicit
 * remove()) disables and removes it. Non-copyable; movable is unnecessary for
 * the manager's storage model (entries are pointer-stable in a map node).
 */
class ScopedHook {
public:
    ScopedHook() : target_(nullptr), created_(false), enabled_(false) {}
    ~ScopedHook();

    ScopedHook(const ScopedHook&) = delete;
    ScopedHook& operator=(const ScopedHook&) = delete;

    /**
     * @brief Create and enable a hook on @p target routing to @p detour.
     * @param target    Address of the function to hook.
     * @param detour    Address of the replacement function.
     * @param out_original Receives the trampoline (call-through to the
     *        original). Untouched on failure.
     * @return HookStatus::Ok on success, HookStatus::Unsupported otherwise.
     */
    HookStatus create(void* target, void* detour, void** out_original);

    /// Disable and remove the hook if created. Safe to call repeatedly.
    HookStatus remove();

    /// True while the hook is installed and enabled.
    bool active() const { return created_ && enabled_; }

    /// The hooked target address, or nullptr when not created.
    void* target() const { return target_; }

private:
    void* target_;
    bool created_;
    bool enabled_;
};

}  // namespace hooks
}  // namespace naturo

#endif  // NATURO_HOOKS_MINHOOK_WRAPPER_H
