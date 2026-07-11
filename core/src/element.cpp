/**
 * @file element.cpp
 * @brief UI element tree inspection using Windows UIAutomation COM API.
 *
 * Walks the UIAutomation tree to build a JSON representation of UI elements.
 * Uses IUIAutomation, IUIAutomationElement, and IUIAutomationTreeWalker.
 *
 * Performance: Uses IUIAutomationCacheRequest to batch-fetch properties
 * (Name, ControlType, AutomationId, BoundingRectangle) in a single
 * cross-process COM call per element, reducing IPC overhead by ~4x.
 */

#ifdef _WIN32

#include "naturo/exports.h"
#include <windows.h>
#include <uiautomation.h>
#include <cstdio>
#include <cstring>
#include <climits>
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
 * @brief Read a UIA element's keyboard shortcut (AcceleratorKey, else AccessKey).
 *
 * The UIA backend exposes two related accessibility properties: AcceleratorKey
 * (the directly actionable invoke chord, e.g. "Ctrl+S") and AccessKey (the
 * navigation mnemonic, e.g. "Alt+F"). AcceleratorKey is preferred when present
 * because it is the shortcut a keyboard-only user actually presses to invoke the
 * element; AccessKey is the fallback for menu mnemonics that have no accelerator.
 * Returns an empty string when neither property is set — the common case for
 * plain controls — which callers serialize as JSON ``null`` (#886).
 *
 * @param element The UIA element to query.
 * @param use_cache Read pre-fetched cached properties (true) or live Current
 *                  properties (false). When true, the cache request must include
 *                  ``UIA_AcceleratorKeyPropertyId`` and ``UIA_AccessKeyPropertyId``.
 * @return JSON-escaped shortcut string, or "" when none is present.
 */
static std::string read_keyboard_shortcut(IUIAutomationElement* element,
                                           bool use_cache) {
    BSTR accelerator_bstr = NULL;
    if (use_cache) {
        element->get_CachedAcceleratorKey(&accelerator_bstr);
    } else {
        element->get_CurrentAcceleratorKey(&accelerator_bstr);
    }
    std::string shortcut;
    if (accelerator_bstr && SysStringLen(accelerator_bstr) > 0) {
        shortcut = json_escape(accelerator_bstr);
    }
    if (accelerator_bstr) SysFreeString(accelerator_bstr);

    if (shortcut.empty()) {
        BSTR access_bstr = NULL;
        if (use_cache) {
            element->get_CachedAccessKey(&access_bstr);
        } else {
            element->get_CurrentAccessKey(&access_bstr);
        }
        if (access_bstr && SysStringLen(access_bstr) > 0) {
            shortcut = json_escape(access_bstr);
        }
        if (access_bstr) SysFreeString(access_bstr);
    }
    return shortcut;
}

/**
 * @brief Append a ``"keyboard_shortcut"`` JSON field for the given shortcut.
 *
 * Emits ``,"keyboard_shortcut":null`` for an empty shortcut and
 * ``,"keyboard_shortcut":"<value>"`` otherwise, matching the MSAA/IA2 backends
 * which always emit the field. The value is assumed already JSON-escaped.
 *
 * @param shortcut JSON-escaped shortcut string (empty for none).
 * @param out Output string to append to.
 */
static void append_keyboard_shortcut_field(const std::string& shortcut,
                                           std::string& out) {
    out += ",\"keyboard_shortcut\":";
    if (shortcut.empty()) {
        out += "null";
    } else {
        out += "\"";
        out += shortcut;
        out += "\"";
    }
}

/**
 * @brief Read cached properties from a UIAutomation element and append JSON.
 *
 * Uses get_CachedXxx methods which read from the pre-fetched cache,
 * avoiding additional cross-process COM calls.
 *
 * @param element Element with cached properties.
 * @param out Output string to append JSON to.
 */
// Read a cached VT_BOOL property (pattern-availability etc.); false if absent.
static bool cached_bool(IUIAutomationElement* element, PROPERTYID pid) {
    VARIANT v;
    VariantInit(&v);
    bool result = false;
    if (SUCCEEDED(element->GetCachedPropertyValue(pid, &v)) && v.vt == VT_BOOL) {
        result = (v.boolVal != VARIANT_FALSE);
    }
    VariantClear(&v);
    return result;
}

static void append_element_json_cached(IUIAutomationElement* element,
                                        std::string& out) {
    // Read from cache (no IPC — properties already fetched in batch)
    BSTR name_bstr = NULL;
    HRESULT hr = element->get_CachedName(&name_bstr);
    std::string name;
    if (SUCCEEDED(hr) && name_bstr) {
        name = json_escape(name_bstr);
        SysFreeString(name_bstr);
    }

    CONTROLTYPEID control_type = 0;
    hr = element->get_CachedControlType(&control_type);
    if (FAILED(hr)) control_type = 0;
    const char* role = control_type_to_role(control_type);

    BSTR auto_id_bstr = NULL;
    hr = element->get_CachedAutomationId(&auto_id_bstr);
    std::string auto_id;
    if (SUCCEEDED(hr) && auto_id_bstr) {
        auto_id = json_escape(auto_id_bstr);
        SysFreeString(auto_id_bstr);
    }

    RECT rect = {0, 0, 0, 0};
    hr = element->get_CachedBoundingRectangle(&rect);
    if (FAILED(hr)) {
        rect = {0, 0, 0, 0};
    }

    char buf[1024];
    snprintf(buf, sizeof(buf),
        "{\"id\":\"%s\",\"role\":\"%s\",\"name\":\"%s\",\"value\":null,"
        "\"x\":%ld,\"y\":%ld,\"width\":%ld,\"height\":%ld",
        auto_id.c_str(), role, name.c_str(),
        rect.left, rect.top,
        rect.right - rect.left,
        rect.bottom - rect.top);
    out += buf;

    // (#886) Emit the keyboard shortcut so UIA elements expose the same
    // accessibility metadata as the MSAA/IA2 backends instead of always null.
    append_keyboard_shortcut_field(read_keyboard_shortcut(element, true), out);

    // True per-node capabilities from UIA pattern availability (faithful, not
    // role-guessed): readable = Value or Text pattern; editable = a writable
    // ValuePattern; actionable = Invoke or Toggle pattern.
    bool has_value = cached_bool(element, UIA_IsValuePatternAvailablePropertyId);
    bool has_text = cached_bool(element, UIA_IsTextPatternAvailablePropertyId);
    bool readonly = cached_bool(element, UIA_ValueIsReadOnlyPropertyId);
    bool has_invoke = cached_bool(element, UIA_IsInvokePatternAvailablePropertyId);
    bool has_toggle = cached_bool(element, UIA_IsTogglePatternAvailablePropertyId);
    out += (has_value || has_text) ? ",\"readable\":true" : ",\"readable\":false";
    out += (has_value && !readonly) ? ",\"editable\":true" : ",\"editable\":false";
    out += (has_invoke || has_toggle) ? ",\"actionable\":true" : ",\"actionable\":false";
}

/**
 * @brief Recursively build a JSON element tree using cached tree walking.
 *
 * Uses GetFirstChildElementBuildCache/GetNextSiblingElementBuildCache
 * to navigate the tree, fetching all properties in one COM call per
 * navigation step instead of separate calls for each property.
 *
 * @param walker The UIAutomation tree walker.
 * @param element The current element (must have cached properties).
 * @param cache_request The cache request for property batching.
 * @param depth Remaining depth to traverse.
 * @param out Output string to append JSON to.
 * @param count Running count of elements processed.
 */
static void build_element_json_cached(IUIAutomationTreeWalker* walker,
                                       IUIAutomationElement* element,
                                       IUIAutomationCacheRequest* cache_request,
                                       int depth, std::string& out,
                                       int& count) {
    if (!element) return;

    count++;
    append_element_json_cached(element, out);

    // Children
    out += ",\"children\":[";
    if (depth > 1) {
        IUIAutomationElement* child = NULL;
        HRESULT hr = walker->GetFirstChildElementBuildCache(
            element, cache_request, &child);
        bool first = true;
        while (SUCCEEDED(hr) && child) {
            if (!first) out += ",";
            first = false;
            build_element_json_cached(walker, child, cache_request,
                                       depth - 1, out, count);

            IUIAutomationElement* next = NULL;
            hr = walker->GetNextSiblingElementBuildCache(
                child, cache_request, &next);
            child->Release();
            child = next;
        }
    }
    out += "]}";
}

/**
 * @brief Fallback: build element JSON using Current (non-cached) properties.
 *
 * Used when CacheRequest creation fails (should not happen normally).
 */
static void build_element_json_current(IUIAutomationTreeWalker* walker,
                                        IUIAutomationElement* element,
                                        int depth, std::string& out,
                                        int& count) {
    if (!element) return;

    count++;

    BSTR name_bstr = NULL;
    element->get_CurrentName(&name_bstr);
    std::string name = name_bstr ? json_escape(name_bstr) : "";
    if (name_bstr) SysFreeString(name_bstr);

    CONTROLTYPEID control_type = 0;
    element->get_CurrentControlType(&control_type);
    const char* role = control_type_to_role(control_type);

    BSTR auto_id_bstr = NULL;
    element->get_CurrentAutomationId(&auto_id_bstr);
    std::string auto_id = auto_id_bstr ? json_escape(auto_id_bstr) : "";
    if (auto_id_bstr) SysFreeString(auto_id_bstr);

    RECT rect = {0, 0, 0, 0};
    element->get_CurrentBoundingRectangle(&rect);

    char buf[1024];
    snprintf(buf, sizeof(buf),
        "{\"id\":\"%s\",\"role\":\"%s\",\"name\":\"%s\",\"value\":null,"
        "\"x\":%ld,\"y\":%ld,\"width\":%ld,\"height\":%ld",
        auto_id.c_str(), role, name.c_str(),
        rect.left, rect.top,
        rect.right - rect.left,
        rect.bottom - rect.top);
    out += buf;

    // (#886) Emit the keyboard shortcut (live Current properties — this is the
    // fallback path used when the cache request could not be created).
    append_keyboard_shortcut_field(read_keyboard_shortcut(element, false), out);

    out += ",\"children\":[";
    if (depth > 1) {
        IUIAutomationElement* child = NULL;
        HRESULT hr = walker->GetFirstChildElement(element, &child);
        bool first = true;
        while (SUCCEEDED(hr) && child) {
            if (!first) out += ",";
            first = false;
            build_element_json_current(walker, child, depth - 1, out, count);

            IUIAutomationElement* next = NULL;
            hr = walker->GetNextSiblingElement(child, &next);
            child->Release();
            child = next;
        }
    }
    out += "]}";
}

extern "C" {

/**
 * @brief Create a CacheRequest for the standard element properties.
 *
 * Batches Name, ControlType, AutomationId, and BoundingRectangle
 * into a single fetch per element.
 *
 * @param uia The UIAutomation instance.
 * @param[out] cache_request Receives the created cache request.
 * @return S_OK on success, error HRESULT on failure.
 */
static HRESULT create_element_cache_request(
    IUIAutomation* uia, IUIAutomationCacheRequest** cache_request) {

    HRESULT hr = uia->CreateCacheRequest(cache_request);
    if (FAILED(hr) || !*cache_request) return hr;

    (*cache_request)->AddProperty(UIA_NamePropertyId);
    (*cache_request)->AddProperty(UIA_ControlTypePropertyId);
    (*cache_request)->AddProperty(UIA_AutomationIdPropertyId);
    (*cache_request)->AddProperty(UIA_BoundingRectanglePropertyId);
    // (#886) Keyboard shortcut sources — AcceleratorKey (e.g. "Ctrl+S") and
    // AccessKey (e.g. "Alt+F"); batched here so get_CachedAcceleratorKey/
    // get_CachedAccessKey resolve without extra cross-process COM calls.
    (*cache_request)->AddProperty(UIA_AcceleratorKeyPropertyId);
    (*cache_request)->AddProperty(UIA_AccessKeyPropertyId);
    // Per-node capability truth (readable/actionable/editable) — pattern
    // availability + ValuePattern read-only, batched into the cache so each node
    // reports what it actually supports without extra COM round-trips.
    (*cache_request)->AddProperty(UIA_IsValuePatternAvailablePropertyId);
    (*cache_request)->AddProperty(UIA_IsTextPatternAvailablePropertyId);
    (*cache_request)->AddProperty(UIA_IsInvokePatternAvailablePropertyId);
    (*cache_request)->AddProperty(UIA_IsTogglePatternAvailablePropertyId);
    (*cache_request)->AddProperty(UIA_ValueIsReadOnlyPropertyId);

    // Fetch direct children scope for tree walking
    (*cache_request)->put_TreeScope(TreeScope_Element);

    return S_OK;
}

NATURO_API int naturo_get_element_tree(uintptr_t hwnd, int depth,
                                       char* result_json, int buf_size) {
    if (!result_json || buf_size <= 0) return -1;
    // Honor the caller's depth up to a generous bound (matches the CLI's
    // --depth max). The old cap of 10 silently ignored any larger --depth, so
    // deeply-nested UIA trees (Electron/WebView DOM-as-UIA, complex WPF/WinForms,
    // UWP frames) were truncated with no signal.
    if (depth < 1) depth = 1;
    if (depth > 50) depth = 50;

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

    // Create CacheRequest for batch property fetching
    IUIAutomationCacheRequest* cache_request = NULL;
    hr = create_element_cache_request(uia, &cache_request);
    bool use_cache = SUCCEEDED(hr) && cache_request;

    IUIAutomationElement* root = NULL;
    if (use_cache) {
        // ElementFromHandleBuildCache: fetch root + its properties in one call
        hr = uia->ElementFromHandleBuildCache(target, cache_request, &root);
    } else {
        hr = uia->ElementFromHandle(target, &root);
    }
    if (FAILED(hr) || !root) {
        if (cache_request) cache_request->Release();
        uia->Release();
        return -2;
    }

    IUIAutomationTreeWalker* walker = NULL;
    hr = uia->get_ControlViewWalker(&walker);
    if (FAILED(hr) || !walker) {
        root->Release();
        if (cache_request) cache_request->Release();
        uia->Release();
        return -2;
    }

    std::string json;
    json.reserve(8192);
    int count = 0;

    if (use_cache) {
        build_element_json_cached(walker, root, cache_request, depth, json, count);
    } else {
        // Fallback to non-cached path
        build_element_json_current(walker, root, depth, json, count);
    }

    walker->Release();
    root->Release();
    if (cache_request) cache_request->Release();
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

    // Create CacheRequest for batch property fetching on found element
    IUIAutomationCacheRequest* cache_request = NULL;
    hr = create_element_cache_request(uia, &cache_request);
    bool use_cache = SUCCEEDED(hr) && cache_request;

    // Build search condition
    IUIAutomationCondition* condition = NULL;

    if (role && name) {
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
        uia->CreateTrueCondition(&condition);
    }

    if (!condition) {
        root->Release();
        if (cache_request) cache_request->Release();
        uia->Release();
        return -2;
    }

    IUIAutomationElement* found = NULL;
    if (use_cache) {
        // FindFirstBuildCache: find + fetch properties in one COM round-trip
        hr = root->FindFirstBuildCache(TreeScope_Descendants, condition,
                                        cache_request, &found);
    } else {
        hr = root->FindFirst(TreeScope_Descendants, condition, &found);
    }
    condition->Release();

    if (FAILED(hr) || !found) {
        root->Release();
        if (cache_request) cache_request->Release();
        uia->Release();
        return 1;  // Not found
    }

    // If role filter was specified, verify the match
    if (role) {
        CONTROLTYPEID ct = 0;
        if (use_cache) {
            found->get_CachedControlType(&ct);
        } else {
            found->get_CurrentControlType(&ct);
        }
        const char* found_role = control_type_to_role(ct);
        if (_stricmp(found_role, role) != 0) {
            // Role doesn't match — search all descendants and filter
            IUIAutomationElementArray* all = NULL;
            IUIAutomationCondition* true_cond = NULL;
            uia->CreateTrueCondition(&true_cond);

            if (use_cache) {
                hr = root->FindAllBuildCache(TreeScope_Descendants, true_cond,
                                              cache_request, &all);
            } else {
                hr = root->FindAll(TreeScope_Descendants, true_cond, &all);
            }
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
                    if (use_cache) {
                        elem->get_CachedControlType(&elem_ct);
                    } else {
                        elem->get_CurrentControlType(&elem_ct);
                    }
                    const char* elem_role = control_type_to_role(elem_ct);

                    bool role_match = (_stricmp(elem_role, role) == 0);
                    bool name_match = true;

                    if (name) {
                        BSTR elem_name = NULL;
                        if (use_cache) {
                            elem->get_CachedName(&elem_name);
                        } else {
                            elem->get_CurrentName(&elem_name);
                        }
                        if (elem_name) {
                            int needed = WideCharToMultiByte(CP_UTF8, 0, elem_name, -1,
                                                             NULL, 0, NULL, NULL);
                            char* utf8 = new char[needed];
                            WideCharToMultiByte(CP_UTF8, 0, elem_name, -1,
                                                utf8, needed, NULL, NULL);
                            name_match = (_stricmp(utf8, name) == 0);
                            delete[] utf8;
                            SysFreeString(elem_name);
                        } else {
                            name_match = false;
                        }
                    }

                    if (role_match && name_match) {
                        found = elem;
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
        if (cache_request) cache_request->Release();
        uia->Release();
        return 1;  // Not found
    }

    // Build JSON for the found element using cached properties
    BSTR found_name_bstr = NULL;
    if (use_cache) {
        found->get_CachedName(&found_name_bstr);
    } else {
        found->get_CurrentName(&found_name_bstr);
    }
    std::string found_name = found_name_bstr ? json_escape(found_name_bstr) : "";
    if (found_name_bstr) SysFreeString(found_name_bstr);

    CONTROLTYPEID found_ct = 0;
    if (use_cache) {
        found->get_CachedControlType(&found_ct);
    } else {
        found->get_CurrentControlType(&found_ct);
    }

    BSTR found_aid_bstr = NULL;
    if (use_cache) {
        found->get_CachedAutomationId(&found_aid_bstr);
    } else {
        found->get_CurrentAutomationId(&found_aid_bstr);
    }
    std::string found_aid = found_aid_bstr ? json_escape(found_aid_bstr) : "";
    if (found_aid_bstr) SysFreeString(found_aid_bstr);

    RECT found_rect = {0, 0, 0, 0};
    if (use_cache) {
        found->get_CachedBoundingRectangle(&found_rect);
    } else {
        found->get_CurrentBoundingRectangle(&found_rect);
    }

    char buf[1024];
    snprintf(buf, sizeof(buf),
        "{\"id\":\"%s\",\"role\":\"%s\",\"name\":\"%s\",\"value\":null,"
        "\"x\":%ld,\"y\":%ld,\"width\":%ld,\"height\":%ld",
        found_aid.c_str(),
        control_type_to_role(found_ct),
        found_name.c_str(),
        found_rect.left, found_rect.top,
        found_rect.right - found_rect.left,
        found_rect.bottom - found_rect.top);

    std::string json(buf);
    // (#886) Surface the keyboard shortcut on find results too, so
    // `naturo find` exposes the same accessibility metadata as `see`.
    append_keyboard_shortcut_field(read_keyboard_shortcut(found, use_cache), json);
    json += ",\"children\":[]}";

    found->Release();
    root->Release();
    if (cache_request) cache_request->Release();
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

/**
 * @brief Locate a UIA element by AutomationId, or by role+name fallback.
 *
 * @param uia       Initialized IUIAutomation instance.
 * @param root      Root element to search within.
 * @param automation_id  AutomationId string (UTF-8), or NULL.
 * @param role      Role filter (e.g. "Edit"), or NULL.
 * @param name      Name filter, or NULL.
 * @return Found element (caller must Release), or NULL.
 */
static IUIAutomationElement* find_element_by_id_or_role(
    IUIAutomation* uia, IUIAutomationElement* root,
    const char* automation_id, const char* role, const char* name,
    int hint_x, int hint_y)
{
    IUIAutomationElement* found = NULL;
    // A snapshot ref carries the exact element's screen point. When several
    // elements share the same role+name and no AutomationId (e.g. Windows
    // Terminal exposes two "命令提示符" Text peers — a tiny label and the full
    // buffer), a bare FindFirst grabs the wrong one. If a hint point is given,
    // prefer the match whose bounds contain it; fall back to the first match.
    const bool have_hint = (hint_x != INT_MIN && hint_y != INT_MIN);

    if (automation_id && automation_id[0]) {
        // Search by AutomationId
        int aid_len = MultiByteToWideChar(CP_UTF8, 0, automation_id, -1, NULL, 0);
        wchar_t* aid_wide = new wchar_t[aid_len];
        MultiByteToWideChar(CP_UTF8, 0, automation_id, -1, aid_wide, aid_len);
        BSTR aid_bstr = SysAllocString(aid_wide);
        delete[] aid_wide;

        VARIANT var;
        var.vt = VT_BSTR;
        var.bstrVal = aid_bstr;

        IUIAutomationCondition* cond = NULL;
        HRESULT hr = uia->CreatePropertyCondition(
            UIA_AutomationIdPropertyId, var, &cond);
        SysFreeString(aid_bstr);

        if (SUCCEEDED(hr) && cond) {
            // Try self first
            root->FindFirst(static_cast<TreeScope>(TreeScope_Element | TreeScope_Descendants),
                            cond, &found);
            cond->Release();
        }
    }

    if (!found && (role || name)) {
        // Fallback: search by role+name (brute-force descendants)
        IUIAutomationCondition* true_cond = NULL;
        uia->CreateTrueCondition(&true_cond);
        if (!true_cond) return NULL;

        IUIAutomationElementArray* all = NULL;
        HRESULT hr = root->FindAll(TreeScope_Descendants, true_cond, &all);
        true_cond->Release();

        if (SUCCEEDED(hr) && all) {
            int length = 0;
            all->get_Length(&length);
            for (int i = 0; i < length; ++i) {
                IUIAutomationElement* elem = NULL;
                all->GetElement(i, &elem);
                if (!elem) continue;

                bool match = true;

                if (role) {
                    CONTROLTYPEID ct = 0;
                    elem->get_CurrentControlType(&ct);
                    if (_stricmp(control_type_to_role(ct), role) != 0)
                        match = false;
                }

                if (match && name) {
                    BSTR n = NULL;
                    elem->get_CurrentName(&n);
                    if (n) {
                        int needed = WideCharToMultiByte(
                            CP_UTF8, 0, n, -1, NULL, 0, NULL, NULL);
                        char* utf8 = new char[needed];
                        WideCharToMultiByte(
                            CP_UTF8, 0, n, -1, utf8, needed, NULL, NULL);
                        if (_stricmp(utf8, name) != 0) match = false;
                        delete[] utf8;
                        SysFreeString(n);
                    } else {
                        match = false;
                    }
                }

                if (match) {
                    if (!have_hint) {
                        found = elem;       // no hint: first match wins (legacy)
                        break;
                    }
                    // With a hint, keep the first match as a fallback but prefer
                    // the one whose bounds contain the hint point.
                    RECT r = {0, 0, 0, 0};
                    elem->get_CurrentBoundingRectangle(&r);
                    bool contains = (hint_x >= r.left && hint_x < r.right &&
                                     hint_y >= r.top && hint_y < r.bottom);
                    if (contains) {
                        if (found) found->Release();
                        found = elem;       // exact hit — done
                        break;
                    }
                    if (!found) {
                        found = elem;       // remember first match, keep scanning
                        continue;           // (don't Release the one we kept)
                    }
                }
                elem->Release();
            }
            all->Release();
        }
    }

    return found;
}

/**
 * @brief Query UIA patterns on an element and build a value JSON response.
 *
 * Tries patterns in priority order: Value, Text, Toggle, Selection, RangeValue.
 */
NATURO_API int naturo_get_element_value(uintptr_t hwnd,
                                         const char* automation_id,
                                         const char* role_filter,
                                         const char* name_filter,
                                         int hint_x, int hint_y,
                                         char* result_json, int buf_size) {
    if (!result_json || buf_size <= 0) return -1;
    if (!automation_id && !role_filter && !name_filter) return -1;

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

    IUIAutomationElement* elem = find_element_by_id_or_role(
        uia, root, automation_id, role_filter, name_filter, hint_x, hint_y);

    if (!elem) {
        root->Release();
        uia->Release();
        return 1;  // Not found
    }

    // Gather basic info
    BSTR elem_name_bstr = NULL;
    elem->get_CurrentName(&elem_name_bstr);
    std::string elem_name = elem_name_bstr ? json_escape(elem_name_bstr) : "";
    if (elem_name_bstr) SysFreeString(elem_name_bstr);

    CONTROLTYPEID elem_ct = 0;
    elem->get_CurrentControlType(&elem_ct);
    const char* elem_role = control_type_to_role(elem_ct);

    BSTR elem_aid_bstr = NULL;
    elem->get_CurrentAutomationId(&elem_aid_bstr);
    std::string elem_aid = elem_aid_bstr ? json_escape(elem_aid_bstr) : "";
    if (elem_aid_bstr) SysFreeString(elem_aid_bstr);

    RECT elem_rect = {0, 0, 0, 0};
    elem->get_CurrentBoundingRectangle(&elem_rect);

    // Try UIA patterns to get value
    std::string value;
    std::string pattern_name = "null";
    bool has_value = false;

    // 0) TextPattern FIRST for text editors (Document/Edit). ValuePattern on a
    //    rich multi-line editor (Win11 Notepad's Document) returns only a partial,
    //    order-scrambled fragment, so read the FULL document text via TextPattern
    //    when the control is a text editor that supports it. Non-editor controls
    //    skip this (control-type gate); a plain Win32 Edit with no TextPattern
    //    falls through to ValuePattern unchanged.
    if (!has_value &&
        (elem_ct == UIA_DocumentControlTypeId || elem_ct == UIA_EditControlTypeId)) {
        IUnknown* pat_unk = NULL;
        hr = elem->GetCurrentPattern(UIA_TextPatternId, &pat_unk);
        if (SUCCEEDED(hr) && pat_unk) {
            IUIAutomationTextPattern* txp = NULL;
            hr = pat_unk->QueryInterface(
                __uuidof(IUIAutomationTextPattern), (void**)&txp);
            if (SUCCEEDED(hr) && txp) {
                IUIAutomationTextRange* range = NULL;
                hr = txp->get_DocumentRange(&range);
                if (SUCCEEDED(hr) && range) {
                    BSTR text = NULL;
                    hr = range->GetText(1048576, &text);  // 1MB for large docs (#374)
                    if (SUCCEEDED(hr) && text) {
                        value = json_escape(text);
                        SysFreeString(text);
                        has_value = true;
                        pattern_name = "\"TextPattern\"";
                    }
                    range->Release();
                }
                txp->Release();
            }
            pat_unk->Release();
        }
    }

    // 1) ValuePattern
    if (!has_value) {
        IUnknown* pat_unk = NULL;
        hr = elem->GetCurrentPattern(UIA_ValuePatternId, &pat_unk);
        if (SUCCEEDED(hr) && pat_unk) {
            IUIAutomationValuePattern* vp = NULL;
            hr = pat_unk->QueryInterface(__uuidof(IUIAutomationValuePattern),
                                          (void**)&vp);
            if (SUCCEEDED(hr) && vp) {
                BSTR val = NULL;
                hr = vp->get_CurrentValue(&val);
                if (SUCCEEDED(hr) && val) {
                    value = json_escape(val);
                    SysFreeString(val);
                    has_value = true;
                    pattern_name = "\"ValuePattern\"";
                }
                vp->Release();
            }
            pat_unk->Release();
        }
    }

    // 2) TogglePattern (checkboxes)
    if (!has_value) {
        IUnknown* pat_unk = NULL;
        hr = elem->GetCurrentPattern(UIA_TogglePatternId, &pat_unk);
        if (SUCCEEDED(hr) && pat_unk) {
            IUIAutomationTogglePattern* tp = NULL;
            hr = pat_unk->QueryInterface(__uuidof(IUIAutomationTogglePattern),
                                          (void**)&tp);
            if (SUCCEEDED(hr) && tp) {
                ToggleState state;
                hr = tp->get_CurrentToggleState(&state);
                if (SUCCEEDED(hr)) {
                    switch (state) {
                        case ToggleState_Off:
                            value = "Off";
                            break;
                        case ToggleState_On:
                            value = "On";
                            break;
                        case ToggleState_Indeterminate:
                            value = "Indeterminate";
                            break;
                    }
                    has_value = true;
                    pattern_name = "\"TogglePattern\"";
                }
                tp->Release();
            }
            pat_unk->Release();
        }
    }

    // 3) SelectionPattern (lists, combos)
    if (!has_value) {
        IUnknown* pat_unk = NULL;
        hr = elem->GetCurrentPattern(UIA_SelectionPatternId, &pat_unk);
        if (SUCCEEDED(hr) && pat_unk) {
            IUIAutomationSelectionPattern* sp = NULL;
            hr = pat_unk->QueryInterface(
                __uuidof(IUIAutomationSelectionPattern), (void**)&sp);
            if (SUCCEEDED(hr) && sp) {
                IUIAutomationElementArray* sel = NULL;
                hr = sp->GetCurrentSelection(&sel);
                if (SUCCEEDED(hr) && sel) {
                    int count = 0;
                    sel->get_Length(&count);
                    std::string items;
                    for (int i = 0; i < count; ++i) {
                        IUIAutomationElement* item = NULL;
                        sel->GetElement(i, &item);
                        if (item) {
                            BSTR n = NULL;
                            item->get_CurrentName(&n);
                            if (n) {
                                if (!items.empty()) items += ", ";
                                items += json_escape(n);
                                SysFreeString(n);
                            }
                            item->Release();
                        }
                    }
                    sel->Release();
                    if (!items.empty()) {
                        value = items;
                        has_value = true;
                        pattern_name = "\"SelectionPattern\"";
                    }
                }
                sp->Release();
            }
            pat_unk->Release();
        }
    }

    // 4) RangeValuePattern (sliders, progress bars)
    if (!has_value) {
        IUnknown* pat_unk = NULL;
        hr = elem->GetCurrentPattern(UIA_RangeValuePatternId, &pat_unk);
        if (SUCCEEDED(hr) && pat_unk) {
            IUIAutomationRangeValuePattern* rp = NULL;
            hr = pat_unk->QueryInterface(
                __uuidof(IUIAutomationRangeValuePattern), (void**)&rp);
            if (SUCCEEDED(hr) && rp) {
                double val = 0.0;
                hr = rp->get_CurrentValue(&val);
                if (SUCCEEDED(hr)) {
                    char num_buf[64];
                    snprintf(num_buf, sizeof(num_buf), "%.6g", val);
                    value = num_buf;
                    has_value = true;
                    pattern_name = "\"RangeValuePattern\"";
                }
                rp->Release();
            }
            pat_unk->Release();
        }
    }

    // 5) TextPattern (rich text — last because it's expensive)
    if (!has_value) {
        IUnknown* pat_unk = NULL;
        hr = elem->GetCurrentPattern(UIA_TextPatternId, &pat_unk);
        if (SUCCEEDED(hr) && pat_unk) {
            IUIAutomationTextPattern* txp = NULL;
            hr = pat_unk->QueryInterface(
                __uuidof(IUIAutomationTextPattern), (void**)&txp);
            if (SUCCEEDED(hr) && txp) {
                IUIAutomationTextRange* range = NULL;
                hr = txp->get_DocumentRange(&range);
                if (SUCCEEDED(hr) && range) {
                    BSTR text = NULL;
                    hr = range->GetText(1048576, &text);  // 1MB for large documents (#374)
                    if (SUCCEEDED(hr) && text) {
                        value = json_escape(text);
                        SysFreeString(text);
                        has_value = true;
                        pattern_name = "\"TextPattern\"";
                    }
                    range->Release();
                }
                txp->Release();
            }
            pat_unk->Release();
        }
    }

    // Build JSON response
    std::string json;
    json.reserve(1024);
    json += "{\"value\":";
    if (has_value) {
        json += "\"";
        json += value;
        json += "\"";
    } else {
        json += "null";
    }
    json += ",\"pattern\":";
    json += pattern_name;

    char meta[512];
    snprintf(meta, sizeof(meta),
        ",\"role\":\"%s\",\"name\":\"%s\",\"automation_id\":\"%s\""
        ",\"x\":%ld,\"y\":%ld,\"width\":%ld,\"height\":%ld}",
        elem_role, elem_name.c_str(), elem_aid.c_str(),
        elem_rect.left, elem_rect.top,
        elem_rect.right - elem_rect.left,
        elem_rect.bottom - elem_rect.top);
    json += meta;

    elem->Release();
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

NATURO_API int naturo_get_element_value(uintptr_t hwnd,
                                         const char* automation_id,
                                         const char* role,
                                         const char* name,
                                         int hint_x, int hint_y,
                                         char* result_json, int buf_size) {
    (void)hwnd;
    (void)automation_id;
    (void)role;
    (void)name;
    (void)hint_x;
    (void)hint_y;
    (void)result_json;
    (void)buf_size;
    return -2;  // Not supported on this platform
}

} // extern "C"

#endif // _WIN32
