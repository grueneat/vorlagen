#!/usr/bin/env python3
"""Pixel-level line-position audit — bypasses pdfplumber's text-matrix Y.

pdfplumber reports the text-matrix Y coordinate Scribus or InDesign sent
to the PDF renderer. The actual rendered ink position depends on the
font's ascent metric, which differs between renderers for the same font
file. Result: pdfplumber-based gap measurements can match between
baseline.pdf and preview.pdf while the rendered images look visibly
different (issue #40 follow-up confirmed for Gotham Narrow Ultra and
Vollkorn Black Italic in the 26-03 leporello).

This tool rasterises both PDFs at a configurable DPI and detects per-
line "ink-top" by scanning pixel rows for non-background pixels inside
each frame's bbox. The ink-top is the y-coordinate of the FIRST row
with significant non-background pixels in the frame's x-range.

Usage:

    python3 tools/line_spacing_pixel_audit.py \\
        --slug 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover \\
        --templates-dir /workspace/templates \\
        --out-yaml build/validation/<slug>/line_spacing_pixel_audit.yml \\
        --out-md  build/validation/<slug>/line_spacing_pixel_audit.md

    # Single-frame probe:
    python3 tools/line_spacing_pixel_audit.py --slug <slug> --probe u1b0
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

try:
    from PIL import Image
except ImportError:
    Image = None
import yaml

_MM_TO_PT = 72.0 / 25.4
_PT_TO_MM = 25.4 / 72.0
_DEFAULT_DPI = 150


# ---------------------------------------------------------------------------
# Background detection


def _sample_background_rgb(
    img: "Image.Image", x: int, y: int, half_w: int = 8, half_h: int = 8
) -> tuple[int, int, int]:
    """Sample the bg color near (x, y) — median of a small patch."""
    px = img.load()
    w, h = img.size
    samples = []
    for dy in range(-half_h, half_h + 1, 2):
        for dx in range(-half_w, half_w + 1, 2):
            xi, yi = max(0, min(w - 1, x + dx)), max(0, min(h - 1, y + dy))
            samples.append(px[xi, yi][:3])
    samples.sort()
    return samples[len(samples) // 2]


def _is_ink(pixel: tuple, bg: tuple[int, int, int], threshold: int = 60) -> bool:
    """Return True if pixel differs from bg by ≥ threshold in any channel."""
    return any(abs(pixel[i] - bg[i]) >= threshold for i in range(3))


# ---------------------------------------------------------------------------
# Frame bbox extraction (mirrors line_spacing_full_audit's build.py walker)


@dataclass
class FrameInfo:
    anname: str
    page: int
    bbox_mm: tuple[float, float, float, float]


def _ast_kw(call: ast.Call, name: str):
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _ast_literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        return None


def parse_textframes_from_build_py(build_py: Path) -> dict[str, FrameInfo]:
    """Return {anname: FrameInfo} for every TextFrame in build.py.

    Page index recovered by walking up to the enclosing pageN.add() call.
    """
    out: dict[str, FrameInfo] = {}
    text = build_py.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    parent_map = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = ""
        if isinstance(node.func, ast.Name):
            fn = node.func.id
        elif isinstance(node.func, ast.Attribute):
            fn = node.func.attr
        if fn != "TextFrame":
            continue
        anname = _ast_literal(_ast_kw(node, "anname"))
        if not anname:
            continue
        x = _ast_literal(_ast_kw(node, "x_mm")) or _ast_literal(_ast_kw(node, "x"))
        y = _ast_literal(_ast_kw(node, "y_mm")) or _ast_literal(_ast_kw(node, "y"))
        w = _ast_literal(_ast_kw(node, "w_mm")) or _ast_literal(_ast_kw(node, "w"))
        h = _ast_literal(_ast_kw(node, "h_mm")) or _ast_literal(_ast_kw(node, "h"))
        if None in (x, y, w, h):
            continue
        page = 0
        cur = parent_map.get(node)
        while cur is not None:
            if (
                isinstance(cur, ast.Call)
                and isinstance(cur.func, ast.Attribute)
                and cur.func.attr == "add"
                and isinstance(cur.func.value, ast.Name)
            ):
                name = cur.func.value.id
                if name.startswith("page") and name[4:].isdigit():
                    page = int(name[4:])
                    break
            cur = parent_map.get(cur)
        out[str(anname)] = FrameInfo(
            anname=str(anname),
            page=page,
            bbox_mm=(float(x), float(y), float(w), float(h)),
        )
    return out


# ---------------------------------------------------------------------------
# Pixel-level measurement


@dataclass
class LineMeasurement:
    page_idx: int
    bbox_mm: tuple[float, float, float, float]
    dpi: int
    line_tops_pt: list[float]    # ink-top y of each detected line, in pt
    line_bottoms_pt: list[float] # ink-bottom y of each detected line, in pt


def _scan_frame_lines(
    img: "Image.Image",
    bbox_mm: tuple[float, float, float, float],
    dpi: int,
    min_ink_columns: int = 6,
    threshold: int = 60,
    line_gap_min_px: int = 4,
) -> tuple[list[float], list[float]]:
    """Return (line_tops_pt, line_bottoms_pt) for the frame bbox.

    Algorithm:
    1. Sample background colour from just outside the bbox top-left corner
       (or 5pt above frame top-left).
    2. For each pixel row inside the frame's x-range, count columns where
       the pixel differs from the bg by ≥ threshold in any channel.
    3. Rows with ≥ min_ink_columns are "ink rows". Gaps ≥ line_gap_min_px
       between ink rows demarcate separate lines.
    4. Return the first and last ink row of each line in PDF points.
    """
    factor = dpi / 72.0
    x_min_pt, y_min_pt, w_pt, h_pt = (
        bbox_mm[0] * _MM_TO_PT,
        bbox_mm[1] * _MM_TO_PT,
        bbox_mm[2] * _MM_TO_PT,
        bbox_mm[3] * _MM_TO_PT,
    )
    x_min_px = int(x_min_pt * factor)
    y_min_px = int(y_min_pt * factor)
    x_max_px = int((x_min_pt + w_pt) * factor)
    y_max_px = int((y_min_pt + h_pt) * factor)
    iw, ih = img.size
    x_min_px = max(0, min(iw - 1, x_min_px))
    x_max_px = max(0, min(iw, x_max_px))
    y_min_px = max(0, min(ih - 1, y_min_px))
    y_max_px = max(0, min(ih, y_max_px))
    if x_max_px <= x_min_px or y_max_px <= y_min_px:
        return [], []
    # Sample background from a 16x16 patch JUST OUTSIDE the frame's top-left.
    bg_sample_x = max(0, x_min_px - 12)
    bg_sample_y = max(0, y_min_px - 12)
    bg = _sample_background_rgb(img, bg_sample_x, bg_sample_y)
    pixels = img.load()
    # Scan each row
    ink_rows: list[int] = []
    for y in range(y_min_px, y_max_px):
        ink_count = 0
        for x in range(x_min_px, x_max_px, 2):
            if _is_ink(pixels[x, y][:3], bg, threshold):
                ink_count += 1
                if ink_count >= min_ink_columns:
                    break
        if ink_count >= min_ink_columns:
            ink_rows.append(y)
    if not ink_rows:
        return [], []
    # Group into lines by gaps
    lines: list[list[int]] = [[ink_rows[0]]]
    for y in ink_rows[1:]:
        if y - lines[-1][-1] > line_gap_min_px:
            lines.append([y])
        else:
            lines[-1].append(y)
    tops = [round(line[0] / factor, 3) for line in lines]
    bottoms = [round(line[-1] / factor, 3) for line in lines]
    return tops, bottoms


def render_pdf_pages_to_png(
    pdf: Path, dpi: int, dest_prefix: Path
) -> list[Path]:
    """Run pdftoppm to render every page to PNG. Returns sorted PNG paths."""
    dest_prefix.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(dest_prefix)],
        check=True, capture_output=True,
    )
    return sorted(dest_prefix.parent.glob(dest_prefix.name + "-*.png"))


def measure_frame(
    anname: str,
    frame: FrameInfo,
    preview_pngs: list[Path],
    baseline_pngs: list[Path],
    dpi: int,
) -> dict:
    """Measure preview vs baseline ink-tops for one frame; return dict."""
    if Image is None:
        return {"anname": anname, "error": "Pillow not installed"}
    pg = frame.page
    if pg >= len(baseline_pngs) or pg >= len(preview_pngs):
        return {"anname": anname, "error": f"page {pg} out of range"}
    bl_img = Image.open(baseline_pngs[pg])
    pv_img = Image.open(preview_pngs[pg])
    bl_tops, bl_bots = _scan_frame_lines(bl_img, frame.bbox_mm, dpi)
    pv_tops, pv_bots = _scan_frame_lines(pv_img, frame.bbox_mm, dpi)
    common = min(len(bl_tops), len(pv_tops))
    per_line_drift = [
        round(pv_tops[i] - bl_tops[i], 3) for i in range(common)
    ]
    cumulative_drift = (
        round((pv_tops[common - 1] - pv_tops[0])
              - (bl_tops[common - 1] - bl_tops[0]), 3)
        if common >= 2 else None
    )
    max_drift = (
        round(max(abs(d) for d in per_line_drift), 3)
        if per_line_drift else None
    )
    return {
        "anname": anname,
        "page": pg,
        "bbox_mm": list(frame.bbox_mm),
        "baseline_line_count": len(bl_tops),
        "preview_line_count": len(pv_tops),
        "baseline_tops_pt": bl_tops,
        "preview_tops_pt": pv_tops,
        "per_line_drift_pt": per_line_drift,
        "cumulative_drift_pt": cumulative_drift,
        "max_drift_pt": max_drift,
    }


# ---------------------------------------------------------------------------
# Output formatting


def write_yaml(rows: list[dict], out_path: Path) -> None:
    counts = {"match": 0, "minor": 0, "major": 0, "unmatched_count": 0}
    for r in rows:
        if r.get("error"):
            counts["unmatched_count"] += 1
            continue
        m = r.get("max_drift_pt")
        if m is None or r.get("baseline_line_count", 0) != r.get("preview_line_count", 0):
            counts["unmatched_count"] += 1
        elif abs(m) <= 1.0:
            counts["match"] += 1
        elif abs(m) <= 3.0:
            counts["minor"] += 1
        else:
            counts["major"] += 1
    payload = {"row_count": len(rows), "summary": counts, "rows": rows}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))


def write_md(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Line-spacing pixel-level audit\n"]
    lines.append(f"Frames measured: **{len(rows)}**\n")
    lines.append("Reported drifts are between rendered ink-top of each line in preview.pdf vs baseline.pdf (in points). Cumulative drift is the change in (last_top - first_top) over the frame's lines.\n")
    lines.append("| Anname | Page | Lines (b/p) | Max drift pt | Cum drift pt | Per-line drift |")
    lines.append("|---|---:|---:|---:|---:|---|")
    # Sort by max_drift descending
    def sort_key(r):
        return -(abs(r.get("max_drift_pt") or 0.0))
    for r in sorted(rows, key=sort_key):
        anname = r.get("anname", "?")
        if r.get("error"):
            lines.append(f"| {anname} | — | — | — | — | error: {r['error']} |")
            continue
        lines.append(
            f"| {anname} | {r.get('page')} | "
            f"{r.get('baseline_line_count')}/{r.get('preview_line_count')} | "
            f"{r.get('max_drift_pt')} | {r.get('cumulative_drift_pt')} | "
            f"{r.get('per_line_drift_pt')} |"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", required=True)
    ap.add_argument("--templates-dir", default="/workspace/templates")
    ap.add_argument("--dpi", type=int, default=_DEFAULT_DPI)
    ap.add_argument("--out-yaml")
    ap.add_argument("--out-md")
    ap.add_argument("--probe", help="Measure a single anname; print JSON to stdout.")
    args = ap.parse_args(argv)

    template_dir = Path(args.templates_dir) / args.slug
    build_py = template_dir / "build.py"
    preview = template_dir / "preview.pdf"
    baseline = template_dir / "baseline.pdf"
    if not (build_py.exists() and preview.exists() and baseline.exists()):
        sys.stderr.write(
            f"Missing build.py / preview.pdf / baseline.pdf in {template_dir}\n"
        )
        return 2

    frames = parse_textframes_from_build_py(build_py)
    if not frames:
        sys.stderr.write("No TextFrames found in build.py\n")
        return 2

    tmpdir = Path(tempfile.mkdtemp(prefix="line_spacing_pixel_"))
    try:
        preview_pngs = render_pdf_pages_to_png(
            preview, args.dpi, tmpdir / "preview"
        )
        baseline_pngs = render_pdf_pages_to_png(
            baseline, args.dpi, tmpdir / "baseline"
        )

        if args.probe:
            frame = frames.get(args.probe)
            if frame is None:
                sys.stderr.write(f"anname {args.probe!r} not found in build.py\n")
                return 2
            result = measure_frame(args.probe, frame, preview_pngs, baseline_pngs, args.dpi)
            print(json.dumps(result, indent=2, default=str))
            return 0

        rows: list[dict] = []
        for anname, info in frames.items():
            rows.append(measure_frame(anname, info, preview_pngs, baseline_pngs, args.dpi))
        if args.out_yaml:
            write_yaml(rows, Path(args.out_yaml))
        if args.out_md:
            write_md(rows, Path(args.out_md))
        summary = {"match": 0, "minor": 0, "major": 0, "errors": 0}
        for r in rows:
            if r.get("error"):
                summary["errors"] += 1
                continue
            m = r.get("max_drift_pt")
            if m is None:
                summary["errors"] += 1
            elif abs(m) <= 1.0:
                summary["match"] += 1
            elif abs(m) <= 3.0:
                summary["minor"] += 1
            else:
                summary["major"] += 1
        print(
            f"pixel-audit complete — {len(rows)} frames; summary: {summary}",
            file=sys.stderr,
        )
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
