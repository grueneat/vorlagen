#!/usr/bin/env python3
"""Structural diff for Scribus 1.6 SLA files.

Compares two SLAs after a normalisation pipeline that absorbs all volatile
attributes (ItemID renumbering, attribute order, float precision, scratch-canvas
position) so the comparison reflects semantic differences only.

Output: per-element issues with severity (critical / warning / info) plus a
JSON / Markdown reporter. Exit codes: 0 when no critical (and no warning when
``--strict``), 1 otherwise.

Pipeline (see RESEARCH.md §sla_diff strategy):

    1. Parse with attribute order preserved
    2. Strip volatile DOCUMENT-level attributes (DOCSAVED, DOCDATE, ...)
    3. Renumber ItemIDs sequentially in document order, propagating
       NEXTITEM / BACKITEM / WeldSource / WeldID via an old->new map
    4. Drop FRAMEOBJECTs (orphan scratch items)
    5. Sort PAGEOBJECTs by (OwnPage, YPOS, XPOS); MASTEROBJECTs analogously
    6. Round floating-point attributes to 6 decimals (incl. path coords)
    7. Sort element attribute order alphabetically before serialise
    8. Drop default-equivalent attributes (LOCALSCX=1, ROT=0, ...)
    9. Re-base item XPOS/YPOS to page-local; strip PAGEXPOS/PAGEYPOS
   10. Sort COLOR / STYLE / CHARSTYLE / LAYERS lists by NAME
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from base64 import b64decode
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional
import zlib

from lxml import etree


SEVERITY_CRITICAL = "critical"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

_SEVERITY_ORDER = {SEVERITY_CRITICAL: 0, SEVERITY_WARNING: 1, SEVERITY_INFO: 2}

# Tolerances per RESEARCH.md §Severity rules.
POSITION_TOLERANCE_PT = 0.5
SIZE_TOLERANCE_PT = 0.5
PAGE_SIZE_TOLERANCE_PT = 0.01
ROT_TOLERANCE_DEG = 0.5
FONTSIZE_TOLERANCE_PT = 0.5

# Default-equivalent attributes dropped before comparison. Any attribute equal
# to the listed value is removed; missing attributes that would default to
# this value are not added (Scribus treats absence and default identically).
DEFAULT_EQUIVALENTS: dict[str, str] = {
    "LOCALSCX": "1",
    "LOCALSCY": "1",
    "LOCALX": "0",
    "LOCALY": "0",
    "LOCALROT": "0",
    "SCALETYPE": "1",
    "RATIO": "1",
    "PICART": "1",
    "ROT": "0",
    "NEXTITEM": "-1",
    "BACKITEM": "-1",
    "LINESPMode": "2",
    "LINESP": "15",
    "gWidth": "0",
    "gHeight": "0",
    "PWIDTH": "0",
    "CLIPEDIT": "0",
    "PLINEART": "1",
    "FLOP": "1",
    "PLTSHOW": "0",
    "BASEOF": "0",
    "textPathType": "0",
    "textPathFlipped": "0",
    "EXTRA": "0",
    "TEXTRA": "0",
    "BEXTRA": "0",
    "REXTRA": "0",
    "VAlign": "0",
    "AUTOTEXT": "0",
}

# Attributes treated as info-level (auto-generated, locale-stamped, etc.).
INFO_ONLY_ATTRS = {"ANNAME", "DOCSAVED", "DOCDATE"}

# DOCUMENT-level attributes stripped before compare (volatile / runtime).
VOLATILE_DOC_ATTRS = {
    "DOCSAVED",
    "DOCDATE",
    "currentProfile",
    "AUTOSAVE",
    "AUTOSAVETIME",
    "AUTOSAVECOUNT",
    "AUTOSAVEKEEP",
    "AUTOSAVEDIR",
    "AUTOSAVEINDOCDIR",
    "DSAVE",
    "ScratchTop",
    "ScratchLeft",
    "ScratchRight",
    "ScratchBottom",
    "GapHorizontal",
    "GapVertical",
}

# PAGE-level attributes stripped before compare.
VOLATILE_PAGE_ATTRS = {"PAGEXPOS", "PAGEYPOS"}

# PTYPE-keyed defaults that the DSL emits but originals omit.
PTYPE_DEFAULTS_PER_TYPE = {
    "4": {"PWIDTH": "0", "AUTOTEXT": "0"},
    "2": {"PWIDTH": "0"},
    "5": {},
    "6": {},
}

_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")


# ---------------------------------------------------------------------------
# Issue / report dataclasses (shape mirrors tools/check_ci.py)
# ---------------------------------------------------------------------------
@dataclass
class Issue:
    severity: str
    code: str
    path: str = ""
    attr: str = ""
    left: str = ""
    right: str = ""
    detail: str = ""

    def short(self) -> str:
        s = f"[{self.severity}] {self.code}"
        if self.path:
            s += f" @ {self.path}"
        if self.attr:
            s += f" .{self.attr}"
        if self.left or self.right:
            s += f" left={self.left!r} right={self.right!r}"
        if self.detail:
            s += f" — {self.detail}"
        return s


@dataclass
class DiffReport:
    left: str
    right: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        out = {SEVERITY_CRITICAL: 0, SEVERITY_WARNING: 0, SEVERITY_INFO: 0}
        for i in self.issues:
            out[i.severity] = out.get(i.severity, 0) + 1
        return out

    @property
    def has_critical(self) -> bool:
        return self.summary[SEVERITY_CRITICAL] > 0

    @property
    def has_warning(self) -> bool:
        return self.summary[SEVERITY_WARNING] > 0


# ---------------------------------------------------------------------------
# Normalisation pipeline
# ---------------------------------------------------------------------------
def _round_float_str(value: str) -> str:
    if _FLOAT_RE.match(value):
        return f"{float(value):.6f}"
    return value


_PATH_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _round_path_coords(path: str) -> str:
    """Round every numeric token in an SVG-like path string to 6 decimals."""
    def repl(m: re.Match) -> str:
        v = m.group(0)
        if "." in v:
            return f"{float(v):.6f}"
        # Integer coordinate: preserve as-is so 'M0 0' stays 'M0 0'
        return v
    return _PATH_NUMBER_RE.sub(repl, path)


def parse_sla(path: Path) -> etree._ElementTree:
    parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False)
    return etree.parse(str(path), parser)


def strip_volatile_doc_attrs(tree: etree._ElementTree) -> None:
    doc = tree.getroot().find("DOCUMENT")
    if doc is None:
        return
    for k in list(doc.attrib.keys()):
        if k in VOLATILE_DOC_ATTRS:
            del doc.attrib[k]


def renumber_item_ids(tree: etree._ElementTree, start: int = 100_000_000) -> dict[str, str]:
    """Renumber ItemIDs sequentially in document order across PAGEOBJECT and
    MASTEROBJECT (FRAMEOBJECTs are dropped first by the caller).

    Updates every NEXTITEM / BACKITEM / WeldSource / WeldID reference in
    lockstep so chains and welds remain intact.

    Returns the old->new map for downstream callers if needed.
    """
    doc = tree.getroot().find("DOCUMENT")
    if doc is None:
        return {}
    next_id = start
    old_to_new: dict[str, str] = {}
    for el in doc.iter():
        if el.tag in ("PAGEOBJECT", "MASTEROBJECT"):
            old = el.attrib.get("ItemID")
            if old is None:
                continue
            new = str(next_id)
            old_to_new[old] = new
            el.set("ItemID", new)
            next_id += 1
    # Update references everywhere
    for el in doc.iter():
        for ref_attr in ("NEXTITEM", "BACKITEM", "WeldSource", "WeldID"):
            if ref_attr in el.attrib:
                v = el.attrib[ref_attr]
                if v in old_to_new:
                    el.set(ref_attr, old_to_new[v])
                # -1 sentinel and unknown ids are left alone
    return old_to_new


def drop_frameobjects(tree: etree._ElementTree) -> int:
    """Remove FRAMEOBJECT elements (orphan scratch items, OwnPage=-1)."""
    doc = tree.getroot().find("DOCUMENT")
    if doc is None:
        return 0
    count = 0
    for el in list(doc.findall("FRAMEOBJECT")):
        doc.remove(el)
        count += 1
    return count


def sort_pageobjects(tree: etree._ElementTree) -> None:
    doc = tree.getroot().find("DOCUMENT")
    if doc is None:
        return
    pageobjects = list(doc.findall("PAGEOBJECT"))
    masterobjects = list(doc.findall("MASTEROBJECT"))
    # Detach
    for el in pageobjects + masterobjects:
        doc.remove(el)
    # Sort
    pageobjects.sort(key=lambda e: (
        int(e.attrib.get("OwnPage", "0")),
        round(float(e.attrib.get("YPOS", "0")), 6),
        round(float(e.attrib.get("XPOS", "0")), 6),
    ))
    masterobjects.sort(key=lambda e: (
        e.attrib.get("OnMasterPage", ""),
        round(float(e.attrib.get("YPOS", "0")), 6),
        round(float(e.attrib.get("XPOS", "0")), 6),
    ))
    # Append in canonical order: MASTEROBJECTs then PAGEOBJECTs (matches
    # Scribus's emission order — masters first per scribus150format_save.cpp).
    for el in masterobjects:
        doc.append(el)
    for el in pageobjects:
        doc.append(el)


def round_floats(tree: etree._ElementTree) -> None:
    for el in tree.getroot().iter():
        for k, v in list(el.attrib.items()):
            if k in ("path", "copath"):
                el.set(k, _round_path_coords(v))
            else:
                rounded = _round_float_str(v)
                if rounded != v:
                    el.set(k, rounded)


def drop_default_equivalents(tree: etree._ElementTree) -> None:
    """Remove attributes equal to their Scribus default. Applied per element.

    Per-paragraph control elements (<para>/<trail>) are left untouched so the
    storytext-attr comparator can see explicit overrides verbatim, including
    values that happen to match a frame-level default (e.g. <para
    LINESPMode="2"/> overriding a parent style whose LINESPMode is not 2).
    Stripping defaults there would silently absorb genuine round-trip drops.
    """
    for el in tree.getroot().iter():
        if el.tag in ("para", "trail"):
            continue
        for k, default in DEFAULT_EQUIVALENTS.items():
            if k in el.attrib and el.attrib[k] in (default, _round_float_str(default)):
                # Special case: gXpos / gYpos are dropped only if equal to XPOS / YPOS
                del el.attrib[k]
        # gXpos / gYpos drop when equal to XPOS / YPOS (group bounding-box default)
        if "gXpos" in el.attrib and "XPOS" in el.attrib:
            if el.attrib["gXpos"] == el.attrib["XPOS"]:
                del el.attrib["gXpos"]
        if "gYpos" in el.attrib and "YPOS" in el.attrib:
            if el.attrib["gYpos"] == el.attrib["YPOS"]:
                del el.attrib["gYpos"]
        # Per-PTYPE defaults (DSL emits PWIDTH=0 on TextFrame/ImageFrame; original
        # omits it on the same frame types).
        ptype = el.attrib.get("PTYPE")
        if ptype in PTYPE_DEFAULTS_PER_TYPE:
            for k, default in PTYPE_DEFAULTS_PER_TYPE[ptype].items():
                if k in el.attrib and el.attrib[k] in (default, _round_float_str(default)):
                    del el.attrib[k]


def rebase_item_coords_to_page_local(tree: etree._ElementTree) -> None:
    """Subtract the owning page's PAGEXPOS/PAGEYPOS from every PAGEOBJECT
    XPOS/YPOS so coords are page-local. MASTEROBJECTs are rebased against
    their owning MASTERPAGE."""
    doc = tree.getroot().find("DOCUMENT")
    if doc is None:
        return
    page_origin: dict[int, tuple[float, float]] = {}
    for page in doc.findall("PAGE"):
        try:
            num = int(page.attrib.get("NUM", "-1"))
        except ValueError:
            continue
        page_origin[num] = (
            float(page.attrib.get("PAGEXPOS", "0")),
            float(page.attrib.get("PAGEYPOS", "0")),
        )
    master_origin: dict[str, tuple[float, float]] = {}
    for m in doc.findall("MASTERPAGE"):
        nam = m.attrib.get("NAM", "")
        master_origin[nam] = (
            float(m.attrib.get("PAGEXPOS", "0")),
            float(m.attrib.get("PAGEYPOS", "0")),
        )
    # Rebase
    for el in doc.findall("PAGEOBJECT"):
        try:
            own = int(el.attrib.get("OwnPage", "-1"))
        except ValueError:
            continue
        if own in page_origin:
            ox, oy = page_origin[own]
            xpos = float(el.attrib.get("XPOS", "0")) - ox
            ypos = float(el.attrib.get("YPOS", "0")) - oy
            el.set("XPOS", f"{xpos:.6f}")
            el.set("YPOS", f"{ypos:.6f}")
            # Also rebase gXpos/gYpos if still present
            if "gXpos" in el.attrib:
                el.set("gXpos", f"{float(el.attrib['gXpos']) - ox:.6f}")
            if "gYpos" in el.attrib:
                el.set("gYpos", f"{float(el.attrib['gYpos']) - oy:.6f}")
    for el in doc.findall("MASTEROBJECT"):
        nam = el.attrib.get("OnMasterPage", "")
        if nam in master_origin:
            ox, oy = master_origin[nam]
            xpos = float(el.attrib.get("XPOS", "0")) - ox
            ypos = float(el.attrib.get("YPOS", "0")) - oy
            el.set("XPOS", f"{xpos:.6f}")
            el.set("YPOS", f"{ypos:.6f}")
    # Strip PAGEXPOS/PAGEYPOS from PAGE/MASTERPAGE
    for el in list(doc.findall("PAGE")) + list(doc.findall("MASTERPAGE")):
        for k in VOLATILE_PAGE_ATTRS:
            if k in el.attrib:
                del el.attrib[k]


def sort_palette_lists(tree: etree._ElementTree) -> None:
    """Sort COLOR / STYLE / CHARSTYLE / LAYERS lists by NAME (or CNAME, or
    LEVEL for LAYERS — LAYERS uses NAME)."""
    doc = tree.getroot().find("DOCUMENT")
    if doc is None:
        return
    for tag, key_attr in (
        ("COLOR", "NAME"),
        ("STYLE", "NAME"),
        ("CHARSTYLE", "CNAME"),
        ("LAYERS", "NAME"),
    ):
        elements = list(doc.findall(tag))
        if not elements:
            continue
        # Find the first occurrence index so we can re-insert at the same spot.
        first = list(doc).index(elements[0])
        for el in elements:
            doc.remove(el)
        elements.sort(key=lambda e: e.attrib.get(key_attr, ""))
        for offset, el in enumerate(elements):
            doc.insert(first + offset, el)


def normalise(tree: etree._ElementTree) -> etree._ElementTree:
    """Run the full pipeline on a parsed tree (mutates in place + returns it)."""
    strip_volatile_doc_attrs(tree)
    drop_frameobjects(tree)
    renumber_item_ids(tree)
    sort_pageobjects(tree)
    round_floats(tree)
    drop_default_equivalents(tree)
    rebase_item_coords_to_page_local(tree)
    sort_palette_lists(tree)
    return tree


def serialise_normalised(tree: etree._ElementTree) -> bytes:
    """Serialise after sorting attribute order alphabetically per element.
    Two trees that normalise to the same logical content always yield identical
    bytes from this function."""
    # Recursively rebuild the tree with attributes in alphabetic order.
    def rebuild(el: etree._Element) -> etree._Element:
        new = etree.Element(el.tag)
        for k in sorted(el.attrib.keys()):
            new.set(k, el.attrib[k])
        if el.text is not None:
            new.text = el.text
        if el.tail is not None:
            new.tail = el.tail
        for child in el:
            new.append(rebuild(child))
        return new
    new_root = rebuild(tree.getroot())
    return etree.tostring(new_root, encoding="UTF-8", xml_declaration=True)


# ---------------------------------------------------------------------------
# Comparator — runs on two normalised trees
# ---------------------------------------------------------------------------
def _attr_float(el: etree._Element, attr: str, default: float = 0.0) -> float:
    try:
        return float(el.attrib.get(attr, str(default)))
    except (TypeError, ValueError):
        return default


def _is_rectangular_path(path: str, width: float, height: float) -> bool:
    """Per RESEARCH.md rectangle-equivalence rule: a path matching one of the
    two canonical 5-vertex closed-rectangle forms (CW or CCW) is equivalent to
    FRTYPE=0 if the WIDTH/HEIGHT of the frame match.

    The path is the post-rounding rounded coordinates form (6 decimals). We
    compare numerically rather than textually to absorb formatting drift.
    """
    if not path:
        return False
    nums = _PATH_NUMBER_RE.findall(path)
    try:
        coords = [float(x) for x in nums]
    except ValueError:
        return False
    # 5 vertices = 10 coordinates (5 (x,y) pairs)
    if len(coords) < 10:
        return False
    pairs = [(coords[i], coords[i + 1]) for i in range(0, 10, 2)]
    # CW: (0,0), (W,0), (W,H), (0,H), (0,0)
    cw = [(0, 0), (width, 0), (width, height), (0, height), (0, 0)]
    # CCW: (0,0), (0,H), (W,H), (W,0), (0,0)
    ccw = [(0, 0), (0, height), (width, height), (width, 0), (0, 0)]

    def close(a: tuple[float, float], b: tuple[float, float], tol: float = 1e-3) -> bool:
        return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol

    cw_match = all(close(p, q) for p, q in zip(pairs[:5], cw))
    ccw_match = all(close(p, q) for p, q in zip(pairs[:5], ccw))
    return cw_match or ccw_match


def _decode_inline_image_sha(image_data_b64: str) -> Optional[str]:
    """Decode a Scribus inline ImageData blob and return SHA-256 of the inner
    bytes. Format per .research/01-sla-format.md §5: base64 of qCompress-ed
    PNG bytes; qCompress = 4-byte big-endian length prefix + zlib stream.

    Returns None if decoding fails.
    """
    try:
        raw = b64decode(image_data_b64)
        if len(raw) < 4:
            return None
        compressed = raw[4:]
        decompressed = zlib.decompress(compressed)
        return hashlib.sha256(decompressed).hexdigest()
    except Exception:
        return None


def _chain_topology(doc: etree._Element) -> list[list[etree._Element]]:
    """Return a list of chains (each chain = list of PAGEOBJECTs in head->tail order)."""
    objs = list(doc.findall("PAGEOBJECT"))
    by_id: dict[str, etree._Element] = {}
    for o in objs:
        if o.attrib.get("PTYPE") == "4":
            by_id[o.attrib.get("ItemID", "")] = o
    chains: list[list[etree._Element]] = []
    visited: set[str] = set()
    for o in objs:
        if o.attrib.get("PTYPE") != "4":
            continue
        oid = o.attrib.get("ItemID", "")
        back = o.attrib.get("BACKITEM", "-1")
        nxt = o.attrib.get("NEXTITEM", "-1")
        if back != "-1" or nxt == "-1":
            continue  # Not a chain head OR isolated frame
        if oid in visited:
            continue
        chain = []
        cur: Optional[etree._Element] = o
        while cur is not None:
            cur_id = cur.attrib.get("ItemID", "")
            if cur_id in visited:
                break
            visited.add(cur_id)
            chain.append(cur)
            nxt_id = cur.attrib.get("NEXTITEM", "-1")
            cur = by_id.get(nxt_id) if nxt_id != "-1" else None
        if len(chain) >= 2:
            chains.append(chain)
    return chains


def _chain_hash(chain: list[etree._Element]) -> str:
    """Return a stable hash of a chain's geometry.

    Coordinates are rounded to 3 decimals (≈ 1 micrometer; far below the 0.5pt
    drift threshold) so converter mm→pt round-trip noise (which can shift a
    coordinate by ~2 microns at A4 dimensions) doesn't trigger a false-positive
    chain mismatch."""
    h = hashlib.sha256()
    for el in chain:
        try:
            tup = (
                int(el.attrib.get("OwnPage", "-1")),
                round(float(el.attrib.get("XPOS", "0")), 3),
                round(float(el.attrib.get("YPOS", "0")), 3),
                round(float(el.attrib.get("WIDTH", "0")), 3),
                round(float(el.attrib.get("HEIGHT", "0")), 3),
            )
        except ValueError:
            tup = (
                el.attrib.get("OwnPage", ""),
                el.attrib.get("XPOS", ""),
                el.attrib.get("YPOS", ""),
                el.attrib.get("WIDTH", ""),
                el.attrib.get("HEIGHT", ""),
            )
        h.update(repr(tup).encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()


def _compare_doc_attrs(left_doc: etree._Element, right_doc: etree._Element,
                       issues: list[Issue]) -> None:
    # Page count
    al = int(left_doc.attrib.get("ANZPAGES", "0"))
    ar = int(right_doc.attrib.get("ANZPAGES", "0"))
    if al != ar:
        issues.append(Issue(SEVERITY_CRITICAL, "page-count-mismatch",
                             path="DOCUMENT", attr="ANZPAGES",
                             left=str(al), right=str(ar)))
    # Page size
    for attr in ("PAGEWIDTH", "PAGEHEIGHT"):
        l = _attr_float(left_doc, attr)
        r = _attr_float(right_doc, attr)
        if abs(l - r) > PAGE_SIZE_TOLERANCE_PT:
            issues.append(Issue(SEVERITY_CRITICAL, "page-size-mismatch",
                                 path="DOCUMENT", attr=attr,
                                 left=f"{l:.6f}", right=f"{r:.6f}",
                                 detail=f"|delta| = {abs(l - r):.4f}pt > {PAGE_SIZE_TOLERANCE_PT}pt"))
    # Bleed
    for attr in ("BleedTop", "BleedBottom", "BleedLeft", "BleedRight"):
        l = _attr_float(left_doc, attr)
        r = _attr_float(right_doc, attr)
        if abs(l - r) > 0.001:
            issues.append(Issue(SEVERITY_CRITICAL, "bleed-mismatch",
                                 path="DOCUMENT", attr=attr,
                                 left=f"{l:.6f}", right=f"{r:.6f}"))


def _compare_pages(left_doc: etree._Element, right_doc: etree._Element,
                   issues: list[Issue]) -> None:
    left_pages = list(left_doc.findall("PAGE"))
    right_pages = list(right_doc.findall("PAGE"))
    # Verify each PAGE's MNAM resolves to an existing master on the same side.
    left_masters = {m.attrib.get("NAM", "") for m in left_doc.findall("MASTERPAGE")}
    right_masters = {m.attrib.get("NAM", "") for m in right_doc.findall("MASTERPAGE")}
    for side, pages, masters in (("left", left_pages, left_masters),
                                  ("right", right_pages, right_masters)):
        for p in pages:
            mnam = p.attrib.get("MNAM", "")
            if mnam and mnam not in masters:
                issues.append(Issue(SEVERITY_CRITICAL, "missing-master",
                                     path=f"PAGE[NUM={p.attrib.get('NUM','?')}] ({side})",
                                     attr="MNAM", left=mnam, right=mnam,
                                     detail=f"MNAM references nonexistent MASTERPAGE on {side}"))

    # Item count per OwnPage
    def per_page_counts(doc: etree._Element) -> dict[int, int]:
        out: dict[int, int] = {}
        for o in doc.findall("PAGEOBJECT"):
            try:
                k = int(o.attrib.get("OwnPage", "-1"))
            except ValueError:
                continue
            out[k] = out.get(k, 0) + 1
        return out
    lc = per_page_counts(left_doc)
    rc = per_page_counts(right_doc)
    all_keys = sorted(set(lc.keys()) | set(rc.keys()))
    for k in all_keys:
        if lc.get(k, 0) != rc.get(k, 0):
            issues.append(Issue(SEVERITY_CRITICAL, "page-item-count-mismatch",
                                 path=f"OwnPage={k}", attr="count",
                                 left=str(lc.get(k, 0)), right=str(rc.get(k, 0))))


def _match_items_per_page(left_doc, right_doc) -> list[tuple[Optional[etree._Element], Optional[etree._Element]]]:
    """Pair up PAGEOBJECTs after normalisation. Both sides have already been
    sorted by (OwnPage, YPOS, XPOS), so positional pairing per page works."""
    pairs: list[tuple[Optional[etree._Element], Optional[etree._Element]]] = []
    by_page_left: dict[int, list[etree._Element]] = {}
    by_page_right: dict[int, list[etree._Element]] = {}
    for o in left_doc.findall("PAGEOBJECT"):
        try:
            k = int(o.attrib.get("OwnPage", "-1"))
        except ValueError:
            continue
        by_page_left.setdefault(k, []).append(o)
    for o in right_doc.findall("PAGEOBJECT"):
        try:
            k = int(o.attrib.get("OwnPage", "-1"))
        except ValueError:
            continue
        by_page_right.setdefault(k, []).append(o)
    for k in sorted(set(by_page_left.keys()) | set(by_page_right.keys())):
        l_items = by_page_left.get(k, [])
        r_items = by_page_right.get(k, [])
        for i in range(max(len(l_items), len(r_items))):
            l = l_items[i] if i < len(l_items) else None
            r = r_items[i] if i < len(r_items) else None
            pairs.append((l, r))
    return pairs


def _compare_item(idx: int, left: etree._Element, right: etree._Element,
                  issues: list[Issue]) -> None:
    own_page = left.attrib.get("OwnPage", right.attrib.get("OwnPage", "?"))
    path = f"PAGEOBJECT[{idx}] OwnPage={own_page}"
    # PTYPE
    lp = left.attrib.get("PTYPE", "")
    rp = right.attrib.get("PTYPE", "")
    if lp != rp:
        issues.append(Issue(SEVERITY_CRITICAL, "ptype-mismatch",
                             path=path, attr="PTYPE", left=lp, right=rp))
        return
    # FRTYPE — apply rectangle-equivalence
    lf = left.attrib.get("FRTYPE", "")
    rf = right.attrib.get("FRTYPE", "")
    if lf != rf:
        if lp == rp and {lf, rf} <= {"0", "3"}:
            # Verify rectangle equivalence: both must be rect-shaped
            lw = _attr_float(left, "WIDTH")
            lh = _attr_float(left, "HEIGHT")
            rw = _attr_float(right, "WIDTH")
            rh = _attr_float(right, "HEIGHT")
            if abs(lw - rw) < 1e-3 and abs(lh - rh) < 1e-3:
                lpath = left.attrib.get("path", "")
                rpath = right.attrib.get("path", "")
                left_rect = _is_rectangular_path(lpath, lw, lh) if lf == "3" else True
                right_rect = _is_rectangular_path(rpath, rw, rh) if rf == "3" else True
                if left_rect and right_rect:
                    issues.append(Issue(SEVERITY_INFO, "frtype-rectangle-equivalent",
                                         path=path, attr="FRTYPE",
                                         left=lf, right=rf,
                                         detail="both sides describe a rectangle of identical W/H"))
                else:
                    issues.append(Issue(SEVERITY_CRITICAL, "frtype-mismatch",
                                         path=path, attr="FRTYPE", left=lf, right=rf))
            else:
                issues.append(Issue(SEVERITY_CRITICAL, "frtype-mismatch",
                                     path=path, attr="FRTYPE", left=lf, right=rf))
        else:
            issues.append(Issue(SEVERITY_CRITICAL, "frtype-mismatch",
                                 path=path, attr="FRTYPE", left=lf, right=rf))
    # Position drift
    for attr in ("XPOS", "YPOS"):
        l = _attr_float(left, attr)
        r = _attr_float(right, attr)
        if abs(l - r) > POSITION_TOLERANCE_PT:
            issues.append(Issue(SEVERITY_WARNING, "position-drift",
                                 path=path, attr=attr,
                                 left=f"{l:.6f}", right=f"{r:.6f}",
                                 detail=f"|delta| = {abs(l - r):.4f}pt > {POSITION_TOLERANCE_PT}pt"))
        elif abs(l - r) > 1e-6:
            issues.append(Issue(SEVERITY_INFO, "position-minor-drift",
                                 path=path, attr=attr,
                                 left=f"{l:.6f}", right=f"{r:.6f}",
                                 detail=f"|delta| = {abs(l - r):.4f}pt"))
    # Size drift
    for attr in ("WIDTH", "HEIGHT"):
        l = _attr_float(left, attr)
        r = _attr_float(right, attr)
        if abs(l - r) > SIZE_TOLERANCE_PT:
            issues.append(Issue(SEVERITY_WARNING, "size-drift",
                                 path=path, attr=attr,
                                 left=f"{l:.6f}", right=f"{r:.6f}",
                                 detail=f"|delta| = {abs(l - r):.4f}pt > {SIZE_TOLERANCE_PT}pt"))
    # Rotation
    lr = _attr_float(left, "ROT")
    rr = _attr_float(right, "ROT")
    if abs(lr - rr) > ROT_TOLERANCE_DEG:
        issues.append(Issue(SEVERITY_WARNING, "rotation-drift",
                             path=path, attr="ROT",
                             left=f"{lr:.4f}", right=f"{rr:.4f}",
                             detail=f"|delta| = {abs(lr - rr):.4f}deg > {ROT_TOLERANCE_DEG}deg"))
    # Color attributes (PCOLOR for polygons, FCOLOR for text frame default)
    for attr in ("PCOLOR", "PCOLOR2", "FCOLOR"):
        l = left.attrib.get(attr)
        r = right.attrib.get(attr)
        if l != r and not (l is None or r is None):
            issues.append(Issue(SEVERITY_WARNING, "color-mismatch",
                                 path=path, attr=attr, left=l or "", right=r or ""))
        elif (l is None) != (r is None):
            issues.append(Issue(SEVERITY_INFO, "color-presence-mismatch",
                                 path=path, attr=attr,
                                 left=l or "(absent)", right=r or "(absent)"))
    # ANNAME — info only
    la = left.attrib.get("ANNAME")
    ra = right.attrib.get("ANNAME")
    if la != ra:
        issues.append(Issue(SEVERITY_INFO, "anname-differs",
                             path=path, attr="ANNAME",
                             left=la or "(absent)", right=ra or "(absent)"))
    # Inline-image equivalence: if both have isInlineImage=1 with ImageData,
    # decode and compare SHA-256; if equal, info, else warning.
    li = left.attrib.get("isInlineImage")
    ri = right.attrib.get("isInlineImage")
    ld = left.attrib.get("ImageData")
    rd = right.attrib.get("ImageData")
    if (li == "1" and ld) and (ri == "1" and rd):
        lh = _decode_inline_image_sha(ld)
        rh = _decode_inline_image_sha(rd)
        if lh and rh and lh != rh:
            issues.append(Issue(SEVERITY_WARNING, "inline-image-content-mismatch",
                                 path=path, attr="ImageData",
                                 left=lh[:12], right=rh[:12]))
    elif (li == "1" and ld) and (rd is None and right.attrib.get("PFILE")):
        # Inline on left, sidecar on right — flagged critical because the
        # rendered PDF differs (qCompress↔PNG-on-disk round-trip is not
        # byte-clean and pages with inline frames showed 3-15x more
        # mismatch than pages with no images). Round-trip must preserve
        # inline ImageData verbatim.
        issues.append(Issue(SEVERITY_CRITICAL, "inline-vs-sidecar-image",
                             path=path,
                             detail=("left has inline ImageData; right has PFILE — "
                                     "round-trip MUST preserve inline data verbatim")))
    elif (ri == "1" and rd) and (ld is None and left.attrib.get("PFILE")):
        issues.append(Issue(SEVERITY_CRITICAL, "inline-vs-sidecar-image",
                             path=path,
                             detail=("right has inline ImageData; left has PFILE — "
                                     "round-trip MUST preserve inline data verbatim")))
    # StoryText paragraph attribute comparison (TextFrame only). Catches per-
    # <para>/<trail> ALIGN / LINESP / LINESPMode overrides that the converter
    # used to silently drop — the diff that would have caught PR #3's bug.
    if lp == "4" and rp == "4":
        _compare_storytext_paragraphs(left, right, path, issues)
        _compare_storytext_sequence(left, right, path, issues)


# Per-paragraph override attributes we compare on <para> and <trail>. PARENT
# (paragraph style name) is treated separately because absence on one side
# means "use frame default" — equivalent to "PARENT=<frame default>" on the
# other side. We compare it as a value, including the absent case, but never
# warn that "the original named the frame's default style explicitly".
_PARA_COMPARED_ATTRS = ("ALIGN", "LINESP", "LINESPMode", "PARENT")

# Element-kind-keyed lists of attributes whose absence/presence is critical
# (silent round-trip drop) and whose value mismatch is a warning. The element
# itself appearing/disappearing or its position in the StoryText drifting is
# always critical: those are the round-trip bugs we're hunting.
_STORYTEXT_KINDS = ("DefaultStyle", "ITEXT", "var", "para", "trail",
                     "breakline", "tab", "breakcol", "breakframe")

# DefaultStyle, ITEXT and var attribute taxonomies. Anything outside these
# whitelists is reported via the "extra-attr" warning so we discover features
# the diff doesn't yet inspect — i.e. follow the "each fix exposes the next
# silently-dropped class" pattern down to zero.
_DEFAULTSTYLE_ATTRS = ("PARENT", "LINESPMode", "LINESP", "ALIGN", "FONT",
                        "FONTSIZE", "FCOLOR", "LANGUAGE", "FONTFEATURES",
                        "FEATURES")
_ITEXT_ATTRS = ("CH", "FONT", "FONTSIZE", "FCOLOR", "FSHADE", "FONTFEATURES",
                 "FEATURES", "KERN", "TXTULP", "TXTSTP", "CPARENT", "LANGUAGE",
                 "SCOLOR", "BGCOLOR", "TXTSHX", "TXTSHY", "TXTOUT")
_VAR_ATTRS = ("name",)


def _compare_storytext_paragraphs(left: etree._Element, right: etree._Element,
                                    path: str, issues: list[Issue]) -> None:
    """Walk both frames' StoryText, align paragraph control elements
    (<para>/<trail>) by index, and report attribute-set diffs.

    A missing override on one side (e.g. left has ALIGN="0", right has no
    ALIGN) is critical: the round-trip dropped a semantically-meaningful
    override. A different value (left ALIGN="0", right ALIGN="1") is a
    warning — visible drift but recoverable. Mismatched paragraph counts
    are critical (text content is structurally different).
    """
    l_story = left.find("StoryText")
    r_story = right.find("StoryText")
    if l_story is None or r_story is None:
        return
    l_paras = [c for c in l_story if c.tag in ("para", "trail")]
    r_paras = [c for c in r_story if c.tag in ("para", "trail")]
    if len(l_paras) != len(r_paras):
        issues.append(Issue(SEVERITY_CRITICAL, "para-count-mismatch",
                             path=path, attr="StoryText",
                             left=str(len(l_paras)), right=str(len(r_paras)),
                             detail="number of <para>/<trail> elements differs"))
        return
    for idx, (lp, rp) in enumerate(zip(l_paras, r_paras)):
        if lp.tag != rp.tag:
            issues.append(Issue(SEVERITY_CRITICAL, "para-kind-mismatch",
                                 path=f"{path} StoryText[{idx}]",
                                 left=lp.tag, right=rp.tag,
                                 detail="paragraph control element kind differs"))
            continue
        for attr in _PARA_COMPARED_ATTRS:
            lv = lp.attrib.get(attr)
            rv = rp.attrib.get(attr)
            if lv == rv:
                continue
            # Presence asymmetry is the critical case: this is the round-trip
            # failure we're guarding against. The bug in PR #3 manifests
            # exactly here: ALIGN="0" on the original, no ALIGN on the
            # rebuilt SLA.
            if lv is None or rv is None:
                issues.append(Issue(SEVERITY_CRITICAL, "para-attr-missing",
                                     path=f"{path} StoryText[{idx}] <{lp.tag}>",
                                     attr=attr,
                                     left=lv if lv is not None else "(absent)",
                                     right=rv if rv is not None else "(absent)",
                                     detail="per-paragraph override present on one side, missing on the other"))
            else:
                issues.append(Issue(SEVERITY_WARNING, "para-attr-value-mismatch",
                                     path=f"{path} StoryText[{idx}] <{lp.tag}>",
                                     attr=attr,
                                     left=lv, right=rv,
                                     detail="per-paragraph override value differs"))


def _compare_storytext_sequence(left: etree._Element, right: etree._Element,
                                 path: str, issues: list[Issue]) -> None:
    """Position-aware comparison of every child of <StoryText> on both sides.

    The original Scribus model puts content (ITEXT, var) BEFORE a separator
    (para / breakline / tab / breakcol / breakframe / trail). PR #4 emitted
    the page-number frame's `<var name="pgno"/>` AFTER `<para PARENT=
    "Seitenzahl"/>` — Scribus then never saw the var because it was attached
    to a non-existent next paragraph. The result: page numbers silently
    dropped on every page.

    This walker compares the FULL StoryText element sequence verbatim:

      - Length mismatch is critical.
      - Element kind at any index differing is critical (e.g. left has
        <var/> at index 1, right has <ITEXT/>).
      - A `<ITEXT CH=""/>` present on only one side is a critical
        ``storytext-spurious-empty-itext`` (this is the fingerprint of the
        old converter's "always emit at least one ITEXT then attach a
        separator" merge logic).
      - Element attributes: missing-on-one-side is critical; value mismatch
        is warning.
    """
    l_story = left.find("StoryText")
    r_story = right.find("StoryText")
    if l_story is None or r_story is None:
        return
    l_seq = list(l_story)
    r_seq = list(r_story)

    # Sequence length — fundamental structural mismatch.
    if len(l_seq) != len(r_seq):
        # Try to localise the discrepancy with a short tag preview so the
        # report tells you which kind of element drifted in count.
        l_tags = [el.tag for el in l_seq]
        r_tags = [el.tag for el in r_seq]
        issues.append(Issue(SEVERITY_CRITICAL, "storytext-length-mismatch",
                             path=path, attr="StoryText",
                             left=f"{len(l_seq)} ({','.join(l_tags)})",
                             right=f"{len(r_seq)} ({','.join(r_tags)})",
                             detail=("StoryText element-sequence length differs"
                                     " — content was added or dropped during round-trip")))
        # Continue to the per-position comparison up to the shorter length so
        # the operator gets the FIRST mismatch position, too.

    n = min(len(l_seq), len(r_seq))
    for idx in range(n):
        le = l_seq[idx]
        re_ = r_seq[idx]
        if le.tag != re_.tag:
            # Spurious-empty-ITEXT case: one side has <ITEXT CH=""/> here, the
            # other doesn't. Surface this with a dedicated code so reports
            # name the bug exactly.
            if le.tag == "ITEXT" and not le.attrib.get("CH", ""):
                issues.append(Issue(SEVERITY_CRITICAL, "storytext-spurious-empty-itext",
                                     path=f"{path} StoryText[{idx}]",
                                     left=le.tag, right=re_.tag,
                                     detail="left has <ITEXT CH=\"\"/> at this position; right does not"))
            elif re_.tag == "ITEXT" and not re_.attrib.get("CH", ""):
                issues.append(Issue(SEVERITY_CRITICAL, "storytext-spurious-empty-itext",
                                     path=f"{path} StoryText[{idx}]",
                                     left=le.tag, right=re_.tag,
                                     detail="right has <ITEXT CH=\"\"/> at this position; left does not"))
            else:
                issues.append(Issue(SEVERITY_CRITICAL, "storytext-element-kind-mismatch",
                                     path=f"{path} StoryText[{idx}]",
                                     left=le.tag, right=re_.tag,
                                     detail=("element type at this position differs — content "
                                             "was reordered during round-trip")))
            continue

        # Same tag at this position — compare attributes by kind.
        if le.tag == "DefaultStyle":
            attrs = _DEFAULTSTYLE_ATTRS
        elif le.tag == "ITEXT":
            attrs = _ITEXT_ATTRS
        elif le.tag == "var":
            attrs = _VAR_ATTRS
        elif le.tag in ("para", "trail"):
            # Already covered by _compare_storytext_paragraphs (PARENT, ALIGN,
            # LINESP, LINESPMode). Skip to avoid double-reporting.
            continue
        else:
            # breakline / tab / breakcol / breakframe — no attributes in
            # Scribus's model; nothing further to compare.
            continue

        for attr in attrs:
            lv = le.attrib.get(attr)
            rv = re_.attrib.get(attr)
            if lv == rv:
                continue
            if lv is None or rv is None:
                # CH="" present on left but absent on right (or vice versa)
                # is allowed: an ITEXT without CH defaults to empty text.
                if le.tag == "ITEXT" and attr == "CH" and (lv == "" or rv == ""):
                    continue
                issues.append(Issue(SEVERITY_CRITICAL, "storytext-element-attr-missing",
                                     path=f"{path} StoryText[{idx}] <{le.tag}>",
                                     attr=attr,
                                     left=lv if lv is not None else "(absent)",
                                     right=rv if rv is not None else "(absent)",
                                     detail=("attribute present on one side, absent on the other "
                                             "— round-trip dropped or invented an attribute")))
            else:
                # Numeric attributes (FONTSIZE, KERN, LINESP) tolerate up to
                # 0.001 difference; everything else compares verbatim.
                if attr in ("FONTSIZE", "KERN", "LINESP"):
                    try:
                        if abs(float(lv) - float(rv)) < 0.001:
                            continue
                    except ValueError:
                        pass
                issues.append(Issue(SEVERITY_WARNING, "storytext-element-attr-value-mismatch",
                                     path=f"{path} StoryText[{idx}] <{le.tag}>",
                                     attr=attr, left=lv, right=rv,
                                     detail="attribute value differs"))


def _compare_palette(left_doc, right_doc, tag: str, key_attr: str,
                     issues: list[Issue], severity_if_extra: str) -> None:
    left_by_name = {e.attrib.get(key_attr, ""): e for e in left_doc.findall(tag)}
    right_by_name = {e.attrib.get(key_attr, ""): e for e in right_doc.findall(tag)}
    for name in left_by_name.keys() - right_by_name.keys():
        issues.append(Issue(severity_if_extra, f"missing-{tag.lower()}",
                             path=tag, attr=key_attr, left=name, right="(absent)",
                             detail=f"{tag} {name!r} present on left, absent on right"))
    for name in right_by_name.keys() - left_by_name.keys():
        issues.append(Issue(severity_if_extra, f"extra-{tag.lower()}",
                             path=tag, attr=key_attr, left="(absent)", right=name,
                             detail=f"{tag} {name!r} present on right, absent on left"))
    for name in left_by_name.keys() & right_by_name.keys():
        le = left_by_name[name]
        re_ = right_by_name[name]
        # Compare attribute sets element-wise; skip already-compared key.
        all_keys = set(le.attrib.keys()) | set(re_.attrib.keys())
        for k in sorted(all_keys):
            if k == key_attr:
                continue
            lv = le.attrib.get(k)
            rv = re_.attrib.get(k)
            if lv == rv:
                continue
            if k == "FONTSIZE":
                # Numeric tolerance
                try:
                    lf = float(lv) if lv else 0
                    rf = float(rv) if rv else 0
                except ValueError:
                    lf = rf = 0
                if abs(lf - rf) > FONTSIZE_TOLERANCE_PT:
                    issues.append(Issue(SEVERITY_WARNING, f"{tag.lower()}-fontsize-drift",
                                         path=f"{tag}[{name}]", attr=k,
                                         left=lv or "", right=rv or "",
                                         detail=f"|delta| = {abs(lf - rf):.4f}pt"))
                else:
                    issues.append(Issue(SEVERITY_INFO, f"{tag.lower()}-fontsize-minor-drift",
                                         path=f"{tag}[{name}]", attr=k,
                                         left=lv or "", right=rv or ""))
            elif k == "FCOLOR":
                issues.append(Issue(SEVERITY_WARNING, f"{tag.lower()}-fcolor-mismatch",
                                     path=f"{tag}[{name}]", attr=k,
                                     left=lv or "(absent)", right=rv or "(absent)"))
            else:
                # Other attributes: info-level (presence/value drift on style attrs).
                issues.append(Issue(SEVERITY_INFO, f"{tag.lower()}-attr-differs",
                                     path=f"{tag}[{name}]", attr=k,
                                     left=lv or "(absent)", right=rv or "(absent)"))


def _compare_layers(left_doc, right_doc, issues: list[Issue]) -> None:
    left_by_name = {e.attrib.get("NAME", ""): e for e in left_doc.findall("LAYERS")}
    right_by_name = {e.attrib.get("NAME", ""): e for e in right_doc.findall("LAYERS")}
    for name in left_by_name.keys() - right_by_name.keys():
        issues.append(Issue(SEVERITY_WARNING, "missing-layer",
                             path="LAYERS", attr="NAME", left=name, right="(absent)"))
    for name in right_by_name.keys() - left_by_name.keys():
        issues.append(Issue(SEVERITY_WARNING, "extra-layer",
                             path="LAYERS", attr="NAME", left="(absent)", right=name))
    for name in left_by_name.keys() & right_by_name.keys():
        le = left_by_name[name]
        re_ = right_by_name[name]
        for k in ("NUMMER", "LEVEL"):
            if le.attrib.get(k) != re_.attrib.get(k):
                issues.append(Issue(SEVERITY_WARNING, "layer-id-differs",
                                     path=f"LAYERS[{name}]", attr=k,
                                     left=le.attrib.get(k, ""), right=re_.attrib.get(k, "")))


def _compare_chains(left_doc, right_doc, issues: list[Issue]) -> None:
    lchains = _chain_topology(left_doc)
    rchains = _chain_topology(right_doc)
    if len(lchains) != len(rchains):
        issues.append(Issue(SEVERITY_CRITICAL, "chain-count-mismatch",
                             path="DOCUMENT", attr="chains",
                             left=str(len(lchains)), right=str(len(rchains))))
        return
    # Pair by sorted (OwnPage of head, length)
    def chain_key(chain: list[etree._Element]) -> tuple[int, int]:
        return (int(chain[0].attrib.get("OwnPage", "-1")), len(chain))
    lchains_sorted = sorted(lchains, key=chain_key)
    rchains_sorted = sorted(rchains, key=chain_key)
    for idx, (lc, rc) in enumerate(zip(lchains_sorted, rchains_sorted)):
        lk = chain_key(lc)
        rk = chain_key(rc)
        if lk != rk:
            issues.append(Issue(SEVERITY_CRITICAL, "chain-key-mismatch",
                                 path=f"chain[{idx}]",
                                 left=str(lk), right=str(rk)))
            continue
        lh = _chain_hash(lc)
        rh = _chain_hash(rc)
        if lh != rh:
            issues.append(Issue(SEVERITY_CRITICAL, "chain-hash-mismatch",
                                 path=f"chain[{idx}] page={lk[0]} length={lk[1]}",
                                 left=lh[:16], right=rh[:16],
                                 detail="member geometry diverges"))


def diff(left_path: Path, right_path: Path) -> DiffReport:
    """Top-level diff entry point. Normalises both sides, then compares."""
    left = parse_sla(left_path)
    right = parse_sla(right_path)
    normalise(left)
    normalise(right)
    report = DiffReport(left=str(left_path), right=str(right_path))
    left_doc = left.getroot().find("DOCUMENT")
    right_doc = right.getroot().find("DOCUMENT")
    if left_doc is None or right_doc is None:
        report.issues.append(Issue(SEVERITY_CRITICAL, "missing-document",
                                    detail="one or both inputs lack a DOCUMENT element"))
        return report
    _compare_doc_attrs(left_doc, right_doc, report.issues)
    _compare_pages(left_doc, right_doc, report.issues)
    _compare_palette(left_doc, right_doc, "COLOR", "NAME", report.issues, SEVERITY_WARNING)
    _compare_palette(left_doc, right_doc, "STYLE", "NAME", report.issues, SEVERITY_WARNING)
    _compare_palette(left_doc, right_doc, "CHARSTYLE", "CNAME", report.issues, SEVERITY_INFO)
    _compare_layers(left_doc, right_doc, report.issues)
    _compare_chains(left_doc, right_doc, report.issues)
    pairs = _match_items_per_page(left_doc, right_doc)
    for idx, (l, r) in enumerate(pairs):
        if l is None and r is not None:
            issues_path = f"PAGEOBJECT[{idx}] OwnPage={r.attrib.get('OwnPage','?')}"
            report.issues.append(Issue(SEVERITY_CRITICAL, "extra-pageobject",
                                        path=issues_path, right=r.attrib.get("ItemID", "")))
            continue
        if r is None and l is not None:
            issues_path = f"PAGEOBJECT[{idx}] OwnPage={l.attrib.get('OwnPage','?')}"
            report.issues.append(Issue(SEVERITY_CRITICAL, "missing-pageobject",
                                        path=issues_path, left=l.attrib.get("ItemID", "")))
            continue
        if l is not None and r is not None:
            _compare_item(idx, l, r, report.issues)
    return report


# ---------------------------------------------------------------------------
# Reporters
# ---------------------------------------------------------------------------
def report_to_json(report: DiffReport) -> str:
    summary = report.summary
    return json.dumps(
        {
            "left": report.left,
            "right": report.right,
            "summary": {k: summary[k] for k in (SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_INFO)},
            "issues": [asdict(i) for i in report.issues],
        },
        ensure_ascii=False, indent=2,
    )


def report_to_markdown(report: DiffReport) -> str:
    summary = report.summary
    lines: list[str] = []
    lines.append(f"# sla_diff: `{Path(report.left).name}` vs `{Path(report.right).name}`")
    lines.append("")
    lines.append(f"- left: `{report.left}`")
    lines.append(f"- right: `{report.right}`")
    lines.append("")
    lines.append(f"**critical: {summary[SEVERITY_CRITICAL]}**, "
                 f"warning: {summary[SEVERITY_WARNING]}, "
                 f"info: {summary[SEVERITY_INFO]}")
    lines.append("")
    if not report.issues:
        lines.append("clean — no structural differences.")
        return "\n".join(lines)
    by_sev: dict[str, list[Issue]] = {SEVERITY_CRITICAL: [], SEVERITY_WARNING: [], SEVERITY_INFO: []}
    for i in report.issues:
        by_sev[i.severity].append(i)
    for sev in (SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_INFO):
        items = by_sev[sev]
        if not items:
            continue
        lines.append(f"## {sev} ({len(items)})")
        lines.append("")
        for i in sorted(items, key=lambda x: (x.code, x.path, x.attr)):
            lines.append(f"- `{i.code}` {i.path}{(' .' + i.attr) if i.attr else ''}: "
                         f"left={i.left!r} right={i.right!r}"
                         f"{(' — ' + i.detail) if i.detail else ''}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Structural diff for Scribus SLA files.")
    ap.add_argument("--left", type=Path, required=True, help="Reference SLA")
    ap.add_argument("--right", type=Path, required=True, help="SLA to compare against the reference")
    ap.add_argument("--json", nargs="?", const="-", default=None,
                    help="Emit JSON. Path or '-' for stdout.")
    ap.add_argument("--markdown", nargs="?", const="-", default=None,
                    help="Emit Markdown. Path or '-' for stdout. Default reporter when no flag set.")
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1 also when warnings are present (default: exit 1 on critical only).")
    ap.add_argument("--allow-brand-extras", action="store_true",
                    help="Filter out 'extra-style' and 'extra-layer' warnings injected by "
                         "Brand profiles (e.g. Brand.gruene_noe()'s ci/* paragraph styles "
                         "and Bilder/Text/Hilfslinien layers). Critical issues are unaffected.")
    args = ap.parse_args(argv)
    report = diff(args.left, args.right)

    if args.allow_brand_extras:
        report.issues = [
            i for i in report.issues
            if not (i.severity == SEVERITY_WARNING and i.code in ("extra-style", "extra-layer"))
        ]

    # Default: print Markdown to stdout if no reporter selected.
    md_target = args.markdown
    json_target = args.json
    if md_target is None and json_target is None:
        md_target = "-"

    if md_target is not None:
        text = report_to_markdown(report)
        if md_target == "-":
            print(text)
        else:
            Path(md_target).write_text(text, encoding="utf-8")
    if json_target is not None:
        text = report_to_json(report)
        if json_target == "-":
            print(text)
        else:
            Path(json_target).write_text(text, encoding="utf-8")

    if report.has_critical:
        return 1
    if args.strict and report.has_warning:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
