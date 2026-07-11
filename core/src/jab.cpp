/**
 * @file jab.cpp
 * @brief UI element inspection via Java Access Bridge (JAB).
 *
 * Provides element tree traversal for Java/Swing/AWT applications
 * using the Windows Java Access Bridge API. JAB is dynamically loaded
 * from WindowsAccessBridge-64.dll (or -32.dll for 32-bit).
 *
 * Key concepts:
 * - JAB communicates with Java VMs through shared memory / message passing
 * - Each element is identified by (vmID, AccessibleContext) pair
 * - IsJavaWindow(HWND) detects Java windows
 * - AccessibleContextInfo provides role, name, bounds, states etc.
 *
 * JAB must be started before use (Windows_run, the AT-side entry point the
 * WindowsAccessBridge DLL actually exports) with its message queue pumped so
 * the asynchronous JVM handshake completes, and all AccessibleContext handles
 * must be released (ReleaseJavaObject) to prevent memory leaks in the JVM.
 */

#ifdef _WIN32

#include "naturo/exports.h"
#include <windows.h>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <queue>

/* ── JAB Type Definitions ─────────────────────────────
 *
 * We define minimal types needed to call the JAB API via
 * GetProcAddress. This avoids needing the JDK headers at
 * compile time.
 */

#define JAB_MAX_STRING_SIZE   1024
#define JAB_SHORT_STRING_SIZE  256

typedef long long JOBJECT64;
typedef JOBJECT64 AccessibleContext;

typedef struct {
    wchar_t name[JAB_MAX_STRING_SIZE];
    wchar_t description[JAB_MAX_STRING_SIZE];
    wchar_t role[JAB_SHORT_STRING_SIZE];
    wchar_t role_en_US[JAB_SHORT_STRING_SIZE];
    wchar_t states[JAB_SHORT_STRING_SIZE];
    wchar_t states_en_US[JAB_SHORT_STRING_SIZE];
    int indexInParent;
    int childrenCount;
    int x;
    int y;
    int width;
    int height;
    BOOL accessibleComponent;
    BOOL accessibleAction;
    BOOL accessibleSelection;
    BOOL accessibleText;
    BOOL accessibleInterfaces;
} AccessibleContextInfo;

/* ── JAB Function Pointer Types ───────────────────── */

// The assistive-technology entry point exported by the shipped
// WindowsAccessBridge-<bits>.dll is `Windows_run` (declared
// `void Windows_run(void)`), NOT `initializeAccessBridge` — that symbol is not
// exported by the DLL, so looking it up returns NULL and JAB never starts.
typedef void  (__cdecl *FN_Windows_run)(void);
typedef BOOL  (__cdecl *FN_shutdownAccessBridge)(void);
typedef BOOL  (__cdecl *FN_IsJavaWindow)(HWND window);
typedef BOOL  (__cdecl *FN_GetAccessibleContextFromHWND)(HWND target, long* vmID, AccessibleContext* ac);
typedef BOOL  (__cdecl *FN_GetAccessibleContextInfo)(long vmID, AccessibleContext ac, AccessibleContextInfo* info);
typedef AccessibleContext (__cdecl *FN_GetAccessibleChildFromContext)(long vmID, AccessibleContext ac, int index);
typedef AccessibleContext (__cdecl *FN_GetAccessibleParentFromContext)(long vmID, AccessibleContext ac);
typedef void  (__cdecl *FN_ReleaseJavaObject)(long vmID, JOBJECT64 object);

/* ── JAB Singleton ────────────────────────────────── */

struct JABState {
    HMODULE dll = nullptr;
    bool loaded = false;         ///< DLL + function pointers resolved (one-shot).
    bool load_failed = false;    ///< DLL/functions permanently unavailable.
    bool bridge_started = false; ///< Windows_run + handshake has been attempted.
    bool attached = false;       ///< A live Java window has been confirmed via the bridge.

    FN_Windows_run               pInitialize = nullptr;
    FN_shutdownAccessBridge      pShutdown = nullptr;
    FN_IsJavaWindow              pIsJavaWindow = nullptr;
    FN_GetAccessibleContextFromHWND pGetContextFromHWND = nullptr;
    FN_GetAccessibleContextInfo  pGetContextInfo = nullptr;
    FN_GetAccessibleChildFromContext pGetChild = nullptr;
    FN_GetAccessibleParentFromContext pGetParent = nullptr;
    FN_ReleaseJavaObject         pReleaseObject = nullptr;
};

static JABState g_jab;

/// Upper bound, in milliseconds, on the first attempt to complete the
/// asynchronous AT<->JVM discovery handshake. The first @c Windows_run + single
/// pump frequently does NOT finish the handshake on a loaded desktop, so the
/// attach loop re-invokes @c Windows_run and keeps draining the message queue up
/// to this budget. Only the first JAB query in a process can pay this cost.
static const DWORD JAB_ATTACH_TIMEOUT_MS = 5000;

/// How long to drain the message queue between discovery probes within the
/// attach loop. JAB answers arrive as window messages, so the queue must be
/// pumped between probes for the handshake to make progress.
static const DWORD JAB_ATTACH_POLL_MS = 150;

/// How often, within the attach loop, to re-invoke @c Windows_run. The decisive
/// in-process A/B (issue #1096) showed the JVM handshake completing only after a
/// *second* @c Windows_run; a single call plus a long pump never attaches.
static const DWORD JAB_RERUN_INTERVAL_MS = 800;

/// Short pump applied on follow-up queries once the bridge is already started,
/// so a JVM that registered after the first attempt is still discovered without
/// paying the full handshake timeout on every query (e.g. the cascade @c auto
/// path probes JAB for every window UIA cannot read).
static const DWORD JAB_REFRESH_PUMP_MS = 150;

/**
 * @brief Pump this thread's Windows message queue for up to @p budget_ms.
 *
 * The Java Access Bridge answers from the JVM are delivered as window messages
 * to the assistive-technology thread and are only processed while that thread
 * drains its message loop. A bare Sleep() blocks without draining the queue, so
 * the bridge never finishes attaching and every subsequent query fails. This
 * drains all pending messages in a bounded loop.
 *
 * @param budget_ms Maximum time to spend pumping, in milliseconds.
 */
static void jab_pump_messages(DWORD budget_ms) {
    DWORD start = GetTickCount();
    MSG msg;
    for (;;) {
        while (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
        // Unsigned subtraction is wrap-safe across the GetTickCount rollover.
        if (GetTickCount() - start >= budget_ms) {
            break;
        }
        Sleep(10);
    }
}

/**
 * @brief Load WindowsAccessBridge and resolve the JAB entry points.
 *
 * This is the one-shot, cacheable part of bringing JAB up: the DLL and its
 * exported functions never change for the life of the process. Starting the
 * bridge (the asynchronous JVM handshake) is handled separately by
 * jab_ensure_init(), because — unlike loading the library — that handshake can
 * fail transiently and must be retried.
 *
 * @return true if the DLL and the required functions are available.
 */
static bool jab_load_library() {
    if (g_jab.loaded) return true;
    if (g_jab.load_failed) return false;

    // Try 64-bit first, then legacy name
    const char* dll_names[] = {
        "WindowsAccessBridge-64.dll",
        "WindowsAccessBridge.dll",
        nullptr
    };

    for (int i = 0; dll_names[i]; ++i) {
        g_jab.dll = LoadLibraryA(dll_names[i]);
        if (g_jab.dll) break;
    }

    if (!g_jab.dll) {
        g_jab.load_failed = true;
        return false;
    }

    // Load function pointers
    g_jab.pInitialize     = (FN_Windows_run)GetProcAddress(g_jab.dll, "Windows_run");
    g_jab.pShutdown       = (FN_shutdownAccessBridge)GetProcAddress(g_jab.dll, "shutdownAccessBridge");
    g_jab.pIsJavaWindow   = (FN_IsJavaWindow)GetProcAddress(g_jab.dll, "isJavaWindow");
    g_jab.pGetContextFromHWND = (FN_GetAccessibleContextFromHWND)GetProcAddress(g_jab.dll, "getAccessibleContextFromHWND");
    g_jab.pGetContextInfo = (FN_GetAccessibleContextInfo)GetProcAddress(g_jab.dll, "getAccessibleContextInfo");
    g_jab.pGetChild       = (FN_GetAccessibleChildFromContext)GetProcAddress(g_jab.dll, "getAccessibleChildFromContext");
    g_jab.pGetParent      = (FN_GetAccessibleParentFromContext)GetProcAddress(g_jab.dll, "getAccessibleParentFromContext");
    g_jab.pReleaseObject  = (FN_ReleaseJavaObject)GetProcAddress(g_jab.dll, "releaseJavaObject");

    // Require minimum set
    if (!g_jab.pInitialize || !g_jab.pIsJavaWindow ||
        !g_jab.pGetContextFromHWND || !g_jab.pGetContextInfo ||
        !g_jab.pGetChild || !g_jab.pReleaseObject) {
        FreeLibrary(g_jab.dll);
        g_jab.dll = nullptr;
        g_jab.load_failed = true;
        return false;
    }

    g_jab.loaded = true;
    return true;
}

/**
 * @brief Probe whether the bridge can currently see any live Java window.
 *
 * Used as the completion test for the discovery handshake: once @c isJavaWindow
 * answers true for a real window, the AT<->JVM channel is up. The foreground
 * window is checked first as the common fast path, then all top-level windows.
 *
 * @return true if at least one Java window is discoverable right now.
 */
static BOOL CALLBACK jab_probe_enum(HWND hwnd, LPARAM lParam) {
    if (g_jab.pIsJavaWindow(hwnd)) {
        *reinterpret_cast<bool*>(lParam) = true;
        return FALSE; // stop enumerating
    }
    return TRUE;
}

static bool jab_bridge_sees_java_window() {
    HWND fg = GetForegroundWindow();
    if (fg && g_jab.pIsJavaWindow(fg)) return true;
    bool found = false;
    EnumWindows(jab_probe_enum, reinterpret_cast<LPARAM>(&found));
    return found;
}

/**
 * @brief Ensure the Java Access Bridge is loaded and its JVM handshake pumped.
 *
 * The handshake by which @c WindowsAccessBridge registers this process as an
 * assistive technology and discovers running JVMs is asynchronous: its replies
 * arrive as window messages on the calling thread and must be pumped. The
 * previous implementation called @c Windows_run exactly once, pumped for a fixed
 * 1000&nbsp;ms, then cached success forever — on a loaded desktop the handshake
 * routinely did not complete in that window, so @c isJavaWindow returned false
 * permanently and every query short-circuited to @c -6 (#1096).
 *
 * This replaces that fire-and-forget init with a bounded pump-and-retry that
 * actually confirms attachment:
 *  - The first attempt re-invokes @c Windows_run periodically and drains the
 *    message queue until a Java window becomes discoverable or
 *    @c JAB_ATTACH_TIMEOUT_MS elapses. (The decisive A/B on #1096 showed the
 *    handshake completing only after a *second* @c Windows_run.)
 *  - Success is recorded stickily (@c attached); it is never cached on a
 *    handshake that produced no Java window, so a JVM that starts later is still
 *    picked up — follow-up queries do a short pump rather than the full retry,
 *    keeping the no-Java case (hit by the cascade @c auto path for every window
 *    UIA cannot read) cheap.
 *
 * @return true if the bridge is available for queries; false only if the DLL or
 *         its required functions are missing. A true return does not promise a
 *         Java window exists — the caller still resolves and validates the HWND.
 */
static bool jab_ensure_init() {
    if (!jab_load_library()) return false;

    // Already confirmed up: drain any freshly delivered messages and proceed.
    if (g_jab.attached) {
        jab_pump_messages(JAB_REFRESH_PUMP_MS);
        return true;
    }

    if (!g_jab.bridge_started) {
        // First attempt: complete the asynchronous handshake. Re-invoke
        // Windows_run on an interval and keep pumping until a Java window is
        // discoverable or the bounded budget is exhausted.
        DWORD start = GetTickCount();
        DWORD last_run = 0;
        bool first_pass = true;
        for (;;) {
            // Unsigned subtraction is wrap-safe across the GetTickCount rollover.
            if (first_pass || (GetTickCount() - last_run) >= JAB_RERUN_INTERVAL_MS) {
                g_jab.pInitialize(); // Windows_run — (re)start the bridge
                last_run = GetTickCount();
                first_pass = false;
            }
            jab_pump_messages(JAB_ATTACH_POLL_MS);
            if (jab_bridge_sees_java_window()) {
                g_jab.attached = true;
                break;
            }
            if (GetTickCount() - start >= JAB_ATTACH_TIMEOUT_MS) break;
        }
        g_jab.bridge_started = true;
        return true;
    }

    // Bridge already started but not yet attached (no Java window on the first
    // attempt). A JVM may have registered since: do a cheap pump + probe so it
    // is picked up without paying the full handshake timeout on every query.
    jab_pump_messages(JAB_REFRESH_PUMP_MS);
    if (jab_bridge_sees_java_window()) {
        g_jab.attached = true;
    }
    return true;
}

/* ── JSON Helpers ─────────────────────────────────── */

static std::string jab_json_escape(const wchar_t* s) {
    if (!s) return "";
    std::string out;
    for (const wchar_t* p = s; *p; ++p) {
        if (*p < 0x80) {
            char c = (char)*p;
            switch (c) {
                case '"':  out += "\\\""; break;
                case '\\': out += "\\\\"; break;
                case '\b': out += "\\b";  break;
                case '\f': out += "\\f";  break;
                case '\n': out += "\\n";  break;
                case '\r': out += "\\r";  break;
                case '\t': out += "\\t";  break;
                default:
                    if (c < 0x20) {
                        char buf[8];
                        snprintf(buf, sizeof(buf), "\\u%04x", (unsigned)c);
                        out += buf;
                    } else {
                        out += c;
                    }
            }
        } else if (*p < 0x800) {
            out += (char)(0xC0 | (*p >> 6));
            out += (char)(0x80 | (*p & 0x3F));
        } else if (*p >= 0xD800 && *p <= 0xDBFF) {
            // Surrogate pair
            if (*(p + 1) >= 0xDC00 && *(p + 1) <= 0xDFFF) {
                unsigned int cp = 0x10000 + ((*p - 0xD800) << 10) + (*(p + 1) - 0xDC00);
                out += (char)(0xF0 | (cp >> 18));
                out += (char)(0x80 | ((cp >> 12) & 0x3F));
                out += (char)(0x80 | ((cp >> 6) & 0x3F));
                out += (char)(0x80 | (cp & 0x3F));
                ++p;
            }
        } else {
            out += (char)(0xE0 | (*p >> 12));
            out += (char)(0x80 | ((*p >> 6) & 0x3F));
            out += (char)(0x80 | (*p & 0x3F));
        }
    }
    return out;
}

/**
 * @brief Map JAB role string to a Naturo-normalized role name.
 *
 * JAB roles are lowercase strings like "push button", "combo box", etc.
 * We normalize them to PascalCase to match UIA/MSAA conventions.
 */
static std::string jab_normalize_role(const wchar_t* role) {
    std::string r = jab_json_escape(role);
    if (r.empty()) return "Unknown";

    // Map common JAB roles to Naturo-standard names
    if (r == "push button") return "Button";
    if (r == "toggle button") return "ToggleButton";
    if (r == "check box") return "CheckBox";
    if (r == "radio button") return "RadioButton";
    if (r == "combo box") return "ComboBox";
    if (r == "text") return "Edit";
    if (r == "password text") return "PasswordEdit";
    if (r == "label") return "Text";
    if (r == "list") return "List";
    if (r == "list item") return "ListItem";
    if (r == "tree") return "Tree";
    if (r == "table") return "Table";
    if (r == "menu bar") return "MenuBar";
    if (r == "menu") return "Menu";
    if (r == "menu item") return "MenuItem";
    if (r == "popup menu") return "PopupMenu";
    if (r == "separator") return "Separator";
    if (r == "scroll bar") return "ScrollBar";
    if (r == "scroll pane") return "ScrollPane";
    if (r == "slider") return "Slider";
    if (r == "progress bar") return "ProgressBar";
    if (r == "tool bar") return "ToolBar";
    if (r == "tool tip") return "ToolTip";
    if (r == "page tab") return "Tab";
    if (r == "page tab list") return "TabList";
    if (r == "panel") return "Pane";
    if (r == "frame") return "Window";
    if (r == "dialog") return "Dialog";
    if (r == "internal frame") return "InternalFrame";
    if (r == "root pane") return "RootPane";
    if (r == "layered pane") return "LayeredPane";
    if (r == "glass pane") return "GlassPane";
    if (r == "option pane") return "OptionPane";
    if (r == "split pane") return "SplitPane";
    if (r == "canvas") return "Canvas";
    if (r == "spin box") return "SpinBox";
    if (r == "status bar") return "StatusBar";
    if (r == "column header") return "ColumnHeader";
    if (r == "row header") return "RowHeader";
    if (r == "viewport") return "Viewport";
    if (r == "alert") return "Alert";
    if (r == "window") return "Window";
    if (r == "file chooser") return "FileChooser";
    if (r == "color chooser") return "ColorChooser";
    if (r == "font chooser") return "FontChooser";
    if (r == "desktop pane") return "DesktopPane";
    if (r == "desktop icon") return "DesktopIcon";
    if (r == "hyperlink") return "Hyperlink";
    if (r == "icon") return "Icon";
    if (r == "filler") return "Filler";
    if (r == "directory pane") return "DirectoryPane";
    if (r == "group box") return "Group";
    if (r == "header") return "Header";
    if (r == "footer") return "Footer";
    if (r == "paragraph") return "Paragraph";
    if (r == "date editor") return "DateEditor";
    if (r == "editbar") return "EditBar";
    if (r == "unknown") return "Unknown";
    if (r == "swing component") return "SwingComponent";
    if (r == "awt component") return "AwtComponent";

    // Unknown role — return as-is (escaped)
    return r;
}

/* ── Element Structures ───────────────────────────── */

struct JABElement {
    long vmID;
    AccessibleContext ac;
    std::string id;       // "jN"
    std::string role;
    std::string raw_role; // original JAB role string
    std::string name;
    std::string value;    // from description
    std::string states;
    int x, y, width, height;
    int child_count;
    std::vector<JABElement> children;
};

static int g_jab_id_counter = 0;

/**
 * @brief Build an element from an AccessibleContextInfo.
 */
static JABElement jab_build_element(long vmID, AccessibleContext ac,
                                     const AccessibleContextInfo& info) {
    JABElement el;
    el.vmID = vmID;
    el.ac = ac;

    char id_buf[16];
    snprintf(id_buf, sizeof(id_buf), "j%d", g_jab_id_counter++);
    el.id = id_buf;

    el.raw_role = jab_json_escape(info.role_en_US[0] ? info.role_en_US : info.role);
    el.role = jab_normalize_role(info.role_en_US[0] ? info.role_en_US : info.role);
    el.name = jab_json_escape(info.name);
    el.value = jab_json_escape(info.description);
    el.states = jab_json_escape(info.states_en_US[0] ? info.states_en_US : info.states);
    el.x = info.x;
    el.y = info.y;
    el.width = info.width;
    el.height = info.height;
    el.child_count = info.childrenCount;

    return el;
}

/**
 * @brief Recursively traverse the JAB tree up to max_depth.
 */
static void jab_traverse(long vmID, AccessibleContext ac, int depth, int max_depth,
                          JABElement& parent) {
    if (depth >= max_depth) return;

    AccessibleContextInfo info;
    memset(&info, 0, sizeof(info));

    if (!g_jab.pGetContextInfo(vmID, ac, &info)) return;

    for (int i = 0; i < info.childrenCount; ++i) {
        AccessibleContext child = g_jab.pGetChild(vmID, ac, i);
        if (!child) continue;

        AccessibleContextInfo child_info;
        memset(&child_info, 0, sizeof(child_info));

        if (g_jab.pGetContextInfo(vmID, child, &child_info)) {
            JABElement child_el = jab_build_element(vmID, child, child_info);

            if (depth + 1 < max_depth && child_info.childrenCount > 0) {
                jab_traverse(vmID, child, depth + 1, max_depth, child_el);
            }

            parent.children.push_back(std::move(child_el));
        }

        if (g_jab.pReleaseObject) {
            g_jab.pReleaseObject(vmID, child);
        }
    }
}

/**
 * @brief Serialize a JABElement to JSON.
 */
static void jab_element_to_json(const JABElement& el, std::string& out) {
    out += "{";
    out += "\"id\":\"" + el.id + "\",";
    out += "\"role\":\"" + el.role + "\",";
    out += "\"name\":\"" + el.name + "\",";
    out += "\"value\":\"" + el.value + "\",";

    char buf[128];
    snprintf(buf, sizeof(buf), "\"x\":%d,\"y\":%d,\"width\":%d,\"height\":%d,",
             el.x, el.y, el.width, el.height);
    out += buf;

    out += "\"states\":\"" + el.states + "\",";
    out += "\"jab_role\":\"" + el.raw_role + "\",";
    out += "\"backend\":\"jab\",";
    out += "\"children\":[";

    for (size_t i = 0; i < el.children.size(); ++i) {
        if (i > 0) out += ",";
        jab_element_to_json(el.children[i], out);
    }

    out += "]}";
}

/* ── Find by HWND — enumerate top-level Java windows ── */

struct EnumJavaData {
    uintptr_t target_hwnd;
    HWND found_java_hwnd;
};

static BOOL CALLBACK jab_enum_java_windows(HWND hwnd, LPARAM lParam) {
    EnumJavaData* data = (EnumJavaData*)lParam;
    if (!g_jab.pIsJavaWindow(hwnd)) return TRUE; // continue

    if (data->target_hwnd == 0) {
        // First Java window found (foreground preference)
        if (hwnd == GetForegroundWindow()) {
            data->found_java_hwnd = hwnd;
            return FALSE; // stop
        }
        if (!data->found_java_hwnd) {
            data->found_java_hwnd = hwnd;
        }
        return TRUE;
    }

    if ((uintptr_t)hwnd == data->target_hwnd) {
        data->found_java_hwnd = hwnd;
        return FALSE;
    }

    // Check if target is a parent/ancestor
    HWND parent = hwnd;
    while (parent) {
        if ((uintptr_t)parent == data->target_hwnd) {
            data->found_java_hwnd = hwnd;
            return FALSE;
        }
        parent = GetParent(parent);
    }

    return TRUE;
}

/* ── Public API ───────────────────────────────────── */

NATURO_API int naturo_jab_check_support(uintptr_t hwnd) {
    if (!jab_ensure_init()) return 0;

    if (hwnd == 0) {
        // Check if foreground window is Java
        HWND fg = GetForegroundWindow();
        if (fg && g_jab.pIsJavaWindow(fg)) return 1;

        // Check any visible Java window exists
        EnumJavaData data = { 0, nullptr };
        EnumWindows(jab_enum_java_windows, (LPARAM)&data);
        return data.found_java_hwnd ? 1 : 0;
    }

    // Check specific window
    HWND h = (HWND)hwnd;
    if (g_jab.pIsJavaWindow(h)) return 1;

    // Check child windows (Java apps often use a child HWND)
    EnumJavaData data = { hwnd, nullptr };
    EnumWindows(jab_enum_java_windows, (LPARAM)&data);
    return data.found_java_hwnd ? 1 : 0;
}

NATURO_API int naturo_jab_get_element_tree(uintptr_t hwnd, int depth,
                                            char* result_json, int buf_size) {
    if (!result_json || buf_size < 4) return -1;
    result_json[0] = '\0';

    // Java/Swing wraps content in many structural panes (a JDesktopPane >
    // InternalFrame dialog nests RootPane > LayeredPane > content pane > … before
    // any control), so the real widgets routinely sit 10-12 levels deep. A cap of
    // 10 silently truncated every --depth above it and hid those controls; allow
    // the caller's depth up to a generous bound (matches the CLI's --depth max).
    if (depth < 1) depth = 1;
    if (depth > 50) depth = 50;

    if (!jab_ensure_init()) return -6; // JAB not available

    // Find the Java HWND
    EnumJavaData data = { hwnd, nullptr };
    if (hwnd == 0) {
        HWND fg = GetForegroundWindow();
        if (fg && g_jab.pIsJavaWindow(fg)) {
            data.found_java_hwnd = fg;
        }
    }
    if (!data.found_java_hwnd) {
        EnumWindows(jab_enum_java_windows, (LPARAM)&data);
    }

    if (!data.found_java_hwnd) return -6; // No Java window found

    // Get root accessible context
    long vmID = 0;
    AccessibleContext ac = 0;
    if (!g_jab.pGetContextFromHWND(data.found_java_hwnd, &vmID, &ac)) {
        return -2;
    }

    // Get root element info
    AccessibleContextInfo info;
    memset(&info, 0, sizeof(info));
    if (!g_jab.pGetContextInfo(vmID, ac, &info)) {
        if (g_jab.pReleaseObject) g_jab.pReleaseObject(vmID, ac);
        return -2;
    }

    // Reset ID counter
    g_jab_id_counter = 0;

    // Build tree
    JABElement root = jab_build_element(vmID, ac, info);
    jab_traverse(vmID, ac, 0, depth, root);

    // Release root context
    if (g_jab.pReleaseObject) g_jab.pReleaseObject(vmID, ac);

    // Serialize to JSON
    std::string json;
    json.reserve(32768);
    jab_element_to_json(root, json);

    int count = 1;
    // Count all elements
    std::queue<const JABElement*> q;
    q.push(&root);
    while (!q.empty()) {
        const JABElement* e = q.front(); q.pop();
        for (auto& c : e->children) {
            ++count;
            q.push(&c);
        }
    }

    if ((int)json.size() + 1 > buf_size) return -4;

    memcpy(result_json, json.c_str(), json.size() + 1);
    return count;
}

NATURO_API int naturo_jab_find_element(uintptr_t hwnd, const char* role,
                                        const char* name,
                                        char* result_json, int buf_size) {
    if (!result_json || buf_size < 4) return -1;
    result_json[0] = '\0';

    if (!jab_ensure_init()) return -6;

    // Find the Java HWND
    EnumJavaData data = { hwnd, nullptr };
    if (hwnd == 0) {
        HWND fg = GetForegroundWindow();
        if (fg && g_jab.pIsJavaWindow(fg)) {
            data.found_java_hwnd = fg;
        }
    }
    if (!data.found_java_hwnd) {
        EnumWindows(jab_enum_java_windows, (LPARAM)&data);
    }
    if (!data.found_java_hwnd) return -6;

    long vmID = 0;
    AccessibleContext ac = 0;
    if (!g_jab.pGetContextFromHWND(data.found_java_hwnd, &vmID, &ac)) {
        return -2;
    }

    // Prepare search criteria (case-insensitive)
    std::string search_role, search_name;
    if (role) {
        search_role = role;
        for (auto& c : search_role) c = tolower(c);
    }
    if (name) {
        search_name = name;
        for (auto& c : search_name) c = tolower(c);
    }

    // BFS search
    struct SearchItem {
        long vmID;
        AccessibleContext ac;
        bool is_root;
    };

    std::queue<SearchItem> bfs;
    bfs.push({ vmID, ac, true });
    bool found = false;
    g_jab_id_counter = 0;

    while (!bfs.empty() && !found) {
        SearchItem item = bfs.front(); bfs.pop();

        AccessibleContextInfo info;
        memset(&info, 0, sizeof(info));
        if (!g_jab.pGetContextInfo(item.vmID, item.ac, &info)) {
            if (!item.is_root && g_jab.pReleaseObject) {
                g_jab.pReleaseObject(item.vmID, item.ac);
            }
            continue;
        }

        // Check if this element matches
        std::string el_role = jab_normalize_role(info.role_en_US[0] ? info.role_en_US : info.role);
        std::string el_name = jab_json_escape(info.name);
        std::string el_role_lower = el_role;
        std::string el_name_lower = el_name;
        for (auto& c : el_role_lower) c = tolower(c);
        for (auto& c : el_name_lower) c = tolower(c);

        bool role_match = search_role.empty() || el_role_lower.find(search_role) != std::string::npos;
        bool name_match = search_name.empty() || el_name_lower.find(search_name) != std::string::npos;

        if (role_match && name_match && (!search_role.empty() || !search_name.empty())) {
            JABElement el = jab_build_element(item.vmID, item.ac, info);
            std::string json;
            json.reserve(1024);
            jab_element_to_json(el, json);

            if ((int)json.size() + 1 <= buf_size) {
                memcpy(result_json, json.c_str(), json.size() + 1);
                found = true;
            } else {
                found = false; // buffer too small
            }

            // Drain BFS queue and release
            while (!bfs.empty()) {
                SearchItem s = bfs.front(); bfs.pop();
                if (!s.is_root && g_jab.pReleaseObject) {
                    g_jab.pReleaseObject(s.vmID, s.ac);
                }
            }
            if (!item.is_root && g_jab.pReleaseObject) {
                g_jab.pReleaseObject(item.vmID, item.ac);
            }
            if (g_jab.pReleaseObject) g_jab.pReleaseObject(vmID, ac);

            return found ? 0 : -4;
        }

        // Enqueue children
        for (int i = 0; i < info.childrenCount; ++i) {
            AccessibleContext child = g_jab.pGetChild(item.vmID, item.ac, i);
            if (child) {
                bfs.push({ item.vmID, child, false });
            }
        }

        if (!item.is_root && g_jab.pReleaseObject) {
            g_jab.pReleaseObject(item.vmID, item.ac);
        }
    }

    // Drain remaining BFS items
    while (!bfs.empty()) {
        SearchItem s = bfs.front(); bfs.pop();
        if (!s.is_root && g_jab.pReleaseObject) {
            g_jab.pReleaseObject(s.vmID, s.ac);
        }
    }

    if (g_jab.pReleaseObject) g_jab.pReleaseObject(vmID, ac);

    return 1; // Not found
}

#else
/* Non-Windows stubs */

#include "naturo/exports.h"

NATURO_API int naturo_jab_check_support(uintptr_t) { return 0; }
NATURO_API int naturo_jab_get_element_tree(uintptr_t, int, char* buf, int sz) {
    if (buf && sz > 0) buf[0] = '\0';
    return -6;
}
NATURO_API int naturo_jab_find_element(uintptr_t, const char*, const char*, char* buf, int sz) {
    if (buf && sz > 0) buf[0] = '\0';
    return -6;
}

#endif /* _WIN32 */
