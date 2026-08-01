"""Unified element tree — merge redundant accessibility sources into one tree.

UIA and MSAA (and JAB/IA2) are largely REDUNDANT descriptions of the *same*
widgets, not complementary regions: a Button exposed by UIA is usually the same
Button MSAA exposes. Winner-take-all (keep the richest single tree) throws away
whatever the loser saw that the winner missed, and mis-fires when the "richest by
raw node count" tree is actually junk (e.g. our own Naturobot: 24 empty offscreen
MSAA nodes "out-counting" the real UIA tree).

This module merges two tagged trees into ONE where each real control is a single
node carrying the UNION of the sources that saw it (``properties["source"]`` ->
``"uia+msaa"``) and the union of their capabilities/attributes. Corresponding
controls collapse (one operable ref, no source-picking for the caller); controls
unique to the secondary source graft under their geometric parent. Redundant
sources therefore cost ~nothing (a full-overlap merge is the same size as the
richer tree); genuinely-additive sources make the tree MORE complete.

Correspondence = geometry (centres close + similar size) + role-equivalence
(roles are already normalized to naturo's vocabulary by the native layer, so this
is a small synonym set) + name compatibility (accelerators/localization
normalized, one-empty allowed). This is the load-bearing decision — see the
mission memory; a loose match bloats the tree, a strict one duplicates.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from naturo.backends.base import ElementInfo

# Genuine cross-source role synonyms. Roles are already normalized to naturo's
# vocabulary by the native layer, so most matches are exact; these cover the few
# where UIA and MSAA legitimately disagree on the label for the same control.
_ROLE_SYNONYMS: Dict[str, frozenset] = {}
for _grp in (
    {"text", "static"},
    {"button", "pushbutton", "splitbutton"},
    {"list", "listbox"},
    {"combobox", "droplist", "dropdown"},
    {"menuitem", "menu item"},
    {"checkbox", "check box"},
    {"radiobutton", "radio button"},
    {"group", "pane", "grouping"},
):
    for _r in _grp:
        _ROLE_SYNONYMS[_r] = frozenset(_grp)

# Roles that are pure structural containers — a container unique to the secondary
# source is rarely worth grafting on its own (its useful children graft
# individually). Keeps the merge from importing redundant wrapper noise.
_CONTAINER_ROLES = frozenset({"pane", "group", "grouping", "window", "custom",
                              "client", "document", "unknown", ""})


def _boxed(n: ElementInfo) -> bool:
    return (getattr(n, "width", 0) or 0) > 0 and (getattr(n, "height", 0) or 0) > 0


def _norm_name(s: Optional[str]) -> str:
    """Normalize a control name for cross-source comparison: drop the ``&``/``(&X)``
    keyboard-accelerator markers, collapse whitespace, casefold."""
    if not s:
        return ""
    return s.replace("&", "").strip().casefold()


def _roles_match(a: str, b: str) -> bool:
    a = (a or "").casefold()
    b = (b or "").casefold()
    if a == b:
        return True
    syn = _ROLE_SYNONYMS.get(a)
    return bool(syn and b in syn)


def _flatten(root: ElementInfo) -> List[ElementInfo]:
    out: List[ElementInfo] = []

    def _v(n: ElementInfo) -> None:
        out.append(n)
        for c in (n.children or []):
            _v(c)

    _v(root)
    return out


def _same_element(a: ElementInfo, b: ElementInfo) -> bool:
    """True when *a* and *b* are the SAME real control seen by two sources.

    Geometry first (centres within a small tolerance AND similar area — so a
    control is never matched to its own container), then role-equivalence, then
    name compatibility (equal after normalization, or one side unnamed).
    """
    if not (_boxed(a) and _boxed(b)):
        return False
    acx, acy = a.x + a.width / 2.0, a.y + a.height / 2.0
    bcx, bcy = b.x + b.width / 2.0, b.y + b.height / 2.0
    tol_x = max(6.0, 0.25 * min(a.width, b.width))
    tol_y = max(6.0, 0.25 * min(a.height, b.height))
    if abs(acx - bcx) > tol_x or abs(acy - bcy) > tol_y:
        return False
    aa, ba = a.width * a.height, b.width * b.height
    if aa and ba and max(aa, ba) / max(1, min(aa, ba)) > 2.5:
        return False  # too different in size — likely control-vs-container
    if not _roles_match(a.role, b.role):
        return False
    na, nb = _norm_name(a.name), _norm_name(b.name)
    if na and nb and na != nb:
        return False
    return True


def _useful(n: ElementInfo) -> bool:
    """A secondary-unique node is worth grafting only if it carries information:
    a name, or a sized non-container (an actual control the primary missed)."""
    if (n.name or "").strip():
        return True
    return _boxed(n) and (n.role or "").casefold() not in _CONTAINER_ROLES


def _smallest_container(root: ElementInfo, target: ElementInfo) -> Optional[ElementInfo]:
    """Smallest boxed node in *root* whose rect contains *target*'s rect (the
    natural graft parent). Returns None if nothing contains it (caller uses root)."""
    tx, ty = target.x, target.y
    tr, tb = target.x + target.width, target.y + target.height
    best: Optional[ElementInfo] = None
    best_area = None
    for n in _flatten(root):
        if not _boxed(n):
            continue
        if n.x <= tx + 2 and n.y <= ty + 2 and n.x + n.width >= tr - 2 and n.y + n.height >= tb - 2:
            area = n.width * n.height
            if best_area is None or area < best_area:
                best, best_area = n, area
    return best


def _union_into(pn: ElementInfo, sn: ElementInfo) -> None:
    """Fold secondary node *sn* into matched primary node *pn*: union the source
    tags, fill a missing name/value, OR the capability flags."""
    pp = pn.properties if isinstance(pn.properties, dict) else {}
    sp = sn.properties if isinstance(sn.properties, dict) else {}
    # Record the secondary as a CORROBORATING source via the existing ADR-§4
    # fusion field — keep the primary ``source`` intact so technique
    # classification (correctness/fusion tags) treats it as multi-deterministic
    # rather than choking on a synthetic joined "uia+msaa" tag.
    ssrc = str(sp.get("source", "") or "")
    psrc = str(pp.get("source", "") or "")
    if ssrc and ssrc != psrc:
        corr = list(pp.get("corroborated_by") or [])
        if ssrc not in corr:
            corr.append(ssrc)
        pp["corroborated_by"] = corr
    if not (pn.name or "").strip() and (sn.name or "").strip():
        pn.name = sn.name
    if (pn.value in (None, "")) and (sn.value not in (None, "")):
        pn.value = sn.value
    # Union capability truth: if either source says a control is actionable/
    # editable/readable/focusable, it is — this is the "operate via whichever
    # backend can" robustness the unified tree exists for.
    for k in ("actionable", "editable", "readable", "focusable"):
        if sp.get(k) and not pp.get(k):
            pp[k] = sp[k]
    pn.properties = pp


def _shallow_copy_leaf(n: ElementInfo) -> ElementInfo:
    """Copy *n* WITHOUT children — grafted secondary-unique nodes attach as leaves
    (their descendants graft individually by geometry, avoiding double-counting a
    node the primary also has deeper)."""
    return ElementInfo(
        id=n.id, role=n.role, name=n.name, value=n.value,
        x=n.x, y=n.y, width=n.width, height=n.height,
        children=[], properties=dict(n.properties or {}),
    )


def merge_a11y_trees(primary: ElementInfo, secondary: ElementInfo) -> ElementInfo:
    """Merge *secondary* into *primary* (the richer skeleton) in place, returning
    *primary*. Corresponding controls union onto the primary node; controls unique
    to *secondary* graft under their geometric parent. Both trees must already be
    ``_tag_source``-tagged. One node per real control — no duplicate refs.
    """
    if primary is None:
        return secondary
    if secondary is None:
        return primary

    by_role: Dict[str, List[ElementInfo]] = defaultdict(list)
    for n in _flatten(primary):
        if _boxed(n):
            by_role[(n.role or "").casefold()].append(n)

    claimed: set = set()

    def _find_match(sn: ElementInfo) -> Optional[ElementInfo]:
        role = (sn.role or "").casefold()
        cands = list(by_role.get(role, []))
        syn = _ROLE_SYNONYMS.get(role)
        if syn:
            for r in syn:
                if r != role:
                    cands.extend(by_role.get(r, []))
        best = None
        best_d = None
        scx, scy = sn.x + sn.width / 2.0, sn.y + sn.height / 2.0
        for pn in cands:
            if id(pn) in claimed:
                continue
            if _same_element(pn, sn):
                d = abs((pn.x + pn.width / 2.0) - scx) + abs((pn.y + pn.height / 2.0) - scy)
                if best_d is None or d < best_d:
                    best, best_d = pn, d
        return best

    unique: List[ElementInfo] = []
    for sn in _flatten(secondary):
        if not _boxed(sn):
            continue  # unsized chrome carries nothing to merge
        m = _find_match(sn)
        if m is not None:
            claimed.add(id(m))
            _union_into(m, sn)
        elif _useful(sn):
            unique.append(sn)

    for sn in unique:
        parent = _smallest_container(primary, sn) or primary
        if parent.children is None:
            parent.children = []
        parent.children.append(_shallow_copy_leaf(sn))

    return primary
