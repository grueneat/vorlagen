#!/usr/bin/env python3
"""tools/sla_inventory.py — Scribus SLA PAGEOBJECT enumeration.

Parses a Scribus .sla file and enumerates all PAGEOBJECTs (including those
nested inside Group PAGEOBJECTs). Emits sla_inventory.yml with per-element
geometry, style, and group-membership data, keyed by ANNAME.

Un-named elements receive synthetic keys __unnamed_NNN__ so they are
counted and not silently dropped.

CLI:
    python3 tools/sla_inventory.py \\
        --sla originals/.../<file>.sla \\
        --out sla_inventory.yml

Exit code: 0 always (informational tool).
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import yaml

# Points → mm conversion factor.
PT_TO_MM = 25.4 / 72.0

# Scribus PTYPE integer → human-readable label.
PTYPE_LABELS: dict[int, str] = {
    2: "image",
    4: "text",
    5: "line",
    6: "polygon",
    7: "polyline",
    8: "path_text",
    9: "latex_frame",
    10: "osg_frame",
    11: "symbol",
    12: "group",
    13: "regular_polygon",
    14: "arc",
    15: "spiral",
    16: "table",
    17: "note_frame",
}


def _pt_to_mm(val: float) -> float:
    """Convert points to millimetres, rounded to 3 decimal places."""
    return round(val * PT_TO_MM, 3)


def _parse_float(s: Optional[str], default: float = 0.0) -> float:
    if s is None:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _color_or_none(val: Optional[str]) -> Optional[str]:
    """Return the color name, or None if absent / 'None'."""
    if not val or val == "None":
        return None
    return val


def _build_page_offsets(doc_el: ET.Element) -> dict[int, tuple[float, float]]:
    """Return {page_num: (pagexpos_pt, pageypos_pt)} from <PAGE> elements.

    Scribus stores each PAGE at an absolute PAGEXPOS/PAGEYPOS offset within
    the document coordinate space. PAGEOBJECT XPOS/YPOS values are also
    document-absolute. Subtracting the page offset gives page-relative coords
    that match what build.py emits (page-local, origin = page top-left).
    """
    offsets: dict[int, tuple[float, float]] = {}
    for page_el in doc_el.findall("PAGE"):
        try:
            num = int(page_el.get("NUM", "0"))
        except ValueError:
            num = 0
        px = _parse_float(page_el.get("PAGEXPOS"))
        py = _parse_float(page_el.get("PAGEYPOS"))
        offsets[num] = (px, py)
    return offsets


def _nearest_page_offset(
    ypos_abs_pt: float,
    page_offsets: dict[int, tuple[float, float]],
    page_heights_pt: dict[int, float],
) -> tuple[float, float]:
    """For OwnPage=-1 elements, find the nearest page by YPOS and return its offset.

    Scribus assigns OwnPage=-1 to items that fall outside all page boundaries
    (e.g. registration marks in the pasteboard). These still live in document-
    absolute coordinates and should be rendered relative to the nearest page,
    matching the coordinate system used in build.py.

    Strategy: pick the page whose BOTTOM (PAGEYPOS + PAGEHEIGHT) is closest to
    or just below the item's YPOS. This correctly associates items in the
    pasteboard below a page with that page rather than the next one.
    """
    if not page_offsets:
        return (0.0, 0.0)

    def _dist_from_page(num: int) -> float:
        _, py = page_offsets[num]
        ph = page_heights_pt.get(num, 0.0)
        page_top = py
        page_bot = py + ph
        if ypos_abs_pt < page_top:
            # Item is above this page → distance to page top.
            return page_top - ypos_abs_pt
        elif ypos_abs_pt <= page_bot:
            # Item is within this page → zero distance (on-page but OwnPage=-1 is unusual).
            return 0.0
        else:
            # Item is below this page → distance to page bottom.
            return ypos_abs_pt - page_bot

    best_num = min(page_offsets.keys(), key=_dist_from_page)
    return page_offsets[best_num]


def _collect_pageobjects(
    doc_el: ET.Element,
) -> list[dict]:
    """Walk DOCUMENT → PAGEOBJECT recursively, returning a flat list of records.

    Scribus stores group children as nested PAGEOBJECT elements inside the
    parent PAGEOBJECT element (confirmed on Scribus 1.6 SLA format).
    Each record carries:
      - anname: str (or __unnamed_NNN__ for un-named items)
      - ptype: int
      - ptype_label: str
      - xpos_pt / ypos_pt / width_pt / height_pt / rot: float
        (page-relative: XPOS - PAGEXPOS, YPOS - PAGEYPOS)
      - fcolor / pcolor / linescolor: str | None
      - linewidth: float | None
      - own_page: int  (OwnPage, -1 = on multiple / scratch)
      - in_group: str | None  (ANNAME of direct parent group, or None)
    """
    records: list[dict] = []
    unnamed_counter = 0
    page_offsets = _build_page_offsets(doc_el)
    # Build page heights for nearest-page lookup (OwnPage=-1 items).
    page_heights_pt: dict[int, float] = {}
    for page_el in doc_el.findall("PAGE"):
        try:
            num = int(page_el.get("NUM", "0"))
        except ValueError:
            num = 0
        page_heights_pt[num] = _parse_float(page_el.get("PAGEHEIGHT"))

    def _walk(el: ET.Element, parent_anname: Optional[str]) -> None:
        nonlocal unnamed_counter
        for child in el:
            if child.tag != "PAGEOBJECT":
                continue
            anname = child.get("ANNAME", "")
            if not anname:
                anname = f"__unnamed_{unnamed_counter:03d}__"
                unnamed_counter += 1

            ptype_raw = child.get("PTYPE", "0")
            try:
                ptype = int(ptype_raw)
            except ValueError:
                ptype = 0

            xpos_abs = _parse_float(child.get("XPOS"))
            ypos_abs = _parse_float(child.get("YPOS"))
            width = _parse_float(child.get("WIDTH"))
            height = _parse_float(child.get("HEIGHT"))
            rot = _parse_float(child.get("ROT", "0"))

            # Convert document-absolute XPos/YPos to page-relative coords by
            # subtracting the page's own PAGEXPOS/PAGEYPOS. This matches the
            # coordinate system used in build.py (origin = page top-left).
            own_page_raw = child.get("OwnPage", "0")
            try:
                own_page_for_offset = int(own_page_raw)
            except ValueError:
                own_page_for_offset = 0
            if own_page_for_offset == -1:
                # OwnPage=-1 means Scribus treats the item as off-page (pasteboard/
                # registration mark). Use the nearest page's offset so coordinates
                # match the build.py page-relative system.
                page_ox, page_oy = _nearest_page_offset(
                    ypos_abs, page_offsets, page_heights_pt
                )
            else:
                page_ox, page_oy = page_offsets.get(own_page_for_offset, (0.0, 0.0))
            xpos = xpos_abs - page_ox
            ypos = ypos_abs - page_oy

            fcolor = _color_or_none(child.get("FCOLOR"))
            # PCOLOR is the polygon/shape fill in Scribus SLA
            pcolor = _color_or_none(child.get("PCOLOR"))
            # LINESCOLOR is the stroke color; PCOLOR2 is used for some line-type elements
            linescolor = _color_or_none(
                child.get("LINESCOLOR") or child.get("PCOLOR2")
            )

            lw_raw = child.get("LINEWIDTH") or child.get("PWIDTH")
            linewidth: Optional[float] = None
            if lw_raw is not None:
                try:
                    linewidth = float(lw_raw)
                except ValueError:
                    pass

            own_page = own_page_for_offset

            record: dict = {
                "anname": anname,
                "ptype": ptype,
                "ptype_label": PTYPE_LABELS.get(ptype, f"unknown_{ptype}"),
                "xpos_pt": xpos,
                "ypos_pt": ypos,
                "width_pt": width,
                "height_pt": height,
                "rot": rot,
                "fcolor": fcolor,
                "pcolor": pcolor,
                "linescolor": linescolor,
                "linewidth": linewidth,
                "own_page": own_page,
                "in_group": parent_anname,
            }
            records.append(record)

            # Recurse into group children (nested PAGEOBJECTs).
            if ptype == 12:
                _walk(child, anname)

    _walk(doc_el, None)
    return records


def run_sla_inventory(
    sla_path: Path,
    template: Optional[str] = None,
) -> dict:
    """Parse the SLA and return the inventory report dict."""
    if template is None:
        # Derive from parent directory or stem.
        template = sla_path.parent.name if sla_path.parent.name else sla_path.stem

    tree = ET.parse(str(sla_path))
    root = tree.getroot()
    doc = root.find("DOCUMENT")
    if doc is None:
        raise ValueError(f"{sla_path}: no <DOCUMENT> element found")

    records = _collect_pageobjects(doc)

    # Build the by-anname dict (sorted for determinism).
    pageobjects_by_anname: dict[str, dict] = {}
    for rec in records:
        anname = rec["anname"]
        entry: dict = {
            "ptype": rec["ptype"],
            "ptype_label": rec["ptype_label"],
            "bbox_mm": {
                "x": _pt_to_mm(rec["xpos_pt"]),
                "y": _pt_to_mm(rec["ypos_pt"]),
                "w": _pt_to_mm(rec["width_pt"]),
                "h": _pt_to_mm(rec["height_pt"]),
                "rot": round(rec["rot"], 3),
            },
            "fcolor": rec["fcolor"],
            "pcolor": rec["pcolor"],
            "page": rec["own_page"],
            "in_group": rec["in_group"],
        }
        if rec["linescolor"] is not None:
            entry["linescolor"] = rec["linescolor"]
        if rec["linewidth"] is not None:
            entry["linewidth"] = round(rec["linewidth"], 4)
        pageobjects_by_anname[anname] = entry

    # Sort keys for deterministic output.
    sorted_objs = dict(sorted(pageobjects_by_anname.items()))

    report = {
        "template": template,
        "reference_sla": str(sla_path),
        "pageobjects_total": len(records),
        "pageobjects_by_anname": sorted_objs,
    }
    return report


def _yaml_dump(data: dict) -> str:
    """Dump data as YAML with sorted keys and no aliases."""
    return yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=True,
        width=120,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="sla_inventory",
        description="Enumerate Scribus SLA PAGEOBJECTs and emit sla_inventory.yml.",
    )
    parser.add_argument("--sla", required=True, type=Path, help="Source Scribus SLA file path")
    parser.add_argument("--out", required=True, type=Path, help="Output YAML file path")
    parser.add_argument(
        "--template",
        default=None,
        help="Template slug (default: derived from SLA filename)",
    )
    args = parser.parse_args(argv)

    if not args.sla.exists():
        print(f"ERROR: SLA not found: {args.sla}", file=sys.stderr)
        return 1

    report = run_sla_inventory(args.sla, template=args.template)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_yaml_dump(report), encoding="utf-8")
    print(
        f"sla_inventory written → {args.out} "
        f"({report['pageobjects_total']} PAGEOBJECTs)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
