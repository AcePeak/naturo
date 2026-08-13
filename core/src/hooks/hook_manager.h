/**
 * @file hook_manager.h
 * @brief Thread-safe lifecycle manager for in-process Win32 API hooks.
 *
 * The HookManager owns the set of installed hooks (keyed by module+function),
 * a bounded log ring-buffer of intercepted calls, and the per-hook action
 * (log vs. block). Detour functions call record_and_action() from arbitrary
 * threads, so every operation is guarded by a single mutex.
 *
 * The manager only knows how to hook a curated table of resolvable exported
 * APIs (kSupportedApis in hook_manager.cpp): each entry pairs a (module,
 * function) name with a hand-written detour and the storage for its
 * trampoline. This keeps hooking type-safe — a detour matches the real ABI of
 * the function it replaces — while still presenting a name-driven interface.
 */

#ifndef NATURO_HOOKS_HOOK_MANAGER_H
#define NATURO_HOOKS_HOOK_MANAGER_H

#include <cstdint>
#include <deque>
#include <map>
#include <memory>
#include <mutex>
#include <string>

#include "minhook_wrapper.h"

namespace naturo {
namespace hooks {

/// What a hook does when its target API is called.
enum class HookAction : int {
    Log = 0,    ///< Record the call, then forward to the original API.
    Block = 1,  ///< Record the call, then return a sentinel without forwarding.
};

/**
 * @brief Process-wide, thread-safe registry of installed hooks + call log.
 */
class HookManager {
public:
    /// Return the process-wide instance.
    static HookManager& instance();

    /**
     * @brief Install or re-arm a hook on a supported (module, function).
     *
     * Idempotent: an already-installed hook has its action updated in place.
     * @return 0 on success, -1 on unsupported/unknown API, -2 on system error.
     */
    int install(const std::string& module, const std::string& function,
                HookAction action);

    /**
     * @brief Remove an installed hook.
     * @return 0 on success, 1 if not installed.
     */
    int remove(const std::string& module, const std::string& function);

    /// Serialize the installed hooks to a JSON array string.
    std::string list_json();

    /// Return the call log as a JSON array string and clear the buffer.
    std::string drain_log_json();

    /// Remove every hook and clear the log.
    void clear();

    /// Serialize the compile-time supported-API table to a JSON array string.
    static std::string supported_json();

    /// Number of currently installed hooks (thread-safe snapshot).
    int count();

    /**
     * @brief Detour entry point: record a call and return the active action.
     *
     * Called from a hooked API's detour, possibly on any thread. Increments the
     * hook's call counter, appends a bounded log record, and returns the action
     * the detour should apply (log vs. block).
     *
     * @param module   Canonical module name (e.g. "user32.dll").
     * @param function Canonical function name (e.g. "MessageBoxW").
     * @param detail   Human-readable summary of the intercepted arguments.
     * @return The action currently configured for the hook (Log if somehow
     *         not found, so a stray call is never silently blocked).
     */
    HookAction record_and_action(const char* module, const char* function,
                                 const std::string& detail);

private:
    HookManager();
    ~HookManager() = default;
    HookManager(const HookManager&) = delete;
    HookManager& operator=(const HookManager&) = delete;

    struct Entry {
        std::string module;
        std::string function;
        HookAction action;
        uint64_t call_count;
        std::unique_ptr<ScopedHook> hook;  ///< RAII owner; destroys -> disable+remove.
    };

    struct LogRecord {
        uint64_t seq;
        std::string module;
        std::string function;
        HookAction action;
        std::string detail;
    };

    // Key = lowercased "module.dll!Function".
    static std::string make_key(const std::string& module,
                                const std::string& function);

    std::mutex mutex_;
    std::map<std::string, Entry> entries_;
    std::deque<LogRecord> log_;
    size_t log_capacity_;
    uint64_t seq_;
};

}  // namespace hooks
}  // namespace naturo

#endif  // NATURO_HOOKS_HOOK_MANAGER_H
