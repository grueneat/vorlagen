#!/usr/bin/env python3
"""tools/baseline_image_audit.py — PDF baseline image inventory vs build.py.

Runs:
  - pdfimages -list <baseline.pdf>  → raster image count per page
  - pdftocairo -svg per page        → vector path count (content paths, not defs)

Compares against build.py:
  - ImageFrame count vs raster image count per page
  - Polygon count vs SVG content-path count per page
  - Per-image composite-strip detection: multiple ImageFrames referencing the
    same image path with identical local_offset_mm → likely per-Image LocalOffset bug

Emits image_audit.yml.

CLI:
    python3 tools/baseline_image_audit.py \\
        --baseline templates/<slug>/baseline.pdf \\
        --build-py templates/<slug>/build.py \\
        --out image_audit.yml

Exit code: 0 always (informational tool).
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Optional

import yaml


# ---------------------------------------------------------------------------
# PDF raster image enumeration
# ---------------------------------------------------------------------------

def _parse_pdfimages_list(output: str) -> dict[int, int]:
    """Parse pdfimages -list output and return {page_number: raster_image_count}.

    pdfimages reports: page  num  type  ...
    We count only rows where type is 'image' (not 'stencil', 'smask', 'colormap').
    'smask' is the alpha channel of an RGBA image — not a separate image.
    'stencil' is a 1-bit mask.
    We count unique (page, object) pairs with type='image'.
    """
    counts: dict[int, int] = defaultdict(int)
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("page") or line.startswith("---"):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            page = int(parts[0])
            img_type = parts[2]
        except (ValueError, IndexError):
            continue
        # Count only raster images (not smask/stencil/colormap)
        if img_type == "image":
            counts[page] += 1
    return dict(counts)


def _get_raster_counts(baseline_pdf: Path) -> dict[int, int]:
    """Return {page_1idx: raster_image_count} from pdfimages -list."""
    r = subprocess.run(
        ["pdfimages", "-list", str(baseline_pdf)],
        capture_output=True,
        text=True,
    )
    return _parse_pdfimages_list(r.stdout)


# ---------------------------------------------------------------------------
# PDF vector path enumeration via SVG
# ---------------------------------------------------------------------------

def _count_svg_content_paths(svg_path: str) -> int:
    """Count <path> elements outside <defs> sections in the SVG.

    pdftocairo renders font glyphs as path shapes and stores them in <defs>
    (the glyph definitions reused by <use> elements). The content section
    contains only actual rendered vector shapes (filled/stroked paths).
    We exclude:
    - paths in <defs> (glyph definitions, clip paths)
    - paths with d="M 0 0" or near-empty (invisible sentinel paths)
    """
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
    except Exception:
        return 0

    count = [0]

    def walk(el: ET.Element, in_defs: bool = False) -> None:
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        new_in_defs = in_defs or tag == "defs"
        if tag == "path" and not in_defs:
            d = el.get("d", "").strip()
            # Skip trivially empty paths
            if d and d not in ("M 0 0", "M0 0", "M 0,0"):
                count[0] += 1
        for child in el:
            walk(child, new_in_defs)

    walk(root)
    return count[0]


def _get_vector_path_counts(baseline_pdf: Path, page_count: int) -> dict[int, int]:
    """Return {page_1idx: content_path_count} by running pdftocairo per page."""
    counts: dict[int, int] = {}
    with tempfile.TemporaryDirectory() as tmpdir:
        for page_num in range(1, page_count + 1):
            out_base = str(Path(tmpdir) / f"page-{page_num}")
            r = subprocess.run(
                [
                    "pdftocairo",
                    "-svg",
                    "-f", str(page_num),
                    "-l", str(page_num),
                    str(baseline_pdf),
                    out_base,
                ],
                capture_output=True,
            )
            # pdftocairo writes the file at exactly out_base (no .svg suffix)
            svg_file = out_base
            if Path(svg_file).exists():
                counts[page_num] = _count_svg_content_paths(svg_file)
            else:
                counts[page_num] = 0
    return counts


# ---------------------------------------------------------------------------
# build.py parser
# ---------------------------------------------------------------------------

def _extract_imageframes_from_build_py(build_py_path: Path) -> list[dict]:
    """Return list of {anname, image, local_offset_mm, local_scale, page_func} from build.py.

    Parses ImageFrame(...) calls. page_func is 'page_0' or 'page_1' based on
    which _add_page_N function the frame appears in (best-effort).
    """
    text = build_py_path.read_text(encoding="utf-8")
    frames: list[dict] = []

    # Track which _add_page_N function we're in
    func_re = re.compile(r"def _add_page_(\d+)\s*\(")
    frame_re = re.compile(r"ImageFrame\s*\(", re.DOTALL)

    # Find all function definitions and their spans
    func_spans: list[tuple[int, int, str]] = []  # (start, end, page_func)
    func_matches = list(func_re.finditer(text))
    for i, fm in enumerate(func_matches):
        page_id = fm.group(1)
        start = fm.start()
        end = func_matches[i + 1].start() if i + 1 < len(func_matches) else len(text)
        func_spans.append((start, end, f"page_{page_id}"))

    def _page_func_for_pos(pos: int) -> str:
        for start, end, pfunc in func_spans:
            if start <= pos < end:
                return pfunc
        return "unknown"

    # Extract each ImageFrame call
    for m in frame_re.finditer(text):
        start = m.end() - 1  # opening (
        # Find matching )
        depth = 0
        i = start
        while i < len(text):
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        frame_text = text[start : i + 1]

        anname_m = re.search(r"anname=['\"]([^'\"]+)['\"]", frame_text)
        image_m = re.search(r"image=['\"]([^'\"]+)['\"]", frame_text)
        if not anname_m:
            continue

        anname = anname_m.group(1)
        image = image_m.group(1) if image_m else None

        # Parse local_offset_mm=(x, y)
        offset_m = re.search(r"local_offset_mm\s*=\s*\(([^)]+)\)", frame_text)
        local_offset_mm: Optional[tuple[float, float]] = None
        if offset_m:
            try:
                vals = [float(v.strip()) for v in offset_m.group(1).split(",")]
                local_offset_mm = (vals[0], vals[1])
            except (ValueError, IndexError):
                pass

        # Parse local_scale=(x, y)
        scale_m = re.search(r"local_scale\s*=\s*\(([^)]+)\)", frame_text)
        local_scale: Optional[tuple[float, float]] = None
        if scale_m:
            try:
                vals = [float(v.strip()) for v in scale_m.group(1).split(",")]
                local_scale = (vals[0], vals[1])
            except (ValueError, IndexError):
                pass

        page_func = _page_func_for_pos(m.start())

        frames.append({
            "anname": anname,
            "image": image,
            "local_offset_mm": local_offset_mm,
            "local_scale": local_scale,
            "page_func": page_func,
        })

    return frames


def _extract_polygon_count_per_page(build_py_path: Path) -> dict[str, int]:
    """Return {page_func: polygon_count} from Polygon(...) calls in build.py."""
    text = build_py_path.read_text(encoding="utf-8")

    # Find function definitions and their spans
    func_re = re.compile(r"def _add_page_(\d+)\s*\(")
    func_matches = list(func_re.finditer(text))
    func_spans: list[tuple[int, int, str]] = []
    for i, fm in enumerate(func_matches):
        page_id = fm.group(1)
        start = fm.start()
        end = func_matches[i + 1].start() if i + 1 < len(func_matches) else len(text)
        func_spans.append((start, end, f"page_{page_id}"))

    counts: dict[str, int] = defaultdict(int)
    polygon_re = re.compile(r"\bPolygon\s*\(")
    for m in polygon_re.finditer(text):
        pos = m.start()
        for start, end, pfunc in func_spans:
            if start <= pos < end:
                counts[pfunc] += 1
                break

    return dict(counts)


# ---------------------------------------------------------------------------
# Composite-strip detection
# ---------------------------------------------------------------------------

def _detect_composite_strips(frames: list[dict]) -> list[dict]:
    """Detect multiple ImageFrames referencing the same image with identical offsets.

    Pattern: N ImageFrames share the same image= path, but all have the same
    local_offset_mm (or all None). This suggests a per-Image LocalOffset bug
    where the crop was not applied per-frame.
    """
    by_image: dict[str, list[dict]] = defaultdict(list)
    for f in frames:
        if f["image"]:
            by_image[f["image"]].append(f)

    strips: list[dict] = []
    for image_path, image_frames in sorted(by_image.items()):
        if len(image_frames) < 2:
            continue
        # Count unique offsets
        offsets = [f["local_offset_mm"] for f in image_frames]
        unique_offsets = len(set(
            (round(o[0], 4), round(o[1], 4)) if o is not None else None
            for o in offsets
        ))
        if unique_offsets == 1:
            # All frames share the same offset — flag as suspicious
            annames = sorted(f["anname"] for f in image_frames)
            hint = (
                f"{len(image_frames)} frames reference 1 image with "
                f"{unique_offsets} unique offset — likely per-Image LocalOffset bug"
            )
            strips.append({
                "image": image_path,
                "n_frames": len(image_frames),
                "unique_offsets": unique_offsets,
                "annames": annames,
                "hint": hint,
            })

    return strips


# ---------------------------------------------------------------------------
# Page count helper
# ---------------------------------------------------------------------------

def _get_page_count(pdf_path: Path) -> int:
    """Return number of pages in the PDF using pdfinfo."""
    r = subprocess.run(
        ["pdfinfo", str(pdf_path)],
        capture_output=True,
        text=True,
    )
    for line in r.stdout.splitlines():
        if line.lower().startswith("pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
    return 2  # fallback


# ---------------------------------------------------------------------------
# Main audit logic
# ---------------------------------------------------------------------------

def run_image_audit(
    baseline_pdf: Path,
    build_py_path: Path,
    template: Optional[str] = None,
) -> dict:
    """Run the image audit and return the report dict."""
    if template is None:
        template = build_py_path.parent.name

    page_count = _get_page_count(baseline_pdf)
    raster_counts = _get_raster_counts(baseline_pdf)
    vector_counts = _get_vector_path_counts(baseline_pdf, page_count)
    imageframes = _extract_imageframes_from_build_py(build_py_path)
    polygon_count_by_page = _extract_polygon_count_per_page(build_py_path)
    composite_strips = _detect_composite_strips(imageframes)

    # Count ImageFrames per page function
    imageframe_count_by_page: dict[str, int] = defaultdict(int)
    for f in imageframes:
        imageframe_count_by_page[f["page_func"]] += 1

    pages_out: list[dict] = []
    for page_idx in range(page_count):
        page_num = page_idx + 1  # 1-indexed
        page_func = f"page_{page_idx}"

        baseline_raster = raster_counts.get(page_num, 0)
        build_raster = imageframe_count_by_page.get(page_func, 0)
        raster_ok = baseline_raster == build_raster

        baseline_vector = vector_counts.get(page_num, 0)
        build_polygon = polygon_count_by_page.get(page_func, 0)
        vector_delta = baseline_vector - build_polygon

        raster_entry: dict = {
            "baseline_count": baseline_raster,
            "build_py_count": build_raster,
            "ok": raster_ok,
        }
        if not raster_ok:
            # Audit-reliability item 3: this audit only counts raw raster
            # image references — it cannot tell whether the IMAGE renders
            # visibly. A "6 raster image(s) extra in build.py" message
            # gives the misleading impression of a converter bug when in
            # fact the new image_frame_visibility_audit (E5) is the right
            # signal for "are the frames visible?". Rephrase to neutral
            # language pointing readers to E5.
            raster_entry["hint"] = (
                f"image count differs (baseline={baseline_raster}, "
                f"build.py={build_raster}); informational only — see "
                "image_frame_visibility_audit (E5) for per-frame "
                "visibility, the authoritative signal"
            )

        vector_entry: dict = {
            "baseline_count": baseline_vector,
            "build_py_polygon_count": build_polygon,
            "delta": vector_delta,
        }
        if vector_delta > 0:
            vector_entry["hint"] = (
                f"{vector_delta} vector path(s) in baseline have no Polygon emit in "
                "build.py (likely inline vector elements: wind turbine, curly quotes, etc.)"
            )
        elif vector_delta < 0:
            vector_entry["hint"] = (
                f"{abs(vector_delta)} Polygon(s) in build.py have no corresponding "
                "vector path in baseline"
            )

        page_entry: dict = {
            "page": page_idx,
            "raster": raster_entry,
            "vector_paths": vector_entry,
        }
        pages_out.append(page_entry)

    report: dict = {
        "template": template,
        "baseline_pdf": str(baseline_pdf),
        "build_py_path": str(build_py_path),
        "pages": pages_out,
    }
    if composite_strips:
        report["composite_strips"] = composite_strips

    return report


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
        prog="baseline_image_audit",
        description="Audit baseline PDF images vs build.py ImageFrame/Polygon counts.",
    )
    parser.add_argument(
        "--baseline", required=True, type=Path, help="Baseline PDF path"
    )
    parser.add_argument(
        "--build-py", required=True, type=Path, help="build.py path"
    )
    parser.add_argument(
        "--out", required=True, type=Path, help="Output YAML file path"
    )
    parser.add_argument(
        "--template", default=None, help="Template slug (default: parent dir of build.py)"
    )
    args = parser.parse_args(argv)

    if not args.baseline.exists():
        print(f"ERROR: baseline PDF not found: {args.baseline}", file=sys.stderr)
        return 1
    if not args.build_py.exists():
        print(f"ERROR: build.py not found: {args.build_py}", file=sys.stderr)
        return 1

    report = run_image_audit(args.baseline, args.build_py, template=args.template)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_yaml_dump(report), encoding="utf-8")
    print(f"image_audit written → {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
