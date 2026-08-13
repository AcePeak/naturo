# CJK / Chinese-Desktop-App Coverage — naturo's China-Market Wedge

> Positioning note (issue #921, competitiveness pillar 2). This document explains
> *why* naturo is structurally better-positioned than UIA-only Western engines for
> Chinese enterprise desktop automation, and *how* its recognition cascade maps
> onto the UI frameworks that dominate Chinese desktop software.

## The gap in the market

The open-source AI-automation engines built in the West — UFO², Windows-MCP,
Terminator — walk a **single UIA accessibility tree**. That is a reasonable bet
for US enterprise desktops (Win32/WPF/UWP line-of-business apps expose UIA well).
It is a **poor** bet for the Chinese desktop, where the most-used apps are built
on frameworks that UIA sees poorly or not at all:

| App class (examples) | UI framework | What UIA alone sees |
| --- | --- | --- |
| 钉钉 DingTalk, 飞书 Feishu/Lark, new-gen 微信/QQ | **Electron / CEF** (web-rendered) | window chrome only — the entire message/list/content area is one opaque node |
| 企业微信 WeCom, many legacy IM/finance clients | **自绘 / Duilib** (custom-drawn) | little to nothing — controls are painted, not real HWNDs |
| 同花顺 THS and other trading terminals | **hybrid** (自绘 grids + CEF panes) | thin — the盘口/K-line grids are custom-drawn |
| WPS Office (表格/文字/演示) | **COM automation model** | UIA is shallow; the document model lives behind COM |

A UIA-only tool is effectively **blind to the content** of most of these. That is
the wedge: naturo's multi-framework cascade was built precisely for the
"UIA-is-not-enough" case, which is the *common* case in China, not the exception.

## How naturo covers each framework

naturo runs a cascade that fuses several recognition providers and tags every
element with the provider that found it (see [RECOGNITION.md](RECOGNITION.md)):

```
UIA  →  MSAA / IAccessible2  →  Java Access Bridge  →  Electron / CDP  →  Vision (OCR)
```

- **Electron / CEF (钉钉, 飞书, Teams-class)** → the **CDP** provider reads the
  real DOM behind the opaque UIA node, plus **MSAA/IAccessible2** recovers native
  chrome that UIA drops.
- **自绘 / Duilib (企业微信, legacy clients)** → the **vision / OCR** provider
  reads painted text and controls when there is no accessibility tree to walk.
- **hybrid (同花顺)** → CDP for the web panes; OCR for the custom-drawn grids.
- **COM apps (WPS Office)** → naturo drives the application's native object model
  directly for reliable cell/document read-write, the same way it does for
  Microsoft Office.

## Evidence (measured, reproducible)

From the live recognition benchmark ([RECOGNITION.md](RECOGNITION.md), measured
2026-08-13 on a real desktop):

- **钉钉 DingTalk** (CEF) — cascade recovers **+4 unique** elements over the
  UIA-only baseline (59 vs 55), with **44 MSAA nodes** recovered that a
  UIA-only walk misses. The navigation, conversation list, and IM content
  modules become addressable.
- **同花顺 THS** (hybrid) — the CEF/web surface is recognized; the custom-drawn
  盘口/grid surface is thin by design and is recovered through the OCR / 自绘
  path (the same class of work tracked in #1213).
- **飞书 Feishu/Lark** is an Electron/CEF app of exactly the class the CDP
  provider is built for — the same path that yields VS Code's **+98** elements
  (111 vs 13) over UIA-only.

The reproducible methodology (measure the same live window twice — full cascade
vs a UIA-only baseline produced by naturo's own engine) is documented in
RECOGNITION.md, so these are apples-to-apples numbers, not marketing.

## Human-readable output for CJK users

naturo's machine-readable `-j` JSON output emits **literal UTF-8** for Chinese /
Japanese / Korean text rather than `\uXXXX` escapes (fixed in #894 via
`ensure_ascii=False`). CJK window titles, selector names, paths, and error
messages stay human-readable when a Chinese-speaking operator inspects agent
output — a small thing that matters a lot in day-to-day use.

## Positioning

For the China enterprise-RPA market, naturo's story is simple and defensible:

> **The apps your automation actually needs to drive — 钉钉, 飞书, 企业微信,
> 同花顺, WPS — are the ones UIA-only engines can't see. naturo sees them, because
> it fuses CDP, OCR, and native object models on top of UIA, and it tells you how
> confident it is about every element it found.**

This is not a coat of paint on a Western tool; it is the core architecture doing
what it was designed for, on the desktop where it matters most.

## Honest scope

- The recognition wedge (seeing content) is measured and reproducible for the
  CEF/hybrid apps above. A full **interactive** matrix (launch → see → find →
  click → type) across *personal* 微信 and QQ desktop is not yet consolidated
  here — those follow the same CEF / 自绘 patterns, but per-app interaction
  validation is ongoing.
- Custom-drawn (自绘) surfaces depend on the OCR path; grid-cell extraction on
  terminals like 同花顺 is the OCR / 自绘 work tracked in #1213.
