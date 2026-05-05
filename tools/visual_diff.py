#!/usr/bin/env python3
"""Visual diff for DSL-built SLAs against frozen baseline PDFs.

Pipeline:
  1. Render the DSL SLA to PDF via Scribus 1.6.5 (xvfb-run + tools/_export_pdf.py)
  2. Rasterise both baseline.pdf and the DSL PDF at the requested DPI via pdftoppm
  3. ImageMagick `compare -metric AE -fuzz <fuzz_pct>%` per page; mismatched pixel
     count divided by total pixels = mismatch_pct
  4. ImageMagick `montage` builds a baseline | dsl | delta composite per page
  5. Apply per-page / per-region tolerance overrides from the template's diff.yml
  6. Emit visual_diff.json (machine summary) and visual_diff.html (review index)

Usage:
    python3 tools/visual_diff.py templates/<id>/template.sla \\
        --baseline templates/<id>/baseline.pdf \\
        --tolerance templates/<id>/diff.yml \\
        --dpi 96 \\
        --out build/<id>/

Exit codes: 0 if every page (and every region) is within tolerance. 1 otherwise.
``--ci`` is a shortcut for ``--dpi 96`` (CONTEXT.md D4).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import yaml


PT_PER_INCH = 72.0


@dataclass
class TemplateTolerance:
    """Per-template visual-diff tolerance.

    Defaults assume CI runs without bundled fonts; Scribus's DejaVu Sans
    substitution produces sub-pixel anti-aliasing differences that cumulate
    to a few % of pixels per page even when the layout is byte-equivalent.
    ``fuzz_pct=25`` absorbs most of that noise; per-template configs raise
    ``max_pixel_mismatch_pct`` for body-text-heavy templates (e.g. Zeitung)
    where the sum of glyph-edge hinting drift naturally exceeds 1%.
    """
    max_pixel_mismatch_pct: float = 1.0
    fuzz_pct: float = 25.0
    per_page: dict = field(default_factory=dict)   # int -> {max_pixel_mismatch_pct?, fuzz_pct?}
    per_region: list = field(default_factory=list) # list of {page, bbox_mm, max_pixel_mismatch_pct?, fuzz_pct?}

    @classmethod
    def load(cls, path: Optional[Path]) -> "TemplateTolerance":
        if path is None or not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        block = data.get("visual_diff", data)
        per_page_raw = block.get("per_page", []) or []
        per_page: dict[int, dict] = {}
        for entry in per_page_raw:
            page = int(entry.get("page"))
            per_page[page] = {k: v for k, v in entry.items() if k != "page"}
        per_region = block.get("per_region", []) or []
        return cls(
            max_pixel_mismatch_pct=float(block.get("max_pixel_mismatch_pct", 1.0)),
            fuzz_pct=float(block.get("fuzz_pct", 2.0)),
            per_page=per_page,
            per_region=per_region,
        )

    def for_page(self, page_index: int) -> tuple[float, float]:
        cfg = self.per_page.get(page_index, {})
        return (
            float(cfg.get("max_pixel_mismatch_pct", self.max_pixel_mismatch_pct)),
            float(cfg.get("fuzz_pct", self.fuzz_pct)),
        )


@dataclass
class PageResult:
    page_index: int
    mismatch_pixels: int
    total_pixels: int
    mismatch_pct: float
    threshold_pct: float
    fuzz_pct: float
    composite: str
    delta_png: str
    pass_: bool
    region_results: list[dict] = field(default_factory=list)


def _run(cmd: list[str], *, allow_nonzero: bool = False, env: Optional[dict] = None,
          cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True, env=env,
                             cwd=str(cwd) if cwd else None)
    if not allow_nonzero and result.returncode != 0:
        raise RuntimeError(
            f"command failed (rc={result.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def render_sla_to_pdf(sla_path: Path, pdf_path: Path) -> None:
    """Render an SLA to PDF via the sanctioned headless pipeline."""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parent.parent
    _run(
        [
            "xvfb-run", "-a", "scribus", "-g", "-ns", "-py",
            str(repo / "tools" / "_export_pdf.py"),
            str(sla_path), str(pdf_path),
        ],
    )


def rasterise(pdf_path: Path, prefix: Path, dpi: int) -> list[Path]:
    """Run pdftoppm to produce <prefix>-<NN>.png; return sorted list of PNGs."""
    prefix.parent.mkdir(parents=True, exist_ok=True)
    _run(["pdftoppm", "-r", str(dpi), "-png", str(pdf_path), str(prefix)])
    return sorted(prefix.parent.glob(prefix.name + "-*.png"))


_AE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*\(", re.MULTILINE)
_AE_BARE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*$", re.MULTILINE)


def compare_pages(baseline: Path, dsl: Path, diff_path: Path,
                   fuzz_pct: float) -> tuple[int, int]:
    """Run ImageMagick compare. Returns (mismatch_pixels, total_pixels).

    We use ``-metric AE`` (Absolute Error pixel count) and emit the diff PNG
    showing pixels that differ. Identify the total pixel count via ImageMagick
    ``identify``.
    """
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    res = _run([
        "compare", "-metric", "AE", "-fuzz", f"{fuzz_pct}%",
        str(baseline), str(dsl), str(diff_path),
    ], allow_nonzero=True)
    # `compare` writes the AE count to stderr (and exits 1 when any pixels differ;
    # 2 on actual error).
    if res.returncode == 2:
        raise RuntimeError(
            f"compare error (rc=2): {res.stderr}"
        )
    out = res.stderr.strip()
    try:
        mismatch_pixels = int(float(out.splitlines()[0].strip().split()[0]))
    except (ValueError, IndexError):
        raise RuntimeError(f"unparseable compare output: {out!r}")
    # Total pixel count via identify -format
    res = _run(["identify", "-format", "%w %h", str(baseline)])
    w, h = (int(v) for v in res.stdout.strip().split())
    total = w * h
    return mismatch_pixels, total


def montage_composite(baseline: Path, dsl: Path, diff: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    _run([
        "montage",
        str(baseline), str(dsl), str(diff),
        "-tile", "3x1", "-geometry", "+4+4",
        str(out),
    ])


def crop_for_region(image: Path, dpi: int, page_w_pt: float, page_h_pt: float,
                     bbox_mm: dict) -> Path:
    """Use ImageMagick `convert -crop` to extract a sub-rectangle from a raster.
    Returns path to the cropped PNG (sibling of the source)."""
    x_mm = float(bbox_mm.get("x", 0))
    y_mm = float(bbox_mm.get("y", 0))
    w_mm = float(bbox_mm.get("w", 0))
    h_mm = float(bbox_mm.get("h", 0))
    px_per_mm = (dpi / 25.4)
    x_px = int(round(x_mm * px_per_mm))
    y_px = int(round(y_mm * px_per_mm))
    w_px = max(1, int(round(w_mm * px_per_mm)))
    h_px = max(1, int(round(h_mm * px_per_mm)))
    out = image.with_suffix(f".region_{x_px}_{y_px}_{w_px}x{h_px}.png")
    _run(["convert", str(image), "-crop", f"{w_px}x{h_px}+{x_px}+{y_px}", "+repage", str(out)])
    return out


def visual_diff(template_sla: Path, baseline_pdf: Path, tolerance: TemplateTolerance,
                 dpi: int, out_dir: Path) -> tuple[bool, list[PageResult]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dsl_pdf = out_dir / "dsl.pdf"
    render_sla_to_pdf(template_sla, dsl_pdf)
    baseline_pages = rasterise(baseline_pdf, out_dir / "baseline-page", dpi)
    dsl_pages = rasterise(dsl_pdf, out_dir / "dsl-page", dpi)
    if len(baseline_pages) != len(dsl_pages):
        raise RuntimeError(
            f"page count mismatch: baseline={len(baseline_pages)} dsl={len(dsl_pages)}"
        )
    results: list[PageResult] = []
    overall_pass = True
    for idx, (b_png, d_png) in enumerate(zip(baseline_pages, dsl_pages)):
        page_threshold, page_fuzz = tolerance.for_page(idx)
        diff_png = out_dir / f"diff-page-{idx + 1:02d}.png"
        composite = out_dir / f"composite-page-{idx + 1:02d}.png"
        mismatch, total = compare_pages(b_png, d_png, diff_png, page_fuzz)
        montage_composite(b_png, d_png, diff_png, composite)
        mismatch_pct = (mismatch / total) * 100.0 if total else 0.0
        page_pass = mismatch_pct <= page_threshold
        region_results: list[dict] = []
        # Per-region overrides
        for region in tolerance.per_region:
            if int(region.get("page", -1)) != idx:
                continue
            region_threshold = float(region.get("max_pixel_mismatch_pct",
                                                  tolerance.max_pixel_mismatch_pct))
            region_fuzz = float(region.get("fuzz_pct", page_fuzz))
            bbox_mm = region.get("bbox_mm") or {}
            b_crop = crop_for_region(b_png, dpi, 0, 0, bbox_mm)
            d_crop = crop_for_region(d_png, dpi, 0, 0, bbox_mm)
            r_diff = out_dir / f"region-page-{idx+1:02d}-{int(bbox_mm.get('x',0))}-{int(bbox_mm.get('y',0))}.png"
            r_mismatch, r_total = compare_pages(b_crop, d_crop, r_diff, region_fuzz)
            r_pct = (r_mismatch / r_total) * 100.0 if r_total else 0.0
            r_pass = r_pct <= region_threshold
            region_results.append({
                "bbox_mm": bbox_mm,
                "mismatch_pixels": r_mismatch,
                "total_pixels": r_total,
                "mismatch_pct": r_pct,
                "threshold_pct": region_threshold,
                "fuzz_pct": region_fuzz,
                "pass": r_pass,
            })
            if not r_pass:
                page_pass = False
        if not page_pass:
            overall_pass = False
        results.append(PageResult(
            page_index=idx,
            mismatch_pixels=mismatch,
            total_pixels=total,
            mismatch_pct=mismatch_pct,
            threshold_pct=page_threshold,
            fuzz_pct=page_fuzz,
            composite=str(composite.relative_to(out_dir)),
            delta_png=str(diff_png.relative_to(out_dir)),
            pass_=page_pass,
            region_results=region_results,
        ))
    write_reports(out_dir, template_sla, baseline_pdf, dpi, tolerance, results, overall_pass)
    return overall_pass, results


def write_reports(out_dir: Path, template_sla: Path, baseline_pdf: Path,
                   dpi: int, tolerance: TemplateTolerance,
                   results: list[PageResult], overall_pass: bool) -> None:
    summary = {
        "template_sla": str(template_sla),
        "baseline_pdf": str(baseline_pdf),
        "dpi": dpi,
        "default_threshold_pct": tolerance.max_pixel_mismatch_pct,
        "default_fuzz_pct": tolerance.fuzz_pct,
        "pass": overall_pass,
        "pages": [
            {
                "page": r.page_index,
                "mismatch_pixels": r.mismatch_pixels,
                "total_pixels": r.total_pixels,
                "mismatch_pct": round(r.mismatch_pct, 4),
                "threshold_pct": r.threshold_pct,
                "fuzz_pct": r.fuzz_pct,
                "composite": r.composite,
                "delta_png": r.delta_png,
                "pass": r.pass_,
                "regions": r.region_results,
            }
            for r in results
        ],
    }
    (out_dir / "visual_diff.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    # HTML index
    rows = []
    for r in results:
        status = "PASS" if r.pass_ else "FAIL"
        color = "#2c7" if r.pass_ else "#c33"
        rows.append(
            f'<tr><td>{r.page_index + 1}</td>'
            f'<td>{r.mismatch_pixels} / {r.total_pixels}</td>'
            f'<td>{r.mismatch_pct:.4f}%</td>'
            f'<td>{r.threshold_pct:.2f}%</td>'
            f'<td style="color:{color};font-weight:bold">{status}</td>'
            f'<td><a href="{r.composite}">composite</a></td>'
            f'<td><a href="{r.delta_png}">delta</a></td></tr>'
        )
    html = (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>visual_diff: {template_sla.name}</title>"
        "<style>"
        "body{font-family:sans-serif;margin:2em} "
        "table{border-collapse:collapse} "
        "td,th{border:1px solid #ddd;padding:.4em .8em;text-align:left}"
        "</style></head><body>"
        f"<h1>visual_diff — {template_sla.name}</h1>"
        f"<p><strong>baseline:</strong> {baseline_pdf.name}<br>"
        f"<strong>dpi:</strong> {dpi}<br>"
        f"<strong>overall:</strong> "
        f"<span style='color:{'#2c7' if overall_pass else '#c33'};font-weight:bold'>"
        f"{'PASS' if overall_pass else 'FAIL'}</span></p>"
        "<table><thead><tr><th>Page</th><th>Mismatch</th><th>%</th>"
        "<th>Threshold</th><th>Status</th><th>Composite</th><th>Delta</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></body></html>"
    )
    (out_dir / "visual_diff.html").write_text(html, encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Visual diff for DSL-built SLAs.")
    ap.add_argument("template_sla", type=Path, help="DSL-built template.sla")
    ap.add_argument("--baseline", type=Path, required=True,
                    help="Frozen baseline.pdf to compare against")
    ap.add_argument("--tolerance", type=Path, default=None,
                    help="Per-template diff.yml")
    ap.add_argument("--dpi", type=int, default=150,
                    help="Raster DPI (default: 150 for local; use 96 for CI)")
    ap.add_argument("--ci", action="store_true",
                    help="Shortcut for --dpi=96")
    ap.add_argument("--out", type=Path, default=Path("build/visual_diff/"),
                    help="Output directory for reports + composites")
    args = ap.parse_args(argv)
    dpi = 96 if args.ci else args.dpi
    tolerance = TemplateTolerance.load(args.tolerance)
    overall_pass, _ = visual_diff(args.template_sla, args.baseline,
                                    tolerance, dpi, args.out)
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
