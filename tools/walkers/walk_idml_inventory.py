#!/usr/bin/env python3
"""tools/walkers/walk_idml_inventory.py — IDML spread element inventory.

Two surfaces in one module:

1. **Legacy spread audit** (``run_inventory()`` + ``main()``):
   Parses Spreads/Spread_*.xml from the source IDML (Gestaltung layer only)
   and diffs the Self="uXXX" IDs against anname='uXXX' literals in the
   emitted build.py. Emits inventory.yml with elements_total /
   elements_emitted / elements_dropped / elements_extra per spread.

   CLI:
       python3 tools/idml_inventory.py \\
           --idml originals/.../foo.idml \\
           --build-py templates/<slug>/build.py \\
           --out inventory.yml

   Exit code: 0 always (informational tool).

2. **New SCAFFOLD_INVENTORY walker** (``walk_idml()``):
   Returns an :class:`tools.walkers.schema.Inventory` with the IDML-side
   fields populated (text_runs, paragraph_styles, colors, frames keyed by
   ``Self`` ID, assets). Other stage walkers (SLA, PDF, build.py) join into
   this dataclass via :mod:`tools.inventory_extract`.

Back-compat: ``tools/idml_inventory.py`` is a re-export shim.
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


# ---------------------------------------------------------------------------
# SCAFFOLD_INVENTORY walker (`walk_idml`)
# ---------------------------------------------------------------------------
#
# The legacy ``run_inventory`` above audits ONE pair of (idml, build.py) for
# dropped vs emitted Self IDs. ``walk_idml`` below extracts a richer
# IDML-only structural inventory (text runs, paragraph styles, colors,
# frames, assets) suitable for joining with SLA + PDF + build.py walks in
# ``tools.inventory_extract``.
#
# Why a separate function: ``run_inventory`` needs build.py to be useful;
# ``walk_idml`` produces a self-contained snapshot that downstream walkers
# decorate. They share the spread/zip plumbing above.

# Points → millimetres (Adobe IDML pt). Mirrors `tools/idml_to_dsl.py::PT_TO_MM`.
_PT_TO_MM = 25.4 / 72.0


def _idml_pt_to_mm(value_pt: float) -> float:
    return value_pt * _PT_TO_MM


def _bbox_pt_to_mm(bbox_pt: Optional[list[float]]) -> Optional[list[float]]:
    if bbox_pt is None:
        return None
    return [round(_idml_pt_to_mm(v), 3) for v in bbox_pt]


def _walk_idml_colors(idml_zip: zipfile.ZipFile) -> list[dict]:
    """Return ``[{name, cmyk}]`` rows for every ``<Color>`` definition.

    No filtering — we want the full IDML palette even for unused colors,
    since the inventory's job is to record what's declared, not what's printed.
    Returns empty list when Resources/Graphic.xml is absent.
    """
    try:
        xml = idml_zip.read("Resources/Graphic.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml.decode("utf-8"))
    out: list[dict] = []
    for c in root.iter():
        tag = c.tag.split("}")[-1] if "}" in c.tag else c.tag
        if tag != "Color":
            continue
        self_id = c.get("Self", "")
        if not self_id:
            continue
        value_str = c.get("ColorValue", "")
        cmyk: Optional[list[float]] = None
        if value_str:
            try:
                cmyk = [float(v) for v in value_str.split()]
            except ValueError:
                cmyk = None
        out.append({"name": self_id, "cmyk": cmyk})
    return out


def _walk_idml_paragraph_styles(idml_zip: zipfile.ZipFile) -> list[str]:
    """Return list of ``ParagraphStyle/<name>`` Self IDs declared in Resources."""
    try:
        xml = idml_zip.read("Resources/Styles.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml.decode("utf-8"))
    out: list[str] = []
    for p in root.iter():
        tag = p.tag.split("}")[-1] if "}" in p.tag else p.tag
        if tag != "ParagraphStyle":
            continue
        self_id = p.get("Self", "")
        if self_id:
            out.append(self_id)
    return out


def _walk_idml_text_runs(idml_zip: zipfile.ZipFile) -> tuple[int, dict[str, int], list[dict]]:
    """Walk every Stories/Story_*.xml. Return:

    - ``total_idml``: count of ``<CharacterStyleRange>`` with non-empty ``<Content>``
    - ``by_paragraph_style``: ``{ParagraphStyle/<id>: non_empty_csr_count}``
    - ``runs``: ``[{text, font, fontsize, fcolor, paragraph_style}]`` for set-equality
    """
    total = 0
    by_ps: dict[str, int] = {}
    runs: list[dict] = []
    for name in idml_zip.namelist():
        if not name.startswith("Stories/Story_"):
            continue
        try:
            root = ET.fromstring(idml_zip.read(name).decode("utf-8"))
        except Exception:
            continue
        for psr in root.iter():
            tag = psr.tag.split("}")[-1] if "}" in psr.tag else psr.tag
            if tag != "ParagraphStyleRange":
                continue
            ps_self = psr.get("AppliedParagraphStyle", "")
            for csr in psr.iter():
                ctag = csr.tag.split("}")[-1] if "}" in csr.tag else csr.tag
                if ctag != "CharacterStyleRange":
                    continue
                font = ""
                fontsize = 0.0
                fcolor = csr.get("FillColor", "") or ""
                # AppliedFont lives at Properties/AppliedFont/text.
                props = csr.find("Properties")
                if props is not None:
                    af = None
                    for ch in props:
                        cht = ch.tag.split("}")[-1] if "}" in ch.tag else ch.tag
                        if cht == "AppliedFont":
                            af = ch
                            break
                    if af is not None and af.text:
                        font = af.text.strip()
                pt = csr.get("PointSize")
                if pt:
                    try:
                        fontsize = float(pt)
                    except ValueError:
                        fontsize = 0.0
                # Emit ONE run per <Content> child. Concatenating across
                # Content boundaries (the old behaviour) folded multi-Run
                # paragraphs into a single string ("Mehrzeilige Subheadline -
                # mehr Info zum Thema") that never matches build.py's
                # per-Run() emit, defeating the set-equality gate.
                for ch in csr:
                    cht = ch.tag.split("}")[-1] if "}" in (ch.tag or "") else ch.tag
                    if cht != "Content":
                        continue
                    parts = []
                    if ch.text:
                        parts.append(ch.text)
                    for sub in ch:
                        if sub.tail:
                            parts.append(sub.tail)
                    text = "".join(parts)
                    if not text.strip():
                        continue
                    total += 1
                    by_ps[ps_self] = by_ps.get(ps_self, 0) + 1
                    runs.append({
                        "text": text,
                        "font": font,
                        "fontsize": fontsize,
                        "fcolor": fcolor,
                        "paragraph_style": ps_self,
                    })
    return total, by_ps, runs


def _walk_idml_frames(
    idml_zip: zipfile.ZipFile,
    printable_layers: set[str],
) -> dict[str, list[dict]]:
    """Walk every spread; bucket page-items into text/image/polygon/group frames.

    Returns a dict ``{text_frames: [...], image_frames: [...], polygon_frames: [...], group_frames: [...]}``
    where each item is ``{self, idml_position_mm, idml_link?}``.

    Bucketing rules:
    - ``TextFrame`` → text_frames
    - ``Rectangle``/``Polygon``/``Oval`` containing ``<Image>`` or ``<PDF>``
      child → image_frames
    - Other ``Rectangle``/``Polygon``/``Oval``/``GraphicLine`` → polygon_frames
    - ``Group`` → group_frames
    """
    out: dict[str, list[dict]] = {
        "text_frames": [],
        "image_frames": [],
        "polygon_frames": [],
        "group_frames": [],
    }
    spread_names = _load_spread_order(idml_zip)
    seen_groups: set[str] = set()
    for spread_name in spread_names:
        try:
            spread_xml = idml_zip.read(spread_name)
        except KeyError:
            continue
        root = ET.fromstring(spread_xml.decode("utf-8"))
        parent_map = _build_parent_map(root)
        for el in root.iter():
            tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            if tag not in PAGE_ITEM_TAGS:
                continue
            # Skip Image/PDF children of a containing Rectangle/Polygon/Oval —
            # they're already accounted for via the parent's image_frames bucket.
            parent = parent_map.get(el)
            if parent is not None:
                ptag = parent.tag.split("}")[-1] if "}" in parent.tag else parent.tag
                if ptag in PAGE_ITEM_TAGS and tag in CHILD_CONTENT_TAGS:
                    continue
            self_id = el.get("Self", "")
            if not self_id:
                continue
            layer = _get_item_layer(el, parent_map)
            if printable_layers and layer not in printable_layers:
                continue

            bbox_pt = _bbox_from_element(el)
            bbox_mm = _bbox_pt_to_mm(bbox_pt)
            row: dict = {"self": self_id, "idml_position_mm": bbox_mm}

            if tag == "TextFrame":
                out["text_frames"].append(row)
            elif tag in ("Rectangle", "Polygon", "Oval"):
                # Detect Image/PDF child to decide image vs polygon bucket.
                link_basename: Optional[str] = None
                has_image_child = False
                for ch in el:
                    ctag = ch.tag.split("}")[-1] if "}" in ch.tag else ch.tag
                    if ctag in ("Image", "PDF"):
                        has_image_child = True
                        href = ch.get("LinkResourceURI") or ""
                        if not href:
                            link_el = ch.find("Link")
                            if link_el is not None:
                                href = link_el.get("LinkResourceURI", "")
                        if href:
                            # IDML href like ``file:Links/Foo.jpg`` or ``file:./Links/Foo.jpg``;
                            # basename is the trailing segment.
                            link_basename = href.split("/")[-1].split("\\")[-1]
                        break
                if has_image_child:
                    if link_basename:
                        row["idml_link"] = link_basename
                    out["image_frames"].append(row)
                else:
                    out["polygon_frames"].append(row)
            elif tag == "GraphicLine":
                out["polygon_frames"].append(row)
            elif tag == "Group":
                if self_id in seen_groups:
                    continue
                seen_groups.add(self_id)
                out["group_frames"].append(row)
            elif tag in ("Image", "PDF"):
                # Top-level Image/PDF (not wrapped in a Rectangle/Polygon/Oval
                # — these are skipped earlier by the CHILD_CONTENT_TAGS
                # filter when they appear as children). In the corpus IDML
                # always wraps Image in a Rectangle so this branch is
                # defensive (review fix L3); without it a free-standing
                # raster placement would fall through both the image_frames
                # and polygon_frames buckets silently.
                out["image_frames"].append(row)
    return out


def _walk_idml_assets(slug: str, repo_root: Path) -> list[dict]:
    """Return ``[{basename, on_disk, classified, parent_composite?, sha256?, byte_length?}]``.

    Reads ``shared/assets/<slug>/links_export.yml`` (the canonical IDML link
    manifest) and ``meta.yml::asset_policy`` (the embedded/external/shipped
    bucket classification). Composite-AI splits are read from
    ``shared/assets/<slug>/composite_ai_split.yml`` when present.

    When ``on_disk`` is True, also populates the asset's ``sha256`` +
    ``byte_length`` from the file on disk. For composite-AI parents (.ai
    files) we hash the original; for everything else the derived file under
    ``shared/assets/<slug>/``. See issue #40 review F6.
    """
    import hashlib  # local — only needed for the on-disk hash path.
    assets_dir = repo_root / "shared" / "assets" / slug
    manifest_path = assets_dir / "links_export.yml"
    composite_path = assets_dir / "composite_ai_split.yml"
    meta_path = repo_root / "templates" / slug / "meta.yml"

    def _hash_file(path: Path) -> tuple[Optional[str], Optional[int]]:
        """Return (sha256_hex, byte_length) or (None, None) on any failure."""
        if not path or not path.exists() or not path.is_file():
            return None, None
        try:
            data = path.read_bytes()
        except OSError:
            return None, None
        try:
            sha = hashlib.sha256(data).hexdigest()
        except Exception:
            return None, None
        try:
            length = path.stat().st_size
        except OSError:
            length = len(data)
        return sha, length

    # asset_policy buckets (embedded/external/shipped) — classification source.
    policy_map: dict[str, str] = {}
    if meta_path.exists():
        try:
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
            ap = meta.get("asset_policy", {}) or {}
            for bucket_name in ("embedded", "external", "shipped"):
                for basename in ap.get(bucket_name, []) or []:
                    policy_map[basename] = bucket_name
        except Exception:
            policy_map = {}

    # Linked IDML originals — converted into shared/assets/<slug>/ derivatives.
    rows: list[dict] = []
    derived_basenames: set[str] = set()
    if manifest_path.exists():
        try:
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            entries = manifest.get("assets", {}) or {}
        except Exception:
            entries = {}
        for original_name, entry in entries.items():
            for key in ("output", "vector_output"):
                path = (entry or {}).get(key)
                if not path:
                    continue
                basename = Path(path).name
                if basename in derived_basenames:
                    continue
                derived_basenames.add(basename)
                on_disk_path = repo_root / path
                on_disk = on_disk_path.exists()
                sha, blen = _hash_file(on_disk_path) if on_disk else (None, None)
                rows.append({
                    "basename": basename,
                    "on_disk": on_disk,
                    "classified": policy_map.get(basename, "external"),
                    "parent_composite": None,
                    "sha256": sha,
                    "byte_length": blen,
                })

    # Composite-AI splits: each split is a derived asset of one parent .ai.
    # Shape on disk (see leporello example): a single dict
    # ``{ai_basename: <name>, pages_emitted: [{out: <abs_path>, idml_anname: <id>, ...}, ...]}``.
    if composite_path.exists():
        try:
            comp = yaml.safe_load(composite_path.read_text(encoding="utf-8")) or {}
        except Exception:
            comp = {}
        parent = comp.get("ai_basename") if isinstance(comp, dict) else None
        pages = comp.get("pages_emitted", []) if isinstance(comp, dict) else []
        for part in pages or []:
            p = (part or {}).get("out", "")
            if not p:
                continue
            basename = Path(p).name
            if basename in derived_basenames:
                for r in rows:
                    if r["basename"] == basename:
                        r["parent_composite"] = parent
                        break
                continue
            derived_basenames.add(basename)
            on_disk_path = Path(p) if Path(p).is_absolute() else (repo_root / p)
            on_disk = on_disk_path.exists()
            sha, blen = _hash_file(on_disk_path) if on_disk else (None, None)
            rows.append({
                "basename": basename,
                "on_disk": on_disk,
                "classified": policy_map.get(basename, "external"),
                "parent_composite": parent,
                "sha256": sha,
                "byte_length": blen,
            })

    # Any asset_policy entries not seen via the manifest (e.g. PNG twins of
    # vector originals): record them as well so the inventory shows the full
    # on-disk set the template ships.
    for basename, bucket in policy_map.items():
        if basename in derived_basenames:
            continue
        on_disk_path = assets_dir / basename
        on_disk = on_disk_path.exists()
        sha, blen = _hash_file(on_disk_path) if on_disk else (None, None)
        rows.append({
            "basename": basename,
            "on_disk": on_disk,
            "classified": bucket,
            "parent_composite": None,
            "sha256": sha,
            "byte_length": blen,
        })
    return rows


def walk_idml(idml_path: Path, slug: str, *, repo_root: Optional[Path] = None):
    """Return an ``Inventory`` dataclass populated with IDML-side fields.

    Args:
        idml_path: The source ``.idml`` zip file.
        slug: Template slug (used to locate ``shared/assets/<slug>/...``).
        repo_root: Repository root (defaults to ``<this-file>/../../..``).

    The returned Inventory has SLA-, PDF- and build.py-side fields left at
    their dataclass defaults; the orchestrator in
    ``tools.inventory_extract`` fills them in.
    """
    # Local import keeps the legacy ``run_inventory`` path free of the new
    # dependency chain (e.g. so the test suite for run_inventory does not
    # need the schema module loaded).
    from tools.walkers.schema import (
        Inventory, TextRunBucket, TextRunByStyle, Frames,
        TextFrame, ImageFrame, PolygonFrame, GroupFrame,
        ParagraphStyleEntry, ColorEntry, AssetEntry,
    )

    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]

    with zipfile.ZipFile(idml_path) as z:
        printable_layers = _load_printable_layers(z)
        colors_raw = _walk_idml_colors(z)
        ps_names = _walk_idml_paragraph_styles(z)
        total, by_ps, runs_raw = _walk_idml_text_runs(z)
        frames = _walk_idml_frames(z, printable_layers)

    by_style = [
        TextRunByStyle(style=ps, idml_count=count)
        for ps, count in sorted(by_ps.items())
    ]
    # Build IDML-side TextRun dataclasses so the orchestrator can run a real
    # set-equality check against build.py (issue #40 review F3). The walker
    # already collected the per-CSR detail at ``_walk_idml_text_runs`` —
    # surface it instead of discarding.
    from tools.walkers.schema import TextRun as _TextRun  # noqa: WPS433
    idml_runs = [
        _TextRun(
            text=r.get("text", ""),
            font=r.get("font", "") or "",
            fontsize=float(r.get("fontsize") or 0),
            fcolor=r.get("fcolor", "") or "",
            paragraph_style=r.get("paragraph_style", "") or "",
            # text_source on the IDML side is intentionally empty — the
            # build_py/inject_yml tag is only meaningful for the build.py
            # walker. Leave at default.
        )
        for r in runs_raw
    ]

    inv = Inventory(
        schema_version=1,
        template=slug,
        text_runs=TextRunBucket(
            total_idml=total,
            by_paragraph_style=by_style,
            idml_runs=idml_runs,
        ),
        frames=Frames(
            text_frames=[
                TextFrame(anname=r["self"], idml_self=r["self"],
                          idml_position_mm=r.get("idml_position_mm"), source="idml")
                for r in frames["text_frames"]
            ],
            image_frames=[
                ImageFrame(anname=r["self"], idml_self=r["self"],
                           idml_link=r.get("idml_link"),
                           idml_position_mm=r.get("idml_position_mm"), source="idml")
                for r in frames["image_frames"]
            ],
            polygon_frames=[
                PolygonFrame(anname=r["self"], idml_self=r["self"],
                             idml_position_mm=r.get("idml_position_mm"), source="idml")
                for r in frames["polygon_frames"]
            ],
            group_frames=[
                GroupFrame(anname=r["self"], idml_self=r["self"],
                           idml_position_mm=r.get("idml_position_mm"), source="idml")
                for r in frames["group_frames"]
            ],
        ),
        paragraph_styles=[ParagraphStyleEntry(idml=ps) for ps in ps_names],
        colors=[ColorEntry(idml=c["name"], cmyk=c["cmyk"]) for c in colors_raw],
        assets=[
            AssetEntry(
                basename=a["basename"],
                on_disk=a["on_disk"],
                classified=a["classified"],
                parent_composite=a.get("parent_composite"),
                sha256=a.get("sha256"),
                byte_length=a.get("byte_length"),
            )
            for a in _walk_idml_assets(slug, repo_root)
        ],
    )
    return inv


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
