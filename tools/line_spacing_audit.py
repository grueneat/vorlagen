#!/usr/bin/env python3
"""Phase E2 line_spacing_audit: per-TextFrame baseline-to-baseline pt-gap.

Catches the LeadingModel-mismatch class: IDML CSR <Leading>14.3</Leading> but
rendered baseline.pdf shows 16.0pt baseline-to-baseline (LeadingModelAki,
TopOfCaps, or 120%-AutoLeading divergence). Without this audit, body-text
drift accumulates ~1.7pt per line, ~50pt over 30 lines.

Method (Issue #37 Phase E2):
- For each TextFrame in build.py with text content:
  - Extract first 3+ consecutive word lines via pdfplumber from baseline.pdf
    and preview.pdf, both restricted to the frame's mm bbox.
  - Compute median(pairwise y-deltas) for adjacent lines → baseline_linesp.
  - Same for preview_linesp.
  - If |preview - baseline| > threshold_pt (default 0.5), report the frame
    with anname, page, ParaStyle (when available), baseline/preview pt-gap,
    and a recommendation.

Usage:
    python3 tools/line_spacing_audit.py \\
      --preview  templates/<slug>/preview.pdf \\
      --baseline templates/<slug>/baseline.pdf \\
      --build-py templates/<slug>/build.py \\
      --template <slug> \\
      --threshold 0.5 \\
      --out build/validation/<slug>/line_spacing_audit.yml

Exit code: 0 when ok=true; 1 otherwise.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from statistics import median
from typing import Any

import pdfplumber
import yaml


_MM_TO_PT = 72.0 / 25.4


def _extract_line_tops_per_frame(
    pdf: Path,
    frame_bbox_mm: tuple[float, float, float, float],
    page_idx: int,
) -> list[float]:
    """Return clustered y-coords (PDF pt, top-down) of word lines inside
    the frame bbox on page ``page_idx``.

    Uses pdfplumber.extract_words(use_text_flow=False, x_tolerance=2,
    y_tolerance=2) and clusters word tops within 1pt of each other into
    a single line.

    Returns an empty list when the page doesn't exist or contains no words
    inside the bbox.
    """
    x_mm, y_mm, w_mm, h_mm = frame_bbox_mm
    x0_pt = x_mm * _MM_TO_PT
    y0_pt = y_mm * _MM_TO_PT
    x1_pt = (x_mm + w_mm) * _MM_TO_PT
    y1_pt = (y_mm + h_mm) * _MM_TO_PT
    with pdfplumber.open(pdf) as plumber:
        if page_idx >= len(plumber.pages):
            return []
        page = plumber.pages[page_idx]
        try:
            crop = page.crop(
                (x0_pt, y0_pt, x1_pt, y1_pt),
                relative=False,
                strict=False,
            )
        except ValueError:
            # Frame bbox falls partly outside the page; bail.
            return []
        words = crop.extract_words(
            use_text_flow=False,
            x_tolerance=2,
            y_tolerance=2,
        )
    if not words:
        return []
    tops = sorted(round(w["top"], 1) for w in words)
    # Cluster tops within 1pt of each other into the first one we saw.
    lines: list[float] = []
    for t in tops:
        if not lines or t - lines[-1] > 1.0:
            lines.append(t)
    return lines


def _median_baseline_gap(line_tops: list[float]) -> float | None:
    """Return the median of pairwise (line_tops[i+1] - line_tops[i]) gaps.

    Returns None when fewer than 2 line tops are present (can't measure a gap).
    """
    if len(line_tops) < 2:
        return None
    gaps = [line_tops[i + 1] - line_tops[i] for i in range(len(line_tops) - 1)]
    return round(median(gaps), 2)


def _has_text_content(frame: Any) -> bool:
    """True if the frame looks like a TextFrame with actual text content."""
    runs = getattr(frame, "runs", None) or []
    if runs:
        return True
    text = getattr(frame, "text", None)
    return bool(text)


def _frame_first_para_style(frame: Any) -> str:
    """Best-effort extraction of the first paragraph style name on the frame."""
    runs = getattr(frame, "runs", None) or []
    for r in runs:
        ps = getattr(r, "paragraph_style", None)
        if ps:
            return str(ps)
    return ""


def _frame_anname(frame: Any) -> str:
    return getattr(frame, "anname", "") or ""


def run_line_spacing_audit(
    preview_pdf: Path,
    baseline_pdf: Path,
    build_py: Path,
    template: str = "",
    threshold_pt: float = 0.5,
) -> dict[str, Any]:
    """For each TextFrame in build.py with text content, measure baseline-to-
    baseline pt-gap on baseline.pdf and preview.pdf, flag frames whose
    |delta_pt| > threshold_pt. Drift list sorted by descending |delta_pt|.

    Output schema::

        {
          template: str,
          threshold_pt: float,
          line_spacing_drift_count: int,
          line_spacing_drift: [
            {anname, page, para_style, baseline_linesp_pt, preview_linesp_pt,
             delta_pt, recommendation}, ...
          ],
          ok: bool,
        }
    """
    # Import here so the lazy load doesn't crash callers without a build.py.
    tools_dir = Path(__file__).resolve().parent
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from sla_lib.builder.bbox import frame_bbox_mm
    from sla_lib.builder.template_loader import load_build_module

    # template_loader expects a SLUG, not a path; derive the slug from the
    # build.py directory name and let load_build_module find it under the
    # standard templates/ root. If build_py is outside the standard tree
    # (a synthetic test), fall back to importlib by file path.
    slug = build_py.resolve().parent.name
    try:
        module = load_build_module(slug)
    except FileNotFoundError:
        import importlib.util
        mod_name = f"_lsa_build_{slug.replace('-', '_')}"
        sys.modules.pop(mod_name, None)
        spec = importlib.util.spec_from_file_location(mod_name, build_py)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)

    builder = (
        getattr(module, "build_preview", None)
        or getattr(module, "build_template", None)
        or getattr(module, "build_doc", None)
    )
    if builder is None:
        return {
            "template": template,
            "threshold_pt": threshold_pt,
            "line_spacing_drift_count": 0,
            "line_spacing_drift": [],
            "ok": True,
        }
    doc = builder()
    drift: list[dict[str, Any]] = []
    ok = True
    pages = getattr(doc, "pages", []) or []

    for page_idx, page in enumerate(pages):
        for frame in getattr(page, "items", []) or []:
            if not _has_text_content(frame):
                continue
            try:
                bb = frame_bbox_mm(frame, page)
            except Exception:
                continue
            if bb is None or len(bb) != 4:
                continue
            # frame_bbox_mm returns (min_x, min_y, max_x, max_y) per the
            # rotated_bbox helper it delegates to.
            x0_mm, y0_mm, x1_mm, y1_mm = bb
            w_mm = x1_mm - x0_mm
            h_mm = y1_mm - y0_mm
            if w_mm <= 0 or h_mm <= 0:
                continue
            bbox_for_pdf = (x0_mm, y0_mm, w_mm, h_mm)

            base_lines = _extract_line_tops_per_frame(
                baseline_pdf, bbox_for_pdf, page_idx,
            )
            prev_lines = _extract_line_tops_per_frame(
                preview_pdf, bbox_for_pdf, page_idx,
            )
            if len(base_lines) < 3 or len(prev_lines) < 3:
                continue  # Single-line headlines, captions — no gap to measure.
            base_linesp = _median_baseline_gap(base_lines)
            prev_linesp = _median_baseline_gap(prev_lines)
            if base_linesp is None or prev_linesp is None:
                continue
            delta = round(prev_linesp - base_linesp, 2)
            if abs(delta) > threshold_pt:
                drift.append({
                    "anname": _frame_anname(frame),
                    "page": page_idx,
                    "para_style": _frame_first_para_style(frame),
                    "baseline_linesp_pt": base_linesp,
                    "preview_linesp_pt": prev_linesp,
                    "delta_pt": delta,
                    "recommendation": (
                        f"override ParaStyle linesp to {base_linesp}"
                    ),
                })
                ok = False

    drift.sort(key=lambda d: -abs(d["delta_pt"]))

    return {
        "template": template,
        "threshold_pt": threshold_pt,
        "line_spacing_drift_count": len(drift),
        "line_spacing_drift": drift,
        "ok": ok,
    }


def _yaml_dump(payload: dict) -> str:
    return yaml.dump(
        payload,
        sort_keys=True,
        allow_unicode=True,
        default_flow_style=False,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="line_spacing_audit")
    ap.add_argument("--preview", type=Path, required=True)
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--build-py", type=Path, required=True)
    ap.add_argument("--template", default="")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    report = run_line_spacing_audit(
        args.preview, args.baseline, args.build_py,
        template=args.template, threshold_pt=args.threshold,
    )
    yaml_text = _yaml_dump(report)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(yaml_text, encoding="utf-8")
    print(yaml_text, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
