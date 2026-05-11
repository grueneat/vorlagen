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
import json
import re
import subprocess
import sys
import warnings
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


def load_dpi(out_dir: Path) -> int:
    """Return the ``dpi`` integer from ``out_dir/visual_diff.json``.

    Raises ``DiffBBoxError`` if ``visual_diff.json`` is missing or has no
    top-level ``dpi`` field. The DPI is required for px -> mm conversion;
    we deliberately do NOT fall back to a default since the resulting mm
    bboxes would silently disagree with the slot bboxes from the template
    build.
    """
    vd_path = out_dir / "visual_diff.json"
    if not vd_path.exists():
        raise DiffBBoxError(
            f"missing visual_diff.json in {out_dir} — run tools/visual_diff.py first"
        )
    payload = json.loads(vd_path.read_text(encoding="utf-8"))
    if "dpi" not in payload:
        raise DiffBBoxError(
            f"visual_diff.json missing 'dpi' field at {vd_path}"
        )
    return int(payload["dpi"])


def load_template_slots(template_slug: str) -> dict[int, dict[str, dict]]:
    """For each page index, return ``{anname: {x, y, w, h} mm}``.

    Mirrors ``tools/audit_alignment.py``'s build-and-iterate idiom verbatim
    (the canonical slot enumerator for this repo). Returns an empty dict
    if the template build fails for any reason: this is the soft-warn path
    (post-processor, not a CI gate) — diff bboxes are still emitted with
    ``attributed_slot: null``.

    Page-index convention: keys are 0-indexed page integers, matching
    ``visual_diff.json``'s ``page`` field. NOTE: the file naming
    (``diff-page-01.png``) is 1-indexed via ``f"{idx+1:02d}"`` at
    ``tools/visual_diff.py:231``. File names = 1-based; JSON / slot keys
    = 0-based. Don't conflate.

    Limitation (inherited from ``frame_bbox_mm``): templates that use
    verbatim-pt overrides (``xpos_pt`` / ``width_pt`` etc.) will get
    slightly off bbox coordinates; attribution will still work in most
    cases via the top-3 candidates list (decision 4).
    """
    # Lazy imports — keep this module importable even if the build path
    # is broken in some weird CI environment.
    try:
        from sla_lib.builder.template_loader import load_build_module
        from sla_lib.builder.bbox import frame_bbox_mm
    except Exception as exc:  # pragma: no cover - import failure is exotic
        warnings.warn(
            f"diff_bbox_extract: cannot import slot-loader helpers ({exc!r}); "
            "attribution disabled",
            stacklevel=2,
        )
        return {}

    repo_root = Path(__file__).resolve().parent.parent
    try:
        mod = load_build_module(template_slug, repo_root)
        doc = mod.build_preview() if hasattr(mod, "build_preview") else mod.build_doc()
    except Exception as exc:
        warnings.warn(
            f"diff_bbox_extract: template '{template_slug}' build failed "
            f"({exc!r}); attribution skipped",
            stacklevel=2,
        )
        return {}

    slots: dict[int, dict[str, dict]] = {}
    for idx, page in enumerate(doc.pages):
        if getattr(page, "is_master", False):
            continue
        page_slots: dict[str, dict] = {}
        for item in page.items:
            anname = getattr(item, "anname", None) or ""
            if not anname:
                continue
            b4 = frame_bbox_mm(item, page)  # (min_x, min_y, max_x, max_y) mm or None
            if b4 is None:
                continue
            min_x, min_y, max_x, max_y = b4
            page_slots[anname] = {
                "x": round(min_x, 1),
                "y": round(min_y, 1),
                "w": round(max_x - min_x, 1),
                "h": round(max_y - min_y, 1),
            }
        if page_slots:
            slots[idx] = page_slots
    return slots


def px_to_mm_bbox(bbox_px: dict, dpi: int) -> dict:
    """Convert a ``{x_px, y_px, w_px, h_px}`` pixel bbox to ``{x, y, w, h}`` mm.

    Each component is rounded to 0.1 mm. The round step is what makes the
    pipeline FP-stable across runs (determinism decision 5b) — without it
    the trailing-binary FP drift can flip the last decimal between two
    otherwise-identical executions.
    """
    mm_per_px = 25.4 / dpi
    return {
        "x": round(bbox_px["x_px"] * mm_per_px, 1),
        "y": round(bbox_px["y_px"] * mm_per_px, 1),
        "w": round(bbox_px["w_px"] * mm_per_px, 1),
        "h": round(bbox_px["h_px"] * mm_per_px, 1),
    }


def coverage_of_diff_inside_slot(diff_bbox: dict, slot_bbox: dict) -> float:
    """Fraction of the diff bbox that lies inside the slot bbox, in [0, 1].

    Decision 4: this metric (``area_intersect / area_diff_bbox``) is
    preferred over pure IoU. A 5 mm^2 portrait shift inside a 50x70 mm
    slot has IoU ~= 0.001 but coverage 1.0 — and "1.0" is the correct
    attribution. Returns 0.0 if the diff bbox has zero area (degenerate).
    """
    ix = max(
        0.0,
        min(diff_bbox["x"] + diff_bbox["w"], slot_bbox["x"] + slot_bbox["w"])
        - max(diff_bbox["x"], slot_bbox["x"]),
    )
    iy = max(
        0.0,
        min(diff_bbox["y"] + diff_bbox["h"], slot_bbox["y"] + slot_bbox["h"])
        - max(diff_bbox["y"], slot_bbox["y"]),
    )
    intersect = ix * iy
    diff_area = diff_bbox["w"] * diff_bbox["h"]
    return (intersect / diff_area) if diff_area > 0 else 0.0


def attribute_diff_bbox(
    diff_bbox: dict, page_slots: dict[str, dict],
    coverage_threshold: float = 0.5,
) -> tuple[Optional[str], float, list[dict]]:
    """Return ``(attributed_slot_or_None, overlap_pct, top3_candidates)``.

    ``candidates`` shape (decision 4, top-3, sorted descending by coverage,
    tie-break ascending by slot area_mm^2 so the more-specific smaller
    slot wins when two coverages tie):
        [{"slot": str, "coverage_pct": float, "slot_area_mm2": float}, ...]

    Attribution returns the first candidate iff its raw coverage is
    >= ``coverage_threshold`` (default 0.5). ``overlap_pct`` is the
    attribution's coverage as a percentage (0..100). When no candidate
    passes the threshold or ``page_slots`` is empty, returns
    ``(None, 0.0, candidates_top3)`` so the JSON consumer still sees the
    alternatives.
    """
    ranked: list[tuple[str, float, float]] = []
    for name, sbox in page_slots.items():
        cov = coverage_of_diff_inside_slot(diff_bbox, sbox)
        area = sbox["w"] * sbox["h"]
        ranked.append((name, cov, area))
    # Sort: higher coverage first, then smaller slot first (more specific
    # attribution wins ties — decision 4 tie-break).
    ranked.sort(key=lambda r: (-r[1], r[2]))

    top3 = ranked[:3]
    candidates = [
        {
            "slot": name,
            "coverage_pct": round(cov * 100.0, 1),
            "slot_area_mm2": round(area, 1),
        }
        for name, cov, area in top3
    ]

    if top3 and top3[0][1] >= coverage_threshold:
        chosen_name = top3[0][0]
        chosen_overlap = round(top3[0][1] * 100.0, 1)
        return chosen_name, chosen_overlap, candidates
    return None, 0.0, candidates


def extract_all(
    out_dir: Path,
    *,
    template_slug: Optional[str] = None,
    threshold: int = 200,
    min_area_px: int = 100,
    coverage_threshold: float = 0.5,
    overlay_out: bool = False,
) -> dict:
    """Top-level pipeline: iterate ``visual_diff.json``'s pages, run the
    connected-components extractor on each delta PNG, attribute against
    template slots, return the full ``diff_bboxes.json`` payload as a dict.

    Page enumeration uses the ``delta_png`` field recorded in
    ``visual_diff.json`` rather than re-deriving from the page index —
    this matters because ``baseline-page-N.png`` is variable-padded but
    ``diff-page-NN.png`` is always 2-digit, and we want to be robust to
    future renaming.

    When ``overlay_out=True``, also writes a ``diff-page-NN-overlay.png``
    next to each delta (red rectangle outlines on the DSL rendering).
    Implemented in task 7; this kwarg is forwarded there.

    Determinism (decision 5): the returned dict's per-page ``bboxes`` list
    is sorted by ``(y, x, w, h)`` mm; ``write_json`` serialises with
    ``sort_keys=True`` so the top-level dict ordering doesn't matter.
    """
    dpi = load_dpi(out_dir)
    vd_path = out_dir / "visual_diff.json"
    vd_payload = json.loads(vd_path.read_text(encoding="utf-8"))

    slots = load_template_slots(template_slug) if template_slug else {}

    pages_out: list[dict] = []
    for page_entry in vd_payload.get("pages", []):
        page_idx = int(page_entry["page"])
        delta_rel = page_entry["delta_png"]
        delta_path = out_dir / delta_rel
        bboxes_px = extract_bboxes_px(delta_path, threshold, min_area_px)
        page_slots = slots.get(page_idx, {})

        bbox_records: list[dict] = []
        for bpx in bboxes_px:
            bmm = px_to_mm_bbox(bpx, dpi)
            w_px = bpx["w_px"]
            h_px = bpx["h_px"]
            rect_px = w_px * h_px
            mismatch_pct_in_bbox = (
                round((bpx["area_px"] / rect_px) * 100.0, 1) if rect_px > 0 else 0.0
            )
            attr_slot, overlap_pct, candidates = attribute_diff_bbox(
                bmm, page_slots, coverage_threshold,
            )
            bbox_records.append({
                "bbox_px": {
                    "x": bpx["x_px"], "y": bpx["y_px"],
                    "w": w_px, "h": h_px,
                },
                "bbox_mm": bmm,
                "area_px": bpx["area_px"],
                "mismatch_pct_in_bbox": mismatch_pct_in_bbox,
                "attributed_slot": attr_slot,
                "attribution_overlap_pct": overlap_pct,
                "attribution_candidates": candidates,
            })

        # Sort per-page bboxes by (y_mm, x_mm, w_mm, h_mm) — decision 5a.
        bbox_records.sort(key=lambda r: (
            r["bbox_mm"]["y"], r["bbox_mm"]["x"],
            r["bbox_mm"]["w"], r["bbox_mm"]["h"],
        ))

        page_record: dict = {
            "page": page_idx,
            "delta_png": delta_rel,
            "bboxes": bbox_records,
        }
        # Stash the px-bboxes alongside so the overlay writer (task 7) can
        # paint them without re-running the IM CC pass. Strip before
        # serialising; see write_json's filter.
        page_record["_bboxes_px_internal"] = bboxes_px
        pages_out.append(page_record)

    if overlay_out:
        _write_overlays(out_dir, pages_out)

    payload: dict = {
        "dpi": dpi,
        "template_slug": template_slug,
        "pages": pages_out,
    }
    return payload


def _strip_internal(payload: dict) -> dict:
    """Return a copy of ``payload`` without the ``_bboxes_px_internal``
    helper keys that ``extract_all`` stashes for the overlay writer."""
    return {
        "dpi": payload["dpi"],
        "template_slug": payload.get("template_slug"),
        "pages": [
            {
                "page": p["page"],
                "delta_png": p["delta_png"],
                "bboxes": p["bboxes"],
            }
            for p in payload.get("pages", [])
        ],
    }


def write_json(payload: dict, json_path: Path) -> None:
    """Serialise ``payload`` to ``json_path`` deterministically.

    Uses ``sort_keys=True`` (decision 5c) + ``indent=2`` + UTF-8 so two
    runs against the same input produce byte-identical files. Strips the
    internal ``_bboxes_px_internal`` helper keys ``extract_all`` stashes
    for the overlay writer.
    """
    clean = _strip_internal(payload)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(clean, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_overlay_png(
    src_png: Path, bboxes_px: list[dict], dst_png: Path,
) -> None:
    """Draw red rectangle outlines (no fill, 2-px stroke) for each px bbox
    on a copy of ``src_png``; save to ``dst_png``. Mode is preserved as
    RGBA for downstream tooling.

    Pillow is imported lazily so the module stays importable in
    environments that only need the bbox JSON (no overlays).
    """
    from PIL import Image, ImageDraw  # lazy import
    img = Image.open(src_png).convert("RGBA")
    draw = ImageDraw.Draw(img)
    for b in bboxes_px:
        x, y = b["x_px"], b["y_px"]
        w, h = b["w_px"], b["h_px"]
        draw.rectangle(
            [x, y, x + w, y + h],
            outline=(255, 0, 0, 255), width=2,
        )
    dst_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst_png, format="PNG")


def _write_overlays(out_dir: Path, pages_out: list[dict]) -> None:
    """For each page in ``pages_out``, locate the corresponding
    ``dsl-page-N.png`` (variable-padded — pdftoppm picks 1-digit for <=9
    pages, 2-digit otherwise) and write a sibling
    ``diff-page-NN-overlay.png`` with the page's px bboxes outlined in red.

    Silent no-op if a page's dsl PNG is missing — overlay is a convenience
    output, not a contract.
    """
    for page in pages_out:
        idx = int(page["page"])
        bboxes_px = page.get("_bboxes_px_internal", [])
        if not bboxes_px:
            continue  # nothing to outline
        # Try the unpadded form first (matches pdftoppm output for <=9 pages),
        # then 2-digit zero-padded. visual_diff.py's diff-page-NN files are
        # always 2-digit, but dsl-page-N follows pdftoppm's variable padding.
        candidates = [
            out_dir / f"dsl-page-{idx + 1}.png",
            out_dir / f"dsl-page-{idx + 1:02d}.png",
        ]
        src = next((c for c in candidates if c.exists()), None)
        if src is None:
            continue
        dst = out_dir / f"diff-page-{idx + 1:02d}-overlay.png"
        write_overlay_png(src, bboxes_px, dst)


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
    out_dir: Path = args.out_dir
    json_out: Path = args.json_out or (out_dir / "diff_bboxes.json")
    try:
        payload = extract_all(
            out_dir,
            template_slug=args.template_slug,
            threshold=args.threshold,
            min_area_px=args.min_area_px,
            coverage_threshold=args.coverage_threshold,
            overlay_out=args.overlay_out,
        )
    except DiffBBoxError as exc:
        # Strict-mode raise — print a clean error and return non-zero so
        # the caller (e.g. visual_diff.py --extract-bboxes) sees failure.
        # Stack-trace would obscure the actionable path in the message.
        print(f"diff_bbox_extract: {exc}", file=sys.stderr)
        return 1
    write_json(payload, json_out)
    n_pages = len(payload.get("pages", []))
    n_bboxes = sum(len(p["bboxes"]) for p in payload.get("pages", []))
    print(f"wrote {json_out} ({n_bboxes} bboxes across {n_pages} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
