"""Resolve an ``--app`` name to its content-bearing window tree(s).

UWP / WinUI apps (Calculator, the Win11 Notepad, Settings…) expose ONE running
app through SEVERAL top-level windows at once: empty ``ApplicationFrameWindow``
frames, off-screen ghost frames, and the live ``Windows.UI.Core.CoreWindow``
that actually holds the controls. ``_resolve_hwnd`` / ``_resolve_hwnds`` collapse
to a single window and can pick a ghost — so ``see --app calc`` returned only
chrome (no buttons).

This module gathers ALL of an app's windows (resolved + same-title siblings +
same-process windows, the last of which catches the live CoreWindow whose title
is often empty), cascades each, scores the real on-screen content, and returns
only the window(s) that actually have UI — dropping the ghosts.
"""
from __future__ import annotations

import os
from typing import Any, Optional

# Roles that mark real, interactive on-screen content (not window chrome).
_CONTENT_ROLES = frozenset({
    "button", "menuitem", "checkbox", "radiobutton", "edit", "text", "listitem",
    "tab", "combobox", "link", "hyperlink", "treeitem", "cell", "slider",
    "spinbutton", "spinner", "document", "image",
})


def content_score(tree: Any) -> int:
    """Count on-screen interactive nodes — distinguishes a live window from a
    zombie whose only nodes are off-screen (0×0) chrome."""
    n = 0
    stack = [tree] if tree is not None else []
    while stack:
        el = stack.pop()
        w = getattr(el, "width", 0) or 0
        h = getattr(el, "height", 0) or 0
        role = (getattr(el, "role", "") or "").lower()
        if w > 0 and h > 0 and role in _CONTENT_ROLES:
            n += 1
        stack.extend(getattr(el, "children", None) or [])
    return n


def _candidate_hwnds(backend, app: str) -> list[int]:
    """Resolved windows + same-title siblings + same-process windows."""
    try:
        cands = list(backend._resolve_hwnds(app=app) or [])
    except Exception:
        cands = []
    if not cands:
        return cands
    try:
        wins = list(backend.list_windows())
    except Exception:
        return cands

    def _wh(w):
        return getattr(w, "handle", None) or getattr(w, "hwnd", None)

    def _proc(w):
        p = os.path.basename(getattr(w, "process_name", "") or "").lower()
        return p[:-4] if p.endswith(".exe") else p

    titles = {(getattr(w, "title", "") or "").strip()
              for w in wins if _wh(w) in cands}
    titles.discard("")
    appl = (app or "").lower()
    for w in wins:
        h = _wh(w)
        if h in cands:
            continue
        t = (getattr(w, "title", "") or "").strip()
        pr = _proc(w)
        # same title as a resolved window, OR a process name related to the app
        # term — the latter catches the live CoreWindow (empty title, process
        # e.g. CalculatorApp/Notepad) that title matching alone would miss.
        if (t and t in titles) or (appl and pr and (appl in pr or pr in appl)):
            cands.append(h)
    return cands


def app_content_tree(
    backend, app: str, *, depth: int, backend_name: str = "auto",
    coverage_target: float = 0.0, max_windows: int = 8,
) -> tuple[Optional[Any], Optional[Any]]:
    """Cascade every window of ``app``, drop content-less ghosts, return the
    live tree.

    Returns ``(tree, stats)``:
    - one live window → its cascade tree + stats;
    - several live windows (genuinely separate instances) → a virtual
      ``app_root`` merging each under a ``WindowGroup`` node;
    - nothing content-bearing found → ``(None, None)`` so the caller can fall
      back to its normal single-window resolution.
    """
    from naturo.cascade._run import run_cascade
    from naturo.backends.base import ElementInfo as BaseElementInfo

    cands = _candidate_hwnds(backend, app)
    if not cands:
        return None, None

    built = []
    for h in cands[:max_windows]:
        try:
            r = run_cascade(backend, hwnd=h, depth=depth,
                            backend_name=backend_name,
                            coverage_target=coverage_target)
        except Exception:
            continue
        sc = content_score(r.tree) if r.tree is not None else 0
        if sc > 0:
            built.append((h, r.tree, r.stats, sc))

    if not built:
        return None, None

    # Keep windows whose content is a meaningful fraction of the richest; drop
    # chrome-only frames that are just duplicates of the same instance.
    best = max(b[3] for b in built)
    keep = [b for b in built if b[3] >= max(best * 0.5, 3)]

    if len(keep) == 1:
        return keep[0][1], keep[0][2]

    root = BaseElementInfo(
        id="app_root", role="Application", name=app, value=None,
        x=0, y=0, width=0, height=0, children=[], properties={},
    )
    for h, st, _stats, _sc in keep:
        root.children.append(BaseElementInfo(
            id=f"window_{h}", role="WindowGroup",
            name=f"{st.name} (HWND:{h})", value=None,
            x=st.x, y=st.y, width=st.width, height=st.height,
            children=[st], properties={},
        ))
    return root, keep[0][2]
