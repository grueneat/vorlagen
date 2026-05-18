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
  7. (optional, --extract-bboxes) Run tools/diff_bbox_extract.py to produce
     diff_bboxes.json and merge its per-page ``bboxes`` field back into
     visual_diff.json. Combine with --template-slug for slot attribution.

Usage:
    python3 tools/visual_diff.py templates/<id>/template.sla \\
        --baseline templates/<id>/baseline.pdf \\
        --tolerance templates/<id>/diff.yml \\
        --dpi 96 \\
        --out build/<id>/ \\
        [--extract-bboxes --template-slug <slug>]

Exit codes: 0 if every page (and every region) is within tolerance. 1 otherwise.
``--ci`` is a shortcut for ``--dpi 96`` (CONTEXT.md D4).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import yaml
from PIL import Image, ImageChops, ImageDraw, ImageFont


PT_PER_INCH = 72.0

# Default per-region grid shape (Issue #37 Backport 12 / P2 task 7).
# 6x4 cells per page is ~ "design-slot sized" on A4 (35×74 mm per cell).
DEFAULT_GRID_COLS = 6
DEFAULT_GRID_ROWS = 4


@dataclass
class TemplateTolerance:
    """Per-template visual-diff tolerance.

    Defaults assume CI runs without bundled fonts; Scribus's DejaVu Sans
    substitution produces sub-pixel anti-aliasing differences that cumulate
    to a few % of pixels per page even when the layout is byte-equivalent.
    ``fuzz_pct=25`` absorbs most of that noise; per-template configs raise
    ``max_pixel_mismatch_pct`` for body-text-heavy templates (e.g. Zeitung)
    where the sum of glyph-edge hinting drift naturally exceeds 1%.

    The ``region_grid`` block (Issue #37 P2 / Backport 12) adds a per-cell
    diff metric so semantically large but pixel-small drift (e.g. a centred
    headline shifted 5 mm) is no longer washed out by the page-wide average.
    Schema::

        region_grid:
          cols: int (default 6)
          rows: int (default 4)
          default_max_pixel_mismatch_pct: float (defaults to max_pixel_mismatch_pct)
          default_fuzz_pct: float (defaults to fuzz_pct)
          per_cell:
            - page: int
              col: int
              row: int
              max_pixel_mismatch_pct: float (optional)
              fuzz_pct: float (optional)
    """
    max_pixel_mismatch_pct: float = 1.0
    fuzz_pct: float = 25.0
    per_page: dict = field(default_factory=dict)   # int -> {max_pixel_mismatch_pct?, fuzz_pct?}
    per_region: list = field(default_factory=list) # list of {page, bbox_mm, max_pixel_mismatch_pct?, fuzz_pct?}
    region_grid: dict = field(default_factory=dict)

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
        region_grid = block.get("region_grid", {}) or {}
        if region_grid:
            region_grid.setdefault("cols", DEFAULT_GRID_COLS)
            region_grid.setdefault("rows", DEFAULT_GRID_ROWS)
            region_grid.setdefault("per_cell", [])
            cols = region_grid["cols"]
            rows = region_grid["rows"]
            assert isinstance(cols, int) and cols > 0, (
                f"region_grid.cols must be a positive int, got {cols!r}"
            )
            assert isinstance(rows, int) and rows > 0, (
                f"region_grid.rows must be a positive int, got {rows!r}"
            )
        return cls(
            max_pixel_mismatch_pct=float(block.get("max_pixel_mismatch_pct", 1.0)),
            fuzz_pct=float(block.get("fuzz_pct", 2.0)),
            per_page=per_page,
            per_region=per_region,
            region_grid=region_grid,
        )

    def for_page(self, page_index: int) -> tuple[float, float]:
        cfg = self.per_page.get(page_index, {})
        return (
            float(cfg.get("max_pixel_mismatch_pct", self.max_pixel_mismatch_pct)),
            float(cfg.get("fuzz_pct", self.fuzz_pct)),
        )

    def for_cell(self, page_index: int, col: int, row: int) -> tuple[float, float]:
        """Resolve (max_pixel_mismatch_pct, fuzz_pct) for one grid cell.

        Resolution order:
        1. per_cell override matching (page, col, row) keys
        2. region_grid.default_{max_pixel_mismatch_pct,fuzz_pct}
        3. per-page tolerance (via ``for_page``)

        Issue #37 P2 task 7.
        """
        page_max, page_fuzz = self.for_page(page_index)
        grid = self.region_grid or {}
        max_pct = float(grid.get("default_max_pixel_mismatch_pct", page_max))
        fuzz = float(grid.get("default_fuzz_pct", page_fuzz))
        for cell in grid.get("per_cell", []) or []:
            if (
                cell.get("page") == page_index
                and cell.get("col") == col
                and cell.get("row") == row
            ):
                max_pct = float(cell.get("max_pixel_mismatch_pct", max_pct))
                fuzz = float(cell.get("fuzz_pct", fuzz))
                break
        return max_pct, fuzz


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
    """Render an SLA to PDF via the sanctioned headless pipeline.

    Mirrors tools/gallery_build.py invocation: absolute paths, explicit
    screen geometry, UTF-8 locale env. Scribus on Ubuntu CI exits 0
    without writing the PDF if the output path is relative (it changes
    cwd internally on openDoc), so we resolve to absolute paths and
    assert the output exists afterwards.
    """
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    sla_abs = sla_path.resolve()
    pdf_abs = pdf_path.resolve()
    repo = Path(__file__).resolve().parent.parent
    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
    }
    _run(
        [
            "xvfb-run", "-a", "--server-args=-screen 0 1024x768x24",
            "scribus", "-g", "-ns", "-py",
            str(repo / "tools" / "_export_pdf.py"),
            str(sla_abs), str(pdf_abs),
        ],
        env=env,
    )
    if not pdf_abs.exists():
        raise RuntimeError(
            f"render_sla_to_pdf: scribus exited 0 but produced no PDF at {pdf_abs}"
        )


def rasterise(pdf_path: Path, prefix: Path, dpi: int) -> list[Path]:
    """Run pdftoppm to produce <prefix>-<NN>.png; return sorted list of PNGs.

    Stale <prefix>-<NN>.png files from a prior render are removed first:
    ``pdftoppm`` only overwrites the page numbers the *current* PDF has, so
    if the page count DECREASED since the last run (e.g. a converter change
    that merges facing-pages spreads 6->4 pages) the leftover higher-numbered
    PNGs would inflate the returned list and trigger a spurious
    "page count mismatch" RuntimeError.
    """
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for stale in prefix.parent.glob(prefix.name + "-*.png"):
        stale.unlink()
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


def compare_grid(
    baseline_png: Path,
    preview_png: Path,
    cols: int,
    rows: int,
    fuzz_pct: float = 25.0,
) -> list[dict]:
    """Per-cell pixel diff over a ``cols × rows`` grid laid on both rasters.

    Both images MUST be the same pixel dimensions (caller's responsibility to
    ensure DPI-matched pdftoppm rasterisation). Returns a list of dicts in
    (row, col) reading order::

        {col, row, mismatch_pixels, total_pixels, mismatch_pct,
         bbox_px: {x, y, w, h}}

    Mismatch semantics approximate ImageMagick ``compare -metric AE -fuzz N%``:
    per pixel, the maximum per-channel absolute delta is compared to
    ``threshold = round(255 * fuzz_pct / 100)`` and counted as mismatched if
    strictly greater. Cell totals do NOT exactly equal the page-wide
    ImageMagick AE value (Euclidean vs max-channel semantics; ~1-2 % drift),
    which is expected — see ``ecosystem.md`` §10.5.

    Implementation uses Pillow (``ImageChops.difference`` + ``lighter``) so
    there are no fork-cost overheads from 24+ subprocess calls per page.

    Issue #37 P2 task 8 (Backport 12).
    """
    base = Image.open(baseline_png).convert("RGB")
    prev = Image.open(preview_png).convert("RGB")
    if base.size != prev.size:
        # A 1-2px difference is sub-pixel rasterisation rounding (the trim
        # crop and the page-size conversion each round independently), not a
        # real geometry mismatch — crop both to the common extent so the
        # region diff still runs. A larger gap is a genuine page-size bug.
        dw = abs(base.size[0] - prev.size[0])
        dh = abs(base.size[1] - prev.size[1])
        if dw > 2 or dh > 2:
            raise ValueError(
                f"image size mismatch: baseline={base.size}, "
                f"preview={prev.size}"
            )
        cw = min(base.size[0], prev.size[0])
        ch = min(base.size[1], prev.size[1])
        base = base.crop((0, 0, cw, ch))
        prev = prev.crop((0, 0, cw, ch))
    w_px, h_px = base.size

    # Integer cell sizes; the LAST column/row absorbs the modulus so we
    # always cover the full image without overlap or gap.
    col_widths = [w_px // cols] * cols
    col_widths[-1] += w_px % cols
    row_heights = [h_px // rows] * rows
    row_heights[-1] += h_px % rows

    threshold = round(255 * fuzz_pct / 100.0)

    results: list[dict] = []
    y = 0
    for row in range(rows):
        x = 0
        for col in range(cols):
            cell_w = col_widths[col]
            cell_h = row_heights[row]
            b_crop = base.crop((x, y, x + cell_w, y + cell_h))
            p_crop = prev.crop((x, y, x + cell_w, y + cell_h))
            diff = ImageChops.difference(b_crop, p_crop)
            r, g, b = diff.split()
            max_chan = ImageChops.lighter(ImageChops.lighter(r, g), b)
            hist = max_chan.histogram()  # 256 bins
            mismatch_px = sum(hist[threshold + 1:])
            total_px = cell_w * cell_h
            results.append({
                "col": col,
                "row": row,
                "mismatch_pixels": int(mismatch_px),
                "total_pixels": int(total_px),
                "mismatch_pct": (
                    round(mismatch_px / total_px * 100, 4) if total_px else 0.0
                ),
                "bbox_px": {"x": x, "y": y, "w": cell_w, "h": cell_h},
            })
            x += cell_w
        y += row_heights[row]
    return results


def _heatmap_color(mismatch_pct: float, threshold_pct: float) -> tuple[int, int, int, int]:
    """Linear ramp green → amber → red, RGBA tuple. Alpha fixed at 180/255.

    - ``pct <= 0``           → green  (76, 175, 80)
    - ``pct == threshold``   → amber  (255, 193, 7)
    - ``pct >= 2*threshold`` → red    (244, 67, 54)

    Linear interpolation between segments. Threshold = 0 (defensive) makes
    every positive pct red.

    Issue #37 P2 task 9 (Backport 12).
    """
    green = (76, 175, 80)
    amber = (255, 193, 7)
    red = (244, 67, 54)
    if mismatch_pct <= 0:
        rgb = green
    elif threshold_pct <= 0:
        rgb = red
    elif mismatch_pct >= 2 * threshold_pct:
        rgb = red
    elif mismatch_pct <= threshold_pct:
        t = mismatch_pct / threshold_pct
        rgb = tuple(int(green[i] + (amber[i] - green[i]) * t) for i in range(3))
    else:
        t = (mismatch_pct - threshold_pct) / threshold_pct
        rgb = tuple(int(amber[i] + (red[i] - amber[i]) * t) for i in range(3))
    return (rgb[0], rgb[1], rgb[2], 180)


def render_grid_heatmap(
    baseline_png: Path,
    cells: list[dict],
    threshold_pct: float,
    out_png: Path,
) -> None:
    """Render an RGBA heatmap overlaying ``cells`` on a grayscale baseline.

    Each cell is filled with a green→amber→red ramped color (per
    ``_heatmap_color``) and labelled with its ``mismatch_pct``. Output is
    saved as a PNG with the same pixel dimensions as ``baseline_png``.

    Issue #37 P2 task 9 (Backport 12).
    """
    base = Image.open(baseline_png).convert("L").convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=14,
        )
    except Exception:
        font = ImageFont.load_default()
    for cell in cells:
        bx = cell["bbox_px"]["x"]
        by = cell["bbox_px"]["y"]
        bw = cell["bbox_px"]["w"]
        bh = cell["bbox_px"]["h"]
        color = _heatmap_color(cell["mismatch_pct"], threshold_pct)
        draw.rectangle(
            [bx, by, bx + bw - 1, by + bh - 1],
            fill=color,
            outline=(0, 0, 0, 255),
            width=1,
        )
        label = f"{cell['mismatch_pct']:.1f}%"
        draw.text((bx + 4, by + 4), label, fill=(0, 0, 0, 255), font=font)
    composite = Image.alpha_composite(base, overlay)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    composite.save(out_png, format="PNG")


def run_region_grid_audit(
    baseline_png_dir: Path,
    preview_png_dir: Path,
    tolerance: TemplateTolerance,
    out_dir: Path,
    template: str = "",
) -> dict:
    """Run per-cell visual diff on every page; emit heatmap PNGs + report dict.

    Looks for ``baseline-page-{N}.png`` / ``dsl-page-{N}.png`` pairs (1-indexed)
    in the given directories. Stops when a page's PNG pair isn't found.

    ``tolerance.region_grid`` controls the grid shape; per-cell overrides are
    resolved via ``tolerance.for_cell``. Heatmaps are saved into ``out_dir``
    as ``visual_diff_heatmap-page-{N:02d}.png``.

    Returns a dict::

        {
          template: str,
          grid: {cols: int, rows: int},
          pages: [
            {page: int, regions: [...], hot_regions: [...], heatmap_png: str},
            ...
          ],
          ok: bool,
        }

    Issue #37 P2 task 10 (Backport 12).
    """
    if not tolerance.region_grid:
        tolerance.region_grid = {
            "cols": DEFAULT_GRID_COLS,
            "rows": DEFAULT_GRID_ROWS,
            "per_cell": [],
        }
    cols = tolerance.region_grid["cols"]
    rows = tolerance.region_grid["rows"]

    out_dir.mkdir(parents=True, exist_ok=True)
    pages: list[dict] = []
    page_idx = 0
    while True:
        base_p = baseline_png_dir / f"baseline-page-{page_idx + 1}.png"
        prev_p = preview_png_dir / f"dsl-page-{page_idx + 1}.png"
        if not base_p.exists() or not prev_p.exists():
            break
        page_max, page_fuzz = tolerance.for_page(page_idx)
        cells = compare_grid(base_p, prev_p, cols, rows, fuzz_pct=page_fuzz)
        # Apply per-cell tolerances (and recompute mismatch if per_cell fuzz
        # differs from the page default — semantics MUST match the override).
        for cell in cells:
            cell_max, cell_fuzz = tolerance.for_cell(
                page_idx, cell["col"], cell["row"]
            )
            cell["threshold_pct"] = cell_max
            cell["fuzz_pct"] = cell_fuzz
            if abs(cell_fuzz - page_fuzz) > 1e-6:
                # Recompute this cell with the per-cell fuzz.
                recomputed = compare_grid(
                    base_p, prev_p, cols, rows, fuzz_pct=cell_fuzz,
                )
                for rc in recomputed:
                    if rc["col"] == cell["col"] and rc["row"] == cell["row"]:
                        cell["mismatch_pixels"] = rc["mismatch_pixels"]
                        cell["total_pixels"] = rc["total_pixels"]
                        cell["mismatch_pct"] = rc["mismatch_pct"]
                        break
            cell["pass"] = cell["mismatch_pct"] <= cell_max

        hot_sorted = sorted(
            (c for c in cells if not c["pass"]),
            key=lambda c: -c["mismatch_pct"],
        )[:10]
        hot_regions = [
            {
                "col": c["col"],
                "row": c["row"],
                "mismatch_pct": c["mismatch_pct"],
            }
            for c in hot_sorted
        ]

        heatmap_name = f"visual_diff_heatmap-page-{page_idx + 1:02d}.png"
        heatmap_path = out_dir / heatmap_name
        render_grid_heatmap(base_p, cells, page_max, heatmap_path)

        pages.append({
            "page": page_idx,
            "regions": cells,
            "hot_regions": hot_regions,
            "heatmap_png": heatmap_name,
        })
        page_idx += 1

    page_ok = all(c["pass"] for page in pages for c in page["regions"])
    return {
        "template": template,
        "grid": {"cols": cols, "rows": rows},
        "pages": pages,
        "ok": page_ok if pages else True,
    }


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


def _merge_bboxes_into_visual_diff(
    out_dir: Path, template_slug: Optional[str],
) -> None:
    """Shell out to ``tools/diff_bbox_extract.py`` and merge its per-page
    bboxes into the just-written ``visual_diff.json``.

    Backward-compatible (Issue #36): every existing key in visual_diff.json
    is preserved verbatim; only a per-page ``bboxes`` field is added. The
    extractor's standalone ``diff_bboxes.json`` is also written and left
    in place for downstream consumers.

    We deliberately do NOT import ``diff_bbox_extract`` at module scope —
    keeps ``visual_diff.py`` importable in environments where the extractor
    is not on path, and matches the visual_diff convention of shelling out
    to siblings (cf. ``_run`` for IM).
    """
    extractor = Path(__file__).resolve().parent / "diff_bbox_extract.py"
    cmd = [sys.executable, str(extractor), str(out_dir)]
    if template_slug:
        cmd += ["--template-slug", template_slug]
    _run(cmd)
    bb_path = out_dir / "diff_bboxes.json"
    vd_path = out_dir / "visual_diff.json"
    bb = json.loads(bb_path.read_text(encoding="utf-8"))
    vd = json.loads(vd_path.read_text(encoding="utf-8"))
    # Index extractor's pages by their page index for safe merging — the
    # extractor sorts by (y, x, w, h) per page but the page list order
    # already matches visual_diff.json's order.
    bb_by_idx = {
        int(p["page"]): p.get("bboxes", [])
        for p in bb.get("pages", [])
    }
    for page in vd.get("pages", []):
        page["bboxes"] = bb_by_idx.get(int(page["page"]), [])
    vd_path.write_text(
        json.dumps(vd, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


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
    ap.add_argument("--extract-bboxes", action="store_true",
                    help="After comparing, run tools/diff_bbox_extract.py "
                         "and merge per-page bboxes into visual_diff.json")
    ap.add_argument("--template-slug", type=str, default=None,
                    help="Template slug for bbox slot attribution "
                         "(only used with --extract-bboxes)")
    args = ap.parse_args(argv)
    dpi = 96 if args.ci else args.dpi
    tolerance = TemplateTolerance.load(args.tolerance)
    overall_pass, _ = visual_diff(args.template_sla, args.baseline,
                                    tolerance, dpi, args.out)
    if args.extract_bboxes:
        _merge_bboxes_into_visual_diff(args.out, args.template_slug)
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
