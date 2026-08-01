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

from typing import Dict, List, Optional

from naturo.backends.base import ElementInfo
from naturo.cascade._coverage import _flatten

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

# GENERIC wrapper roles that different sources use for the SAME control — MSAA in
# particular reports almost everything as ``window``/``client`` (the HWND frame +
# its client area), where UIA gives the specific role (Button/Text/Pane). When
# either side wears a generic role, geometry + name carry the correspondence and
# the role must NOT veto the match — otherwise every UIA control gets a duplicate
# MSAA ``window``/``client`` grafted under it instead of corroborating it.
_GENERIC_ROLES = frozenset({"window", "client", "pane", "group", "grouping",
                            "custom", "unknown", ""})


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
    # Role must agree UNLESS one side wears a generic wrapper role (MSAA
    # window/client), in which case geometry + name decide.
    ar, br = (a.role or "").casefold(), (b.role or "").casefold()
    if not (_roles_match(a.role, b.role)
            or ar in _GENERIC_ROLES or br in _GENERIC_ROLES):
        return False
    na, nb = _norm_name(a.name), _norm_name(b.name)
    if na and nb and na != nb:
        return False
    # Two UNNAMED generic wrappers matching on centre-tolerance alone would be
    # too loose (any coincident wrappers). But an identical container (same tree
    # seen by two sources, or a real structural pane) MUST still dedup — so allow
    # it only on a NEAR-EXACT rect, not merely a close centre.
    if not na and not nb and ar in _GENERIC_ROLES and br in _GENERIC_ROLES:
        if (abs(a.x - b.x) > 2 or abs(a.y - b.y) > 2
                or abs(a.width - b.width) > 2 or abs(a.height - b.height) > 2):
            return False
    return True


def _useful(n: ElementInfo) -> bool:
    """A secondary-unique node is worth grafting only if it carries information:
    a name, or a sized non-container (an actual control the primary missed)."""
    if (n.name or "").strip():
        return True
    return _boxed(n) and (n.role or "").casefold() not in _CONTAINER_ROLES


def _smallest_container(
    boxed: List[ElementInfo], target: ElementInfo
) -> Optional[ElementInfo]:
    """Smallest node in *boxed* whose rect contains *target*'s rect (the natural
    graft parent). *boxed* is the primary tree's boxed nodes, flattened ONCE by
    the caller — grafts only ever nest under original primary nodes, so this list
    need not be recomputed per graft. Returns None if nothing contains it."""
    tx, ty = target.x, target.y
    tr, tb = target.x + target.width, target.y + target.height
    best: Optional[ElementInfo] = None
    best_area = None
    for n in boxed:
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


def merge_a11y_trees(primary: ElementInfo, secondary: ElementInfo):
    """Merge *secondary* into *primary* (the richer skeleton) in place.

    Corresponding controls (geometry + role-equivalence + normalized-name) union
    onto the primary node — one operable ref, the secondary recorded as a
    corroborating source; controls unique to *secondary* graft under their
    geometric parent. Both trees must already be ``_tag_source``-tagged.

    Returns ``(primary, grafted)`` where *grafted* is the list of newly-added
    (secondary-unique) leaf nodes — callers use it to report how many controls
    the secondary source contributed, and to extend a flat element list without
    re-flattening the whole tree.
    """
    if primary is None:
        return secondary, _flatten(secondary) if secondary is not None else []
    if secondary is None:
        return primary, []

    prim_boxed = [n for n in _flatten(primary) if _boxed(n)]

    def _find_match(sn: ElementInfo) -> Optional[ElementInfo]:
        # A generic-role secondary node (MSAA window/client) can correspond to a
        # primary node of ANY role, so we can't bucket by role — scan boxed
        # primaries and let _same_element decide. MULTIPLE secondary nodes may
        # map to one primary (MSAA's window+client pair for one control); that is
        # fine — each simply corroborates it, none is grafted as a duplicate.
        best = None
        best_key = None
        scx, scy = sn.x + sn.width / 2.0, sn.y + sn.height / 2.0
        sname = _norm_name(sn.name)
        for pn in prim_boxed:
            if pn is primary:
                continue  # root handled separately; never fold a control into it
            if not _same_element(pn, sn):
                continue
            # Rank matches so the RIGHT primary wins when several are eligible
            # (e.g. overlapping controls, or a degenerate same-bounds tree):
            #  1) genuine role agreement beats a generic-wrapper match — a MSAA
            #     Document must pick the UIA Document, not a same-rect UIA Pane;
            #  2) an actual name match beats a one-side-empty match;
            #  3) then nearest centre.
            role_tier = 0 if _roles_match(pn.role, sn.role) else 1
            name_tier = 0 if (sname and _norm_name(pn.name) == sname) else 1
            d = abs((pn.x + pn.width / 2.0) - scx) + abs((pn.y + pn.height / 2.0) - scy)
            key = (role_tier, name_tier, d)
            if best_key is None or key < best_key:
                best, best_key = pn, key
        return best

    sec_flat = _flatten(secondary)
    # Both trees are the SAME window (get_element_tree of one hwnd), so their
    # ROOTS are the same window frame by construction — corroborate them
    # directly (their names can differ across sources, e.g. UIA "frame" vs JAB
    # "jroot", which would otherwise fail the name guard and duplicate the frame).
    if sec_flat:
        _union_into(primary, sec_flat[0])

    unique: List[ElementInfo] = []
    for sn in sec_flat[1:]:  # skip the secondary root (handled above)
        if not _boxed(sn):
            continue  # unsized chrome carries nothing to merge
        m = _find_match(sn)
        if m is not None:
            _union_into(m, sn)   # corroborate (window+client pair both fold in)
        elif _useful(sn):
            unique.append(sn)

    # Collapse secondary-unique WRAPPER PAIRS before grafting: MSAA emits a
    # window/client + the real control for one label (e.g. a Window and a Text
    # both named "字符集"), which would otherwise graft as two duplicate nodes.
    # Key by coarse geometry + name; keep the most specific (non-generic) role.
    # Only NAMED or GENERIC-wrapper nodes are collapsed — two DISTINCT unnamed
    # non-container controls (e.g. adjacent unlabeled toolbar icons whose boxes
    # quantise to the same bucket) must NOT be merged into one, so they bypass
    # the collapse and each graft on its own.
    deduped: Dict[tuple, ElementInfo] = {}
    order: List[tuple] = []
    passthrough: List[ElementInfo] = []
    for sn in unique:
        collapsible = bool(_norm_name(sn.name)) or (sn.role or "").casefold() in _GENERIC_ROLES
        if not collapsible:
            passthrough.append(sn)
            continue
        key = (round(sn.x / 4.0), round(sn.y / 4.0),
               round(sn.width / 4.0), round(sn.height / 4.0), _norm_name(sn.name))
        prev = deduped.get(key)
        if prev is None:
            deduped[key] = sn
            order.append(key)
        elif ((prev.role or "").casefold() in _GENERIC_ROLES
              and (sn.role or "").casefold() not in _GENERIC_ROLES):
            deduped[key] = sn  # replace generic wrapper with the specific control

    grafted: List[ElementInfo] = []
    for sn in [deduped[k] for k in order] + passthrough:
        parent = _smallest_container(prim_boxed, sn) or primary
        if parent.children is None:
            parent.children = []
        leaf = _shallow_copy_leaf(sn)
        parent.children.append(leaf)
        grafted.append(leaf)

    return primary, grafted
