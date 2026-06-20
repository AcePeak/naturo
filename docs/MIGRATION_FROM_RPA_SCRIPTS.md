# Migration Guide: From RPA Scripts to naturo

This guide helps developers migrate existing automation scripts — built with DrissionPage,
Selenium, pywinauto, uiautomation, or raw CDP — to naturo. Every section shows real
production code patterns (anonymized from actual client projects) alongside the naturo
equivalent.

> **Target version**: naturo v0.3.2+
>
> **Audience**: RPA developers who have production scripts using DrissionPage / Selenium /
> pywinauto and want to consolidate into a single tool.

---

## Table of Contents

- [Why Migrate](#why-migrate)
- [Architecture Overview](#architecture-overview)
- [Quick Reference: API Mapping](#quick-reference-api-mapping)
- [Browser Automation](#browser-automation)
  - [Chrome Profile Management](#chrome-profile-management)
  - [Page Navigation](#page-navigation)
  - [Element Finding](#element-finding)
  - [Element Interaction](#element-interaction)
  - [Hover](#hover)
  - [Scroll](#scroll)
  - [Waiting](#waiting)
  - [Screenshots](#screenshots)
  - [Cookie Management](#cookie-management)
  - [JavaScript Execution](#javascript-execution)
  - [Tab Management](#tab-management)
  - [File Upload](#file-upload)
  - [File Download](#file-download)
  - [iframe Handling](#iframe-handling)
  - [Network Request Interception](#network-request-interception)
- [Desktop Automation](#desktop-automation)
  - [Window Finding](#window-finding)
  - [Desktop Element Interaction](#desktop-element-interaction)
  - [Keyboard Input](#keyboard-input)
- [Mixed Browser + Desktop Workflows](#mixed-browser--desktop-workflows)
- [Anti-Detection](#anti-detection)
- [Captcha Handling](#captcha-handling)
  - [Slider Captcha](#slider-captcha)
  - [Image Recognition Captcha](#image-recognition-captcha)
  - [Cookie Cycling Anti-Captcha](#cookie-cycling-anti-captcha)
- [Human-Like Input](#human-like-input)
  - [Mouse Movement Trajectories](#mouse-movement-trajectories)
  - [Typing Profiles](#typing-profiles)
- [Common Script Patterns](#common-script-patterns)
  - [Multi-Account Management](#multi-account-management)
  - [Data Scraping with Infinite Scroll](#data-scraping-with-infinite-scroll)
  - [Form Filling](#form-filling)
  - [Dropdown / Playlist Selection](#dropdown--playlist-selection)
- [Full Migration Example](#full-migration-example)
- [Troubleshooting](#troubleshooting)

---

## Why Migrate

| Pain Point | Before (multi-library) | After (naturo) |
|------------|----------------------|----------------|
| **Dependency count** | DrissionPage + pywinauto + pyautogui + psutil + ... | `pip install naturo` |
| **Browser + Desktop** | Separate libraries, separate APIs, separate mental models | One CLI, one SDK — `naturo browser` for web, `naturo find`/`naturo click` for desktop |
| **Anti-detection** | 5+ manual hacks per Selenium script | Stealth ON by default, zero config |
| **Captcha handling** | Copy-paste trajectory code across every project | `naturo drag --trajectory bezier --jitter 2 --overshoot 12` |
| **Profile management** | Manual Chrome `--user-data-dir` + port wrangling | `naturo browser profile create myaccount` |
| **Boilerplate** | LoggerClass, Utils, process management copied everywhere | naturo handles Chrome lifecycle, process cleanup, logging |

**The key advantage**: naturo is the only tool that does desktop + browser + AI vision in one CLI.
No competitor — not Playwright, not Selenium, not browseruse — can automate a WeChat desktop
window and a Chrome tab in the same script.

---

## Architecture Overview

```
                          naturo CLI / Python SDK
                                   |
                 +-----------------+-----------------+
                 |                 |                 |
          naturo browser     naturo find/click   naturo see (AI)
          (CDP protocol)     (UIA / MSAA / Win32) (Vision models)
                 |                 |                 |
          Chrome / Edge      Any desktop app    Screenshot + LLM
          Electron apps      Win32, WPF, UWP    Anthropic/OpenAI/
                             Qt, WinForms       Gemini/Ollama
```

All three engines work together. `naturo see --app feishu` returns UIA elements AND
CDP elements AND AI-detected elements in one unified tree. You don't need to know
which engine found which element — just use `naturo click e42`.

---

## Quick Reference: API Mapping

### DrissionPage to naturo

| DrissionPage | naturo CLI | naturo Python SDK |
|-------------|-----------|-------------------|
| `ChromiumOptions()` | `naturo browser launch` | `BrowserPage()` |
| `co.set_user_data_path(path)` | `--profile <name>` | `BrowserPage(profile="name")` |
| `co.set_local_port(9222)` | `--port 9222` | `BrowserPage(port=9222)` |
| `ChromiumPage(addr_or_opts=co)` | `naturo browser launch --profile x` | `BrowserPage(profile="x")` |
| `page.get(url)` | `naturo browser navigate <url>` | `page.navigate(url)` |
| `page.ele("xpath://...")` | `naturo browser find "xpath://..."` | `page.find("xpath://...")` |
| `page.eles("xpath://...")` | `naturo browser find "xpath://..." --all` | `page.find_all("xpath://...")` |
| `ele.click()` | `naturo browser click <selector>` | `element.click()` |
| `ele.click(by_js=True)` | `naturo browser click <selector> --js` | `element.click(js=True)` |
| `ele.input(text)` | `naturo browser type <selector> <text>` | `element.type(text)` |
| `ele.input(text, True)` | `naturo browser type <selector> <text> --clear-first` | `element.type(text, clear_first=True)` |
| `ele.text` | `naturo browser text <selector>` | `element.text` |
| `ele.attr("href")` | `naturo browser attr <selector> href` | `element.attr("href")` |
| `ele.hover().click()` | `naturo browser hover <sel> && naturo browser click <sel>` | `element.hover(); element.click()` |
| `ele.scroll.to_see()` | `naturo browser scroll --to-element <sel>` | `page.scroll_to_element(sel)` |
| `page.scroll.down(1000)` | `naturo browser scroll --by 1000` | `page.scroll_by(1000)` |
| `page.wait.doc_loaded()` | `naturo browser wait --load` | `page.wait_for_load()` |
| `page.get_screenshot(path)` | `naturo browser screenshot --path file.png` | `page.screenshot("file.png")` |
| `page.set.window.max()` | `naturo app maximize --app chrome` | N/A (use CLI) |
| `page.run_js_loaded(js)` | `naturo browser eval <js>` | `page.evaluate(js)` |
| `ele.click.to_upload(path)` | `naturo browser click <sel>` + `naturo dialog type <path>` + `naturo dialog accept` | see [File Upload](#file-upload) |

### Selenium to naturo

| Selenium | naturo CLI | naturo Python SDK |
|----------|-----------|-------------------|
| `webdriver.Chrome(options=opts)` | `naturo browser launch` | `BrowserPage()` |
| `WebDriverWait(d,t).until(EC.presence(...))` | `naturo browser wait <selector> --timeout <ms>` | `page.wait_for(selector, timeout=ms)` |
| `driver.find_element(By.XPATH, '...')` | `naturo browser find "xpath://..."` | `page.find("xpath://...")` |
| `driver.find_elements(By.XPATH, '...')` | `naturo browser find "xpath://..." --all` | `page.find_all("xpath://...")` |
| `element.send_keys(text)` | `naturo browser type <sel> <text>` | `element.type(text)` |
| `element.send_keys(Keys.CONTROL, 'v')` | `naturo hotkey ctrl+v` | N/A (use CLI) |
| `ActionChains(d).click_and_hold(e).move_by_offset(x,y).release()` | `naturo drag --from-element <sel> --offset-x <x>` | see [Slider Captcha](#slider-captcha) |
| `driver.execute_script(js)` | `naturo browser eval <js>` | `page.evaluate(js)` |
| `driver.execute_cdp_cmd(...)` | Built-in (stealth is default) | Built-in |
| `driver.get_cookies()` | `naturo browser cookies save --path f.json` | `page.cookies.save(path)` |
| `driver.add_cookie(c)` | `naturo browser cookies load --path f.json` | `page.cookies.load(path)` |
| `driver.switch_to.frame(el)` | `naturo browser frame-find <frame> <selector>` | `page.frame(selector).find(...)` |
| `options.set_capability('goog:loggingPrefs', ...)` | `naturo browser requests --pattern <glob>` | `page.network.capture_snapshot()` |

### pywinauto / uiautomation to naturo

| pywinauto / uiautomation | naturo CLI |
|--------------------------|-----------|
| `auto.WindowControl(searchDepth=1, Name="微信")` | `naturo find --name "微信" --control-type Window --app 微信` |
| `window.ButtonControl(Name="X").Click()` | `naturo find --name "X" --control-type Button --app 微信 \| naturo click` |
| `window.EditControl()` | `naturo find --control-type Edit --app 微信` |
| `window.TextControl(Name="X")` | `naturo find --name "X" --control-type Text --app 微信` |
| `window.PaneControl(ClassName="Chrome_WidgetWin_0")` | `naturo find --class-name "Chrome_WidgetWin_0" --app 微信` |
| `window.GroupControl(ClassName="QWidget")` | `naturo find --class-name "QWidget" --app 微信` |
| `window.Exists(timeout, 0)` | `naturo wait --element --name "X" --timeout <s>` |
| `window.SetTopmost(True); window.SetActive()` | `naturo app focus --app 微信` |
| `window.ShowWindow(9)` | `naturo app restore --app 微信` |
| `send_keys('^a')` | `naturo hotkey ctrl+a` |
| `send_keys('^v')` | `naturo hotkey ctrl+v` |
| `send_keys('{ENTER}')` | `naturo press enter` |
| `send_keys('{PGDN}')` | `naturo press pagedown` |
| `pyperclip.copy(text); send_keys('^v')` | `naturo type --paste "text"` |

---

## Browser Automation

### Chrome Profile Management

**Before** — from a Xiaohongshu scraping project (DrissionPage):
```python
# Every project manually manages Chrome profiles and ports
co = ChromiumOptions()
co.set_user_data_path(user_data_path)                      # user-data-dir path
co.set_browser_path(browser_path)                           # custom Chrome binary
co.set_local_port(local_port)                               # debugging port, e.g. 9222
co.set_pref("credentials_enable_service", False)            # suppress "save password" bubble
co.set_pref("download.prompt_for_download", False)          # suppress download prompt
co.set_argument("--hide-crash-restore-bubble")              # suppress crash restore dialog
page = WebPage(mode="d", chromium_options=co)
page.set.window.max()
```

Another variant — attach to a manually launched Chrome (from a Dianping scraping project):
```python
# Start Chrome as a separate process, then connect
os.system(fr'start {chrome_path} --remote-debugging-port={chrome_port}')
time.sleep(random.randint(2, 3))
co = ChromiumOptions().set_local_port(chrome_port)
page = ChromiumPage(addr_or_opts=co)
page.set.window.max()
```

**After** — naturo manages profiles, ports, and Chrome lifecycle:
```bash
# One-time setup: create a named profile
naturo browser profile create xhs-main

# Interactive login: opens Chrome so you can log in manually, then saves state
naturo browser profile setup xhs-main

# List all profiles with metadata
naturo browser profile list

# Launch with profile — port auto-assigned, no collisions, anti-detection on by default
naturo browser launch --profile xhs-main
naturo app maximize --app chrome
```

```python
from naturo.browser import ProfileManager, BrowserPage

# Create and manage profiles
pm = ProfileManager()
pm.create("xhs-main")
pm.list()  # [{"name": "xhs-main", "created": "...", "last_used": "...", "port": 19200}]

# Launch with profile — zero config needed
page = BrowserPage(profile="xhs-main")
```

Profiles are stored in `~/.naturo/browser/profiles/<name>/`. Each profile gets an
auto-assigned debugging port from range 19200-19299 — no more port collisions when
running multiple accounts simultaneously.

### Page Navigation

**Before** — from a Xiaohongshu scraping project (DrissionPage):
```python
page.get(target_url, retry=3, timeout=10)
```

**Before** — from a Dianping scraping project (DrissionPage, with manual wait):
```python
page.get("https://ecom.example.com/dashboard/evaluation/poi")
time.sleep(random.uniform(0.5, 1.5))
```

**Before** — from a Douyin project (Selenium, with manual retry on failure):
```python
page.get(target_url, retry=3, timeout=10)
sleep(1)
if not page.ele(self.ele_dict["发布时间和发布地点"]):
    page.refresh()
```

**After**:
```bash
naturo browser navigate "https://ecom.example.com/dashboard/evaluation/poi"
naturo browser wait --load --timeout 10000
```

```python
page.navigate("https://ecom.example.com/dashboard/evaluation/poi")
page.wait_for_load(timeout=10000)
```

### Element Finding

**Before** — from a Xiaohongshu project (DrissionPage, element dictionary pattern):
```python
class XhsScraper:
    ele_dict = {
        "博主昵称": "xpath://div[@class='author-wrapper']//a[@class='name']",
        "小红书号": "xpath://span[@class='user-id']",
        "性别": "xpath://use[@id='gender-icon']",
        "标签组": "xpath://div[@class='tag-list']//a[@class='tag']",
        "笔记链接": "xpath://a[@class='note-link']",
        "是否视频": "xpath://div[@class='play-icon']",
    }

    def scrape_detail(self):
        info = {}
        info["作者昵称"] = page.ele(self.ele_dict["博主昵称"]).text
        tt = page.ele(self.ele_dict["小红书号"]).text
        info["小红书号"] = tt.split("：")[-1]
        # Check optional element
        is_ele = page.ele(self.ele_dict["性别"])
        if is_ele:
            tt = is_ele.attr("xlink:href")
            if "#female" in tt:
                info["性别"] = "女"
        # Multiple elements
        is_eles = page.eles(self.ele_dict["标签组"])
        if is_eles and len(is_eles) > 1:
            for ele in is_eles[1:-1]:
                info.setdefault("标签", []).append(ele.text)
```

**After** — naturo auto-detects selector type (CSS/XPath/text):
```python
from naturo.browser import BrowserPage

page = BrowserPage(profile="xhs-main")

selectors = {
    "author_name": "xpath://div[@class='author-wrapper']//a[@class='name']",
    "user_id": "xpath://span[@class='user-id']",
    "gender_icon": "xpath://use[@id='gender-icon']",
    "tags": "xpath://div[@class='tag-list']//a[@class='tag']",
}

info = {}
info["author"] = page.find(selectors["author_name"]).text
raw_id = page.find(selectors["user_id"]).text
info["user_id"] = raw_id.split("：")[-1]

gender_el = page.find(selectors["gender_icon"])
if gender_el:
    href = gender_el.attr("xlink:href")
    if "#female" in href:
        info["gender"] = "female"

tags = page.find_all(selectors["tags"])
if tags and len(tags) > 1:
    info["tags"] = [el.text for el in tags[1:-1]]
```

```bash
# CLI equivalents
naturo browser text "xpath://div[@class='author-wrapper']//a[@class='name']"
naturo browser attr "xpath://use[@id='gender-icon']" "xlink:href"
naturo browser find "xpath://div[@class='tag-list']//a[@class='tag']" --all --json
```

### Element Interaction

**Before** — from a Dianping dashboard project (DrissionPage):
```python
# Click through tabs, fill search, read results
page.ele(self.ele_dict["点评评价"]).click()
time.sleep(random.uniform(0.5, 1.5))

page.ele(self.ele_dict["门店选择点击"]).click()
time.sleep(random.uniform(0.5, 1.5))

page.ele(self.ele_dict["查询门店输入框"]).input(item["门店名称"])
time.sleep(random.uniform(0.5, 1.5))

if page.ele(self.ele_dict["输入查询结果"]):
    page.ele(self.ele_dict["输入查询结果"]).click()
    # Poll until loading spinner disappears
    for try_i in range(300):
        time.sleep(random.uniform(0.5, 1.5))
        if not page.ele(self.ele_dict["正在加载"]):
            break
    page.ele(self.ele_dict["确定匹配结果"]).click()
    score = page.ele(self.ele_dict["店铺评分"]).text
```

**After**:
```bash
naturo browser click "xpath://div[@class='tab-review']"
naturo browser click "xpath://div[@class='store-selector']"
naturo browser type "xpath://input[@class='store-search']" "My Store Name" --clear-first
naturo browser wait "xpath://div[@class='search-result']" --state visible --timeout 5000
naturo browser click "xpath://div[@class='search-result']"
naturo browser wait "xpath://div[@class='loading-spinner']" --state hidden --timeout 30000
naturo browser click "xpath://button[@class='confirm-match']"
naturo browser text "xpath://span[@class='store-score']"
```

```python
page.find("xpath://div[@class='tab-review']").click()
page.find("xpath://div[@class='store-selector']").click()
page.find("xpath://input[@class='store-search']").type("My Store Name", clear_first=True)
page.wait_for("xpath://div[@class='search-result']", state="visible", timeout=5000)
page.find("xpath://div[@class='search-result']").click()
page.wait_for("xpath://div[@class='loading-spinner']", state="hidden", timeout=30000)
page.find("xpath://button[@class='confirm-match']").click()
score = page.find("xpath://span[@class='store-score']").text
```

Key improvements:
- No more `time.sleep(random.uniform(...))` — use proper element state waits
- No more polling loops — `naturo browser wait --state hidden` handles this
- One line per action instead of three (action + sleep + check)

### Hover

**Before** — from a YouTube publishing project (DrissionPage):
```python
# Hover then click — common for buttons that only appear on hover
self.page.ele(self.elements['上传视频']).hover().click(True)

# Hover to reveal dropdown, then click item
self.page.ele(self.elements['预定']).hover().click(True)
```

**After**:
```bash
naturo browser hover "xpath://button[@class='upload-video']"
naturo browser click "xpath://button[@class='upload-video']" --js

naturo browser hover "xpath://div[@class='schedule-dropdown']"
naturo browser click "xpath://div[@class='schedule-dropdown']" --js
```

```python
page.find("xpath://button[@class='upload-video']").hover()
page.find("xpath://button[@class='upload-video']").click(js=True)
```

### Scroll

**Before** — from a Xiaohongshu infinite-scroll project (DrissionPage):
```python
# Scroll the whole page down by pixels
page.scroll.down(1000)
time.sleep(1)
```

**Before** — from a YouTube publishing project (DrissionPage, scroll to specific element):
```python
element = self.page.ele(self.elements['标签'])
element.scroll.to_see()
element.click()

element = self.page.ele(self.elements['缩略图'])
element.scroll.to_center()
element.click.to_upload(img_path)
```

**Before** — from a WeChat Video Channel project (pywinauto, desktop scroll):
```python
send_keys('{PGDN}')
```

**After**:
```bash
# Scroll page down by pixels
naturo browser scroll --by 1000

# Scroll to specific element
naturo browser scroll --to-element "xpath://div[@class='tag-input']"

# Scroll to page bottom (infinite scroll)
naturo browser scroll --to-bottom

# Scroll to page top
naturo browser scroll --to-top

# Scroll within a scrollable container
naturo browser scroll --element ".scrollable-panel" --by 500

# Desktop scroll (Page Down)
naturo press pagedown
```

```python
page.scroll_by(1000)
page.scroll_to_element("xpath://div[@class='tag-input']")
page.scroll_to_bottom()
page.find(".scrollable-panel").scroll_by(500)
```

### Waiting

**Before** — from a Dianping project (DrissionPage, manual polling loop):
```python
page.ele(self.ele_dict["门店选择点击"]).click()
# Hand-written polling loop to wait for loading to finish
for try_i in range(300):
    time.sleep(random.uniform(0.5, 1.5))
    if not page.ele(self.ele_dict["正在加载"]):
        break
```

**Before** — from a Douyin project (Selenium, explicit wait):
```python
WebDriverWait(self.browser, 30, 0.5).until(
    EC.presence_of_element_located(self.elements["登录"])
)
WebDriverWait(self.browser, 4, 0.5).until(EC.title_contains('验证码'))
```

**Before** — the universal "pray it's enough" pattern (everywhere):
```python
time.sleep(random.uniform(0.5, 1.5))  # scattered throughout every script
```

**After** — event-driven waits, no guessing:
```bash
# Page lifecycle
naturo browser wait --load                          # Page fully loaded
naturo browser wait --dom-ready                     # DOM content loaded
naturo browser wait --network-idle                  # No network activity for 500ms
naturo browser wait --network-idle --time 1000      # Custom idle threshold

# Element state
naturo browser wait ".results" --timeout 10000               # Element exists in DOM
naturo browser wait ".results" --state visible --timeout 10000  # Element is visible
naturo browser wait ".spinner" --state hidden --timeout 30000   # Spinner gone
naturo browser wait ".old-item" --state detached              # Element removed from DOM

# Navigation
naturo browser wait --navigate --url-contains "success"

# JS condition
naturo browser wait --eval "window.dataLoaded === true" --timeout 5000
```

```python
page.wait_for_load()
page.wait_for_network_idle(time=500)
page.wait_for(".results", state="visible", timeout=10000)
page.wait_for(".spinner", state="hidden", timeout=30000)
page.wait_for_navigation(url_contains="success")
page.wait_for_eval("window.dataLoaded === true")
```

### Screenshots

**Before** — from a YouTube publishing project (DrissionPage):
```python
self.page.get_screenshot(img_path, '异常截图.png')
```

**Before** — from a Douyin QR login project (PIL desktop capture):
```python
from PIL import ImageGrab
pic = ImageGrab.grab()
pic.save(picture_path.joinpath(total_picture_name))
```

**After**:
```bash
# Browser page screenshot
naturo browser screenshot --path screenshot.png

# Screenshot a specific element (e.g. captcha region)
naturo browser screenshot --selector "#captcha-container" --path captcha.png

# Full scrollable page
naturo browser screenshot --path full.png --full-page

# Desktop window screenshot (any app, not just browser)
naturo capture --app 微信 --path wechat.png
```

```python
page.screenshot("screenshot.png")
page.screenshot("captcha.png", selector="#captcha-container")
```

### Cookie Management

**Before** — from a Douyin messaging project (Selenium, cookie cycling to bypass captcha):
```python
def process_slider_verify_code(self):
    for i in range(10):
        try:
            WebDriverWait(self.browser, 4, 0.5).until(EC.title_contains('验证码'))
        except:
            break
        cookies = self.browser.get_cookies()
        self.browser.delete_all_cookies()
        sleep(5)
        for cookie in cookies:
            self.browser.add_cookie(cookie)
        self.browser.execute_script('location.reload()')
        self.browser.implicitly_wait(10)
```

**Before** — from a live streaming project (delete cookie file directly):
```python
def delete_cookie(self):
    path = self.user_data_dir.joinpath(r'Default\Network\cookies')
    if os.path.exists(path):
        os.remove(path)
```

**After**:
```bash
naturo browser cookies save --path cookies.json
naturo browser cookies clear
naturo browser cookies load --path cookies.json
naturo browser navigate "https://www.douyin.com"
naturo browser cookies delete --domain ".douyin.com"
```

```python
page.cookies.save("cookies.json")
page.cookies.clear()
page.cookies.load("cookies.json")
page.cookies.delete(domain=".douyin.com")
```

### JavaScript Execution

**Before** — from a Douyin project (Selenium, JS click fallback):
```python
self.browser.execute_script('arguments[0].click()', self.get_element("登录", timeout=30))
```

**Before** — from a Douyin project (Selenium, page reload and state check):
```python
self.browser.execute_script('location.reload()')
state = self.browser.execute_script('return document.readyState')
```

**Before** — from a Xiaohongshu project (DrissionPage, zoom adjustment):
```python
page.run_js_loaded("document.body.style.zoom='0.85'")
```

**Before** — from a YouTube project (DrissionPage, JS click fallback):
```python
elements[0].click(by_js=True)
```

**After**:
```bash
# Evaluate and get result
naturo browser eval "document.readyState"
naturo browser eval "document.querySelectorAll('.item').length"

# Execute action
naturo browser eval "location.reload()"
naturo browser eval "document.body.style.zoom='0.85'"

# JS click (when regular click is intercepted)
naturo browser click "#login-btn" --js
```

```python
state = page.evaluate("document.readyState")
count = page.evaluate("document.querySelectorAll('.item').length")
page.evaluate("document.body.style.zoom='0.85'")
page.find("#login-btn").click(js=True)
```

### Tab Management

**Before** — from a YouTube publishing project (DrissionPage):
```python
browser = Chromium(addr_or_opts=co)
active_tab = browser.latest_tab
old_tab_count = len(browser.get_tabs())
# ... do work that opens a new tab ...
# Switch to the new tab
if len(browser.get_tabs()) > old_tab_count:
    new_tab = browser.latest_tab
```

**After**:
```bash
# List open tabs
naturo browser tabs

# Switch to a specific tab
naturo browser tab <tab-id>
```

```python
tabs = page.tabs()
page.switch_tab(tabs[-1]["id"])  # switch to newest tab
```

### File Upload

**Before** — from a YouTube publishing project (DrissionPage):
```python
# Upload video file
self.page.ele(self.elements['选择文件']).click.to_upload(video_path)

# Upload thumbnail — scroll to element first
element = self.page.ele(self.elements['缩略图'])
element.scroll.to_center()
element.click.to_upload(img_path)
```

**After** — naturo handles the native OS file dialog automatically:
```bash
# Click the upload button — triggers native file dialog
naturo browser click "xpath://input[@class='file-select']"
# Fill in the file path and confirm the dialog
naturo dialog type "/path/to/video.mp4"
naturo dialog accept
# Wait for upload to complete
naturo browser wait ".upload-progress-done" --state visible --timeout 60000

# Thumbnail upload — scroll to element first
naturo browser scroll --to-element "xpath://div[@class='thumbnail-upload']"
naturo browser click "xpath://div[@class='thumbnail-upload']"
naturo dialog type "/path/to/thumbnail.png"
naturo dialog accept
```

```python
page.scroll_to_element("xpath://div[@class='thumbnail-upload']")
page.find("xpath://div[@class='thumbnail-upload']").click()
# Native file dialog handled by naturo desktop automation
```

This is where naturo's browser + desktop integration shines — the file dialog is a
native OS window, not a browser element. Other tools need workarounds; naturo handles
it natively.

### File Download

**Before** — from various projects (DrissionPage, suppress download prompt):
```python
co.set_pref("download.prompt_for_download", False)
co.set_pref("download.default_directory", download_dir)
# ... click download button, then poll filesystem for the file ...
while not os.path.exists(expected_file):
    time.sleep(1)
```

**After**:
```bash
# Set download directory before triggering download
naturo browser download --dir /path/to/downloads

# Click download link
naturo browser click "#export-btn"

# Wait for download to complete — returns filename and path
naturo browser download --wait --timeout 30000
```

```python
page.set_download_dir("/path/to/downloads")
page.find("#export-btn").click()
download = page.wait_for_download(timeout=30000)
print(download.path)  # /path/to/downloads/report.xlsx
```

### iframe Handling

**Before** — from a live streaming login project (Selenium, captcha inside iframe):
```python
# Element dictionary defines iframe selector
elements = {
    "iframe": (By.XPATH, '//*[@id="loginForm-slide-container"]/iframe'),
    "slider": (By.XPATH, '//div[@class="secsdk-captcha-drag-icon"]'),
}

# Switch to iframe to interact with captcha
iframe = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located(elements["iframe"])
)
driver.switch_to.frame(iframe)

# Now interact with elements inside iframe
slider = driver.find_element(*elements["slider"])
# ... drag slider ...

# Switch back to main content
driver.switch_to.default_content()
```

**After** — naturo addresses each frame per command (a CSS selector, frame
`name`, or URL substring), so there is no stateful "switch / switch back":
```bash
# List every frame on the page (main frame + nested iframes)
naturo browser frames

# Find an element scoped to a specific iframe, identified by a CSS selector
# for the <iframe> element (the captcha lives inside the login iframe):
naturo browser frame-find "#loginForm-slide-container iframe" ".secsdk-captcha-drag-icon"
# ... drag slider ...

# Or address the frame by its name / URL instead of a selector:
naturo browser frame-find "captcha" "input" --by-name
naturo browser frame-eval "payment.example.com" "document.title" --by-url
```

```python
# page.frame() returns a BrowserFrame scoped to the iframe; find/find_all/
# evaluate run inside it. Identify the frame by selector=, name=, or url=.
frame = page.frame(selector="#loginForm-slide-container iframe")
slider = frame.find(".secsdk-captcha-drag-icon")
# ... drag slider ...

# Nested iframes chain via .frame() on the parent frame:
inner = frame.frame(name="captcha-level2")
inner.find("#deep-element")
```

### Network Request Interception

**Before** — from a live streaming data project (Selenium, performance log interception):
```python
# Enable performance logging to capture network requests
options.set_capability('goog:loggingPrefs', {"performance": "INFO"})

# Later, parse performance logs to extract API responses
logs = driver.get_log("performance")
for log in logs:
    message = json.loads(log["message"])
    if "Network.responseReceived" in message["message"]["method"]:
        url = message["message"]["params"]["response"]["url"]
        if "api/v1/live/data" in url:
            request_id = message["message"]["params"]["requestId"]
            body = driver.execute_cdp_cmd("Network.getResponseBody",
                                          {"requestId": request_id})
            data = json.loads(body["body"])
```

**After** — observe request metadata and intercept (block / mock) requests:
```bash
# Navigate to trigger the requests
naturo browser navigate "https://dashboard.example.com/live"

# List the requests the page made (URL, type, size, duration)
naturo browser requests
naturo browser requests --pattern "*/api/v1/*" --json

# Block unwanted requests (ads, analytics)
naturo browser intercept "*.doubleclick.net/*" --action abort
naturo browser intercept "*/analytics/*" --action abort

# Mock a response for matching requests
naturo browser intercept "*/api/v1/config*" --action fulfill \
    --body '{"debug": true}' --status 200
```

```python
# Observe the requests the page has made (metadata via the Performance API)
page.navigate("https://dashboard.example.com/live")
requests = page.network.capture_snapshot()
api_requests = page.network.find_requests("*/api/v1/*")

# Block unwanted requests
page.network.abort_pattern("*.doubleclick.net/*")

# Mock a response for matching requests
page.network.mock_response("*/api/v1/config*", body='{"debug": true}', status_code=200)
```

This replaces the boilerplate of enabling performance logging and parsing raw CDP
events from a log buffer: naturo manages the CDP subscription and exposes request
metadata and interception directly.

> **Not yet supported:** reading a captured response **body** (the Selenium
> `Network.getResponseBody` step shown above). `naturo browser requests` reports
> request *metadata* only (URL, type, size, timing); use `intercept --action
> fulfill` to supply a *mock* body. Capturing a real response body (await a
> response and parse its JSON, or stream responses via a callback) is tracked as
> a future enhancement — see
> [#1088](https://github.com/AcePeak/naturo/issues/1088).

---

## Desktop Automation

naturo's desktop automation uses UIA/MSAA/Win32 — the same engines that power
Windows Accessibility. No driver installation, no version matching, no webdriver at all.

### Window Finding

**Before** — from a WeChat Video Channel project (uiautomation):
```python
import uiautomation as auto

# Find main WeChat window
self.main_window = auto.WindowControl(searchDepth=1, Name="微信")
# Alternative: by class name
# self.main_window = auto.WindowControl(searchDepth=1, ClassName="mmui::MainWindow")

# Find embedded browser panel inside WeChat
qwidget = self.main_window.GroupControl(ClassName="QWidget")
self.wechat_ex_window = qwidget.PaneControl(ClassName="Chrome_WidgetWin_0")

# Window management
wechat_window.ShowWindow(9)   # SW_RESTORE
wechat_window.SetActive()
```

**After**:
```bash
# Find and focus WeChat
naturo app focus --app 微信

# Find the embedded browser panel inside WeChat
naturo find --class-name "Chrome_WidgetWin_0" --app 微信

# Wait for window to appear (up to 10 seconds)
naturo wait --element --name "微信" --timeout 10

# Restore minimized window
naturo app restore --app 微信
```

### Desktop Element Interaction

**Before** — from a WeChat Video Channel project (uiautomation):
```python
# Navigate to Video Channel tab
video_tab = self.wechat_ex_window.TextControl(Name="视频号")
video_tab.Click()

# Search for content
search_edit = self.wechat_ex_window.EditControl()
search_edit.Click()
pyperclip.copy(keyword)
send_keys('^a')  # Select all
send_keys('^v')  # Paste

# Click sort button
latest_button = self.wechat_ex_window.TextControl(Name="最新")
latest_button.Click()

# Window management during automation
wechat_window.ShowWindow(6)  # SW_MINIMIZE
```

**After**:
```bash
# Navigate to Video Channel tab
naturo find --name "视频号" --control-type Text --app 微信 | naturo click

# Search — naturo type --paste handles Chinese text natively
naturo find --control-type Edit --app 微信 | naturo click
naturo hotkey ctrl+a
naturo type --paste "$KEYWORD"

# Click sort button
naturo find --name "最新" --control-type Text --app 微信 | naturo click

# Window management
naturo app minimize --app 微信
```

Or use the `naturo see` + element ref workflow:
```bash
# See all elements in WeChat — shows numbered elements: e1, e2, e3...
naturo see --app 微信

# Click and type by reference
naturo click e15
naturo type e23 "message text"
```

### Keyboard Input

**Before** — from a WeChat Video Channel project (pywinauto + pyperclip):
```python
from pywinauto.keyboard import send_keys
import pyperclip

# Chinese text input: copy to clipboard, then paste
pyperclip.copy(keyword)
send_keys('^a')   # Ctrl+A select all
send_keys('^v')   # Ctrl+V paste

# Press Enter to submit
send_keys('{ENTER}')

# Page Down to scroll
send_keys('{PGDN}')

# Other shortcuts
send_keys('^c')   # Copy
send_keys('^z')   # Undo
```

**After**:
```bash
# Type Chinese text directly (--paste uses clipboard internally)
naturo type --paste "搜索关键词"

# Hotkey combinations
naturo hotkey ctrl+a
naturo hotkey ctrl+v
naturo hotkey ctrl+c
naturo hotkey ctrl+z

# Single key press
naturo press enter
naturo press pagedown
naturo press tab
naturo press escape

# Type with human-like delays
naturo type "search keyword" --profile human --wpm 80
```

---

## Mixed Browser + Desktop Workflows

This is naturo's killer feature. No other tool can do this.

**Before** — from a real project that scrapes Dianping (browser) and posts to WeChat Video
Channel (desktop). This requires three separate libraries with different APIs:
```python
from DrissionPage import ChromiumPage, ChromiumOptions
import uiautomation as auto
from pywinauto.keyboard import send_keys
import pyperclip

# === Part 1: Scrape Dianping (browser via DrissionPage) ===
co = ChromiumOptions()
co.set_user_data_path(user_data_path)
co.set_local_port(9533)
co.set_browser_path(browser_path)
page = ChromiumPage(addr_or_opts=co)
page.get("https://ecom.example.com/dashboard/evaluation/poi")
time.sleep(random.uniform(0.5, 1.5))

page.ele(self.ele_dict["点评评价"]).click()
time.sleep(random.uniform(0.5, 1.5))
page.ele(self.ele_dict["查询门店输入框"]).input(store_name)
time.sleep(random.uniform(0.5, 1.5))
page.ele(self.ele_dict["输入查询结果"]).click()
score = page.ele(self.ele_dict["店铺评分"]).text

# === Part 2: Post to WeChat Video Channel (desktop via uiautomation) ===
wechat = auto.WindowControl(searchDepth=1, Name="微信")
wechat.SetActive()
qwidget = wechat.GroupControl(ClassName="QWidget")
wechat_browser = qwidget.PaneControl(ClassName="Chrome_WidgetWin_0")
video_tab = wechat_browser.TextControl(Name="视频号")
video_tab.Click()
search_edit = wechat_browser.EditControl()
search_edit.Click()
pyperclip.copy(score)
send_keys('^v')
send_keys('{ENTER}')
```

**After** — one tool, one mental model, same result:
```bash
#!/bin/bash
# === Part 1: Scrape Dianping (browser) ===
naturo browser launch --profile dianping
naturo browser navigate "https://ecom.example.com/dashboard/evaluation/poi"
naturo browser wait --load

naturo browser click "xpath://div[@class='tab-review']"
naturo browser type "xpath://input[@class='store-search']" "My Store Name" --clear-first
naturo browser wait "xpath://div[@class='search-result']" --state visible --timeout 5000
naturo browser click "xpath://div[@class='search-result']"
naturo browser wait "xpath://div[@class='loading-spinner']" --state hidden --timeout 30000
SCORE=$(naturo browser text "xpath://span[@class='store-score']")

# === Part 2: Post to WeChat Video Channel (desktop) ===
naturo app focus --app 微信
naturo find --name "视频号" --control-type Text --app 微信 | naturo click
naturo find --control-type Edit --app 微信 | naturo click
naturo type --paste "$SCORE"
naturo press enter
```

No library imports, no driver version management, no context switching between APIs.
The browser CDP connection stays alive while you interact with the desktop.

---

## Anti-Detection

**naturo's browser automation has anti-detection ON by default.** You don't configure anything.

**Before** — from a Douyin messaging project (Selenium, 20+ lines of anti-detection):
```python
options = ChromeOptions()
options.binary_location = self.chrome_path
options.add_argument('--no-sandbox')
options.add_argument('--disable-gpu')
options.add_argument('--hide-scrollbars')
options.add_argument('--user-data-dir={}'.format(self.user_data_dir))
options.add_argument('--ignore-certificate-errors')
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...")
options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(service=ChromeService(self.driver_path), options=options)

# Still need to inject CDP command to mask webdriver property
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": """
        Object.defineProperty(navigator, 'webdriver', {
          get: () => undefined
        });
        """
})
driver.maximize_window()
driver.set_script_timeout(60 * 3)
driver.set_page_load_timeout(60 * 3)
```

**After** — naturo does all of this automatically:
```bash
naturo browser launch --profile myaccount
# That's it. All anti-detection is built-in:
# - navigator.webdriver = false
# - No automation Chrome flags
# - No "controlled by automated software" infobar
# - Standard Chrome User-Agent
# - cdc_ markers removed
```

```python
page = BrowserPage(profile="myaccount")  # stealth is the default
```

What naturo does automatically on every `browser launch`:
1. Connects via CDP natively (no WebDriver protocol = no `navigator.webdriver` flag)
2. Injects stealth scripts before any page loads:
   - `navigator.webdriver` → `false` / `undefined`
   - Removes `window.cdc_` and `document.$cdc_` DevTools markers
   - Overrides `navigator.permissions.query` for notifications
3. Launches Chrome with anti-detection flags:
   - `--disable-blink-features=AutomationControlled`
   - Excludes `enable-automation` switch
   - Suppresses "controlled by automated software" infobar
4. Uses standard Chrome User-Agent (no "Headless" marker)

To **disable** stealth for debugging:
```bash
naturo browser launch --profile myaccount --no-stealth
```

**Verify stealth**:
```bash
naturo browser stealth-check
# Checks bot.sannysoft.com, creepjs.com — reports PASS/WARN/FAIL per vector
```

---

## Captcha Handling

naturo provides the **primitives** to handle captchas. You bring the solver
(Chaojiying, ddddocr, or your own model). naturo does the rest.

### Slider Captcha

This is the most common captcha type (Douyin, Taobao, Bilibili). Every client project
has a copy-pasted trajectory generation algorithm.

**Before** — from a live streaming data project (Selenium + custom trajectory):
```python
def _get_tracks(distance):
    """4-phase acceleration model — copy-pasted into 10+ projects"""
    track = []
    mid1 = round(distance * random.uniform(0.1, 0.2))
    mid2 = round(distance * random.uniform(0.65, 0.76))
    mid3 = round(distance * random.uniform(0.84, 0.88))
    current, v, t = 0, 0, 0.2
    distance = round(distance)
    while current < distance:
        if current < mid1:
            a = random.randint(10, 15)
        elif current < mid2:
            a = random.randint(30, 40)
        elif current < mid3:
            a = -70
        else:
            a = random.randint(-25, -18)
        v0 = v
        v = v0 + a * t
        v = v if v >= 0 else 0
        move = v0 * t + 1 / 2 * a * (t ** 2)
        move = round(move if move >= 0 else 1)
        current += move
        track.append(move)
    back_tracks = []
    out_range = distance - current
    if out_range < -8:
        sub = int(out_range + 8)
        back_tracks = [-1, sub, -3, -1, -1, -1, -1]
    elif out_range < -2:
        sub = int(out_range + 3)
        back_tracks = [-1, -1, sub]
    return {'forward_tracks': track, 'back_tracks': back_tracks}

def _slider_action(driver, tracks, start_xpath):
    slider = wait.until(EC.element_to_be_clickable((By.XPATH, start_xpath)))
    ActionChains(driver, duration=40).click_and_hold(slider).perform()
    for track in tracks['forward_tracks']:
        yoffset_random = random.uniform(-2, 4)
        ActionChains(driver, duration=random.randint(40, 50)).move_by_offset(
            xoffset=track, yoffset=yoffset_random
        ).perform()
    for back_track in tracks['back_tracks']:
        yoffset_random = random.uniform(-2, 2)
        ActionChains(driver, duration=random.randint(50, 60)).move_by_offset(
            xoffset=back_track, yoffset=yoffset_random
        ).perform()
    # Final jitter
    ActionChains(driver, duration=70).move_by_offset(
        xoffset=random.uniform(0, -1.67), yoffset=random.uniform(-1, 1)
    ).perform()
    ActionChains(driver, duration=90).move_by_offset(
        xoffset=random.uniform(0, 1.67), yoffset=random.uniform(-1, 1)
    ).perform()
    ActionChains(driver, duration=60).release().perform()
```

**Before** — same algorithm in DrissionPage variant (from Xiaohongshu project):
```python
ac = Actions(self.page)
slider = self.page.ele(self.ele_dict["滑块条"])
self.page.actions.move_to(slider)
self.page.actions.hold(slider)
for track in tracks['forward_tracks']:
    yoffset_random = random.uniform(-2, 4)
    self.page.actions.move(offset_x=track, offset_y=yoffset_random,
                           duration=random.randint(10, 20) / 100)
self.page.actions.release()
```

**After** — one command replaces 50+ lines of custom trajectory code:
```bash
# Step 1: Screenshot the captcha
naturo browser screenshot --selector "#captcha-container" --path captcha.png

# Step 2: Get slide distance from your solver
DISTANCE=$(python my_solver.py captcha.png)

# Step 3: Drag with human-like trajectory
naturo drag \
  --from-element "#slider-handle" \
  --offset-x $DISTANCE --offset-y 0 \
  --trajectory bezier \
  --duration 600 \
  --jitter 2 \
  --overshoot 12 \
  --release-delay 80

# Step 4: Verify success
naturo browser wait ".captcha-success" --timeout 3000
```

What `--trajectory bezier --jitter 2 --overshoot 12` does internally:
```
Phase 1 (0-20%):   slow start, ease-in cubic       — matches _get_tracks mid1 phase
Phase 2 (20-60%):  acceleration, near-linear speed  — matches mid2 phase
Phase 3 (60-85%):  deceleration, ease-out cubic     — matches mid3 phase
Phase 4 (85-100%): micro-adjustment, slow approach  — matches final deceleration
Phase 5:           overshoot 12px → backward correction — matches back_tracks
Each step: +random Y jitter within [-2, +2]px       — matches yoffset_random
Variable timing per step                             — matches random duration
```

**Convenience command** (wraps the full flow):
```bash
naturo browser captcha solve --solver slider \
  --handle "#slider-handle" \
  --container "#captcha-container"
```

### Image Recognition Captcha

**Before** — from various projects (Chaojiying API integration):
```python
from chaojiying import Chaojiying_Client

cjy = Chaojiying_Client(username, password, soft_id)
# Capture captcha image
img = driver.find_element(By.CSS_SELECTOR, "#captcha-image").screenshot_as_png
# Submit to Chaojiying
result = cjy.PostPic(img, codetype=9004)  # 9004 = click coordinates
coords = result['pic_str']  # "123,45|234,67"
# Parse and click each point
for coord in coords.split('|'):
    x, y = coord.split(',')
    # Calculate offset relative to captcha image element
    ActionChains(driver).move_to_element_with_offset(
        captcha_img, int(x), int(y)
    ).click().perform()
```

**After**:
```bash
# Screenshot the captcha image
naturo browser screenshot --selector "#captcha-image" --path captcha.png

# Submit to your solver (Chaojiying, ddddocr, or custom)
COORDS=$(python chaojiying_client.py captcha.png 9004)
# Returns: "123,45|234,67"

# Click each coordinate relative to the captcha image element
naturo browser click "#captcha-image" --offset-x 123 --offset-y 45
naturo browser click "#captcha-image" --offset-x 234 --offset-y 67

# Submit
naturo browser click ".verify-captcha-submit-button"
```

```python
page.screenshot("captcha.png", selector="#captcha-image")
coords = my_solver("captcha.png")  # returns [(123, 45), (234, 67)]
for x, y in coords:
    page.find("#captcha-image").click(offset_x=x, offset_y=y)
page.find(".verify-captcha-submit-button").click()
```

For **text captcha** (recognize text from image):
```bash
naturo browser screenshot --selector "#captcha-image" --path captcha.png
TEXT=$(python chaojiying_client.py captcha.png 1902)
naturo browser type "#captcha-input" "$TEXT"
naturo browser click "#captcha-submit"
```

### Cookie Cycling Anti-Captcha

Some platforms (e.g., Douyin) can be bypassed by cycling cookies before the slider
triggers.

**Before** — from a Douyin messaging project (Selenium):
```python
def process_slider_verify_code(self):
    for i in range(10):
        try:
            WebDriverWait(self.browser, 4, 0.5).until(EC.title_contains('验证码'))
        except:
            break
        cookies = self.browser.get_cookies()
        self.browser.delete_all_cookies()
        sleep(5)
        for cookie in cookies:
            self.browser.add_cookie(cookie)
        self.browser.execute_script('location.reload()')
        self.browser.implicitly_wait(10)
```

**After**:
```bash
for i in $(seq 1 10); do
  # Check if captcha page appeared
  TITLE=$(naturo browser title)
  if [[ "$TITLE" != *"验证码"* ]]; then
    break
  fi
  # Cookie cycle
  naturo browser cookies save --path /tmp/cookies.json
  naturo browser cookies clear
  sleep 5
  naturo browser cookies load --path /tmp/cookies.json
  naturo browser eval "location.reload()"
  naturo browser wait --load --timeout 10000
done
```

```python
for _ in range(10):
    title = page.evaluate("document.title")
    if "验证码" not in title:
        break
    page.cookies.save("/tmp/cookies.json")
    page.cookies.clear()
    time.sleep(5)
    page.cookies.load("/tmp/cookies.json")
    page.evaluate("location.reload()")
    page.wait_for_load(timeout=10000)
```

---

## Human-Like Input

### Mouse Movement Trajectories

**Before** — every project has hand-rolled trajectory code (see [Slider Captcha](#slider-captcha)
for the full 50-line `_get_tracks` function). There is no reusable library; it's
copy-pasted between projects.

**After** — built into `naturo move` and `naturo drag`:
```bash
# Instant teleport (default, backward compatible)
naturo move 500 300

# Smooth bezier curve (human-like)
naturo move 500 300 --trajectory bezier --duration 800

# With Y-axis jitter (makes movement look less robotic)
naturo move 500 300 --trajectory bezier --duration 800 --jitter 3

# Linear interpolation (smooth but not curved)
naturo move 500 300 --trajectory linear --duration 500

# Drag with full human simulation
naturo drag --from 200 400 --to 500 400 \
  --trajectory bezier --duration 600 --jitter 2 \
  --overshoot 15 --release-delay 100
```

| Flag | Description | Default |
|------|-------------|---------|
| `--trajectory` | `instant`, `linear`, `bezier` | `instant` |
| `--duration` | Total movement time in ms | auto |
| `--steps` | Number of intermediate points | auto (based on duration) |
| `--jitter` | Max random perpendicular offset in px | 0 |
| `--overshoot` | Overshoot past target then correct, in px | 0 |
| `--release-delay` | Pause before releasing drag, in ms | 0 |

### Typing Profiles

**Before** — from various projects (constant delay or random sleep):
```python
for char in text:
    element.send_keys(char)
    time.sleep(random.uniform(0.05, 0.15))
```

**After**:
```bash
# Instant (default)
naturo type "hello world"

# Human-like with variable delays
naturo type "hello world" --profile human --wpm 80

# Paste mode — handles Chinese text, special characters
naturo type --paste "中文内容"
```

---

## Common Script Patterns

### Multi-Account Management

**Before** — from a live streaming project (Selenium, one port, kill between sessions):
```python
# Each account gets its own user-data-dir, all share port 9345
for live_user_name in eval(live_user_name_list):
    user_data_dir = HOME_PATH.joinpath(fr"Application\{live_user_name}_user_data")
    port_number = 9345  # same port — must kill Chrome between sessions!
    log_in = Log_in(chrome_path, driver_path, user_data_dir, port_number, live_user_name)
    log_in.start_login(cell_phone_number)
    kill_process(processes)  # kill Chrome before next account
```

**Before** — from a Douyin QR login project (Selenium):
```python
user_data_dir = HOME_PATH.joinpath(fr"Application\{account_code}_user_data")
prot = "9345"
# Port collision if two accounts run simultaneously → crash
```

**After** — naturo auto-assigns unique ports per profile:
```bash
# One-time setup (each profile gets auto-assigned port: 19200, 19201, 19202...)
naturo browser profile create account-zhangsan
naturo browser profile create account-lisi
naturo browser profile create account-wangwu

# Interactive login for each (one-time)
naturo browser profile setup account-zhangsan
naturo browser profile setup account-lisi
naturo browser profile setup account-wangwu

# Script: iterate over accounts — can even run simultaneously, no port conflicts
for ACCOUNT in account-zhangsan account-lisi account-wangwu; do
  naturo browser launch --profile "$ACCOUNT"
  naturo browser navigate "https://www.example.com"
  # ... do work ...
  naturo browser close
done
```

### Data Scraping with Infinite Scroll

**Before** — from a Xiaohongshu brand keyword project (DrissionPage):
```python
url_list = []
info_list = []
flag = False
for i in range(80):
    eles = page.eles(self.ele_dict["笔记组"])
    for ele in eles:
        info_dict = {"笔记链接": "", "图文or视频": ""}
        is_ele = ele.ele(self.ele_dict["笔记链接"], timeout=0.5)
        if not is_ele:
            continue
        url = is_ele.link
        url_key = url.split("/")[-1]
        url_id = url_key.split('?')[0]
        check_url = "https://www.xiaohongshu.com/explore/{0}".format(url_key)
        if url_id not in url_list:
            url_list.append(url_id)
            info_dict["笔记链接"] = check_url
            is_ele = ele.ele(self.ele_dict["是否视频"], timeout=0.5)
            if not is_ele:
                info_dict["图文or视频"] = "图文"
            else:
                info_dict["图文or视频"] = "视频"
            info_list.append(info_dict)
            if len(info_list) >= target_count:
                flag = True
                break
    if flag or page.ele(self.ele_dict["THE_END"], timeout=0.5):
        break
    else:
        page.scroll.down(1000)
        time.sleep(1)
```

**After**:
```python
from naturo.browser import BrowserPage

page = BrowserPage(profile="xhs-main")
page.navigate("https://www.xiaohongshu.com/explore")
page.wait_for_load()

seen_ids = set()
results = []
for _ in range(80):
    notes = page.find_all("xpath://div[@class='note-item']")
    for note in notes:
        link_el = note.find("xpath:.//a[@class='note-link']")
        if not link_el:
            continue
        href = link_el.attr("href")
        note_id = href.split("/")[-1].split("?")[0]
        if note_id not in seen_ids:
            seen_ids.add(note_id)
            has_video = note.find("xpath:.//div[@class='play-icon']")
            results.append({
                "link": f"https://www.xiaohongshu.com/explore/{note_id}",
                "type": "video" if has_video else "image",
            })
            if len(results) >= target_count:
                break

    if len(results) >= target_count:
        break
    # Check for end-of-list marker
    if page.find("xpath://div[@class='end-marker']"):
        break
    page.scroll_by(1000)
    time.sleep(1)
```

```bash
# Or pure CLI for simpler extraction
naturo browser launch --profile xhs-main
naturo browser navigate "https://www.xiaohongshu.com/explore"
naturo browser wait --load

for i in $(seq 1 80); do
  naturo browser find "xpath://div[@class='note-item']//a[@class='note-link']" --all --json \
    >> raw_links.jsonl

  # Check for end marker
  naturo browser find "xpath://div[@class='end-marker']" 2>/dev/null && break

  naturo browser scroll --by 1000
  sleep 1
done
```

### Form Filling

**Before** — from a YouTube publishing project (DrissionPage):
```python
# Fill title (clear existing text first)
self.page.ele(self.elements['标题']).input(
    video_parameter_data.get('YT发布标题')[0].get('text'), True
)

# Fill description
self.page.ele(self.elements['说明']).input(explain, True)

# Scroll to tags field, then fill
element = self.page.ele(self.elements['标签'])
element.scroll.to_see()
element.click()
element.input(tag_text)
```

**After**:
```bash
naturo browser type "xpath://input[@id='title']" "My Video Title" --clear-first
naturo browser type "xpath://textarea[@id='description']" "Video description here" --clear-first
naturo browser scroll --to-element "xpath://input[@id='tags']"
naturo browser click "xpath://input[@id='tags']"
naturo browser type "xpath://input[@id='tags']" "tag1, tag2, tag3"
```

```python
page.find("xpath://input[@id='title']").type("My Video Title", clear_first=True)
page.find("xpath://textarea[@id='description']").type("Video description here", clear_first=True)
page.scroll_to_element("xpath://input[@id='tags']")
page.find("xpath://input[@id='tags']").click()
page.find("xpath://input[@id='tags']").type("tag1, tag2, tag3")
```

### Dropdown / Playlist Selection

**Before** — from a YouTube publishing project (DrissionPage, hover+click dropdown):
```python
# Open dropdown
element = self.page.ele(self.elements['播放选择'])
element.scroll.to_center()
element.hover().click()

# Select matching items from the dropdown list
element_list = self.page.eles(self.elements['播放列表'])
for element in element_list:
    element.scroll.to_see()
    if element.text in video_parameter_data.get('播放列表'):
        element.click()

# Confirm selection
self.page.ele(self.elements['完成']).click()
```

**After**:
```bash
# Open dropdown
naturo browser scroll --to-element "xpath://div[@class='playlist-select']"
naturo browser hover "xpath://div[@class='playlist-select']"
naturo browser click "xpath://div[@class='playlist-select']"

# Select matching items
ITEMS=$(naturo browser find "xpath://div[@class='playlist-item']" --all --json)
# Parse and click matching items
echo "$ITEMS" | python3 -c "
import json, sys, subprocess
items = json.load(sys.stdin)
target_playlists = ['My Playlist 1', 'My Playlist 2']
for item in items:
    if item.get('text') in target_playlists:
        subprocess.run(['naturo', 'browser', 'click', f'e{item[\"ref\"]}'])
"

# Confirm
naturo browser click "xpath://button[@class='done']"
```

```python
page.scroll_to_element("xpath://div[@class='playlist-select']")
page.find("xpath://div[@class='playlist-select']").hover()
page.find("xpath://div[@class='playlist-select']").click()

target_playlists = ["My Playlist 1", "My Playlist 2"]
for item in page.find_all("xpath://div[@class='playlist-item']"):
    page.scroll_to_element(item)
    if item.text in target_playlists:
        item.click()

page.find("xpath://button[@class='done']").click()
```

---

## Full Migration Example

Complete migration of a Xiaohongshu brand keyword scraping script — real production
code structure (anonymized).

### Before: DrissionPage + pywinauto (120+ lines, 4 dependencies)

```python
import os, time, json, random
from DrissionPage import WebPage, ChromiumOptions
from DrissionPage.common import Actions
import pyperclip

class XhsScraper:
    ele_dict = {
        "笔记组": "xpath://div[contains(@class,'note-item')]",
        "笔记链接": "xpath:.//a[@class='note-link']",
        "是否视频": "xpath:.//div[@class='play-icon']",
        "博主昵称": "xpath://div[@class='author-wrapper']//a[@class='name']",
        "小红书号": "xpath://span[@class='user-id']",
        "性别": "xpath://use[@id='gender-icon']",
        "标签组": "xpath://div[@class='tag-list']//a[@class='tag']",
        "发布时间和发布地点": "xpath://span[@class='publish-date']",
        "THE_END": "xpath://div[@class='end-marker']",
        "滑块条": "xpath://div[@class='slider-handle']",
    }

    def __init__(self, account_name, port):
        user_data_path = os.path.join(os.getcwd(), "profiles", account_name)
        os.makedirs(user_data_path, exist_ok=True)
        co = ChromiumOptions()
        co.set_user_data_path(user_data_path)
        co.set_browser_path(r"C:\Users\me\Application\chrome.exe")
        co.set_local_port(port)
        co.set_pref("credentials_enable_service", False)
        co.set_pref("download.prompt_for_download", False)
        co.set_argument("--hide-crash-restore-bubble")
        self.page = WebPage(mode="d", chromium_options=co)
        self.page.set.window.max()

    def search(self, keyword):
        self.page.get("https://www.xiaohongshu.com/explore", retry=3, timeout=10)
        self.page.wait.doc_loaded()
        time.sleep(random.uniform(1, 2))
        search = self.page.ele("xpath://input[@id='search-input']")
        search.input(keyword, True)
        time.sleep(0.5)
        self.page.ele("xpath://div[@class='search-icon']").click()
        self.page.wait.doc_loaded()

    def scrape_list(self, target_count):
        url_list = []
        info_list = []
        flag = False
        for i in range(80):
            eles = self.page.eles(self.ele_dict["笔记组"])
            for ele in eles:
                is_ele = ele.ele(self.ele_dict["笔记链接"], timeout=0.5)
                if not is_ele:
                    continue
                url = is_ele.link
                url_id = url.split("/")[-1].split("?")[0]
                if url_id not in url_list:
                    url_list.append(url_id)
                    has_video = ele.ele(self.ele_dict["是否视频"], timeout=0.5)
                    info_list.append({
                        "link": f"https://www.xiaohongshu.com/explore/{url_id}",
                        "type": "视频" if has_video else "图文",
                    })
                    if len(info_list) >= target_count:
                        flag = True
                        break
            if flag or self.page.ele(self.ele_dict["THE_END"], timeout=0.5):
                break
            self.page.scroll.down(1000)
            time.sleep(1)
        return info_list

    def scrape_detail(self, url):
        self.page.get(url, retry=3, timeout=10)
        time.sleep(1)
        if not self.page.ele(self.ele_dict["发布时间和发布地点"]):
            self.page.refresh()
            time.sleep(2)
        info = {}
        info["author"] = self.page.ele(self.ele_dict["博主昵称"]).text
        raw_id = self.page.ele(self.ele_dict["小红书号"]).text
        info["user_id"] = raw_id.split("：")[-1]
        gender_el = self.page.ele(self.ele_dict["性别"])
        if gender_el:
            href = gender_el.attr("xlink:href")
            info["gender"] = "female" if "#female" in href else "male"
        tags = self.page.eles(self.ele_dict["标签组"])
        if tags and len(tags) > 1:
            info["tags"] = [t.text for t in tags[1:-1]]
        return info

if __name__ == "__main__":
    scraper = XhsScraper("xhs-main", 9222)
    scraper.search("咖啡推荐")
    notes = scraper.scrape_list(target_count=50)
    results = []
    for note in notes:
        detail = scraper.scrape_detail(note["link"])
        detail["type"] = note["type"]
        results.append(detail)
    with open("results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
```

### After: naturo Python SDK (65 lines, 1 dependency)

```python
#!/usr/bin/env python3
"""xhs_scrape.py — Xiaohongshu scraper using naturo"""
import json, time, random
from naturo.browser import BrowserPage

# One-time setup (run once):
#   naturo browser profile create xhs-main
#   naturo browser profile setup xhs-main   # log in manually

selectors = {
    "notes": "xpath://div[contains(@class,'note-item')]",
    "note_link": "xpath:.//a[@class='note-link']",
    "play_icon": "xpath:.//div[@class='play-icon']",
    "author": "xpath://div[@class='author-wrapper']//a[@class='name']",
    "user_id": "xpath://span[@class='user-id']",
    "gender": "xpath://use[@id='gender-icon']",
    "tags": "xpath://div[@class='tag-list']//a[@class='tag']",
    "publish_date": "xpath://span[@class='publish-date']",
    "end_marker": "xpath://div[@class='end-marker']",
}

page = BrowserPage(profile="xhs-main")  # anti-detection automatic, port auto-assigned

# Search
page.navigate("https://www.xiaohongshu.com/explore")
page.wait_for_load()
time.sleep(random.uniform(1, 2))
page.find("#search-input").type("咖啡推荐", clear_first=True)
page.find(".search-icon").click()
page.wait_for_load()

# Scrape list with infinite scroll
seen_ids, notes = set(), []
for _ in range(80):
    for note in page.find_all(selectors["notes"]):
        link_el = note.find(selectors["note_link"])
        if not link_el:
            continue
        note_id = link_el.attr("href").split("/")[-1].split("?")[0]
        if note_id not in seen_ids:
            seen_ids.add(note_id)
            notes.append({
                "link": f"https://www.xiaohongshu.com/explore/{note_id}",
                "type": "video" if note.find(selectors["play_icon"]) else "image",
            })
            if len(notes) >= 50:
                break
    if len(notes) >= 50 or page.find(selectors["end_marker"]):
        break
    page.scroll_by(1000)
    time.sleep(1)

# Scrape details
results = []
for note in notes:
    page.navigate(note["link"])
    page.wait_for(selectors["publish_date"], timeout=10000)
    info = {"type": note["type"]}
    info["author"] = page.find(selectors["author"]).text
    info["user_id"] = page.find(selectors["user_id"]).text.split("：")[-1]
    gender_el = page.find(selectors["gender"])
    if gender_el:
        info["gender"] = "female" if "#female" in gender_el.attr("xlink:href") else "male"
    tags = page.find_all(selectors["tags"])
    if tags and len(tags) > 1:
        info["tags"] = [t.text for t in tags[1:-1]]
    results.append(info)

with open("results.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"Scraped {len(results)} notes")
page.close()
```

**Migration result**:
- 120+ lines → 65 lines (46% reduction)
- 4 dependencies (DrissionPage, pywinauto, pyperclip, psutil) → 1 dependency (naturo)
- 10 lines of Chrome profile setup → 0 lines (naturo manages it)
- 0 lines of anti-detection config (it's the default)
- `time.sleep()` replaced with proper `wait_for()` where possible

---

## Troubleshooting

### Chrome won't launch

**Before** — common client script workaround:
```python
# Kill all Chrome processes before launching
os.system('taskkill /f /im chrome.exe')
time.sleep(2)
```

**After**:
```bash
# Check if Chrome is already running on the profile's port
naturo browser profile info <profile-name>

# Kill orphaned Chrome processes
naturo app quit --app chrome --force

# Then launch normally
naturo browser launch --profile <name>
```

### CDP connection refused

**Before** — common client script pattern:
```python
os.system(fr'start {chrome_path} --remote-debugging-port={port}')
time.sleep(random.randint(2, 3))  # hope Chrome started in time
co = ChromiumOptions().set_local_port(port)
page = ChromiumPage(addr_or_opts=co)  # may fail if Chrome isn't ready
```

**After**:
```bash
# naturo browser launch handles the full lifecycle:
# 1. Starts Chrome with correct flags
# 2. Waits for CDP port to be ready
# 3. Connects automatically
naturo browser launch --profile <name>

# Or connect to manually-started Chrome
naturo browser connect --port 9222
```

### Element not found

**Before** — common client script pattern:
```python
for try_i in range(300):
    time.sleep(random.uniform(0.5, 1.5))
    if page.ele(selector):
        break
```

**After**:
```bash
# Wait for element with proper timeout (no polling loop needed)
naturo browser wait "#my-element" --timeout 10000

# Check if element is in an iframe
naturo browser frames
naturo browser frame-find "#content-iframe" "#my-element"

# Use naturo see for visual debugging — shows ALL elements including AI-detected ones
naturo see --app chrome
```

### Slider captcha fails

**Before** — adjust the trajectory algorithm constants:
```python
# Tweak acceleration values, add more jitter...
a = random.randint(10, 15)  # try different ranges
```

**After**:
```bash
# Adjust trajectory parameters — no code changes needed
# Slower duration + less overshoot for stricter captchas
naturo drag --from-element "#slider" --offset-x $DIST \
  --trajectory bezier --duration 1000 --jitter 1 --overshoot 5

# More aggressive for lenient captchas
naturo drag --from-element "#slider" --offset-x $DIST \
  --trajectory bezier --duration 400 --jitter 3 --overshoot 15

# Verify your solver returns the correct distance
naturo browser screenshot --selector "#captcha-container" --path debug.png
```

### Desktop element not found after browser interaction

**Before** — common client script pattern:
```python
wechat.SetTopmost(True)
wechat.SetActive()
time.sleep(1)  # wait for window to come to foreground
```

**After**:
```bash
# Ensure the desktop app has focus
naturo app focus --app 微信

# Wait for a specific element to appear
naturo wait --element --name "视频号" --timeout 5

# Use naturo see to verify what's visible
naturo see --app 微信
```
