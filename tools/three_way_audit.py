#!/usr/bin/env python3
"""tools/three_way_audit.py — 3-way Venn audit: IDML / Scribus-SLA / build.py.

Classifies each ANNAME into one of five buckets:
  converter_bug    — in IDML + in Scribus-SLA + NOT in build.py (PRIMARY ACTION LIST)
  shared_drop      — in IDML + NOT in Scribus-SLA + NOT in build.py (both importers skip)
  match            — in all three (structural OK)
  geometry_drift   — in all three but SLA bbox != build.py bbox by > 1 mm on any axis
  suspicious_emit  — in build.py + NOT in IDML + NOT in Scribus-SLA

Inputs:
  inventory.yml     — produced by tools/idml_inventory.py (IDML spread elements)
  sla_inventory.yml — produced by tools/sla_inventory.py (Scribus PAGEOBJECT elements)
  build.py          — template build script (anname='uXXX' literals parsed)

Output: three_way_audit.yml
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

import yaml

# Tolerance in mm for geometry_drift classification.
GEOMETRY_DRIFT_THRESHOLD_MM = 1.0


# ---------------------------------------------------------------------------
# build.py parsing
# ---------------------------------------------------------------------------

def _extract_build_py_annames(build_py_path: Path) -> dict[str, dict]:
    """Parse anname='uXXX' literals from build.py.

    Returns {anname: {'prim_type': str, 'bbox_mm': dict | None}}.
    Only bare uXXX annames (no _hl / _dreiz suffixes) are returned.

    Geometry extraction: looks for x_mm, y_mm, w_mm, h_mm keyword args
    in the same primitive call as the anname.
    """
    text = build_py_path.read_text(encoding="utf-8")

    # Match primitive calls with anname inside.
    # We use a block-scan approach: find each constructor call and extract
    # all kwargs within it.
    prim_re = re.compile(
        r"(TextFrame|ImageFrame|Polygon|Oval|GraphicLine|Line)"
        r"\s*\(([^)]*?)\)",
        re.DOTALL,
    )
    anname_kw_re = re.compile(r"anname=['\"]([^'\"]+)['\"]")
    coord_re = re.compile(
        r"\b(x_mm|y_mm|w_mm|h_mm)\s*=\s*([\d.+-]+)"
    )

    result: dict[str, dict] = {}

    for m in prim_re.finditer(text):
        prim_type = m.group(1)
        block = m.group(2)
        anname_m = anname_kw_re.search(block)
        if not anname_m:
            continue
        anname = anname_m.group(1)
        # Only bare uXXX annames (skip synthetic _hl, _dreiz, etc.)
        if not re.fullmatch(r"u[0-9a-f]+", anname):
            continue
        if anname in result:
            continue  # first occurrence wins

        coords: dict[str, float] = {}
        for cm in coord_re.finditer(block):
            try:
                coords[cm.group(1)] = float(cm.group(2))
            except ValueError:
                pass

        bbox_mm: Optional[dict] = None
        if len(coords) >= 2:
            bbox_mm = {
                "x": coords.get("x_mm"),
                "y": coords.get("y_mm"),
                "w": coords.get("w_mm"),
                "h": coords.get("h_mm"),
            }

        result[anname] = {
            "prim_type": prim_type,
            "bbox_mm": bbox_mm,
        }

    # Also capture any bare anname not caught by the above (e.g. multiline).
    all_annames_re = re.compile(r"anname=['\"]([^'\"]+)['\"]")
    for m in all_annames_re.finditer(text):
        anname = m.group(1)
        if not re.fullmatch(r"u[0-9a-f]+", anname):
            continue
        if anname not in result:
            result[anname] = {"prim_type": "unknown", "bbox_mm": None}

    return result


# ---------------------------------------------------------------------------
# inventory.yml parsing
# ---------------------------------------------------------------------------

def _load_idml_dropped_annames(inventory_path: Path) -> set[str]:
    """Return IDML Self IDs that are listed as dropped in inventory.yml."""
    data = yaml.safe_load(inventory_path.read_text(encoding="utf-8"))
    annames: set[str] = set()
    for spread in data.get("spreads", []):
        for item in spread.get("elements_dropped", []):
            annames.add(item["self"])
    return annames


# ---------------------------------------------------------------------------
# Geometry drift check
# ---------------------------------------------------------------------------

def _bbox_drift(sla_bbox: dict, build_bbox: dict) -> Optional[dict]:
    """Return per-axis delta if any axis exceeds GEOMETRY_DRIFT_THRESHOLD_MM, else None."""
    axes = ("x", "y", "w", "h")
    deltas: dict[str, float] = {}
    for ax in axes:
        sv = sla_bbox.get(ax)
        bv = build_bbox.get(ax)
        if sv is None or bv is None:
            continue
        delta = abs(sv - bv)
        if delta > GEOMETRY_DRIFT_THRESHOLD_MM:
            deltas[ax] = round(sv - bv, 3)
    return deltas if deltas else None


# ---------------------------------------------------------------------------
# Main audit logic
# ---------------------------------------------------------------------------

def run_three_way_audit(
    inventory_path: Path,
    sla_inventory_path: Path,
    build_py_path: Path,
    template: Optional[str] = None,
) -> dict:
    """Produce the 3-way Venn audit report dict."""
    if template is None:
        template = build_py_path.parent.name

    # Load sla_inventory.
    sla_data = yaml.safe_load(sla_inventory_path.read_text(encoding="utf-8"))
    sla_objs: dict[str, dict] = sla_data.get("pageobjects_by_anname", {})
    # Filter to bare uXXX annames only.
    sla_annames = {k for k in sla_objs if re.fullmatch(r"u[0-9a-f]+", k)}

    # Load build.py annames.
    build_annames_full = _extract_build_py_annames(build_py_path)
    build_annames = set(build_annames_full.keys())

    # Load IDML inventory — dropped elements only.
    # Items emitted from IDML are present in build.py + SLA (both importers).
    idml_dropped = _load_idml_dropped_annames(inventory_path)
    # "In IDML" = dropped items + items in SLA (Scribus imported them from IDML)
    # + build.py items that are also in SLA (our converter handled them).
    # We conservatively define: in_idml = dropped OR in_sla OR in_build_and_in_sla.
    # For the Venn logic below, we track idml_dropped separately.

    # Universe = union of all three sources.
    all_annames = idml_dropped | sla_annames | build_annames

    # Classification buckets.
    converter_bug: list[dict] = []
    shared_drop: list[dict] = []
    match_: list[dict] = []
    geometry_drift: list[dict] = []
    suspicious_emit: list[dict] = []

    for anname in sorted(all_annames):
        in_idml_dropped = anname in idml_dropped
        in_sla = anname in sla_annames
        in_build = anname in build_annames
        # "In IDML" = definitively dropped from IDML OR imported by Scribus (in SLA)
        # OR emitted by our converter (in build.py AND in SLA — both processed same IDML).
        in_idml = in_idml_dropped or in_sla or (in_build and in_sla)

        sla_obj = sla_objs.get(anname, {})

        if in_idml_dropped and in_sla and not in_build:
            # Converter bug — IDML dropped + Scribus handled it, we didn't.
            entry: dict = {
                "anname": anname,
                "ptype_label": sla_obj.get("ptype_label", "unknown"),
                "bbox_mm": sla_obj.get("bbox_mm"),
                "fcolor": sla_obj.get("fcolor"),
                "pcolor": sla_obj.get("pcolor"),
                "page": sla_obj.get("page"),
                "hint": "extract PAGEOBJECT geometry from Scribus-SLA into build.py",
            }
            if sla_obj.get("linescolor"):
                entry["linescolor"] = sla_obj["linescolor"]
            if sla_obj.get("in_group"):
                entry["in_group"] = sla_obj["in_group"]
            converter_bug.append(entry)

        elif in_idml_dropped and not in_sla and not in_build:
            # Shared drop — both our converter and Scribus skip this.
            shared_drop.append({"anname": anname})

        elif in_sla and in_build:
            # In SLA + in build.py → check geometry drift.
            build_info = build_annames_full.get(anname, {})
            build_bbox = build_info.get("bbox_mm")
            sla_bbox = sla_obj.get("bbox_mm")

            if build_bbox and sla_bbox:
                deltas = _bbox_drift(sla_bbox, build_bbox)
                if deltas:
                    geometry_drift.append({
                        "anname": anname,
                        "sla_bbox_mm": sla_bbox,
                        "build_py_bbox_mm": build_bbox,
                        "delta_mm": deltas,
                    })
                else:
                    match_.append({"anname": anname})
            else:
                match_.append({"anname": anname})

        elif in_build and not in_sla and not in_idml_dropped:
            # We emit something not found in SLA or IDML-dropped — suspicious.
            suspicious_emit.append({
                "anname": anname,
                "prim_type": build_annames_full.get(anname, {}).get("prim_type", "unknown"),
            })

        # Remaining edge cases (e.g. in_sla only) are not classified further.

    summary = {
        "total": len(all_annames),
        "converter_bug": len(converter_bug),
        "shared_drop": len(shared_drop),
        "match": len(match_),
        "geometry_drift": len(geometry_drift),
        "suspicious_emit": len(suspicious_emit),
    }

    return {
        "template": template,
        "total_annames": len(all_annames),
        "classification": {
            "converter_bug": converter_bug,
            "geometry_drift": geometry_drift,
            "match": match_,
            "shared_drop": shared_drop,
            "suspicious_emit": suspicious_emit,
        },
        "summary": summary,
    }


def _yaml_dump(data: dict) -> str:
    return yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=True,
        width=120,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="three_way_audit",
        description="3-way Venn audit: IDML / Scribus-SLA / build.py.",
    )
    parser.add_argument(
        "--inventory", required=True, type=Path,
        help="inventory.yml from tools/idml_inventory.py",
    )
    parser.add_argument(
        "--sla-inventory", required=True, type=Path,
        help="sla_inventory.yml from tools/sla_inventory.py",
    )
    parser.add_argument(
        "--build-py", required=True, type=Path,
        help="Template build.py path",
    )
    parser.add_argument(
        "--out", required=True, type=Path,
        help="Output three_way_audit.yml path",
    )
    parser.add_argument("--template", default=None, help="Template slug")
    args = parser.parse_args(argv)

    for p in (args.inventory, args.sla_inventory, args.build_py):
        if not p.exists():
            print(f"ERROR: not found: {p}", file=sys.stderr)
            return 1

    report = run_three_way_audit(
        args.inventory,
        args.sla_inventory,
        args.build_py,
        template=args.template,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_yaml_dump(report), encoding="utf-8")

    s = report["summary"]
    print(
        f"[{report['template']}] three_way_audit: "
        f"{s['converter_bug']} converter_bug, "
        f"{s['geometry_drift']} geometry_drift, "
        f"{s['suspicious_emit']} suspicious_emit "
        f"→ REVIEW",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
