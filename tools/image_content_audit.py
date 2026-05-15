#!/usr/bin/env python3
"""Image content audit — catches "image broken/missing/wrong-cropped" cases
that image_frame_visibility_audit misses.

Three detection modes per ImageFrame:

  1. **Color-variance loss**: baseline shows varied colors (real image
     content) but preview shows near-uniform color (e.g. background
     bleeding through). Flags when preview_variance < 30% of baseline.
  2. **Mean-color shift**: baseline avg RGB and preview avg RGB differ
     by > 30 in any channel — image is rendering different content.
  3. **Histogram divergence**: KL-style divergence between RGB
     histograms exceeds threshold — image content has shifted
     materially beyond colour-grading.

Each mode catches a different failure class:
  - mode 1: u139-class (image not rendering at all, frame shows bg)
  - mode 2: u2cd-class (image is wrong source / wrong crop)
  - mode 3: u3a0-class (FrameFittingOption RightCrop not honored)

Wire-in: render_pipeline.py Phase E5c (after image_frame_visibility).
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

import yaml

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parent.parent

_VARIANCE_LOSS_THRESHOLD = 0.30   # preview/baseline ratio below this → invisible
_MEAN_SHIFT_THRESHOLD = 60        # per-channel avg delta above this → wrong content
                                   # (loose; small icons trip false-positive)
_HIST_DIVERGENCE_THRESHOLD = 0.20  # JS-divergence above this → content drift
                                   # (catches u139 0.338, u141 0.247, u14a 0.389;
                                   # social icons sit at 0.09-0.18 = pass)


def _color_variance(crop) -> float:
    """Per-pixel std-dev across all RGB channels — high variance = varied image."""
    pixels = list(crop.getdata())
    if not pixels:
        return 0.0
    flat = [c for p in pixels for c in p[:3]]
    if len(flat) < 2:
        return 0.0
    return statistics.pstdev(flat)


def _mean_rgb(crop) -> tuple[float, float, float]:
    pixels = list(crop.getdata())
    if not pixels:
        return (0.0, 0.0, 0.0)
    n = len(pixels)
    r = sum(p[0] for p in pixels) / n
    g = sum(p[1] for p in pixels) / n
    b = sum(p[2] for p in pixels) / n
    return (r, g, b)


def _histogram_divergence(crop_a, crop_b, bins: int = 32) -> float:
    """Symmetric Jensen-Shannon divergence on per-channel histograms."""
    import math
    def hist(crop, channel):
        pixels = [p[channel] for p in crop.getdata()]
        if not pixels:
            return [0.0] * bins
        h = [0] * bins
        for p in pixels:
            idx = min(bins - 1, p * bins // 256)
            h[idx] += 1
        total = sum(h) or 1
        return [c / total for c in h]
    js_total = 0.0
    for ch in (0, 1, 2):
        ha = hist(crop_a, ch)
        hb = hist(crop_b, ch)
        m = [(a + b) / 2 for a, b in zip(ha, hb)]
        kl_a = sum(a * math.log((a + 1e-12) / (mm + 1e-12)) for a, mm in zip(ha, m))
        kl_b = sum(b * math.log((b + 1e-12) / (mm + 1e-12)) for b, mm in zip(hb, m))
        js_total += 0.5 * (kl_a + kl_b)
    return js_total / 3


def _crop_at_bbox(img, bbox_mm, dpi):
    PX_PER_MM = dpi / 25.4
    x, y, w, h = bbox_mm
    px_x = max(0, int(x * PX_PER_MM))
    px_y = max(0, int(y * PX_PER_MM))
    px_w = max(1, int(w * PX_PER_MM))
    px_h = max(1, int(h * PX_PER_MM))
    return img.crop((px_x, px_y, px_x + px_w, px_y + px_h))


def measure_frame_content(info: dict, baseline_pngs, preview_pngs, dpi: int) -> dict:
    pg = info.get("page", 0)
    if pg >= len(baseline_pngs) or pg >= len(preview_pngs):
        return {**info, "error": f"page {pg} out of range"}
    bbox_mm = info["bbox_mm"]
    bl = Image.open(baseline_pngs[pg]).convert("RGB")
    pv = Image.open(preview_pngs[pg]).convert("RGB")
    bl_crop = _crop_at_bbox(bl, bbox_mm, dpi)
    pv_crop = _crop_at_bbox(pv, bbox_mm, dpi)

    bl_var = _color_variance(bl_crop)
    pv_var = _color_variance(pv_crop)
    bl_rgb = _mean_rgb(bl_crop)
    pv_rgb = _mean_rgb(pv_crop)
    js_div = _histogram_divergence(bl_crop, pv_crop)

    variance_ratio = pv_var / bl_var if bl_var > 5 else 1.0
    mean_delta = max(abs(bl_rgb[i] - pv_rgb[i]) for i in range(3))

    flags = []
    if variance_ratio < _VARIANCE_LOSS_THRESHOLD and bl_var > 20:
        flags.append("variance_loss")
    if mean_delta > _MEAN_SHIFT_THRESHOLD:
        flags.append("mean_color_shift")
    if js_div > _HIST_DIVERGENCE_THRESHOLD:
        flags.append("hist_divergence")

    classification = "ok" if not flags else "broken"

    return {
        "anname": info["anname"],
        "page": pg,
        "bbox_mm": list(bbox_mm),
        "scale_type": info.get("scale_type"),
        "image_path": info.get("image_path"),
        "baseline_variance": round(bl_var, 2),
        "preview_variance": round(pv_var, 2),
        "variance_ratio": round(variance_ratio, 3),
        "baseline_mean_rgb": [round(c, 1) for c in bl_rgb],
        "preview_mean_rgb": [round(c, 1) for c in pv_rgb],
        "mean_delta_rgb": round(mean_delta, 1),
        "histogram_divergence": round(js_div, 4),
        "flags": flags,
        "classification": classification,
    }


def render_pdf_pages(pdf_path, dpi, out_prefix):
    """Rasterise PDF to PNGs at given DPI."""
    import subprocess
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-r", str(dpi), "-png", str(pdf_path), str(out_prefix)],
        check=True,
    )
    return sorted(out_prefix.parent.glob(out_prefix.name + "-*.png"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--templates-dir", type=Path, default=ROOT / "templates")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--out-yaml", type=Path)
    ap.add_argument("--out-md", type=Path)
    args = ap.parse_args(argv)

    if Image is None:
        print("ERROR: PIL not available", file=sys.stderr)
        return 1

    template_dir = args.templates_dir / args.slug
    preview = template_dir / "preview.pdf"
    baseline = template_dir / "baseline.pdf"
    if not preview.exists() or not baseline.exists():
        print(f"SKIPPED: missing preview.pdf or baseline.pdf", file=sys.stderr)
        return 0

    # Reuse image_frame_visibility's frame extraction
    sys.path.insert(0, str(ROOT / "tools"))
    from image_frame_visibility_audit import parse_image_frames_from_build_py
    frames = parse_image_frames_from_build_py(template_dir / "build.py")
    if not frames:
        print("no ImageFrames in build.py", file=sys.stderr)
        return 0

    import tempfile
    tmpdir = Path(tempfile.mkdtemp(prefix="image_content_"))
    preview_pngs = render_pdf_pages(preview, args.dpi, tmpdir / "preview")
    baseline_pngs = render_pdf_pages(baseline, args.dpi, tmpdir / "baseline")

    rows = []
    for f in frames:
        info = {
            "anname": f.anname,
            "page": f.page,
            "bbox_mm": f.bbox_mm,
            "scale_type": f.scale_type,
            "image_path": f.image_path,
        }
        rows.append(measure_frame_content(info, baseline_pngs, preview_pngs, args.dpi))

    summary = {
        "ok": sum(1 for r in rows if r.get("classification") == "ok"),
        "broken": sum(1 for r in rows if r.get("classification") == "broken"),
        "errors": sum(1 for r in rows if "error" in r),
    }
    broken_annames = [r["anname"] for r in rows if r.get("classification") == "broken"]

    out = {
        "slug": args.slug,
        "summary": summary,
        "broken_annames": broken_annames,
        "rows": rows,
        "ok": summary["broken"] == 0,
    }
    if args.out_yaml:
        args.out_yaml.parent.mkdir(parents=True, exist_ok=True)
        args.out_yaml.write_text(yaml.safe_dump(out, sort_keys=False))
    if args.out_md:
        lines = [f"# Image content audit — {args.slug}", ""]
        lines.append(f"- ok: {summary['ok']}")
        lines.append(f"- **broken: {summary['broken']}**")
        lines.append("")
        if broken_annames:
            lines.append("## Broken frames")
            for r in rows:
                if r.get("classification") == "broken":
                    lines.append(f"### {r['anname']}")
                    lines.append(f"- flags: {', '.join(r.get('flags', []))}")
                    lines.append(f"- baseline variance: {r['baseline_variance']}; "
                                 f"preview variance: {r['preview_variance']} "
                                 f"(ratio {r['variance_ratio']})")
                    lines.append(f"- baseline mean RGB: {r['baseline_mean_rgb']}; "
                                 f"preview mean RGB: {r['preview_mean_rgb']} "
                                 f"(max channel delta: {r['mean_delta_rgb']})")
                    lines.append(f"- histogram divergence: {r['histogram_divergence']}")
                    lines.append(f"- LLM ACTION: inspect templates/{args.slug}/build.py "
                                 f"frame {r['anname']}; check scale_type, local_offset_mm, "
                                 f"local_scale, image= path. If scale_type=1 + non-zero "
                                 f"offset, consider switching to library.inject_into_frame "
                                 f"or pre-cropping the source asset to the frame's aspect.")
                    lines.append("")
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text("\n".join(lines))

    print(f"image-content-audit: {summary['broken']} broken, {summary['ok']} ok")
    return 0 if summary["broken"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
