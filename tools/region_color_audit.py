#!/usr/bin/env python3
"""Per-region mean RGB color delta audit.

For each frame in build.py with a bounding box, sample the corresponding region
from baseline.pdf and preview.pdf (rasterised at 150 dpi). Compute mean and max
RGB delta. Classify by severity: uniform small offset (icc_likely —
icc_drift_uniform_small, sub-percent uniform RGB delta from CMYK to sRGB ICC
profile rendering) vs concentrated large delta (fill_likely — converter
fill-color bug).

Usage:
    python3 tools/region_color_audit.py \\
      --build-py templates/<slug>/build.py \\
      --baseline templates/<slug>/baseline.pdf \\
      --preview templates/<slug>/preview.pdf \\
      --template <slug> \\
      --out build/validation/<slug>/region_color_audit.yml
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from PIL import Image


# ---------------------------------------------------------------------------
# PDF rasterisation
# ---------------------------------------------------------------------------

def rasterise_pdf(pdf_path: Path, out_prefix: Path, dpi: int = 150) -> list[Path]:
    """Use pdftocairo to rasterise all pages of the PDF to PNG.

    Returns a sorted list of PNG paths (one per page), in page order.
    """
    subprocess.run(
        ["pdftocairo", "-png", "-r", str(dpi), str(pdf_path), str(out_prefix)],
        check=True,
        capture_output=True,
    )
    return sorted(out_prefix.parent.glob(f"{out_prefix.name}-*.png"))


# ---------------------------------------------------------------------------
# build.py frame parser
# ---------------------------------------------------------------------------

# Matches one page.add(...) call, capturing: class name, and all keyword args
# as a flat string.  We match greedily up to the closing )) pattern.
_ADD_CALL_RE = re.compile(
    r"page(\d+)\.add\(\s*(TextFrame|ImageFrame|Polygon|PolyLine)\s*\(",
    re.DOTALL,
)

_KW_RE = re.compile(
    r"(?:^|,)\s*"
    r"(x_mm|y_mm|w_mm|h_mm|anname)"
    r"\s*=\s*"
    r"(['\"]?)(-?[\d.]+|'[^']*'|\"[^\"]*\")(['\"]?)",
    re.MULTILINE,
)


def _extract_float(s: str) -> float:
    """Parse a float literal (possibly with surrounding quotes stripped)."""
    s = s.strip().strip("'\"")
    return float(s)


def _extract_str(s: str) -> str:
    """Strip surrounding quote characters from a string literal."""
    return s.strip().strip("'\"")


def parse_frames_from_build_py(build_py: Path) -> list[dict]:
    """Extract frame descriptors from a build.py source file.

    Returns a list of dicts with keys:
      anname, page (0-indexed), type, x_mm, y_mm, w_mm, h_mm

    Handles the standard emit format produced by idml_to_dsl.py:
        pageN.add(Polygon(
            x_mm=..., y_mm=..., w_mm=..., h_mm=...,
            anname='uXXX',
            ...
        ))
    """
    source = build_py.read_text(encoding="utf-8")
    frames: list[dict] = []

    # Find all page.add(ClassName( positions with their page index and type.
    for m in _ADD_CALL_RE.finditer(source):
        page_idx = int(m.group(1))
        frame_type = m.group(2)
        # Scan forward from the opening paren to find the matching closing )).
        start = m.end()
        depth = 1
        pos = start
        while pos < len(source) and depth > 0:
            ch = source[pos]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            pos += 1
        # source[start:pos-1] is the kwargs block inside the inner call.
        kwargs_text = source[start : pos - 1]

        # Extract named keyword values from the kwargs block.
        kv: dict[str, str] = {}
        # Simple line-by-line pass: look for `key=value` pairs.
        for line in kwargs_text.splitlines():
            for key in ("x_mm", "y_mm", "w_mm", "h_mm", "anname"):
                pat = re.search(
                    rf"\b{key}\s*=\s*(-?[\d.]+|'[^']*'|\"[^\"]*\")",
                    line,
                )
                if pat:
                    kv[key] = pat.group(1)

        # Require all geometry fields and anname.
        if not all(k in kv for k in ("x_mm", "y_mm", "w_mm", "h_mm", "anname")):
            continue

        try:
            x_mm = _extract_float(kv["x_mm"])
            y_mm = _extract_float(kv["y_mm"])
            w_mm = _extract_float(kv["w_mm"])
            h_mm = _extract_float(kv["h_mm"])
        except ValueError:
            continue

        anname = _extract_str(kv["anname"])

        frames.append(
            {
                "anname": anname,
                "page": page_idx,
                "type": frame_type,
                "x_mm": x_mm,
                "y_mm": y_mm,
                "w_mm": w_mm,
                "h_mm": h_mm,
            }
        )

    return frames


# ---------------------------------------------------------------------------
# Region sampling
# ---------------------------------------------------------------------------

def mm_to_px(mm: float, dpi: int) -> int:
    """Convert millimetres to pixels at the given DPI.

    Formula: mm × dpi / 25.4 (standard mm → inch → pixel conversion).
    """
    return int(round(mm * dpi / 25.4))


def bbox_mm_to_px(x_mm: float, y_mm: float, w_mm: float, h_mm: float,
                  dpi: int) -> tuple[int, int, int, int]:
    """Convert a bbox in mm to (left, top, right, bottom) in pixels."""
    left = mm_to_px(x_mm, dpi)
    top = mm_to_px(y_mm, dpi)
    right = mm_to_px(x_mm + w_mm, dpi)
    bottom = mm_to_px(y_mm + h_mm, dpi)
    return (left, top, right, bottom)


def sample_region_rgb(image: Image.Image, bbox_px: tuple[int, int, int, int]) -> tuple:
    """Return (mean_r, mean_g, mean_b, n_pixels) for the bbox region.

    bbox_px is (left, top, right, bottom) in pixels.
    Returns (0, 0, 0, 0) for empty or degenerate crops.
    """
    img_w, img_h = image.size
    left, top, right, bottom = bbox_px
    # Clamp to image bounds.
    left = max(0, min(left, img_w))
    top = max(0, min(top, img_h))
    right = max(0, min(right, img_w))
    bottom = max(0, min(bottom, img_h))

    if right <= left or bottom <= top:
        return (0.0, 0.0, 0.0, 0)

    crop = image.crop((left, top, right, bottom)).convert("RGB")
    import numpy as np  # lazy import — optional fast path
    arr = np.array(crop, dtype=float)
    mr = float(arr[:, :, 0].mean())
    mg = float(arr[:, :, 1].mean())
    mb = float(arr[:, :, 2].mean())
    n = (right - left) * (bottom - top)
    return (mr, mg, mb, n)


def _sample_region_rgb_pure(image: Image.Image,
                             bbox_px: tuple[int, int, int, int]) -> tuple:
    """Pure-Python fallback for sample_region_rgb (used in tests)."""
    img_w, img_h = image.size
    left, top, right, bottom = bbox_px
    left = max(0, min(left, img_w))
    top = max(0, min(top, img_h))
    right = max(0, min(right, img_w))
    bottom = max(0, min(bottom, img_h))

    if right <= left or bottom <= top:
        return (0.0, 0.0, 0.0, 0)

    crop = image.crop((left, top, right, bottom)).convert("RGB")
    import struct
    raw = crop.tobytes()
    n = len(raw) // 3
    if n == 0:
        return (0.0, 0.0, 0.0, 0)
    rs = sum(raw[i] for i in range(0, len(raw), 3))
    gs = sum(raw[i] for i in range(1, len(raw), 3))
    bs = sum(raw[i] for i in range(2, len(raw), 3))
    return (rs / n, gs / n, bs / n, n)


def _do_sample(image: Image.Image, bbox_px: tuple[int, int, int, int]) -> tuple:
    """Dispatch to numpy or pure-Python implementation."""
    try:
        return sample_region_rgb(image, bbox_px)
    except ImportError:
        return _sample_region_rgb_pure(image, bbox_px)


# ---------------------------------------------------------------------------
# Severity classification
# ---------------------------------------------------------------------------

def classify_severity(mean_delta: float) -> str:
    """Classify colour delta magnitude into audit severity bucket.

    Thresholds (RGB units, 0-255 scale):
    - ok:          mean_delta < 3   → within rasterisation noise floor
    - icc_likely:  3 ≤ delta < 15  → uniform small offset, consistent with
                   CMYK→sRGB ICC profile rendering drift (icc_drift_uniform_small)
    - fill_likely: delta ≥ 15      → large concentrated delta, likely a
                   wrong fill-color emitted by the converter (fixable)
    """
    if mean_delta < 3:
        return "ok"
    if mean_delta < 15:
        return "icc_likely"
    return "fill_likely"


def classify_pattern(by_severity: dict[str, int]) -> str:
    """Classify overall document pattern from per-region severity counts.

    - predominantly_icc_drift: icc_likely count >= 3× fill_likely count
    - concentrated_fill_bugs:  fill_likely count >= 3
    - mixed:                   neither dominates
    """
    icc = by_severity.get("icc_likely", 0)
    fill = by_severity.get("fill_likely", 0)
    if fill == 0 and icc >= 3:
        return "predominantly_icc_drift"
    if fill > 0 and icc >= 3 * fill:
        return "predominantly_icc_drift"
    if fill >= 3:
        return "concentrated_fill_bugs"
    return "mixed"


# ---------------------------------------------------------------------------
# Main audit entry point
# ---------------------------------------------------------------------------

def run_region_color_audit(
    build_py: Path,
    baseline_pdf: Path,
    preview_pdf: Path,
    template: str,
    dpi: int = 150,
) -> dict:
    """Run the per-region mean RGB delta audit.

    Rasterises baseline_pdf and preview_pdf, then for each frame parsed from
    build_py computes the mean RGB of the corresponding page region in each PDF
    and derives delta + severity classification.

    Returns a dict matching the region_color_audit.yml schema.
    """
    frames = parse_frames_from_build_py(build_py)

    with tempfile.TemporaryDirectory(prefix="region_color_audit_") as tmpdir:
        tmpdir_path = Path(tmpdir)

        base_prefix = tmpdir_path / "base"
        prev_prefix = tmpdir_path / "prev"

        base_pages = rasterise_pdf(baseline_pdf, base_prefix, dpi)
        prev_pages = rasterise_pdf(preview_pdf, prev_prefix, dpi)

        # Cache opened images to avoid re-opening for each frame.
        base_imgs: dict[int, Image.Image] = {}
        prev_imgs: dict[int, Image.Image] = {}
        for idx, p in enumerate(base_pages):
            base_imgs[idx] = Image.open(p)
        for idx, p in enumerate(prev_pages):
            prev_imgs[idx] = Image.open(p)

        results: list[dict] = []
        for f in frames:
            page = f["page"]
            if page not in base_imgs or page not in prev_imgs:
                continue

            bbox_px = bbox_mm_to_px(f["x_mm"], f["y_mm"], f["w_mm"], f["h_mm"], dpi)

            base_rgb = _do_sample(base_imgs[page], bbox_px)
            prev_rgb = _do_sample(prev_imgs[page], bbox_px)

            # Skip degenerate / out-of-bounds frames (0 pixels sampled).
            if base_rgb[3] == 0 or prev_rgb[3] == 0:
                continue

            dr = prev_rgb[0] - base_rgb[0]
            dg = prev_rgb[1] - base_rgb[1]
            db = prev_rgb[2] - base_rgb[2]
            mean_delta = (abs(dr) + abs(dg) + abs(db)) / 3.0
            rms_delta = (dr * dr + dg * dg + db * db) ** 0.5

            severity = classify_severity(mean_delta)

            results.append(
                {
                    "anname": f["anname"],
                    "page": page,
                    "type": f["type"],
                    "bbox_mm": [f["x_mm"], f["y_mm"], f["w_mm"], f["h_mm"]],
                    "baseline_rgb": [
                        round(base_rgb[0], 1),
                        round(base_rgb[1], 1),
                        round(base_rgb[2], 1),
                    ],
                    "preview_rgb": [
                        round(prev_rgb[0], 1),
                        round(prev_rgb[1], 1),
                        round(prev_rgb[2], 1),
                    ],
                    "mean_delta": round(mean_delta, 2),
                    "rms_delta": round(rms_delta, 2),
                    "severity": severity,
                }
            )

    # Sort: fill_likely first, then icc_likely, then ok; within each group
    # descending by mean_delta.
    _sev_order = {"fill_likely": 0, "icc_likely": 1, "ok": 2}
    results.sort(key=lambda r: (_sev_order.get(r["severity"], 3), -r["mean_delta"]))

    by_severity: dict[str, int] = {"ok": 0, "icc_likely": 0, "fill_likely": 0}
    for r in results:
        by_severity[r["severity"]] = by_severity.get(r["severity"], 0) + 1

    pattern = classify_pattern(by_severity)

    return {
        "template": template,
        "by_severity": by_severity,
        "pattern": pattern,
        "frames": results[:40],
    }


# ---------------------------------------------------------------------------
# YAML serialisation
# ---------------------------------------------------------------------------

def _yaml_dump(payload: dict) -> str:
    """Deterministic YAML: sort_keys=True, allow_unicode, no timestamps."""
    return yaml.dump(
        payload,
        sort_keys=True,
        allow_unicode=True,
        default_flow_style=False,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Per-region mean RGB color delta audit (ICC drift vs fill-color bug).",
    )
    ap.add_argument("--build-py", type=Path, required=True,
                    help="Path to templates/<slug>/build.py")
    ap.add_argument("--baseline", type=Path, required=True,
                    help="Path to templates/<slug>/baseline.pdf")
    ap.add_argument("--preview", type=Path, required=True,
                    help="Path to templates/<slug>/preview.pdf")
    ap.add_argument("--template", required=True,
                    help="Template slug (for output labelling)")
    ap.add_argument("--dpi", type=int, default=150,
                    help="Rasterise DPI (default: 150)")
    ap.add_argument("--out", type=Path, required=True,
                    help="Output path for region_color_audit.yml")
    args = ap.parse_args(argv)

    for p, label in [
        (args.build_py, "--build-py"),
        (args.baseline, "--baseline"),
        (args.preview, "--preview"),
    ]:
        if not p.exists():
            print(f"region_color_audit: missing {label}: {p}", file=sys.stderr)
            return 1

    result = run_region_color_audit(
        args.build_py,
        args.baseline,
        args.preview,
        args.template,
        args.dpi,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_yaml_dump(result), encoding="utf-8")

    bs = result["by_severity"]
    print(
        f"[{args.template}] region_color_audit: "
        f"{bs.get('ok', 0)} ok, "
        f"{bs.get('icc_likely', 0)} icc_likely, "
        f"{bs.get('fill_likely', 0)} fill_likely "
        f"— pattern: {result['pattern']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
