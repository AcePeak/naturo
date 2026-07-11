/**
 * @file msaa.cpp
 * @brief UI element inspection via MSAA (Microsoft Active Accessibility).
 *
 * Provides IAccessible-based element tree traversal for legacy applications
 * that lack UIAutomation support (MFC, VB6, Delphi, Win32 native, etc.).
 *
 * Key differences from UIA (element.cpp):
 * - Uses IAccessible COM interface instead of IUIAutomationElement
 * - Role is numeric (ROLE_SYSTEM_*) rather than ControlType
 * - Elements can be identified by child ID (VARIANT) not just automation ID
 * - Better coverage for pre-Vista controls
 */

#ifdef _WIN32

#include "naturo/exports.h"
#include <windows.h>
#include <oleacc.h>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#pragma comment(lib, "oleacc.lib")

/**
 * @brief Escape a wide string for safe JSON embedding.
 */
static std::string msaa_json_escape(const wchar_t* s) {
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
            // Encode non-ASCII as \\uXXXX (supports BMP chars)
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
static std::string bstr_to_json(BSTR bstr) {
    if (!bstr) return "";
    std::string result = msaa_json_escape(bstr);
    SysFreeString(bstr);
    return result;
}

/**
 * @brief Map MSAA role constant to human-readable string.
 *
 * Returns the standard MSAA role name, matching Windows accessibility
 * role definitions. Roles that overlap with UIA use the same names
 * (e.g., "Button", "Edit") for consistency.
 */
static const char* msaa_role_to_string(long role) {
    switch (role) {
        case ROLE_SYSTEM_ALERT:         return "Alert";
        case ROLE_SYSTEM_ANIMATION:     return "Animation";
        case ROLE_SYSTEM_APPLICATION:   return "Application";
        case ROLE_SYSTEM_BORDER:        return "Border";
        case ROLE_SYSTEM_BUTTONDROPDOWN:    return "ButtonDropDown";
        case ROLE_SYSTEM_BUTTONDROPDOWNGRID: return "ButtonDropDownGrid";
        case ROLE_SYSTEM_BUTTONMENU:    return "ButtonMenu";
        case ROLE_SYSTEM_CARET:         return "Caret";
        case ROLE_SYSTEM_CELL:          return "Cell";
        case ROLE_SYSTEM_CHARACTER:     return "Character";
        case ROLE_SYSTEM_CHART:         return "Chart";
        case ROLE_SYSTEM_CHECKBUTTON:   return "CheckBox";
        case ROLE_SYSTEM_CLIENT:        return "Client";
        case ROLE_SYSTEM_CLOCK:         return "Clock";
        case ROLE_SYSTEM_COLUMN:        return "Column";
        case ROLE_SYSTEM_COLUMNHEADER:  return "ColumnHeader";
        case ROLE_SYSTEM_COMBOBOX:      return "ComboBox";
        case ROLE_SYSTEM_CURSOR:        return "Cursor";
        case ROLE_SYSTEM_DIAGRAM:       return "Diagram";
        case ROLE_SYSTEM_DIAL:          return "Dial";
        case ROLE_SYSTEM_DIALOG:        return "Dialog";
        case ROLE_SYSTEM_DOCUMENT:      return "Document";
        case ROLE_SYSTEM_DROPLIST:      return "DropList";
        case ROLE_SYSTEM_EQUATION:      return "Equation";
        case ROLE_SYSTEM_GRAPHIC:       return "Image";
        case ROLE_SYSTEM_GRIP:          return "Grip";
        case ROLE_SYSTEM_GROUPING:      return "Group";
        case ROLE_SYSTEM_HELPBALLOON:   return "HelpBalloon";
        case ROLE_SYSTEM_HOTKEYFIELD:   return "HotKeyField";
        case ROLE_SYSTEM_INDICATOR:     return "Indicator";
        case ROLE_SYSTEM_IPADDRESS:     return "IPAddress";
        case ROLE_SYSTEM_LINK:          return "Hyperlink";
        case ROLE_SYSTEM_LIST:          return "List";
        case ROLE_SYSTEM_LISTITEM:      return "ListItem";
        case ROLE_SYSTEM_MENUBAR:       return "MenuBar";
        case ROLE_SYSTEM_MENUITEM:      return "MenuItem";
        case ROLE_SYSTEM_MENUPOPUP:     return "Menu";
        case ROLE_SYSTEM_OUTLINE:       return "Tree";
        case ROLE_SYSTEM_OUTLINEBUTTON: return "TreeButton";
        case ROLE_SYSTEM_OUTLINEITEM:   return "TreeItem";
        case ROLE_SYSTEM_PAGETAB:       return "TabItem";
        case ROLE_SYSTEM_PAGETABLIST:   return "Tab";
        case ROLE_SYSTEM_PANE:          return "Pane";
        case ROLE_SYSTEM_PROGRESSBAR:   return "ProgressBar";
        case ROLE_SYSTEM_PROPERTYPAGE:  return "PropertyPage";
        case ROLE_SYSTEM_PUSHBUTTON:    return "Button";
        case ROLE_SYSTEM_RADIOBUTTON:   return "RadioButton";
        case ROLE_SYSTEM_ROW:           return "Row";
        case ROLE_SYSTEM_ROWHEADER:     return "RowHeader";
        case ROLE_SYSTEM_SCROLLBAR:     return "ScrollBar";
        case ROLE_SYSTEM_SEPARATOR:     return "Separator";
        case ROLE_SYSTEM_SLIDER:        return "Slider";
        case ROLE_SYSTEM_SOUND:         return "Sound";
        case ROLE_SYSTEM_SPINBUTTON:    return "Spinner";
        case ROLE_SYSTEM_SPLITBUTTON:   return "SplitButton";
        case ROLE_SYSTEM_STATICTEXT:    return "Text";
        case ROLE_SYSTEM_STATUSBAR:     return "StatusBar";
        case ROLE_SYSTEM_TABLE:         return "Table";
        case ROLE_SYSTEM_TEXT:          return "Edit";
        case ROLE_SYSTEM_TITLEBAR:      return "TitleBar";
        case ROLE_SYSTEM_TOOLBAR:       return "ToolBar";
        case ROLE_SYSTEM_TOOLTIP:       return "ToolTip";
        case ROLE_SYSTEM_WHITESPACE:    return "WhiteSpace";
        case ROLE_SYSTEM_WINDOW:        return "Window";
        default:                        return "Unknown";
    }
}

/**
 * @brief Get bounding rectangle for an accessible object.
 */
static bool msaa_get_location(IAccessible* acc, VARIANT child_id,
                               long* out_x, long* out_y,
                               long* out_w, long* out_h) {
    long x = 0, y = 0, w = 0, h = 0;
    HRESULT hr = acc->accLocation(&x, &y, &w, &h, child_id);
    if (SUCCEEDED(hr)) {
        *out_x = x;
        *out_y = y;
        *out_w = w;
        *out_h = h;
        return true;
    }
    *out_x = *out_y = *out_w = *out_h = 0;
    return false;
}

/**
 * @brief Recursively build JSON for an MSAA element tree.
 *
 * MSAA elements can be either:
 * 1. Full IAccessible objects (have their own IAccessible interface)
 * 2. Simple elements (child ID within parent IAccessible)
 *
 * This function handles both cases, creating a uniform JSON tree.
 *
 * @param acc       The IAccessible interface for this element.
 * @param child_id  VARIANT identifying this child (VT_I4 with CHILDID_SELF for root).
 * @param depth     Remaining depth to traverse.
 * @param out       Output string to append JSON to.
 * @param count     Running count of elements processed.
 * @param id_counter Running counter for generating element IDs.
 */
static void build_msaa_json(IAccessible* acc, VARIANT child_id,
                             int depth, std::string& out,
                             int& count, int& id_counter) {
    if (!acc) return;
    count++;

    // Get role
    VARIANT role_var;
    VariantInit(&role_var);
    HRESULT hr = acc->get_accRole(child_id, &role_var);
    const char* role_str = "Unknown";
    long role_num = 0;
    if (SUCCEEDED(hr) && role_var.vt == VT_I4) {
        role_num = role_var.lVal;
        role_str = msaa_role_to_string(role_num);
    }
    VariantClear(&role_var);

    // Get name
    BSTR name_bstr = NULL;
    hr = acc->get_accName(child_id, &name_bstr);
    std::string name = (SUCCEEDED(hr) && name_bstr) ? bstr_to_json(name_bstr) : "";
    // bstr_to_json already freed name_bstr

    // Get value
    BSTR value_bstr = NULL;
    hr = acc->get_accValue(child_id, &value_bstr);
    std::string value = (SUCCEEDED(hr) && value_bstr) ? bstr_to_json(value_bstr) : "";

    // Get keyboard shortcut
    BSTR shortcut_bstr = NULL;
    hr = acc->get_accKeyboardShortcut(child_id, &shortcut_bstr);
    std::string shortcut = (SUCCEEDED(hr) && shortcut_bstr) ? bstr_to_json(shortcut_bstr) : "";

    // Get state
    VARIANT state_var;
    VariantInit(&state_var);
    hr = acc->get_accState(child_id, &state_var);
    long state = 0;
    if (SUCCEEDED(hr) && state_var.vt == VT_I4) {
        state = state_var.lVal;
    }
    VariantClear(&state_var);

    // Get location
    long x = 0, y = 0, w = 0, h = 0;
    msaa_get_location(acc, child_id, &x, &y, &w, &h);

    // Generate element ID
    int elem_id = id_counter++;
    char id_buf[32];
    snprintf(id_buf, sizeof(id_buf), "m%d", elem_id);

    // Build JSON object
    char buf[2048];
    snprintf(buf, sizeof(buf),
        "{\"id\":\"%s\",\"role\":\"%s\",\"role_id\":%ld,\"name\":\"%s\","
        "\"value\":%s,"
        "\"x\":%ld,\"y\":%ld,\"width\":%ld,\"height\":%ld,"
        "\"state\":%ld,"
        "\"keyboard_shortcut\":%s,"
        "\"backend\":\"msaa\"",
        id_buf, role_str, role_num, name.c_str(),
        value.empty() ? "null" : ("\"" + value + "\"").c_str(),
        x, y, w, h,
        state,
        shortcut.empty() ? "null" : ("\"" + shortcut + "\"").c_str());
    out += buf;

    // Children
    out += ",\"children\":[";
    if (depth > 1 && child_id.vt == VT_I4 && child_id.lVal == CHILDID_SELF) {
        long child_count = 0;
        hr = acc->get_accChildCount(&child_count);

        if (SUCCEEDED(hr) && child_count > 0) {
            // Allocate array for AccessibleChildren
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
                        // Full IAccessible child
                        IAccessible* child_acc = NULL;
                        hr = children[i].pdispVal->QueryInterface(
                            IID_IAccessible, (void**)&child_acc);
                        if (SUCCEEDED(hr) && child_acc) {
                            if (!first) out += ",";
                            first = false;
                            VARIANT self;
                            self.vt = VT_I4;
                            self.lVal = CHILDID_SELF;
                            build_msaa_json(child_acc, self, depth - 1,
                                           out, count, id_counter);
                            child_acc->Release();
                        }
                    } else if (children[i].vt == VT_I4) {
                        // Simple element (child ID)
                        if (!first) out += ",";
                        first = false;
                        build_msaa_json(acc, children[i], depth - 1,
                                       out, count, id_counter);
                    }
                    VariantClear(&children[i]);
                }
            } else {
                // Cleanup on failure
                for (long i = 0; i < child_count; i++) {
                    VariantClear(&children[i]);
                }
            }
        }
    }
    out += "]}";
}

extern "C" {

NATURO_API int naturo_msaa_get_element_tree(uintptr_t hwnd, int depth,
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

    IAccessible* acc = NULL;
    HRESULT hr = AccessibleObjectFromWindow(
        target, OBJID_CLIENT, IID_IAccessible, (void**)&acc);
    if (FAILED(hr) || !acc) return -2;

    std::string json;
    json.reserve(8192);
    int count = 0;
    int id_counter = 0;

    VARIANT self;
    self.vt = VT_I4;
    self.lVal = CHILDID_SELF;
    build_msaa_json(acc, self, depth, json, count, id_counter);

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

NATURO_API int naturo_msaa_find_element(uintptr_t hwnd, const char* role,
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

    // Convert name to wide string for comparison
    wchar_t* name_wide = NULL;
    if (name) {
        int len = MultiByteToWideChar(CP_UTF8, 0, name, -1, NULL, 0);
        name_wide = new wchar_t[len];
        MultiByteToWideChar(CP_UTF8, 0, name, -1, name_wide, len);
    }

    // BFS search through MSAA tree
    struct SearchItem {
        IAccessible* acc;
        VARIANT child_id;
    };

    std::vector<SearchItem> queue;
    VARIANT self;
    self.vt = VT_I4;
    self.lVal = CHILDID_SELF;
    root_acc->AddRef();  // queue holds a reference
    queue.push_back({root_acc, self});

    IAccessible* found_acc = NULL;
    VARIANT found_child;
    VariantInit(&found_child);
    bool found = false;

    while (!queue.empty() && !found) {
        SearchItem current = queue.front();
        queue.erase(queue.begin());

        // Check current element
        VARIANT role_var;
        VariantInit(&role_var);
        hr = current.acc->get_accRole(current.child_id, &role_var);
        bool role_match = true;
        if (role && SUCCEEDED(hr) && role_var.vt == VT_I4) {
            const char* cur_role = msaa_role_to_string(role_var.lVal);
            role_match = (_stricmp(cur_role, role) == 0);
        }
        VariantClear(&role_var);

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

        // Enumerate children for BFS (only for CHILDID_SELF elements)
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
                            continue;  // Don't clear — stored in queue
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

    // Cleanup remaining queue items
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
    json.reserve(1024);
    int count = 0;
    int id_counter = 0;
    build_msaa_json(found_acc, found_child, 1, json, count, id_counter);

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

} // extern "C"

#else
// Non-Windows stubs

#include "naturo/exports.h"
#include <cstring>

extern "C" {

NATURO_API int naturo_msaa_get_element_tree(uintptr_t hwnd, int depth,
                                             char* result_json, int buf_size) {
    (void)hwnd;
    (void)depth;
    if (!result_json || buf_size < 3) return -1;
    memcpy(result_json, "{}", 3);
    return -2;
}

NATURO_API int naturo_msaa_find_element(uintptr_t hwnd, const char* role,
                                         const char* name,
                                         char* result_json, int buf_size) {
    (void)hwnd;
    (void)role;
    (void)name;
    (void)result_json;
    (void)buf_size;
    return -2;
}

} // extern "C"

#endif // _WIN32
