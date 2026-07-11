/**
 * @file ia2.cpp
 * @brief UI element inspection via IAccessible2 (IA2).
 *
 * Provides IAccessible2-based element tree traversal for applications
 * that implement IA2 (Firefox, Thunderbird, LibreOffice, etc.).
 *
 * IAccessible2 extends MSAA's IAccessible with richer semantics:
 * - Object attributes (key=value pairs like "tag:div", "class:toolbar")
 * - Relations (e.g., labelled-by, described-by, flows-to)
 * - Extended roles and states
 * - Text interface for rich text content
 *
 * IA2 is obtained via IServiceProvider::QueryService from an IAccessible.
 */

#ifdef _WIN32

#include "naturo/exports.h"
#include <windows.h>
#include <oleacc.h>
#include <servprov.h>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#pragma comment(lib, "oleacc.lib")

/* ── IAccessible2 Interface Definitions ───────────────
 *
 * The IA2 interfaces are not in the Windows SDK. We define the
 * minimum needed: IAccessible2 interface with its IID and vtable
 * entries we actually use. The GUIDs are stable across all IA2
 * implementations.
 */

// IAccessible2 service/interface GUID
// {1546D4B0-4C98-4BDA-89AE-9A64748BDDE4}
static const GUID IID_IAccessible2 = {
    0x1546D4B0, 0x4C98, 0x4BDA,
    {0x89, 0xAE, 0x9A, 0x64, 0x74, 0x8B, 0xDD, 0xE4}
};

// IAccessible2 roles that extend MSAA roles (start at 0x100)
enum IA2Role {
    IA2_ROLE_CANVAS            = 0x401,
    IA2_ROLE_CONTENT_DELETION  = 0x425,
    IA2_ROLE_CONTENT_INSERTION = 0x426,
    IA2_ROLE_FOOTER            = 0x40E,
    IA2_ROLE_FORM              = 0x410,
    IA2_ROLE_HEADER            = 0x413,
    IA2_ROLE_HEADING           = 0x414,
    IA2_ROLE_LANDMARK          = 0x41F,
    IA2_ROLE_NOTE              = 0x41B,
    IA2_ROLE_PAGE              = 0x41D,
    IA2_ROLE_PARAGRAPH         = 0x41E,
    IA2_ROLE_SECTION           = 0x422,
    IA2_ROLE_REDUNDANT_OBJECT  = 0x421,
    IA2_ROLE_TEXT_FRAME         = 0x427,
};

// IAccessible2 states (bitmask, extend MSAA states)
enum IA2State {
    IA2_STATE_ACTIVE           = 0x0001,
    IA2_STATE_EDITABLE         = 0x0008,
    IA2_STATE_MODAL            = 0x0100,
    IA2_STATE_REQUIRED         = 0x0400,
    IA2_STATE_STALE            = 0x4000,
    IA2_STATE_TRANSIENT        = 0x8000,
};

/**
 * @brief Minimal IAccessible2 COM interface declaration.
 *
 * We only declare the vtable methods we use (get_nRelations,
 * get_role, get_attributes, get_extendedStates, etc.).
 * The full IA2 interface has ~30 methods; we define
 * the vtable slots up to what we need.
 */
#undef INTERFACE
#define INTERFACE IAccessible2

DECLARE_INTERFACE_(IAccessible2, IAccessible)
{
    // IAccessible2 methods (after IAccessible vtable)
    // Slot 0: get_nRelations
    STDMETHOD_(HRESULT, get_nRelations)(THIS_ long* nRelations) PURE;
    // Slot 1: get_relation
    STDMETHOD_(HRESULT, get_relation)(THIS_ long relationIndex, IUnknown** relation) PURE;
    // Slot 2: get_relations
    STDMETHOD_(HRESULT, get_relations)(THIS_ long maxRelations, IUnknown** relations, long* nRelations) PURE;
    // Slot 3: role
    STDMETHOD_(HRESULT, role)(THIS_ long* role) PURE;
    // Slot 4: scrollTo
    STDMETHOD_(HRESULT, scrollTo)(THIS_ long scrollType) PURE;
    // Slot 5: scrollToPoint
    STDMETHOD_(HRESULT, scrollToPoint)(THIS_ long coordinateType, long x, long y) PURE;
    // Slot 6: get_groupPosition
    STDMETHOD_(HRESULT, get_groupPosition)(THIS_ long* groupLevel, long* similarItemsInGroup, long* positionInGroup) PURE;
    // Slot 7: get_states
    STDMETHOD_(HRESULT, get_states)(THIS_ long* states) PURE;
    // Slot 8: get_extendedRole
    STDMETHOD_(HRESULT, get_extendedRole)(THIS_ BSTR* extendedRole) PURE;
    // Slot 9: get_localizedExtendedRole
    STDMETHOD_(HRESULT, get_localizedExtendedRole)(THIS_ BSTR* localizedExtendedRole) PURE;
    // Slot 10: get_nExtendedStates
    STDMETHOD_(HRESULT, get_nExtendedStates)(THIS_ long* nExtendedStates) PURE;
    // Slot 11: get_extendedStates
    STDMETHOD_(HRESULT, get_extendedStates)(THIS_ long maxExtendedStates, BSTR** extendedStates, long* nExtendedStates) PURE;
    // Slot 12: get_localizedExtendedStates
    STDMETHOD_(HRESULT, get_localizedExtendedStates)(THIS_ long maxExtendedStates, BSTR** localizedExtendedStates, long* nExtendedStates) PURE;
    // Slot 13: get_uniqueID
    STDMETHOD_(HRESULT, get_uniqueID)(THIS_ long* uniqueID) PURE;
    // Slot 14: get_windowHandle
    STDMETHOD_(HRESULT, get_windowHandle)(THIS_ HWND* windowHandle) PURE;
    // Slot 15: get_indexInParent
    STDMETHOD_(HRESULT, get_indexInParent)(THIS_ long* indexInParent) PURE;
    // Slot 16: get_locale
    STDMETHOD_(HRESULT, get_locale)(THIS_ void* locale) PURE;
    // Slot 17: get_attributes
    STDMETHOD_(HRESULT, get_attributes)(THIS_ BSTR* attributes) PURE;
};


/**
 * @brief Escape a wide string for safe JSON embedding.
 */
static std::string ia2_json_escape(const wchar_t* s) {
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
                    break;
            }
        } else {
            char buf[8];
            snprintf(buf, sizeof(buf), "\\u%04x", (unsigned)*p);
            out += buf;
        }
    }
    return out;
}

/**
 * @brief Convert BSTR to escaped JSON string, then free the BSTR.
 */
static std::string ia2_bstr_to_json(BSTR bstr) {
    if (!bstr) return "";
    std::string result = ia2_json_escape(bstr);
    SysFreeString(bstr);
    return result;
}

/**
 * @brief Map MSAA role constant to human-readable string (shared with msaa.cpp).
 */
static const char* ia2_msaa_role_to_string(long role) {
    switch (role) {
        case ROLE_SYSTEM_ALERT:         return "Alert";
        case ROLE_SYSTEM_APPLICATION:   return "Application";
        case ROLE_SYSTEM_BORDER:        return "Border";
        case ROLE_SYSTEM_BUTTONDROPDOWN: return "ButtonDropDown";
        case ROLE_SYSTEM_BUTTONMENU:    return "ButtonMenu";
        case ROLE_SYSTEM_CELL:          return "Cell";
        case ROLE_SYSTEM_CHECKBUTTON:   return "CheckBox";
        case ROLE_SYSTEM_CLIENT:        return "Client";
        case ROLE_SYSTEM_COLUMN:        return "Column";
        case ROLE_SYSTEM_COLUMNHEADER:  return "ColumnHeader";
        case ROLE_SYSTEM_COMBOBOX:      return "ComboBox";
        case ROLE_SYSTEM_DIALOG:        return "Dialog";
        case ROLE_SYSTEM_DOCUMENT:      return "Document";
        case ROLE_SYSTEM_GRAPHIC:       return "Image";
        case ROLE_SYSTEM_GROUPING:      return "Group";
        case ROLE_SYSTEM_LINK:          return "Hyperlink";
        case ROLE_SYSTEM_LIST:          return "List";
        case ROLE_SYSTEM_LISTITEM:      return "ListItem";
        case ROLE_SYSTEM_MENUBAR:       return "MenuBar";
        case ROLE_SYSTEM_MENUITEM:      return "MenuItem";
        case ROLE_SYSTEM_MENUPOPUP:     return "Menu";
        case ROLE_SYSTEM_OUTLINE:       return "Tree";
        case ROLE_SYSTEM_OUTLINEITEM:   return "TreeItem";
        case ROLE_SYSTEM_PAGETAB:       return "TabItem";
        case ROLE_SYSTEM_PAGETABLIST:   return "Tab";
        case ROLE_SYSTEM_PANE:          return "Pane";
        case ROLE_SYSTEM_PROGRESSBAR:   return "ProgressBar";
        case ROLE_SYSTEM_PUSHBUTTON:    return "Button";
        case ROLE_SYSTEM_RADIOBUTTON:   return "RadioButton";
        case ROLE_SYSTEM_ROW:           return "Row";
        case ROLE_SYSTEM_ROWHEADER:     return "RowHeader";
        case ROLE_SYSTEM_SCROLLBAR:     return "ScrollBar";
        case ROLE_SYSTEM_SEPARATOR:     return "Separator";
        case ROLE_SYSTEM_SLIDER:        return "Slider";
        case ROLE_SYSTEM_SPINBUTTON:    return "Spinner";
        case ROLE_SYSTEM_SPLITBUTTON:   return "SplitButton";
        case ROLE_SYSTEM_STATICTEXT:    return "Text";
        case ROLE_SYSTEM_STATUSBAR:     return "StatusBar";
        case ROLE_SYSTEM_TABLE:         return "Table";
        case ROLE_SYSTEM_TEXT:          return "Edit";
        case ROLE_SYSTEM_TITLEBAR:      return "TitleBar";
        case ROLE_SYSTEM_TOOLBAR:       return "ToolBar";
        case ROLE_SYSTEM_TOOLTIP:       return "ToolTip";
        case ROLE_SYSTEM_WINDOW:        return "Window";
        default:                        return NULL;
    }
}

/**
 * @brief Map IA2-extended role to human-readable string.
 */
static const char* ia2_role_to_string(long role) {
    // First try MSAA roles
    const char* msaa = ia2_msaa_role_to_string(role);
    if (msaa) return msaa;

    // Then IA2-specific roles
    switch (role) {
        case IA2_ROLE_CANVAS:            return "Canvas";
        case IA2_ROLE_CONTENT_DELETION:  return "ContentDeletion";
        case IA2_ROLE_CONTENT_INSERTION: return "ContentInsertion";
        case IA2_ROLE_FOOTER:            return "Footer";
        case IA2_ROLE_FORM:              return "Form";
        case IA2_ROLE_HEADER:            return "Header";
        case IA2_ROLE_HEADING:           return "Heading";
        case IA2_ROLE_LANDMARK:          return "Landmark";
        case IA2_ROLE_NOTE:              return "Note";
        case IA2_ROLE_PAGE:              return "Page";
        case IA2_ROLE_PARAGRAPH:         return "Paragraph";
        case IA2_ROLE_SECTION:           return "Section";
        case IA2_ROLE_REDUNDANT_OBJECT:  return "RedundantObject";
        case IA2_ROLE_TEXT_FRAME:         return "TextFrame";
        default:                         return "Unknown";
    }
}

/**
 * @brief Try to obtain IAccessible2 from an IAccessible via IServiceProvider.
 *
 * @param acc  Source IAccessible interface.
 * @return IAccessible2 pointer (caller must Release), or NULL if not supported.
 */
static IAccessible2* ia2_from_accessible(IAccessible* acc) {
    if (!acc) return NULL;

    IServiceProvider* sp = NULL;
    HRESULT hr = acc->QueryInterface(IID_IServiceProvider, (void**)&sp);
    if (FAILED(hr) || !sp) return NULL;

    IAccessible2* ia2 = NULL;
    hr = sp->QueryService(IID_IAccessible2, IID_IAccessible2, (void**)&ia2);
    sp->Release();

    return SUCCEEDED(hr) ? ia2 : NULL;
}

/**
 * @brief Get bounding rectangle for an accessible object.
 */
static bool ia2_get_location(IAccessible* acc, VARIANT child_id,
                              long* out_x, long* out_y,
                              long* out_w, long* out_h) {
    long x = 0, y = 0, w = 0, h = 0;
    HRESULT hr = acc->accLocation(&x, &y, &w, &h, child_id);
    if (SUCCEEDED(hr)) {
        *out_x = x; *out_y = y; *out_w = w; *out_h = h;
        return true;
    }
    *out_x = *out_y = *out_w = *out_h = 0;
    return false;
}

/**
 * @brief Recursively build JSON for an IA2 element tree.
 *
 * For each element, tries to get IA2 interface for extended properties.
 * Falls back to MSAA-level info if IA2 is not available for that element.
 *
 * @param acc        The IAccessible interface for this element.
 * @param child_id   VARIANT identifying this child.
 * @param depth      Remaining depth to traverse.
 * @param out        Output string to append JSON to.
 * @param count      Running count of elements processed.
 * @param id_counter Running counter for generating element IDs.
 */
static void build_ia2_json(IAccessible* acc, VARIANT child_id,
                            int depth, std::string& out,
                            int& count, int& id_counter) {
    if (!acc) return;
    count++;

    // Get MSAA role
    VARIANT role_var;
    VariantInit(&role_var);
    HRESULT hr = acc->get_accRole(child_id, &role_var);
    long msaa_role = 0;
    if (SUCCEEDED(hr) && role_var.vt == VT_I4) {
        msaa_role = role_var.lVal;
    }
    VariantClear(&role_var);

    // Try to get IA2 interface for extended info
    IAccessible2* ia2 = NULL;
    long ia2_role = msaa_role;
    long ia2_states = 0;
    std::string ia2_attributes;
    long ia2_unique_id = 0;
    bool has_ia2 = false;

    if (child_id.vt == VT_I4 && child_id.lVal == CHILDID_SELF) {
        ia2 = ia2_from_accessible(acc);
        if (ia2) {
            has_ia2 = true;

            // IA2 extended role (may differ from MSAA role)
            long r = 0;
            if (SUCCEEDED(ia2->role(&r))) {
                ia2_role = r;
            }

            // IA2 states
            long s = 0;
            if (SUCCEEDED(ia2->get_states(&s))) {
                ia2_states = s;
            }

            // IA2 attributes (semicolon-separated key:value pairs)
            BSTR attrs = NULL;
            if (SUCCEEDED(ia2->get_attributes(&attrs)) && attrs) {
                ia2_attributes = ia2_bstr_to_json(attrs);
                // bstr_to_json already freed attrs
            }

            // Unique ID
            long uid = 0;
            if (SUCCEEDED(ia2->get_uniqueID(&uid))) {
                ia2_unique_id = uid;
            }
        }
    }

    const char* role_str = ia2_role_to_string(ia2_role);

    // Get name
    BSTR name_bstr = NULL;
    hr = acc->get_accName(child_id, &name_bstr);
    std::string name = (SUCCEEDED(hr) && name_bstr) ? ia2_bstr_to_json(name_bstr) : "";

    // Get value
    BSTR value_bstr = NULL;
    hr = acc->get_accValue(child_id, &value_bstr);
    std::string value = (SUCCEEDED(hr) && value_bstr) ? ia2_bstr_to_json(value_bstr) : "";

    // Get keyboard shortcut
    BSTR shortcut_bstr = NULL;
    hr = acc->get_accKeyboardShortcut(child_id, &shortcut_bstr);
    std::string shortcut = (SUCCEEDED(hr) && shortcut_bstr) ? ia2_bstr_to_json(shortcut_bstr) : "";

    // Get MSAA state
    VARIANT state_var;
    VariantInit(&state_var);
    hr = acc->get_accState(child_id, &state_var);
    long msaa_state = 0;
    if (SUCCEEDED(hr) && state_var.vt == VT_I4) {
        msaa_state = state_var.lVal;
    }
    VariantClear(&state_var);

    // Get location
    long x = 0, y = 0, w = 0, h = 0;
    ia2_get_location(acc, child_id, &x, &y, &w, &h);

    // Generate element ID
    int elem_id = id_counter++;
    char id_buf[32];
    snprintf(id_buf, sizeof(id_buf), "a%d", elem_id);

    // Build JSON object
    char buf[4096];
    snprintf(buf, sizeof(buf),
        "{\"id\":\"%s\",\"role\":\"%s\",\"role_id\":%ld,\"name\":\"%s\","
        "\"value\":%s,"
        "\"x\":%ld,\"y\":%ld,\"width\":%ld,\"height\":%ld,"
        "\"state\":%ld,"
        "\"keyboard_shortcut\":%s,"
        "\"backend\":\"ia2\","
        "\"ia2\":%s",
        id_buf, role_str, ia2_role, name.c_str(),
        value.empty() ? "null" : ("\"" + value + "\"").c_str(),
        x, y, w, h,
        msaa_state,
        shortcut.empty() ? "null" : ("\"" + shortcut + "\"").c_str(),
        has_ia2 ? "true" : "false");
    out += buf;

    // Add IA2-specific fields if available
    if (has_ia2) {
        char ia2_buf[2048];
        snprintf(ia2_buf, sizeof(ia2_buf),
            ",\"ia2_states\":%ld,\"ia2_unique_id\":%ld",
            ia2_states, ia2_unique_id);
        out += ia2_buf;

        if (!ia2_attributes.empty()) {
            out += ",\"ia2_attributes\":\"";
            out += ia2_attributes;
            out += "\"";
        } else {
            out += ",\"ia2_attributes\":null";
        }
    }

    if (ia2) ia2->Release();

    // Children
    out += ",\"children\":[";
    if (depth > 1 && child_id.vt == VT_I4 && child_id.lVal == CHILDID_SELF) {
        long child_count = 0;
        hr = acc->get_accChildCount(&child_count);

        if (SUCCEEDED(hr) && child_count > 0) {
            long obtained = 0;
            std::vector<VARIANT> children(child_count);
            for (long i = 0; i < child_count; i++) {
                VariantInit(&children[i]);
            }

            hr = AccessibleChildren(acc, 0, child_count, children.data(), &obtained);

            if (SUCCEEDED(hr)) {
                bool first = true;
                for (long i = 0; i < obtained; i++) {
                    if (children[i].vt == VT_DISPATCH && children[i].pdispVal) {
                        IAccessible* child_acc = NULL;
                        hr = children[i].pdispVal->QueryInterface(
                            IID_IAccessible, (void**)&child_acc);
                        if (SUCCEEDED(hr) && child_acc) {
                            if (!first) out += ",";
                            first = false;
                            VARIANT self;
                            self.vt = VT_I4;
                            self.lVal = CHILDID_SELF;
                            build_ia2_json(child_acc, self, depth - 1,
                                          out, count, id_counter);
                            child_acc->Release();
                        }
                    } else if (children[i].vt == VT_I4) {
                        if (!first) out += ",";
                        first = false;
                        build_ia2_json(acc, children[i], depth - 1,
                                      out, count, id_counter);
                    }
                    VariantClear(&children[i]);
                }
            } else {
                for (long i = 0; i < child_count; i++) {
                    VariantClear(&children[i]);
                }
            }
        }
    }
    out += "]}";
}

extern "C" {

NATURO_API int naturo_ia2_get_element_tree(uintptr_t hwnd, int depth,
                                            char* result_json, int buf_size) {
    if (!result_json || buf_size <= 0) return -1;
    // Honor the caller's depth up to a generous bound (matches JAB/UIA and the
    // CLI's --depth max). The old cap of 10 silently ignored any larger --depth.
    if (depth < 1) depth = 1;
    if (depth > 50) depth = 50;

    HWND target = (HWND)hwnd;
    if (!target) {
        target = GetForegroundWindow();
        if (!target) return -2;
    }

    // Get root IAccessible
    IAccessible* acc = NULL;
    HRESULT hr = AccessibleObjectFromWindow(
        target, OBJID_CLIENT, IID_IAccessible, (void**)&acc);
    if (FAILED(hr) || !acc) return -2;

    // Verify IA2 is available on the root element
    IAccessible2* root_ia2 = ia2_from_accessible(acc);
    if (!root_ia2) {
        acc->Release();
        return -5;  // IA2 not supported by this application
    }
    root_ia2->Release();

    std::string json;
    json.reserve(16384);
    int count = 0;
    int id_counter = 0;

    VARIANT self;
    self.vt = VT_I4;
    self.lVal = CHILDID_SELF;
    build_ia2_json(acc, self, depth, json, count, id_counter);

    acc->Release();

    if ((int)json.size() + 1 > buf_size) {
        if (buf_size >= 4) {
            int needed = (int)json.size() + 1;
            memcpy(result_json, &needed, 4);
        }
        return -4;
    }

    memcpy(result_json, json.c_str(), json.size() + 1);
    return count;
}

NATURO_API int naturo_ia2_find_element(uintptr_t hwnd, const char* role,
                                        const char* name,
                                        char* result_json, int buf_size) {
    if (!result_json || buf_size <= 0) return -1;
    if (!role && !name) return -1;

    HWND target = (HWND)hwnd;
    if (!target) {
        target = GetForegroundWindow();
        if (!target) return -2;
    }

    IAccessible* root_acc = NULL;
    HRESULT hr = AccessibleObjectFromWindow(
        target, OBJID_CLIENT, IID_IAccessible, (void**)&root_acc);
    if (FAILED(hr) || !root_acc) return -2;

    // Verify IA2 availability
    IAccessible2* root_ia2 = ia2_from_accessible(root_acc);
    if (!root_ia2) {
        root_acc->Release();
        return -5;
    }
    root_ia2->Release();

    // Convert name to wide string for comparison
    wchar_t* name_wide = NULL;
    if (name) {
        int len = MultiByteToWideChar(CP_UTF8, 0, name, -1, NULL, 0);
        name_wide = new wchar_t[len];
        MultiByteToWideChar(CP_UTF8, 0, name, -1, name_wide, len);
    }

    // BFS search
    struct SearchItem {
        IAccessible* acc;
        VARIANT child_id;
    };

    std::vector<SearchItem> queue;
    VARIANT self;
    self.vt = VT_I4;
    self.lVal = CHILDID_SELF;
    root_acc->AddRef();
    queue.push_back({root_acc, self});

    IAccessible* found_acc = NULL;
    VARIANT found_child;
    VariantInit(&found_child);
    bool found = false;

    while (!queue.empty() && !found) {
        SearchItem current = queue.front();
        queue.erase(queue.begin());

        // Check role — use IA2 extended role if available
        long check_role = 0;
        IAccessible2* elem_ia2 = NULL;
        if (current.child_id.vt == VT_I4 && current.child_id.lVal == CHILDID_SELF) {
            elem_ia2 = ia2_from_accessible(current.acc);
        }

        if (elem_ia2) {
            long r = 0;
            if (SUCCEEDED(elem_ia2->role(&r))) {
                check_role = r;
            }
        } else {
            VARIANT role_var;
            VariantInit(&role_var);
            hr = current.acc->get_accRole(current.child_id, &role_var);
            if (SUCCEEDED(hr) && role_var.vt == VT_I4) {
                check_role = role_var.lVal;
            }
            VariantClear(&role_var);
        }

        bool role_match = true;
        if (role) {
            const char* cur_role_str = ia2_role_to_string(check_role);
            role_match = (_stricmp(cur_role_str, role) == 0);
        }

        if (elem_ia2) elem_ia2->Release();

        bool name_match = true;
        if (name_wide) {
            BSTR cur_name = NULL;
            hr = current.acc->get_accName(current.child_id, &cur_name);
            if (SUCCEEDED(hr) && cur_name) {
                name_match = (_wcsicmp(cur_name, name_wide) == 0);
                SysFreeString(cur_name);
            } else {
                name_match = false;
            }
        }

        if (role_match && name_match) {
            found_acc = current.acc;
            found_acc->AddRef();
            found_child = current.child_id;
            found = true;
        }

        // Enumerate children for BFS
        if (!found && current.child_id.vt == VT_I4 &&
            current.child_id.lVal == CHILDID_SELF) {
            long child_count = 0;
            hr = current.acc->get_accChildCount(&child_count);
            if (SUCCEEDED(hr) && child_count > 0) {
                long obtained = 0;
                std::vector<VARIANT> children(child_count);
                for (long i = 0; i < child_count; i++) {
                    VariantInit(&children[i]);
                }

                hr = AccessibleChildren(current.acc, 0, child_count,
                                        children.data(), &obtained);
                if (SUCCEEDED(hr)) {
                    for (long i = 0; i < obtained; i++) {
                        if (children[i].vt == VT_DISPATCH && children[i].pdispVal) {
                            IAccessible* child_acc = NULL;
                            hr = children[i].pdispVal->QueryInterface(
                                IID_IAccessible, (void**)&child_acc);
                            if (SUCCEEDED(hr) && child_acc) {
                                VARIANT cs;
                                cs.vt = VT_I4;
                                cs.lVal = CHILDID_SELF;
                                queue.push_back({child_acc, cs});
                            }
                        } else if (children[i].vt == VT_I4) {
                            current.acc->AddRef();
                            queue.push_back({current.acc, children[i]});
                            continue;
                        }
                        VariantClear(&children[i]);
                    }
                } else {
                    for (long i = 0; i < child_count; i++) {
                        VariantClear(&children[i]);
                    }
                }
            }
        }

        current.acc->Release();
    }

    // Cleanup remaining queue
    for (auto& item : queue) {
        item.acc->Release();
    }

    delete[] name_wide;

    if (!found) {
        root_acc->Release();
        return 1;  // Not found
    }

    // Build JSON for found element
    std::string json;
    json.reserve(2048);
    int count = 0;
    int id_counter = 0;
    build_ia2_json(found_acc, found_child, 1, json, count, id_counter);

    found_acc->Release();
    root_acc->Release();

    if ((int)json.size() + 1 > buf_size) {
        if (buf_size >= 4) {
            int needed = (int)json.size() + 1;
            memcpy(result_json, &needed, 4);
        }
        return -4;
    }

    memcpy(result_json, json.c_str(), json.size() + 1);
    return 0;
}

NATURO_API int naturo_ia2_check_support(uintptr_t hwnd) {
    HWND target = (HWND)hwnd;
    if (!target) {
        target = GetForegroundWindow();
        if (!target) return -2;
    }

    IAccessible* acc = NULL;
    HRESULT hr = AccessibleObjectFromWindow(
        target, OBJID_CLIENT, IID_IAccessible, (void**)&acc);
    if (FAILED(hr) || !acc) return -2;

    IAccessible2* ia2 = ia2_from_accessible(acc);
    acc->Release();

    if (ia2) {
        ia2->Release();
        return 1;  // IA2 supported
    }
    return 0;  // IA2 not supported
}

} // extern "C"

#else
// Non-Windows stubs

#include "naturo/exports.h"
#include <cstring>

extern "C" {

NATURO_API int naturo_ia2_get_element_tree(uintptr_t hwnd, int depth,
                                            char* result_json, int buf_size) {
    (void)hwnd;
    (void)depth;
    if (!result_json || buf_size < 3) return -1;
    memcpy(result_json, "{}", 3);
    return -2;
}

NATURO_API int naturo_ia2_find_element(uintptr_t hwnd, const char* role,
                                        const char* name,
                                        char* result_json, int buf_size) {
    (void)hwnd;
    (void)role;
    (void)name;
    (void)result_json;
    (void)buf_size;
    return -2;
}

NATURO_API int naturo_ia2_check_support(uintptr_t hwnd) {
    (void)hwnd;
    return -2;
}

} // extern "C"

#endif // _WIN32
