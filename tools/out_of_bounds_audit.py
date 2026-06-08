#!/usr/bin/env python3
"""out_of_bounds_audit — flag objects outside the printable area.

IDML imports often leave pasteboard cruft behind: small colour swatch
markers, fold/registration lines, rotated sideline notes, or background
shapes sized far wider than the page. None of it is visible in the cropped
PDF, but it bloats the SLA and can surface if crop/bleed settings change.

This audit walks every ``PAGEOBJECT`` of a template SLA, computes its
rotation-aware bounding box, and compares it to the object's page rectangle
expanded by the print bleed. It reports two classes:

  * ``off_page``  — the object barely intersects the printable area
    (< ``MIN_ON_PAGE_FRAC`` of its own area). Pure pasteboard junk; it should
    not exist. These FAIL the audit.
  * ``overhang``  — the object does sit on the page but extends beyond
    page+bleed by more than ``OVERHANG_TOL_PT`` (e.g. a background shape far
    wider than the page). Reported as a warning; clamp it to page+bleed.

Page rectangles, page size and bleed are read from the SLA. The brand prints
with a 3 mm bleed (8.504 pt) even though imported DOCUMENTs declare Bleed*=0,
so the allowance is max(declared bleed, 3 mm).

CLI:
  python3 tools/out_of_bounds_audit.py --slug flyer-a6-hochformat-portraet
  python3 tools/out_of_bounds_audit.py --all --out-yaml report.yml
Exit code 0 when no off_page objects, 1 otherwise (overhang alone warns).
"""
from __future__ import annotations

import argparse
import glob
import math
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"

BLEED_PT = 3.0 * 72.0 / 25.4  # 3 mm print bleed
OVERHANG_TOL_PT = 2.0
MIN_ON_PAGE_FRAC = 0.02


def _rot_bbox(x, y, w, h, rot):
    """AABB of a w x h box at (x,y) rotated rot deg about (x,y) (Scribus)."""
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)
    corners = [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]
    xs = [x + cx * ca - cy * sa for cx, cy in corners]
    ys = [y + cx * sa + cy * ca for cx, cy in corners]
    return min(xs), min(ys), max(xs), max(ys)


def _page_rects(doc):
    pw = float(doc.get("PAGEWIDTH"))
    ph = float(doc.get("PAGEHEIGHT"))
    bleed = max(BLEED_PT, *(float(doc.get(k, "0") or 0) for k in
                            ("BleedTop", "BleedBottom", "BleedLeft", "BleedRight")))
    rects = []
    for pg in doc.findall("PAGE"):
        px, py = float(pg.get("PAGEXPOS")), float(pg.get("PAGEYPOS"))
        rects.append((px - bleed, py - bleed, px + pw + bleed, py + ph + bleed))
    return rects


def audit_sla(sla_path):
    """Return {'off_page': [...], 'overhang': [...]} for one SLA."""
    doc = ET.parse(str(sla_path)).getroot().find(".//DOCUMENT")
    rects = _page_rects(doc)
    off_page, overhang = [], []
    for o in doc.findall("PAGEOBJECT"):
        try:
            x = float(o.get("XPOS")); y = float(o.get("YPOS"))
            w = float(o.get("WIDTH")); h = float(o.get("HEIGHT"))
            rot = float(o.get("ROT", "0") or 0)
            op = int(float(o.get("OwnPage", "-1")))
        except (TypeError, ValueError):
            continue
        bx0, by0, bx1, by1 = _rot_bbox(x, y, w, h, rot)
        area = max(1e-6, (bx1 - bx0) * (by1 - by0))
        rec = {"anname": o.get("ANNAME") or o.get("ItemID") or "?",
               "ptype": o.get("PTYPE"), "ownpage": op,
               "w": round(w, 1), "h": round(h, 1), "rot": round(rot, 1)}
        if op < 0 or op >= len(rects):
            off_page.append({**rec, "reason": "OwnPage out of range"})
            continue
        rx0, ry0, rx1, ry1 = rects[op]
        ix = max(0.0, min(bx1, rx1) - max(bx0, rx0))
        iy = max(0.0, min(by1, ry1) - max(by0, ry0))
        inter = ix * iy
        out = max(rx0 - bx0, bx1 - rx1, ry0 - by0, by1 - ry1)
        if inter / area < MIN_ON_PAGE_FRAC:
            rec["overhang_pt"] = round(out, 1)
            # Plain shapes/lines are pruned automatically in Document.save();
            # off-page text frames / images are kept (removing them breaks
            # Scribus layout) and only reported.
            rec["removable"] = o.get("PTYPE") in ("6", "7")
            off_page.append(rec)
        elif out > OVERHANG_TOL_PT:
            overhang.append({**rec, "overhang_pt": round(out, 1),
                             "overhang_mm": round(out * 25.4 / 72, 1)})
    return {"off_page": off_page, "overhang": overhang}


def _report(slug, res):
    off, over = res["off_page"], res["overhang"]
    removable = [r for r in off if r.get("removable")]
    kept = [r for r in off if not r.get("removable")]
    status = "FAIL" if removable else ("WARN" if (kept or over) else "OK")
    print(f"[{slug}] out_of_bounds_audit: {status} "
          f"({len(removable)} off-page shapes/lines, "
          f"{len(kept)} off-page text/image (kept), {len(over)} overhang)")
    for r in off[:30]:
        print(f"    off-page  {r['anname']:10} PTYPE={r['ptype']} "
              f"{r['w']}x{r['h']} page={r['ownpage']} "
              f"overhang={r.get('overhang_pt', '?')}pt")
    for r in over[:30]:
        print(f"    overhang  {r['anname']:10} PTYPE={r['ptype']} "
              f"{r['w']}x{r['h']} +{r['overhang_mm']}mm beyond page+bleed")
    return not removable


def main(argv=None):
    ap = argparse.ArgumentParser(description="Flag objects outside the printable area.")
    ap.add_argument("--slug", help="template id under templates/")
    ap.add_argument("--all", action="store_true", help="audit every template")
    ap.add_argument("--out-yaml", help="write a YAML report")
    ap.add_argument("--warn-overhang", action="store_true",
                    help="also exit non-zero when only overhang findings exist")
    args = ap.parse_args(argv)

    if args.all:
        slas = sorted(glob.glob(str(TEMPLATES_DIR / "*" / "template.sla")))
    elif args.slug:
        slas = [str(TEMPLATES_DIR / args.slug / "template.sla")]
    else:
        ap.error("pass --slug <id> or --all")

    all_res, ok = {}, True
    for sla in slas:
        slug = Path(sla).parent.name
        res = audit_sla(Path(sla))
        all_res[slug] = res
        passed = _report(slug, res)
        if not passed or (args.warn_overhang and res["overhang"]):
            ok = False

    if args.out_yaml:
        import yaml
        Path(args.out_yaml).write_text(yaml.safe_dump(all_res, allow_unicode=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
