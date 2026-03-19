/**
 * @file element.cpp
 * @brief UI element tree inspection using Windows UIAutomation COM API.
 *
 * Walks the UIAutomation tree to build a JSON representation of UI elements.
 * Uses IUIAutomation, IUIAutomationElement, and IUIAutomationTreeWalker.
 */

#ifdef _WIN32

#include "naturo/exports.h"
#include <windows.h>
#include <uiautomation.h>
#include <cstdio>
#include <cstring>
#include <string>
#include <atomic>

/**
 * @brief Escape a string for safe JSON embedding.
 */
static std::string json_escape(const wchar_t* s) {
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
            // Encode non-ASCII as \\uXXXX
            char buf[8];
            snprintf(buf, sizeof(buf), "\\u%04x", (unsigned)*p);
            out += buf;
        }
    }
    return out;
}

/**
 * @brief Map UIAutomation ControlType ID to a human-readable role string.
 * @param type The UIA control type ID.
 * @return Role name string (e.g., "Button", "Edit").
 */
static const char* control_type_to_role(CONTROLTYPEID type) {
    switch (type) {
        case UIA_ButtonControlTypeId:       return "Button";
        case UIA_CalendarControlTypeId:     return "Calendar";
        case UIA_CheckBoxControlTypeId:     return "CheckBox";
        case UIA_ComboBoxControlTypeId:     return "ComboBox";
        case UIA_EditControlTypeId:         return "Edit";
        case UIA_HyperlinkControlTypeId:    return "Hyperlink";
        case UIA_ImageControlTypeId:        return "Image";
        case UIA_ListItemControlTypeId:     return "ListItem";
        case UIA_ListControlTypeId:         return "List";
        case UIA_MenuControlTypeId:         return "Menu";
        case UIA_MenuBarControlTypeId:      return "MenuBar";
        case UIA_MenuItemControlTypeId:     return "MenuItem";
        case UIA_ProgressBarControlTypeId:  return "ProgressBar";
        case UIA_RadioButtonControlTypeId:  return "RadioButton";
        case UIA_ScrollBarControlTypeId:    return "ScrollBar";
        case UIA_SliderControlTypeId:       return "Slider";
        case UIA_SpinnerControlTypeId:      return "Spinner";
        case UIA_StatusBarControlTypeId:    return "StatusBar";
        case UIA_TabControlTypeId:          return "Tab";
        case UIA_TabItemControlTypeId:      return "TabItem";
        case UIA_TextControlTypeId:         return "Text";
        case UIA_ToolBarControlTypeId:      return "ToolBar";
        case UIA_ToolTipControlTypeId:      return "ToolTip";
        case UIA_TreeControlTypeId:         return "Tree";
        case UIA_TreeItemControlTypeId:     return "TreeItem";
        case UIA_CustomControlTypeId:       return "Custom";
        case UIA_GroupControlTypeId:        return "Group";
        case UIA_ThumbControlTypeId:        return "Thumb";
        case UIA_DataGridControlTypeId:     return "DataGrid";
        case UIA_DataItemControlTypeId:     return "DataItem";
        case UIA_DocumentControlTypeId:     return "Document";
        case UIA_SplitButtonControlTypeId:  return "SplitButton";
        case UIA_WindowControlTypeId:       return "Window";
        case UIA_PaneControlTypeId:         return "Pane";
        case UIA_HeaderControlTypeId:       return "Header";
        case UIA_HeaderItemControlTypeId:   return "HeaderItem";
        case UIA_TableControlTypeId:        return "Table";
        case UIA_TitleBarControlTypeId:     return "TitleBar";
        case UIA_SeparatorControlTypeId:    return "Separator";
        default:                            return "Unknown";
    }
}

/**
 * @brief Recursively build a JSON representation of a UI element and its children.
 * @param walker The UIAutomation tree walker.
 * @param element The current element.
 * @param depth Remaining depth to traverse.
 * @param out Output string to append JSON to.
 * @param count Running count of elements processed.
 */
static void build_element_json(IUIAutomationTreeWalker* walker,
                                IUIAutomationElement* element,
                                int depth, std::string& out,
                                int& count) {
    if (!element) return;

    count++;

    // Get element properties
    BSTR name_bstr = NULL;
    element->get_CurrentName(&name_bstr);
    std::string name = name_bstr ? json_escape(name_bstr) : "";
    if (name_bstr) SysFreeString(name_bstr);

    CONTROLTYPEID control_type = 0;
    element->get_CurrentControlType(&control_type);
    const char* role = control_type_to_role(control_type);

    // Get automation ID as element id
    BSTR auto_id_bstr = NULL;
    element->get_CurrentAutomationId(&auto_id_bstr);
    std::string auto_id = auto_id_bstr ? json_escape(auto_id_bstr) : "";
    if (auto_id_bstr) SysFreeString(auto_id_bstr);

    // Get bounding rectangle
    RECT rect = {0, 0, 0, 0};
    element->get_CurrentBoundingRectangle(&rect);

    // Build this element's JSON
    char buf[1024];
    snprintf(buf, sizeof(buf),
        "{\"id\":\"%s\",\"role\":\"%s\",\"name\":\"%s\",\"value\":null,"
        "\"x\":%ld,\"y\":%ld,\"width\":%ld,\"height\":%ld",
        auto_id.c_str(), role, name.c_str(),
        rect.left, rect.top,
        rect.right - rect.left,
        rect.bottom - rect.top);
    out += buf;

    // Children
    out += ",\"children\":[";
    if (depth > 1) {
        IUIAutomationElement* child = NULL;
        HRESULT hr = walker->GetFirstChildElement(element, &child);
        bool first = true;
        while (SUCCEEDED(hr) && child) {
            if (!first) out += ",";
            first = false;
            build_element_json(walker, child, depth - 1, out, count);

            IUIAutomationElement* next = NULL;
            hr = walker->GetNextSiblingElement(child, &next);
            child->Release();
            child = next;
        }
    }
    out += "]}";
}

extern "C" {

NATURO_API int naturo_get_element_tree(uintptr_t hwnd, int depth,
                                       char* result_json, int buf_size) {
    if (!result_json || buf_size <= 0) return -1;
    if (depth < 1) depth = 1;
    if (depth > 10) depth = 10;

    HWND target = (HWND)hwnd;
    if (!target) {
        target = GetForegroundWindow();
        if (!target) return -2;
    }

    IUIAutomation* uia = NULL;
    HRESULT hr = CoCreateInstance(__uuidof(CUIAutomation), NULL,
                                  CLSCTX_INPROC_SERVER, __uuidof(IUIAutomation),
                                  (void**)&uia);
    if (FAILED(hr) || !uia) return -2;

    IUIAutomationElement* root = NULL;
    hr = uia->ElementFromHandle(target, &root);
    if (FAILED(hr) || !root) {
        uia->Release();
        return -2;
    }

    IUIAutomationTreeWalker* walker = NULL;
    hr = uia->get_ControlViewWalker(&walker);
    if (FAILED(hr) || !walker) {
        root->Release();
        uia->Release();
        return -2;
    }

    std::string json;
    json.reserve(8192);
    int count = 0;
    build_element_json(walker, root, depth, json, count);

    walker->Release();
    root->Release();
    uia->Release();

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

NATURO_API int naturo_find_element(uintptr_t hwnd, const char* role,
                                    const char* name, char* result_json,
                                    int buf_size) {
    if (!result_json || buf_size <= 0) return -1;
    if (!role && !name) return -1;  // Must provide at least one filter

    HWND target = (HWND)hwnd;
    if (!target) {
        target = GetForegroundWindow();
        if (!target) return -2;
    }

    IUIAutomation* uia = NULL;
    HRESULT hr = CoCreateInstance(__uuidof(CUIAutomation), NULL,
                                  CLSCTX_INPROC_SERVER, __uuidof(IUIAutomation),
                                  (void**)&uia);
    if (FAILED(hr) || !uia) return -2;

    IUIAutomationElement* root = NULL;
    hr = uia->ElementFromHandle(target, &root);
    if (FAILED(hr) || !root) {
        uia->Release();
        return -2;
    }

    // Build search condition
    IUIAutomationCondition* condition = NULL;

    if (role && name) {
        // Find the control type ID for the role string
        // We search by name condition and then filter by role in results
        BSTR name_bstr = NULL;
        int name_len = MultiByteToWideChar(CP_UTF8, 0, name, -1, NULL, 0);
        wchar_t* name_wide = new wchar_t[name_len];
        MultiByteToWideChar(CP_UTF8, 0, name, -1, name_wide, name_len);
        name_bstr = SysAllocString(name_wide);
        delete[] name_wide;

        IUIAutomationCondition* name_cond = NULL;
        VARIANT var;
        var.vt = VT_BSTR;
        var.bstrVal = name_bstr;
        uia->CreatePropertyCondition(UIA_NamePropertyId, var, &name_cond);
        SysFreeString(name_bstr);

        condition = name_cond;
    } else if (name) {
        BSTR name_bstr = NULL;
        int name_len = MultiByteToWideChar(CP_UTF8, 0, name, -1, NULL, 0);
        wchar_t* name_wide = new wchar_t[name_len];
        MultiByteToWideChar(CP_UTF8, 0, name, -1, name_wide, name_len);
        name_bstr = SysAllocString(name_wide);
        delete[] name_wide;

        VARIANT var;
        var.vt = VT_BSTR;
        var.bstrVal = name_bstr;
        uia->CreatePropertyCondition(UIA_NamePropertyId, var, &condition);
        SysFreeString(name_bstr);
    } else {
        // role only — we search with TrueCondition and filter
        uia->CreateTrueCondition(&condition);
    }

    if (!condition) {
        root->Release();
        uia->Release();
        return -2;
    }

    IUIAutomationElement* found = NULL;
    hr = root->FindFirst(TreeScope_Descendants, condition, &found);
    condition->Release();

    if (FAILED(hr) || !found) {
        root->Release();
        uia->Release();
        return 1;  // Not found
    }

    // If role filter was specified, verify the match
    if (role) {
        CONTROLTYPEID ct = 0;
        found->get_CurrentControlType(&ct);
        const char* found_role = control_type_to_role(ct);
        if (_stricmp(found_role, role) != 0) {
            // Role doesn't match — need to search more thoroughly
            // For simplicity, search all descendants and filter
            IUIAutomationElementArray* all = NULL;
            IUIAutomationCondition* true_cond = NULL;
            uia->CreateTrueCondition(&true_cond);
            hr = root->FindAll(TreeScope_Descendants, true_cond, &all);
            true_cond->Release();
            found->Release();
            found = NULL;

            if (SUCCEEDED(hr) && all) {
                int length = 0;
                all->get_Length(&length);
                for (int i = 0; i < length; ++i) {
                    IUIAutomationElement* elem = NULL;
                    all->GetElement(i, &elem);
                    if (!elem) continue;

                    CONTROLTYPEID elem_ct = 0;
                    elem->get_CurrentControlType(&elem_ct);
                    const char* elem_role = control_type_to_role(elem_ct);

                    bool role_match = (_stricmp(elem_role, role) == 0);
                    bool name_match = true;

                    if (name) {
                        BSTR elem_name = NULL;
                        elem->get_CurrentName(&elem_name);
                        if (elem_name) {
                            // Convert to UTF-8 for comparison
                            int needed = WideCharToMultiByte(CP_UTF8, 0, elem_name, -1, NULL, 0, NULL, NULL);
                            char* utf8 = new char[needed];
                            WideCharToMultiByte(CP_UTF8, 0, elem_name, -1, utf8, needed, NULL, NULL);
                            name_match = (_stricmp(utf8, name) == 0);
                            delete[] utf8;
                            SysFreeString(elem_name);
                        } else {
                            name_match = false;
                        }
                    }

                    if (role_match && name_match) {
                        found = elem;  // Transfer ownership
                        break;
                    }
                    elem->Release();
                }
                all->Release();
            }
        }
    }

    if (!found) {
        root->Release();
        uia->Release();
        return 1;  // Not found
    }

    // Build JSON for the found element
    BSTR found_name_bstr = NULL;
    found->get_CurrentName(&found_name_bstr);
    std::string found_name = found_name_bstr ? json_escape(found_name_bstr) : "";
    if (found_name_bstr) SysFreeString(found_name_bstr);

    CONTROLTYPEID found_ct = 0;
    found->get_CurrentControlType(&found_ct);

    BSTR found_aid_bstr = NULL;
    found->get_CurrentAutomationId(&found_aid_bstr);
    std::string found_aid = found_aid_bstr ? json_escape(found_aid_bstr) : "";
    if (found_aid_bstr) SysFreeString(found_aid_bstr);

    RECT found_rect = {0, 0, 0, 0};
    found->get_CurrentBoundingRectangle(&found_rect);

    char buf[1024];
    snprintf(buf, sizeof(buf),
        "{\"id\":\"%s\",\"role\":\"%s\",\"name\":\"%s\",\"value\":null,"
        "\"x\":%ld,\"y\":%ld,\"width\":%ld,\"height\":%ld,\"children\":[]}",
        found_aid.c_str(),
        control_type_to_role(found_ct),
        found_name.c_str(),
        found_rect.left, found_rect.top,
        found_rect.right - found_rect.left,
        found_rect.bottom - found_rect.top);

    std::string json(buf);

    found->Release();
    root->Release();
    uia->Release();

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

NATURO_API int naturo_get_element_tree(uintptr_t hwnd, int depth,
                                       char* result_json, int buf_size) {
    (void)hwnd;
    (void)depth;
    if (!result_json || buf_size < 3) return -1;
    memcpy(result_json, "{}", 3);
    return -2;  // Not supported on this platform
}

NATURO_API int naturo_find_element(uintptr_t hwnd, const char* role,
                                    const char* name, char* result_json,
                                    int buf_size) {
    (void)hwnd;
    (void)role;
    (void)name;
    (void)result_json;
    (void)buf_size;
    return -2;  // Not supported on this platform
}

} // extern "C"

#endif // _WIN32
