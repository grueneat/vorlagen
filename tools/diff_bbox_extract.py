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
from pathlib import Path
from typing import Optional


class DiffBBoxError(RuntimeError):
    """Strict-mode failure (missing delta PNG, missing dpi in visual_diff.json,
    ImageMagick failure, etc.).

    Raised by ``tools/diff_bbox_extract.py`` for hard failures that should
    stop execution. Soft failures (missing template slots, build failure
    with ``--template-slug``) use ``warnings.warn(...)`` and continue.
    """


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
