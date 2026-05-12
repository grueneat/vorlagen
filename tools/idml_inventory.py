#!/usr/bin/env python3
"""tools/idml_inventory.py — IDML spread element inventory vs build.py emitted frames.

Parses Spreads/Spread_*.xml from the source IDML (Gestaltung layer only) and
diffs the Self="uXXX" IDs against anname='uXXX' literals in the emitted build.py.

Emits inventory.yml with:
  - elements_total: count of Gestaltung-layer PageItems in the spread
  - elements_emitted: count whose Self appears as anname in build.py
  - elements_dropped: items in IDML not emitted (with type + hint)
  - elements_extra: annames in build.py not found in IDML (suspicious)

CLI:
    python3 tools/idml_inventory.py \\
        --idml originals/.../foo.idml \\
        --build-py templates/<slug>/build.py \\
        --out inventory.yml

Exit code: 0 always (informational tool).
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import yaml

# Tags considered "page items" in IDML spread XML.
PAGE_ITEM_TAGS = frozenset({
    "Rectangle", "Polygon", "Oval", "TextFrame",
    "Image", "PDF", "Group", "GraphicLine",
})

# Tags that are NOT themselves top-level items but children of them.
CHILD_CONTENT_TAGS = frozenset({"Image", "PDF"})

# Layer IDs that are printable (Gestaltung). We discover these from designmap.xml.
# Fallback: include all items when layer info is unavailable.


def _load_printable_layers(idml_zip: zipfile.ZipFile) -> set[str]:
    """Return the set of layer Self IDs that are Printable=true."""
    try:
        root = ET.fromstring(idml_zip.read("designmap.xml").decode("utf-8"))
    except Exception:
        return set()
    printable: set[str] = set()
    for el in root.iter():
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if tag == "Layer":
            if el.get("Printable", "true").lower() == "true":
                self_ = el.get("Self", "")
                if self_:
                    printable.add(self_)
    return printable


def _load_spread_order(idml_zip: zipfile.ZipFile) -> list[str]:
    """Return spread XML paths in document order from designmap.xml."""
    try:
        root = ET.fromstring(idml_zip.read("designmap.xml").decode("utf-8"))
    except Exception:
        return sorted(n for n in idml_zip.namelist() if n.startswith("Spreads/Spread_"))
    ordered: list[str] = []
    for el in root.iter():
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if tag == "Spread":
            src = el.get("src", "")
            if src:
                ordered.append(src)
    return ordered


def _build_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    """Return child→parent map for the entire element tree."""
    pm: dict[ET.Element, ET.Element] = {}
    for parent in root.iter():
        for child in parent:
            pm[child] = parent
    return pm


def _get_item_layer(el: ET.Element, parent_map: dict[ET.Element, ET.Element]) -> Optional[str]:
    """Walk up the tree to find the first ItemLayer attribute."""
    cur: Optional[ET.Element] = el
    while cur is not None:
        layer = cur.get("ItemLayer")
        if layer:
            return layer
        cur = parent_map.get(cur)
    return None


def _get_parent_group_chain(
    el: ET.Element, parent_map: dict[ET.Element, ET.Element]
) -> list[str]:
    """Return Self IDs of all ancestor Group elements."""
    groups: list[str] = []
    cur = parent_map.get(el)
    while cur is not None:
        tag = cur.tag.split("}")[-1] if "}" in cur.tag else cur.tag
        if tag == "Group":
            self_ = cur.get("Self", "")
            if self_:
                groups.append(self_)
        cur = parent_map.get(cur)
    return groups


def _has_image_or_pdf_child(el: ET.Element) -> bool:
    """Return True if the element has an Image or PDF direct child."""
    for child in el:
        ctag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if ctag in ("Image", "PDF"):
            return True
    return False


def _get_story_info(
    el: ET.Element, idml_zip: zipfile.ZipFile
) -> tuple[Optional[str], int]:
    """Return (story_self, paragraph_count) for a TextFrame, or (None, 0)."""
    story_self = el.get("ParentStory")
    if not story_self:
        return None, 0
    story_file = f"Stories/Story_{story_self}.xml"
    try:
        story_root = ET.fromstring(idml_zip.read(story_file).decode("utf-8"))
    except Exception:
        return story_self, 0
    paras = sum(
        1 for s in story_root.iter()
        if (s.tag.split("}")[-1] if "}" in s.tag else s.tag) == "ParagraphStyleRange"
    )
    return story_self, paras


def _bbox_from_element(el: ET.Element) -> Optional[list[float]]:
    """Compute bounding box [x, y, w, h] in points from PathPointArray + ItemTransform.

    Returns None when PathPointArray is absent (Groups, etc.).
    This is best-effort: only handles identity + translate transforms.
    """
    transform = el.get("ItemTransform", "1 0 0 1 0 0")
    parts = transform.split()
    try:
        tx = float(parts[4])
        ty = float(parts[5])
    except (IndexError, ValueError):
        tx = ty = 0.0

    # Find PathPointArray
    ppa = None
    for child in el.iter():
        ctag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if ctag == "PathPointArray":
            ppa = child
            break
    if ppa is None:
        return None

    xs: list[float] = []
    ys: list[float] = []
    for pp in ppa:
        anchor = pp.get("Anchor", "")
        if anchor:
            try:
                ax, ay = (float(v) for v in anchor.split())
                xs.append(ax + tx)
                ys.append(ay + ty)
            except ValueError:
                pass
    if not xs:
        return None
    x0, y0 = min(xs), min(ys)
    x1, y1 = max(xs), max(ys)
    return [round(x0, 3), round(y0, 3), round(x1 - x0, 3), round(y1 - y0, 3)]


def _build_hint(
    el: ET.Element,
    tag: str,
    parent_groups: list[str],
    idml_zip: zipfile.ZipFile,
) -> str:
    """Build a human-readable hint for a dropped element."""
    parts: list[str] = []

    if tag in ("Rectangle", "Polygon", "Oval"):
        fill = el.get("FillColor", "")
        stroke = el.get("StrokeColor", "")
        has_content = _has_image_or_pdf_child(el)
        if (fill or stroke) and not has_content:
            parts.append("inline vector path (no <Image>/<PDF> child)")
        elif has_content:
            parts.append("has Image/PDF child but not emitted")

    if tag == "TextFrame":
        story_self, para_count = _get_story_info(el, idml_zip)
        if story_self:
            parts.append(f"story {story_self}, {para_count} paragraph(s)")
        else:
            parts.append("text frame, empty story")

    if tag == "Group":
        parts.append("group container")

    if tag == "GraphicLine":
        parts.append("graphic line")

    if parent_groups:
        parts.append(f"inside Group {parent_groups[0]}")

    if not parts:
        parts.append(f"{tag} element")

    return "; ".join(parts)


def _collect_spread_items(
    spread_xml: bytes,
    printable_layers: set[str],
    idml_zip: zipfile.ZipFile,
    spread_id: str,
) -> list[dict]:
    """Return list of page-item dicts for Gestaltung-layer items in the spread."""
    root = ET.fromstring(spread_xml.decode("utf-8"))
    parent_map = _build_parent_map(root)
    items: list[dict] = []

    for el in root.iter():
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if tag not in PAGE_ITEM_TAGS:
            continue
        # Skip child Image/PDF (they are content inside Rectangle, not top-level)
        parent = parent_map.get(el)
        if parent is not None:
            ptag = parent.tag.split("}")[-1] if "}" in parent.tag else parent.tag
            if ptag in PAGE_ITEM_TAGS and tag in CHILD_CONTENT_TAGS:
                continue

        self_ = el.get("Self", "")
        if not self_:
            continue

        # Layer filter: only printable (Gestaltung) items
        layer = _get_item_layer(el, parent_map)
        if printable_layers and layer not in printable_layers:
            continue

        parent_groups = _get_parent_group_chain(el, parent_map)

        # Group containers are intentionally omitted from build.py: the
        # converter flattens Groups, emitting only their leaf children.
        # Marking Groups as "dropped" causes three_way_audit to falsely flag
        # them as converter_bug (the children ARE emitted with their own
        # annames). Skip Group elements here so they don't appear in the
        # dropped inventory.
        if tag == "Group":
            continue

        bbox = _bbox_from_element(el)
        hint = _build_hint(el, tag, parent_groups, idml_zip)

        item: dict = {
            "self": self_,
            "type": tag,
            "bbox_pt": bbox,
            "hint": hint,
            "parent_groups": parent_groups,
        }
        items.append(item)

    return items


def _extract_annames_from_build_py(build_py_path: Path) -> dict[str, str]:
    """Return {anname: primitive_type} from anname='...' literals in build.py."""
    text = build_py_path.read_text(encoding="utf-8")
    # Match anname='uXXX' inside constructor calls
    anname_re = re.compile(r"anname=['\"]([^'\"]+)['\"]")
    # Look at context: which class is being constructed
    # We scan for patterns like: TextFrame(..., anname='uXXX', ...
    prim_re = re.compile(
        r"(TextFrame|ImageFrame|Polygon|Oval|GraphicLine)"
        r"\s*\([^)]*?anname=['\"]([^'\"]+)['\"]",
        re.DOTALL,
    )
    result: dict[str, str] = {}
    for m in prim_re.finditer(text):
        prim_type = m.group(1)
        anname = m.group(2)
        result[anname] = prim_type

    # Also capture any anname not caught by the above (e.g. multiline)
    for m in anname_re.finditer(text):
        anname = m.group(1)
        if anname not in result:
            result[anname] = "unknown"

    return result


def run_inventory(
    idml_path: Path,
    build_py_path: Path,
    template: Optional[str] = None,
) -> dict:
    """Run the full inventory and return the report dict."""
    if template is None:
        template = build_py_path.parent.name

    with zipfile.ZipFile(idml_path) as z:
        printable_layers = _load_printable_layers(z)
        spread_names = _load_spread_order(z)

        # All annames in build.py (global across all pages).
        annames = _extract_annames_from_build_py(build_py_path)
        # Bare IDML Self IDs (uXXX hex, no synthetic suffix like _hl, _dreiz).
        bare_idml_annames = {
            a for a in annames if re.fullmatch(r"u[0-9a-f]+", a)
        }

        # First pass: collect all IDML selfs across all spreads so we can
        # compute truly "extra" annames (not in any spread).
        all_idml_selfs: set[str] = set()
        spread_items_list: list[list[dict]] = []
        for spread_name in spread_names:
            spread_id = Path(spread_name).stem
            spread_xml = z.read(spread_name)
            items = _collect_spread_items(spread_xml, printable_layers, z, spread_id)
            spread_items_list.append(items)
            all_idml_selfs.update(item["self"] for item in items)

        # Global extras: bare annames not found in any IDML spread.
        global_extras = bare_idml_annames - all_idml_selfs

        spreads_out: list[dict] = []
        for page_idx, (spread_name, items) in enumerate(
            zip(spread_names, spread_items_list)
        ):
            spread_id = Path(spread_name).stem  # e.g. Spread_ueb
            idml_selfs = {item["self"] for item in items}
            emitted_selfs = set(annames.keys()) & idml_selfs
            dropped_selfs = idml_selfs - set(annames.keys())

            # Build dropped list (sorted for determinism)
            elements_dropped: list[dict] = []
            for item in sorted(items, key=lambda x: x["self"]):
                if item["self"] in dropped_selfs:
                    entry: dict = {
                        "self": item["self"],
                        "type": item["type"],
                    }
                    if item["bbox_pt"] is not None:
                        entry["bbox_pt"] = item["bbox_pt"]
                    entry["hint"] = item["hint"]
                    elements_dropped.append(entry)

            # Per-spread extras: global extras not found in any spread.
            # (We only show this on the last spread to avoid duplication;
            # since extras aren't spread-specific, we attach to the report root.)
            spread_entry: dict = {
                "spread_id": spread_id,
                "page": page_idx,
                "elements_total": len(items),
                "elements_emitted": len(emitted_selfs),
            }
            if elements_dropped:
                spread_entry["elements_dropped"] = elements_dropped
            spreads_out.append(spread_entry)

    # Build global extras section.
    elements_extra: list[dict] = []
    for anname in sorted(global_extras):
        elements_extra.append({
            "anname": anname,
            "type_in_build_py": annames[anname],
            "hint": "anname in build.py not found in any IDML spread — verify intent",
        })

    report: dict = {
        "template": template,
        "idml_path": str(idml_path),
        "build_py_path": str(build_py_path),
        "spreads": spreads_out,
    }
    if elements_extra:
        report["elements_extra_global"] = elements_extra
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
        prog="idml_inventory",
        description="Inventory IDML spread elements vs emitted build.py annames.",
    )
    parser.add_argument("--idml", required=True, type=Path, help="Source IDML file path")
    parser.add_argument(
        "--build-py", required=True, type=Path, help="Emitted build.py path"
    )
    parser.add_argument(
        "--out", required=True, type=Path, help="Output YAML file path"
    )
    parser.add_argument("--template", default=None, help="Template slug (default: parent dir of build.py)")
    args = parser.parse_args(argv)

    if not args.idml.exists():
        print(f"ERROR: IDML not found: {args.idml}", file=sys.stderr)
        return 1
    if not args.build_py.exists():
        print(f"ERROR: build.py not found: {args.build_py}", file=sys.stderr)
        return 1

    report = run_inventory(args.idml, args.build_py, template=args.template)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_yaml_dump(report), encoding="utf-8")
    print(f"inventory written → {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
