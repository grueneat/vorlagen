#!/usr/bin/env python3
"""Per-frame image visibility audit — catches "embedded but invisible" icons.

The existing `image_audit.yml` counts ImageFrame emissions in build.py
vs `pdfimages -list` raster placements in baseline.pdf. The counts
diverge for legitimate reasons (InDesign frequently embeds icons as
vector PDFs not raster), so the audit hint "N extra in build.py" is
noisy and easily dismissed.

This audit answers the actual question: **for each ImageFrame in
build.py, is the rendered preview substantially less dense than the
rendered baseline?** If preview is mostly background colour where
baseline has ink, the icon embedded but didn't render — likely the
Scribus 1.6.x SCALETYPE=1 + small-frame + RGBA white-on-transparent
PNG bug (see `tools/sla_lib/builder/primitives.py:807-813`).

Algorithm:
1. Parse build.py for every ImageFrame (anname, page, bbox_mm).
2. Rasterise preview.pdf + baseline.pdf at 150 dpi.
3. For each frame, count "ink" pixels (non-background) inside the bbox
   for both renders.
4. Flag frames where preview ink density ≤ 30% of baseline.

Usage:

    python3 tools/image_frame_visibility_audit.py \\
        --slug 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover \\
        --templates-dir /workspace/templates \\
        --out-yaml build/validation/<slug>/image_frame_visibility_audit.yml \\
        --out-md  build/validation/<slug>/image_frame_visibility_audit.md
"""
from __future__ import annotations

import argparse
import ast
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
_DEFAULT_DPI = 150
_MIN_VISIBLE_RATIO = 0.30  # preview ink density must be ≥ 30% of baseline


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


@dataclass
class ImageFrameInfo:
    anname: str
    page: int
    bbox_mm: tuple[float, float, float, float]
    scale_type: Optional[int]
    has_inline: bool
    image_path: Optional[str]


def parse_image_frames_from_build_py(build_py: Path) -> list[ImageFrameInfo]:
    out: list[ImageFrameInfo] = []
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
        if fn != "ImageFrame":
            continue
        anname = _ast_literal(_ast_kw(node, "anname"))
        if not anname:
            continue
        # Coordinates of 0 are valid — `or`-chain would silently drop them.
        def _coord(primary: str, alt: str):
            v = _ast_literal(_ast_kw(node, primary))
            if v is not None:
                return v
            return _ast_literal(_ast_kw(node, alt))
        x = _coord("x_mm", "x")
        y = _coord("y_mm", "y")
        w = _coord("w_mm", "w")
        h = _coord("h_mm", "h")
        if None in (x, y, w, h):
            continue
        scale_type = _ast_literal(_ast_kw(node, "scale_type"))
        inline_kw = _ast_kw(node, "inline_image_data")
        has_inline = inline_kw is not None
        image_path = _ast_literal(_ast_kw(node, "image"))
        if image_path is None:
            image_path = _ast_literal(_ast_kw(node, "src"))
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
        out.append(ImageFrameInfo(
            anname=str(anname),
            page=page,
            bbox_mm=(float(x), float(y), float(w), float(h)),
            scale_type=int(scale_type) if scale_type is not None else None,
            has_inline=has_inline,
            image_path=image_path if isinstance(image_path, str) else None,
        ))
    return out


def _sample_bg(img: "Image.Image", x_px: int, y_px: int) -> tuple[int, int, int]:
    """Sample background near (x, y) — median of a small patch."""
    px = img.load()
    w, h = img.size
    samples = []
    for dy in range(-8, 9, 2):
        for dx in range(-8, 9, 2):
            xi, yi = max(0, min(w - 1, x_px + dx)), max(0, min(h - 1, y_px + dy))
            samples.append(px[xi, yi][:3])
    samples.sort()
    return samples[len(samples) // 2]


def _count_ink_pixels(
    img: "Image.Image",
    bbox_mm: tuple[float, float, float, float],
    dpi: int,
    threshold: int = 60,
) -> tuple[int, int, tuple[int, int, int]]:
    """Return (ink_pixel_count, total_pixel_count, bg_rgb) for the bbox."""
    factor = dpi / 72.0
    x_min = int(bbox_mm[0] * _MM_TO_PT * factor)
    y_min = int(bbox_mm[1] * _MM_TO_PT * factor)
    x_max = int((bbox_mm[0] + bbox_mm[2]) * _MM_TO_PT * factor)
    y_max = int((bbox_mm[1] + bbox_mm[3]) * _MM_TO_PT * factor)
    iw, ih = img.size
    x_min = max(0, min(iw - 1, x_min))
    x_max = max(0, min(iw, x_max))
    y_min = max(0, min(ih - 1, y_min))
    y_max = max(0, min(ih, y_max))
    if x_max <= x_min or y_max <= y_min:
        return 0, 0, (0, 0, 0)
    bg = _sample_bg(img, max(0, x_min - 10), max(0, y_min - 10))
    px = img.load()
    ink = 0
    total = 0
    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            total += 1
            pixel = px[x, y][:3]
            if any(abs(pixel[i] - bg[i]) >= threshold for i in range(3)):
                ink += 1
    return ink, total, bg


def measure_frame_visibility(
    info: ImageFrameInfo,
    baseline_pngs: list[Path],
    preview_pngs: list[Path],
    dpi: int,
) -> dict:
    pg = info.page
    if pg >= len(baseline_pngs) or pg >= len(preview_pngs):
        return {"anname": info.anname, "error": f"page {pg} out of range"}
    bl = Image.open(baseline_pngs[pg])
    pv = Image.open(preview_pngs[pg])
    bl_ink, bl_total, bl_bg = _count_ink_pixels(bl, info.bbox_mm, dpi)
    pv_ink, pv_total, pv_bg = _count_ink_pixels(pv, info.bbox_mm, dpi)
    bl_density = bl_ink / bl_total if bl_total else 0.0
    pv_density = pv_ink / pv_total if pv_total else 0.0
    # Visibility ratio: preview ink / baseline ink. <0.3 = likely invisible.
    visibility_ratio = pv_density / bl_density if bl_density > 0 else 1.0
    classification = "ok"
    if bl_density > 0.02 and visibility_ratio < _MIN_VISIBLE_RATIO:
        classification = "invisible_in_preview"
    elif bl_density > 0.02 and visibility_ratio < 0.7:
        classification = "faint_in_preview"
    return {
        "anname": info.anname,
        "page": pg,
        "bbox_mm": list(info.bbox_mm),
        "scale_type": info.scale_type,
        "has_inline": info.has_inline,
        "image_path": info.image_path,
        "baseline_ink_density": round(bl_density, 4),
        "preview_ink_density": round(pv_density, 4),
        "visibility_ratio": round(visibility_ratio, 3),
        "classification": classification,
    }


def write_yaml(rows: list[dict], out_path: Path) -> None:
    counts = {"ok": 0, "faint_in_preview": 0, "invisible_in_preview": 0, "errors": 0}
    invisible = []
    for r in rows:
        if r.get("error"):
            counts["errors"] += 1
            continue
        c = r.get("classification", "ok")
        counts[c] = counts.get(c, 0) + 1
        if c == "invisible_in_preview":
            invisible.append(r.get("anname"))
    payload = {
        "row_count": len(rows),
        "summary": counts,
        "invisible_frames": invisible,
        "rows": rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))


def write_md(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Image-frame visibility audit\n"]
    lines.append(f"Frames measured: **{len(rows)}**\n")
    lines.append("Flags ImageFrames that are embedded but render less than 30% as dense as in baseline.pdf.\n")
    lines.append("Common cause: Scribus 1.6.x renders SCALETYPE=1 + small-frame + RGBA white-on-transparent PNG as transparent (CMYK conversion bug).\n")
    lines.append("| Anname | Page | scale_type | inline? | image | Baseline density | Preview density | Visibility ratio | Class |")
    lines.append("|---|---:|---:|---:|---|---:|---:|---:|---|")
    def sort_key(r):
        c = r.get("classification", "ok")
        order = {"invisible_in_preview": 0, "faint_in_preview": 1, "ok": 2}.get(c, 3)
        return (order, r.get("visibility_ratio") or 0)
    for r in sorted(rows, key=sort_key):
        if r.get("error"):
            lines.append(f"| {r.get('anname')} | — | — | — | — | — | — | — | error: {r['error']} |")
            continue
        img_path = (r.get("image_path") or "")[-30:]
        lines.append(
            f"| {r['anname']} | {r['page']} | {r.get('scale_type')} | "
            f"{'Y' if r['has_inline'] else 'N'} | {img_path} | "
            f"{r['baseline_ink_density']} | {r['preview_ink_density']} | "
            f"{r['visibility_ratio']} | {r['classification']} |"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_pdf_pages(pdf: Path, dpi: int, prefix: Path) -> list[Path]:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(prefix)],
        check=True, capture_output=True,
    )
    return sorted(prefix.parent.glob(prefix.name + "-*.png"))


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", required=True)
    ap.add_argument("--templates-dir", default="/workspace/templates")
    ap.add_argument("--dpi", type=int, default=_DEFAULT_DPI)
    ap.add_argument("--out-yaml")
    ap.add_argument("--out-md")
    ap.add_argument(
        "--skip-freshness", action="store_true",
        help="Skip artifact freshness check. Set by render-gallery internal "
             "calls that know they just produced the artifacts. Manual "
             "callers should NEVER pass this flag.",
    )
    args = ap.parse_args(argv)

    if Image is None:
        sys.stderr.write("Pillow not installed\n")
        return 2

    template_dir = Path(args.templates_dir) / args.slug
    build_py = template_dir / "build.py"
    preview = template_dir / "preview.pdf"
    baseline = template_dir / "baseline.pdf"
    if not (build_py.exists() and preview.exists() and baseline.exists()):
        sys.stderr.write(f"Missing required files in {template_dir}\n")
        return 2

    if not args.skip_freshness:
        from _freshness_gate import ensure_fresh, StaleArtifactsError
        try:
            ensure_fresh(template_dir, audit_name="image_frame_visibility_audit")
        except StaleArtifactsError as exc:
            sys.stderr.write(str(exc))
            return 3

    frames = parse_image_frames_from_build_py(build_py)
    if not frames:
        sys.stderr.write("No ImageFrames in build.py\n")
        return 0

    tmpdir = Path(tempfile.mkdtemp(prefix="image_visibility_"))
    try:
        preview_pngs = render_pdf_pages(preview, args.dpi, tmpdir / "preview")
        baseline_pngs = render_pdf_pages(baseline, args.dpi, tmpdir / "baseline")
        rows = [measure_frame_visibility(f, baseline_pngs, preview_pngs, args.dpi)
                for f in frames]
        if args.out_yaml:
            write_yaml(rows, Path(args.out_yaml))
        if args.out_md:
            write_md(rows, Path(args.out_md))
        summary = {"ok": 0, "faint_in_preview": 0, "invisible_in_preview": 0, "errors": 0}
        invisible = []
        for r in rows:
            if r.get("error"):
                summary["errors"] += 1
                continue
            summary[r.get("classification", "ok")] += 1
            if r.get("classification") == "invisible_in_preview":
                invisible.append(r["anname"])
        print(
            f"image-visibility complete — {len(rows)} frames; summary: {summary}; "
            f"invisible: {invisible}",
            file=sys.stderr,
        )
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
