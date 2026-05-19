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
        --slug falzflyer-z-falz-6-seitig-zweigeteiltes-cover \\
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
    # Frame rotation in degrees (build.py ``rotation_deg=`` kwarg). 0.0 for
    # the common un-rotated frame. Rotation is around the frame's unrotated
    # top-left corner — the same pivot Scribus uses for ``ROT``.
    rotation_deg: float = 0.0
    # Run fill colors found in this frame (brand-palette names, e.g.
    # "White"/"Gelb"). Used by the split-headline audit to colour-scan each
    # line — heavy display headlines sit on a photo, so a generic background-
    # difference ink scan is unreliable; the line's known fill colour is the
    # robust signal.
    fill_colors: tuple[str, ...] = ()
    # Concatenated visible text of the frame's Runs (no separators). Lets the
    # split-headline detector confirm a line frame carries text.
    text: str = ""


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
        rot = _ast_literal(_ast_kw(node, "rotation_deg"))
        # Run fill colors + concatenated text — walk the runs= list literal.
        fill_colors: list[str] = []
        run_text_parts: list[str] = []
        runs_node = _ast_kw(node, "runs")
        if isinstance(runs_node, ast.List):
            for run_call in runs_node.elts:
                if not (isinstance(run_call, ast.Call)):
                    continue
                rfn = ""
                if isinstance(run_call.func, ast.Name):
                    rfn = run_call.func.id
                elif isinstance(run_call.func, ast.Attribute):
                    rfn = run_call.func.attr
                if rfn != "Run":
                    continue
                fc = _ast_literal(_ast_kw(run_call, "fcolor"))
                if isinstance(fc, str) and fc:
                    fill_colors.append(fc)
                rt = _ast_literal(_ast_kw(run_call, "text"))
                if isinstance(rt, str):
                    run_text_parts.append(rt)
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
            rotation_deg=float(rot) if rot is not None else 0.0,
            fill_colors=tuple(fill_colors),
            text="".join(run_text_parts),
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
# Split mixed-font headline audit
#
# A mixed-font forced-break headline (Gotham + a Vollkorn accent word) is
# emitted by the converter as N single-line TextFrames, each named
# ``<base>``, ``<base>_l2``, ``<base>_l3`` … (see idml_to_dsl.py
# ``_emit_mixed_font_headline``). Every split frame keeps the FULL original
# frame height, so the N frames overlap by whole lines.
#
# This wrecked the per-frame ink scan: ``_scan_frame_lines`` for ``<base>_l2``
# scans a 24mm-tall box that also contains line 1's ink, so it reports line
# 1's cap-top — IDENTICAL in baseline and preview — and a genuine inter-line
# mis-spacing of the Vollkorn line reads as 0.0 drift. The mixed-font headline
# split-calibration bug rendered the Vollkorn line 5-8pt off and this audit
# silently passed it.
#
# The fix here: detect split-headline groups, scan the group's UNION bbox for
# each line's KNOWN FILL COLOUR (the Run carries ``fcolor``; a colour scan is
# robust where a generic background-difference scan is not — these headlines
# sit on a photo), and check per-line ink-top drift AND inter-line spacing
# with a tight tolerance. A mis-spaced headline now produces a real finding.

# Approximate sRGB for the brand-palette fill names (process CMYK → naive
# sRGB). Only the names that appear on split-headline lines are needed.
_BRAND_RGB: dict[str, tuple[int, int, int]] = {
    "White": (255, 255, 255),
    "Gelb": (255, 242, 0),
    "Hellgrün": (79, 175, 50),
    "Dunkelgrün": (0, 95, 53),
    "Black": (0, 0, 0),
}
# Per-line ink-top drift bar: a split-headline line whose rendered ink-top is
# off by more than this many points vs the baseline is a real mis-spacing.
# 2.0pt ≈ 0.7mm — tight enough to catch the 5-8pt FLOP-ratio mis-calibration
# while admitting raster/anti-alias jitter.
SPLIT_HEADLINE_TOL_PT = 2.0


def detect_split_headline_groups(
    frames: dict[str, FrameInfo],
) -> list[list[str]]:
    """Return groups of annames forming one split mixed-font headline.

    A group is a base frame ``X`` plus every sibling ``X_l2``, ``X_l3`` …
    present in ``frames``. Only groups with >= 2 members are returned —
    a lone frame is an ordinary headline, not a split one.
    """
    groups: dict[str, list[str]] = {}
    for an in frames:
        # Sibling line frames are named "<base>_l<N>" with N >= 2.
        base = an
        if "_l" in an:
            head, _, tail = an.rpartition("_l")
            if tail.isdigit() and int(tail) >= 2 and head:
                base = head
        groups.setdefault(base, []).append(an)

    def _line_idx(an: str) -> int:
        if "_l" in an:
            tail = an.rpartition("_l")[2]
            if tail.isdigit():
                return int(tail)
        return 1

    out: list[list[str]] = []
    for base, members in groups.items():
        if len(members) < 2 or base not in frames:
            continue
        out.append(sorted(members, key=_line_idx))
    return out


def _color_match(r: int, g: int, b: int, fill: str) -> bool:
    """True when the pixel is the headline line's brand fill colour.

    A split headline sits on a photo, so the test must be specific:
      * White — near-pure white. Loose RGB-distance admits the gray jacket's
        highlights (a phantom ink-top at the frame edge); require all
        channels >= 235.
      * Gelb — saturated yellow: high R and G, low B, distinctly warm. A
        green photo never satisfies this.
      * Hellgrün / Dunkelgrün / Black — fall back to a moderate RGB distance.
    """
    if fill == "White":
        return r >= 235 and g >= 235 and b >= 235
    if fill == "Gelb":
        return r >= 200 and g >= 175 and b <= 165 and (r - b) >= 70
    tr, tg, tb = _BRAND_RGB.get(fill, (255, 255, 255))
    return abs(r - tr) <= 55 and abs(g - tg) <= 55 and abs(b - tb) <= 55


def _scan_color_lines(
    img: "Image.Image",
    bbox_mm: tuple[float, float, float, float],
    fill: str,
    dpi: int,
    min_ink_columns: int = 6,
    line_gap_min_px: int = 6,
) -> tuple[list[float], list[float]]:
    """Return (line_tops_pt, line_bottoms_pt) for pixels of ``fill`` colour.

    Like ``_scan_frame_lines`` but matches a SPECIFIC brand fill colour
    instead of "differs from background". A headline line sits on a photo;
    the line's known brand fill (white / yellow) is the only reliable signal
    there. ``fill`` is the brand-palette name (see ``_color_match``).
    """
    factor = dpi / 72.0
    x_min_pt = bbox_mm[0] * _MM_TO_PT
    y_min_pt = bbox_mm[1] * _MM_TO_PT
    w_pt, h_pt = bbox_mm[2] * _MM_TO_PT, bbox_mm[3] * _MM_TO_PT
    iw, ih = img.size
    x0 = max(0, min(iw - 1, int(x_min_pt * factor)))
    x1 = max(0, min(iw, int((x_min_pt + w_pt) * factor)))
    y0 = max(0, min(ih - 1, int(y_min_pt * factor)))
    y1 = max(0, min(ih, int((y_min_pt + h_pt) * factor)))
    if x1 <= x0 or y1 <= y0:
        return [], []
    px = img.load()
    ink_rows: list[int] = []
    for y in range(y0, y1):
        cnt = 0
        for x in range(x0, x1, 2):
            r, g, b = px[x, y][:3]
            if _color_match(r, g, b, fill):
                cnt += 1
                if cnt >= min_ink_columns:
                    break
        if cnt >= min_ink_columns:
            ink_rows.append(y)
    if not ink_rows:
        return [], []
    lines: list[list[int]] = [[ink_rows[0]]]
    for y in ink_rows[1:]:
        if y - lines[-1][-1] > line_gap_min_px:
            lines.append([y])
        else:
            lines[-1].append(y)
    tops = [round(ln[0] / factor, 3) for ln in lines]
    bottoms = [round(ln[-1] / factor, 3) for ln in lines]
    return tops, bottoms


def _scan_color_headline_top(
    img: "Image.Image",
    bbox_mm: tuple[float, float, float, float],
    fill: str,
    dpi: int,
    line_gap_min_px: int = 6,
) -> Optional[float]:
    """Return the ink-top (pt) of the DENSEST ``fill``-coloured band in ``bbox``.

    A split mixed-font headline frame is widened past its IDML text width by
    the converter's clip-safety margin, so its bbox can overhang a photo. When
    that photo carries a near-``fill`` tone (e.g. white atmospheric fog under a
    white headline) the ordinary top-down "first row above a low column count"
    scan latches onto the diffuse photo texture instead of the glyphs and
    reports a phantom drift.

    Glyph strokes of a large headline line form a band whose peak per-row
    matched-column count is several times that of any diffuse photo band, so
    this scan groups all matched rows into bands and returns the TOP of the
    band with the highest peak density — the real headline line. Diffuse
    contamination bands are discarded. Returns ``None`` when no band is found.
    """
    factor = dpi / 72.0
    x_min_pt = bbox_mm[0] * _MM_TO_PT
    y_min_pt = bbox_mm[1] * _MM_TO_PT
    w_pt, h_pt = bbox_mm[2] * _MM_TO_PT, bbox_mm[3] * _MM_TO_PT
    iw, ih = img.size
    x0 = max(0, min(iw - 1, int(x_min_pt * factor)))
    x1 = max(0, min(iw, int((x_min_pt + w_pt) * factor)))
    y0 = max(0, min(ih - 1, int(y_min_pt * factor)))
    y1 = max(0, min(ih, int((y_min_pt + h_pt) * factor)))
    if x1 <= x0 or y1 <= y0:
        return None
    px = img.load()
    # Per-row matched-column count (sample every other column, as elsewhere).
    row_counts: list[tuple[int, int]] = []
    for y in range(y0, y1):
        cnt = 0
        for x in range(x0, x1, 2):
            r, g, b = px[x, y][:3]
            if _color_match(r, g, b, fill):
                cnt += 1
        if cnt > 0:
            row_counts.append((y, cnt))
    if not row_counts:
        return None
    # Group consecutive matched rows into bands.
    bands: list[list[tuple[int, int]]] = [[row_counts[0]]]
    for y, cnt in row_counts[1:]:
        if y - bands[-1][-1][0] > line_gap_min_px:
            bands.append([(y, cnt)])
        else:
            bands[-1].append((y, cnt))
    # The real headline line is the band with the highest peak column count;
    # diffuse photo contamination forms low-peak bands and is discarded.
    best = max(bands, key=lambda band: max(c for _, c in band))
    peak = max(c for _, c in best)
    # Diffuse photo contamination (e.g. fog) can border the glyphs closely
    # enough to merge into the same band; its rows carry far fewer matched
    # columns than a glyph cap row. Return the first row inside the densest
    # band whose count reaches half the band peak — the glyph cap-top — so a
    # faint contamination skirt below the threshold cannot pull the top up.
    for y, cnt in best:
        if cnt * 2 >= peak:
            return round(y / factor, 3)
    return round(best[0][0] / factor, 3)


def measure_split_headline(
    group: list[str],
    frames: dict[str, FrameInfo],
    preview_pngs: list[Path],
    baseline_pngs: list[Path],
    dpi: int,
) -> dict:
    """Measure a split mixed-font headline's per-line rendered ink-tops.

    For each line frame in ``group`` the line's fill colour is colour-scanned
    inside the GROUP UNION bbox (so the line is found wherever it rendered,
    in both PDFs). Per-line ink-top drift and inter-line spacing are compared
    between preview and baseline. A drift beyond ``SPLIT_HEADLINE_TOL_PT`` on
    any line, or an inter-line gap that drifts beyond it, is a real bug.
    """
    base = group[0]
    if Image is None:
        return {"anname": base, "kind": "split_headline", "error": "Pillow not installed"}
    pg = frames[base].page
    if pg >= len(baseline_pngs) or pg >= len(preview_pngs):
        return {"anname": base, "kind": "split_headline",
                "error": f"page {pg} out of range"}
    bl_img = Image.open(baseline_pngs[pg]).convert("RGB")
    pv_img = Image.open(preview_pngs[pg]).convert("RGB")
    # Union bbox of every line frame in the group.
    xs0 = [frames[a].bbox_mm[0] for a in group]
    ys0 = [frames[a].bbox_mm[1] for a in group]
    xs1 = [frames[a].bbox_mm[0] + frames[a].bbox_mm[2] for a in group]
    ys1 = [frames[a].bbox_mm[1] + frames[a].bbox_mm[3] for a in group]
    union = (min(xs0), min(ys0), max(xs1) - min(xs0), max(ys1) - min(ys0))

    bl_tops: list[float] = []
    pv_tops: list[float] = []
    per_line: list[dict] = []
    for an in group:
        fi = frames[an]
        # The line's fill colour: first run fcolor, default White.
        fcolor = fi.fill_colors[0] if fi.fill_colors else "White"
        # Scan a per-line band: the union bbox restricted vertically to a
        # window anchored at this line frame's authored top and one frame-
        # height tall. A colour shared by two lines (two white lines) cannot
        # cross-contaminate as long as the lines are within ~one line of
        # their authored position; the colour scan takes the FIRST band so a
        # line that drifted DOWN still reports its own top, and a line that
        # drifted UP into its sibling is exactly the mis-spacing this catches.
        line_box = (union[0], fi.bbox_mm[1], union[2], fi.bbox_mm[3])
        # Density-aware scan: the converter widens a split-headline frame past
        # its IDML text width, so the band can overhang a photo whose tone
        # matches the headline fill (e.g. white fog under a white headline).
        # The densest matched band is the real glyph line; diffuse photo
        # contamination forms low-peak bands and is discarded.
        b_top = _scan_color_headline_top(bl_img, line_box, fcolor, dpi)
        p_top = _scan_color_headline_top(pv_img, line_box, fcolor, dpi)
        bl_tops.append(b_top)
        pv_tops.append(p_top)
        drift = (round(p_top - b_top, 3)
                 if (b_top is not None and p_top is not None) else None)
        per_line.append({
            "anname": an, "fill": fcolor,
            "baseline_top_pt": b_top, "preview_top_pt": p_top,
            "drift_pt": drift,
        })

    drifts = [pl["drift_pt"] for pl in per_line if pl["drift_pt"] is not None]
    max_drift = round(max(abs(d) for d in drifts), 3) if drifts else None
    # Inter-line spacing drift: change in gap between consecutive lines.
    spacing_drifts: list[float] = []
    for i in range(1, len(group)):
        bp, bpp = bl_tops[i], bl_tops[i - 1]
        pp, ppp = pv_tops[i], pv_tops[i - 1]
        if None in (bp, bpp, pp, ppp):
            continue
        spacing_drifts.append(round((pp - ppp) - (bp - bpp), 3))
    max_spacing_drift = (
        round(max(abs(d) for d in spacing_drifts), 3)
        if spacing_drifts else None
    )
    return {
        "anname": base,
        "kind": "split_headline",
        "page": pg,
        "group": group,
        "per_line": per_line,
        "max_drift_pt": max_drift,
        "spacing_drifts_pt": spacing_drifts,
        "max_spacing_drift_pt": max_spacing_drift,
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
        if r.get("kind") == "split_headline":
            # Graded on per-line ink-top drift AND inter-line spacing drift.
            sd = r.get("max_spacing_drift_pt")
            if m is None and sd is None:
                counts["unmatched_count"] += 1
                continue
            worst = max(
                abs(m) if m is not None else 0.0,
                abs(sd) if sd is not None else 0.0,
            )
            if worst <= 1.0:
                counts["match"] += 1
            elif worst <= SPLIT_HEADLINE_TOL_PT:
                counts["minor"] += 1
            else:
                counts["major"] += 1
            continue
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
        if r.get("kind") == "split_headline":
            per = [pl.get("drift_pt") for pl in r.get("per_line", [])]
            lines.append(
                f"| {anname} (split headline) | {r.get('page')} | "
                f"{len(r.get('group', []))} lines | "
                f"{r.get('max_drift_pt')} | {r.get('max_spacing_drift_pt')} | "
                f"per-line {per}; spacing {r.get('spacing_drifts_pt')} |"
            )
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
    ap.add_argument(
        "--skip-freshness", action="store_true",
        help="Skip artifact freshness check. Set by render-gallery internal calls "
             "that know they just produced the artifacts. Manual callers should "
             "NEVER pass this flag — let the audit refuse stale inputs.",
    )
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

    if not args.skip_freshness:
        from _freshness_gate import ensure_fresh, StaleArtifactsError
        try:
            ensure_fresh(template_dir, audit_name="line_spacing_pixel_audit")
        except StaleArtifactsError as exc:
            sys.stderr.write(str(exc))
            return 3

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
            # If the probed frame is part of a split mixed-font headline,
            # report the GROUP measurement — a per-frame scan of a split
            # line frame is misleading (overlapping sibling ink).
            for grp in detect_split_headline_groups(frames):
                if args.probe in grp:
                    result = measure_split_headline(
                        grp, frames, preview_pngs, baseline_pngs, args.dpi
                    )
                    print(json.dumps(result, indent=2, default=str))
                    return 0
            result = measure_frame(args.probe, frame, preview_pngs, baseline_pngs, args.dpi)
            print(json.dumps(result, indent=2, default=str))
            return 0

        # Split mixed-font headline groups are measured as ONE reconstructed
        # headline (colour-scanned, inter-line spacing checked) — NOT as N
        # independent single-line frames. A per-frame scan of a split line
        # frame reads its overlapping sibling's ink and reports a phantom
        # 0.0 drift, hiding a real mis-spacing; the group measurement is the
        # authoritative signal for these frames.
        split_groups = detect_split_headline_groups(frames)
        split_members = {an for grp in split_groups for an in grp}

        rows: list[dict] = []
        for anname, info in frames.items():
            if anname in split_members:
                continue  # covered by the split_headline group row
            rows.append(measure_frame(anname, info, preview_pngs, baseline_pngs, args.dpi))
        split_rows: list[dict] = []
        for grp in split_groups:
            split_rows.append(
                measure_split_headline(grp, frames, preview_pngs, baseline_pngs, args.dpi)
            )
        rows.extend(split_rows)
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
            if r.get("kind") == "split_headline":
                # A split headline is also graded on inter-line spacing.
                sd = r.get("max_spacing_drift_pt")
                worst = max(
                    abs(m) if m is not None else 0.0,
                    abs(sd) if sd is not None else 0.0,
                )
                if m is None and sd is None:
                    summary["errors"] += 1
                elif worst <= 1.0:
                    summary["match"] += 1
                elif worst <= SPLIT_HEADLINE_TOL_PT:
                    summary["minor"] += 1
                else:
                    summary["major"] += 1
                continue
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
