#!/usr/bin/env python3
"""Visual-diff bbox extractor with slot attribution (Issue #36).

Post-processor on ``tools/visual_diff.py``'s output directory: reads each
``diff-page-NN.png`` (the ImageMagick ``compare`` delta PNG, mode RGBA,
mismatch pixels = ``(199, 23, 35, 255)``), runs ImageMagick 8-connected-components
labelling, converts the resulting pixel bboxes to mm via the DPI recorded in
``visual_diff.json``, optionally attributes each bbox to a template-defined
named-frame slot (loaded via the same ``load_build_module`` + ``frame_bbox_mm``
path ``tools/audit_alignment.py`` uses), and writes a deterministic
``diff_bboxes.json`` next to the deltas.

Defaults (overridable via CLI flags):
  threshold=200            red-channel cutoff; pixels above are "diff"
  min_area_px=100          drop connected components below this area
  coverage_threshold=0.5   minimum coverage_of_diff_inside_slot for
                           attribution (area_intersect / area_diff_bbox)
  dilate disabled in v1    (kernel-based merge of near-pixel clusters
                           may land in a follow-up if AA-noise rectangles
                           split too aggressively)

Strict-mode behaviour:
  Raises ``DiffBBoxError`` for hard failures (missing ``visual_diff.json``,
  missing ``dpi`` field, missing referenced delta PNG, ImageMagick failure).
  Emits ``warnings.warn(...)`` for soft failures (template build failure with
  ``--template-slug``, template has no anname'd slots) and continues with
  ``attributed_slot: null``. This is a post-processor, not a CI gate.

Usage:
    # Standalone — no slot attribution:
    python3 tools/diff_bbox_extract.py <visual-diff-out-dir>

    # With slot attribution + overlays:
    python3 tools/diff_bbox_extract.py <visual-diff-out-dir> \\
        --template-slug postkarte-a6-kampagne \\
        --threshold 200 --min-area-px 100 --coverage-threshold 0.5 \\
        --overlay-out

    # Via visual_diff.py wrapper (issue #36 task 9):
    python3 tools/visual_diff.py <sla> --baseline <pdf> --tolerance <yml> \\
        --extract-bboxes --template-slug <slug> --out build/<id>/
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from typing import Optional


# Parse one line of ImageMagick's `-connected-components 8 -define
# connected-components:verbose=true` output:
#
#   Objects (id: bounding-box centroid area mean-color):
#     0: 1240x1754+0+0 619.5,876.7 2174960 srgba(255,255,255,1)
#     1: 12x18+340+512  345.5,520.5 216 srgba(199,23,35,1)
#
# Groups: (id, w, h, x, y, area, mean_color_str).
_CC_RE = re.compile(
    r"^\s*(\d+):\s+(\d+)x(\d+)\+(\d+)\+(\d+)\s+[\d.]+,[\d.]+\s+(\d+)\s+(.+)$"
)


class DiffBBoxError(RuntimeError):
    """Strict-mode failure (missing delta PNG, missing dpi in visual_diff.json,
    ImageMagick failure, etc.).

    Raised by ``tools/diff_bbox_extract.py`` for hard failures that should
    stop execution. Soft failures (missing template slots, build failure
    with ``--template-slug``) use ``warnings.warn(...)`` and continue.
    """


def extract_bboxes_px(
    delta_png: Path, threshold: int = 200, min_area_px: int = 100,
) -> list[dict]:
    """Run ImageMagick 8-connected-components on a single delta PNG.

    Returns a list of dicts (one per non-background component):
        {"x_px": int, "y_px": int, "w_px": int, "h_px": int,
         "area_px": int, "mean_color": str}

    Algorithm (locked decisions 1 + 2):
      - The delta PNG is RGBA red-on-white (mismatch pixels rendered by IM
        ``compare`` as ``(199,23,35,255)`` — high R, low G, low B). Matched
        pixels are NOT pure white: they're the baseline lightened by a red
        overlay at low alpha, producing tints like ``(210,227,215)``. The
        luminance discriminator is therefore unreliable (both tinted-matched
        AND saturated-red have luma < 230). We instead threshold the
        **HSL saturation** channel: saturation is very high for the
        red-overlay diff pixels and ~0 for both pure-white and grey-tinted
        matched pixels. ``-colorspace HSL -channel G -separate +channel
        -threshold 30%`` cleanly classifies diff vs matched.
      - Run ``-connected-components 8 -define connected-components:verbose=true``
        on the binary mask and parse the resulting object table from stdout.
      - Drop ``id == 0`` (background object — IM emits the topmost-leftmost
        object as id 0; with the HSL-saturation mask this is the full-page
        non-saturated background, ``gray(0)``, dropped unconditionally).
      - Drop components with ``area_px < min_area_px`` (page-edge AA noise).
      - Sort by (y_px, x_px, w_px, h_px) for deterministic ordering. This
        complements the cross-page sort in ``extract_all`` (decision 5a).

    ``threshold`` is part of the public API but currently informational — the
    IM pipeline uses a fixed 30% saturation threshold which discriminates
    red diff pixels from tinted-matched pixels reliably across observed
    ``compare`` outputs. Future tuning (e.g. switching to a per-channel
    red-cutoff) will honour this kwarg.

    Raises ``DiffBBoxError`` if ``delta_png`` does not exist or if the
    ``convert`` invocation fails (e.g. unreadable PNG).
    """
    if not delta_png.exists():
        raise DiffBBoxError(f"missing delta PNG: {delta_png}")
    _ = threshold  # reserved for future per-channel threshold path
    cmd = [
        "convert", str(delta_png),
        # Isolate the HSL saturation channel — high for red diff pixels,
        # ~0 for matched-but-tinted background. See function docstring.
        "-colorspace", "HSL", "-channel", "G", "-separate", "+channel",
        "-threshold", "30%",
        "-define", "connected-components:verbose=true",
        "-connected-components", "8",
        "info:-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        raise DiffBBoxError(
            f"ImageMagick convert failed on {delta_png} "
            f"(rc={exc.returncode}): {exc.stderr.strip()}"
        ) from exc
    except FileNotFoundError as exc:
        raise DiffBBoxError(
            "ImageMagick `convert` binary not found on PATH"
        ) from exc

    results: list[dict] = []
    for line in proc.stdout.splitlines():
        match = _CC_RE.match(line)
        if not match:
            continue
        obj_id = int(match.group(1))
        if obj_id == 0:
            # Background object — IM always emits the largest object first;
            # after -negate it is the dilated non-diff area. Drop unconditionally.
            continue
        w_px = int(match.group(2))
        h_px = int(match.group(3))
        x_px = int(match.group(4))
        y_px = int(match.group(5))
        area_px = int(match.group(6))
        mean_color = match.group(7).strip()
        if area_px < min_area_px:
            continue
        results.append({
            "x_px": x_px, "y_px": y_px, "w_px": w_px, "h_px": h_px,
            "area_px": area_px, "mean_color": mean_color,
        })
    results.sort(key=lambda b: (b["y_px"], b["x_px"], b["w_px"], b["h_px"]))
    return results


def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Visual-diff bbox extractor with slot attribution.",
    )
    ap.add_argument(
        "out_dir", type=Path,
        help="visual_diff.py output directory (contains visual_diff.json + diff-page-NN.png files).",
    )
    ap.add_argument(
        "--template-slug", type=str, default=None,
        help="Template slug for bbox slot attribution. If absent, attribution is skipped.",
    )
    ap.add_argument(
        "--threshold", type=int, default=200,
        help="Red-channel cutoff (0-255) for non-white pixels in the RGBA delta PNG. Default: 200.",
    )
    ap.add_argument(
        "--min-area-px", type=int, default=100,
        help="Drop connected components below this pixel area (AA-noise filter). Default: 100.",
    )
    ap.add_argument(
        "--coverage-threshold", type=float, default=0.5,
        help="Minimum coverage_of_diff_inside_slot to attribute a bbox to a slot. Default: 0.5.",
    )
    ap.add_argument(
        "--overlay-out", action="store_true",
        help="Also write diff-page-NN-overlay.png (red rectangle outlines over the DSL render).",
    )
    ap.add_argument(
        "--json-out", type=Path, default=None,
        help="JSON output path. Default: <out_dir>/diff_bboxes.json.",
    )
    return ap


def main(argv: Optional[list[str]] = None) -> int:
    ap = _build_argparser()
    args = ap.parse_args(argv)
    # Real logic lands in tasks 2-10. Bootstrap CLI prints the parsed args.
    print(
        f"diff_bbox_extract bootstrap: out_dir={args.out_dir} "
        f"template_slug={args.template_slug} threshold={args.threshold} "
        f"min_area_px={args.min_area_px} coverage_threshold={args.coverage_threshold} "
        f"overlay_out={args.overlay_out} json_out={args.json_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
