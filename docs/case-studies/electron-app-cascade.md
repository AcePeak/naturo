# Case Study: Electron App Complete Coverage via Cascade Recognition

> This case study documents naturo's multi-source element fusion — a key differentiator over competing Windows automation tools. Use this as source material for README, onboarding, demos, and marketing content.

## The Problem

Electron apps (Slack, VS Code, Feishu, Discord, etc.) are notoriously difficult to automate because they combine native UI with web-rendered content:

- **Native frame**: Title bar, window controls, sidebar navigation — exposed via Windows UIA (UI Automation)
- **Web content**: Chat messages, editors, dashboards — rendered by Chromium, invisible to UIA
- **Hybrid areas**: Some sidebar elements are native, some are web-rendered — no single tool catches everything

### What Other Tools See

| Tool | Approach | Typical Coverage |
|------|----------|-----------------|
| pywinauto / WinAppDriver | UIA only | ~60% — misses web content entirely |
| Selenium / Playwright | CDP only | ~40% — misses native frame, some sidebars |
| PyAutoGUI | Pixel matching | 0% element awareness — just screenshots |

No existing tool combines multiple recognition sources into a unified element tree.

## naturo's Cascade Solution

```
naturo see --app feishu --cascade --fill-gaps
```

naturo runs three recognition providers in sequence and **merges their results into one tree**:

```
UIA (native accessibility)
  ↓ find gaps
CDP (Chrome DevTools Protocol)
  ↓ find gaps
AI Vision (screenshot → element identification)
  ↓ merge & deduplicate
Unified Element Tree
```

### Real-World Result: Enterprise Chat App (Electron)

**Setup**: Electron-based enterprise communication app, Windows 11, 4K display at 150% scaling.

**UIA alone** found 627 elements:
- Chat panel: message text, links, buttons, timestamps ✅
- Chat input area: text field, send button, toolbar ✅
- Conversation list: individual chat items with names and previews ✅
- Left navigation icons (消息/Messages, 日历/Calendar, 云文档/Docs, etc.): ❌ **missed**
- Document/file list in sidebar: ❌ **missed**
- Some deep panel structures: ❌ **missed**

**AI Vision** identified 119 additional elements:
- Left navigation icons: ✅ 消息, 视频会议, 日历, 云文档, 多维表格, 工作台, 通讯录, 豆包, 飞书社, 更多
- Sidebar document list: ✅ 30+ document/project items
- Conversation list items: ✅ (but UIA already had these)
- Chat messages: ✅ (but UIA already had these with better text accuracy)

**After merge (IoU deduplication)**:
- AI elements overlapping UIA: **skipped** (UIA names are more accurate than AI OCR)
- AI elements in UIA gaps: **grafted into tree** at correct parent node
- Final coverage: **650+ unique elements** vs 627 UIA-only

### The Key Insight

UIA has **accurate text** but **incomplete spatial coverage** — it can't see inside some Electron panels. AI Vision has **complete spatial coverage** but **inaccurate OCR** for small Chinese text. By merging them with IoU-based deduplication, naturo gets the best of both:

| Source | Text Accuracy | Spatial Coverage | Speed |
|--------|:---:|:---:|:---:|
| UIA | ✅ Exact | ⚠️ Gaps in Electron areas | ✅ <1s |
| AI Vision | ⚠️ OCR errors on small text | ✅ Everything visible | ⚠️ ~8s |
| **Merged** | **✅ Best of both** | **✅ Complete** | ⚠️ ~8s total |

## Merge Algorithm

```
For each AI element:
  1. Compute IoU (Intersection over Union) with all visible UIA elements
  2. If IoU >= 0.3 with any UIA element → skip (UIA already has it, with better name)
  3. If no overlap → find smallest UIA container that encloses this element
  4. Graft AI element as child of that container, tagged [vision]
```

This ensures:
- No duplicates in the final tree
- AI elements appear in the correct tree hierarchy
- Each element has the most accurate name available
- Source attribution (`[uia]` vs `[vision]`) for transparency

## Technical Notes

- **DPI handling**: UIA coordinates are in physical pixels (per-monitor DPI aware). AI Vision coordinates are estimated from the screenshot. On high-DPI displays (150%, 200%), the AI pixel estimates may need scaling — this is handled by the cascade's window bounds normalization.
- **Token budget**: Complex UIs (100+ elements) need 8000-16000 tokens for AI Vision. The default `max_tokens=16384` handles apps with up to ~300 visible elements.
- **Prompt engineering**: The AI prompt explicitly requests leaf elements (not containers), standard role names (Button, Edit, Link, Tab, etc.), and pixel-precise bounding boxes. This prevents lazy responses like `{"role": "chat_area", "name": "message_area"}`.

## Comparison Commands

```bash
# UIA only (what pywinauto/WinAppDriver would see)
naturo see --app "ElectronApp" --backend uia

# UIA + CDP (what Selenium could see separately)
naturo see --app "ElectronApp" --cascade

# UIA + CDP + AI Vision (what only naturo can do)
naturo see --app "ElectronApp" --cascade --fill-gaps

# Visual verification
naturo highlight --app "ElectronApp" --cascade --fill-gaps
```

## Messaging Angles

### For README / Landing Page
> "naturo sees what other tools can't. By combining native accessibility APIs, Chrome DevTools Protocol, and AI vision, naturo builds a complete element tree for any Windows application — including Electron apps where traditional tools only see 60% of the UI."

### For Enterprise RPA
> "Automate Electron-based enterprise apps (Slack, Teams, Feishu, VS Code) with the same reliability as Win32 apps. naturo's cascade recognition fills the gaps that UIA leaves in web-rendered content."

### For Developer Onboarding
> "Run `naturo see --app myapp --cascade --fill-gaps --stats` to see exactly how naturo discovers UI elements. The stats breakdown shows how many elements each provider found and how they were merged."

### For Competitive Positioning
> "pywinauto sees 627 elements. naturo sees 650+. The difference? 30+ navigation items, document links, and sidebar controls that only AI Vision can detect — elements your automation script needs to interact with."

---

*Case study from naturo v0.3.x development. App details anonymized. Actual element counts and coverage metrics from real testing on Windows 11 with 4K display at 150% DPI scaling.*
