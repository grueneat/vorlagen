"""Integration regression test for per-region visual_diff (Issue #37 P2 task 12).

Acceptance per ISSUE.md line 1227-1229:
    "shift a single 9pt headline by 50pt produces a region with >10%
    mismatch even when page-wide stays <1%."

Built directly on PIL synthetic images (no PDF round-trip): the regions
audit consumes PNGs, not PDFs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from visual_diff import (  # noqa: E402
    TemplateTolerance,
    compare_grid,
    run_region_grid_audit,
)


def _make_page(headline_xy=(200, 300), headline_text="Headline", font_size=30,
               w_px=600, h_px=850):
    """A4-shaped white page with one bold headline. Use a reduced 600×850
    raster instead of the full 300DPI 2480×3508 so the test runs in <1s.
    """
    img = Image.new("RGB", (w_px, h_px), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            size=font_size,
        )
    except Exception:
        font = ImageFont.load_default()
    d.text(headline_xy, headline_text, fill="black", font=font)
    return img


def test_shifted_headline_localises_to_one_cell(tmp_path):
    """50-px headline shift produces a hot cell >10 % while page-wide stays small."""
    base_png = tmp_path / "baseline-page-1.png"
    prev_png = tmp_path / "dsl-page-1.png"
    _make_page(headline_xy=(200, 300)).save(base_png)
    _make_page(headline_xy=(200, 350)).save(prev_png)  # +50 px vertical shift

    cells = compare_grid(base_png, prev_png, cols=6, rows=4, fuzz_pct=25)
    total_px = sum(c["total_pixels"] for c in cells)
    total_mismatch = sum(c["mismatch_pixels"] for c in cells)
    page_wide_pct = total_mismatch / total_px * 100

    hottest = max(cells, key=lambda c: c["mismatch_pct"])
    assert hottest["mismatch_pct"] > 10, (
        f"hottest cell mismatch_pct={hottest['mismatch_pct']:.2f}% (expected > 10%)"
    )
    # Hot cell should dominate the page-wide average.
    assert hottest["mismatch_pct"] > 5 * page_wide_pct, (
        f"hot cell {hottest['mismatch_pct']:.2f}% should dominate page-wide "
        f"{page_wide_pct:.2f}%"
    )


def test_identical_pages_all_clean(tmp_path):
    """Identical PNGs → every cell 0 % mismatch."""
    base_png = tmp_path / "baseline-page-1.png"
    prev_png = tmp_path / "dsl-page-1.png"
    img = _make_page()
    img.save(base_png)
    img.save(prev_png)
    cells = compare_grid(base_png, prev_png, cols=6, rows=4, fuzz_pct=25)
    for c in cells:
        assert c["mismatch_pixels"] == 0
        assert c["mismatch_pct"] == 0.0


def test_run_region_grid_audit_emits_heatmap(tmp_path):
    """Smoke: run_region_grid_audit writes a heatmap PNG + a regions YAML-able dict."""
    base_dir = tmp_path / "pngs"
    base_dir.mkdir()
    _make_page(headline_xy=(200, 300)).save(base_dir / "baseline-page-1.png")
    _make_page(headline_xy=(200, 350)).save(base_dir / "dsl-page-1.png")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    tolerance = TemplateTolerance(
        max_pixel_mismatch_pct=1.0, fuzz_pct=25.0,
        region_grid={"cols": 6, "rows": 4, "per_cell": []},
    )
    result = run_region_grid_audit(
        baseline_png_dir=base_dir,
        preview_png_dir=base_dir,
        tolerance=tolerance,
        out_dir=out_dir,
        template="test",
    )
    assert result["template"] == "test"
    assert result["grid"] == {"cols": 6, "rows": 4}
    assert len(result["pages"]) == 1
    assert (out_dir / "visual_diff_heatmap-page-01.png").exists()
    # At least one cell should be a hot region given the 50-px headline shift
    assert any(p["hot_regions"] for p in result["pages"])
