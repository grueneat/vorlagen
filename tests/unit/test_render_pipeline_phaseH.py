"""Unit tests for Phase H (visual_diff_regions) wiring (Issue #37 P2 task 10)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from visual_diff import (  # noqa: E402
    TemplateTolerance,
    run_region_grid_audit,
)


def _make_pages(tmp_path: Path, n_pages: int, *, drift_at: tuple[int, int, int] | None = None) -> None:
    """Create ``n_pages`` of identical 60×40 baseline/dsl PNG pairs at tmp_path.

    ``drift_at = (page_idx_1based, x_px, y_px)`` (optional): paste a 5×5
    black patch into dsl-page-N.png at that pixel location.
    """
    for p in range(1, n_pages + 1):
        base = Image.new("RGB", (60, 40), "white")
        prev = base.copy()
        if drift_at and drift_at[0] == p:
            patch = Image.new("RGB", (5, 5), "black")
            prev.paste(patch, (drift_at[1], drift_at[2]))
        base.save(tmp_path / f"baseline-page-{p}.png")
        prev.save(tmp_path / f"dsl-page-{p}.png")


def test_identical_pages_all_pass(tmp_path):
    _make_pages(tmp_path, 2)
    tol = TemplateTolerance(
        max_pixel_mismatch_pct=1.0, fuzz_pct=25.0,
        region_grid={"cols": 6, "rows": 4, "per_cell": []},
    )
    result = run_region_grid_audit(
        baseline_png_dir=tmp_path,
        preview_png_dir=tmp_path,
        tolerance=tol,
        out_dir=tmp_path,
        template="t",
    )
    assert result["template"] == "t"
    assert result["grid"] == {"cols": 6, "rows": 4}
    assert len(result["pages"]) == 2
    assert result["ok"] is True
    for page in result["pages"]:
        assert page["hot_regions"] == []


def test_localised_drift_produces_hot_region(tmp_path):
    """Drift in page 0 at col=1, row=0 → that cell appears in hot_regions."""
    _make_pages(tmp_path, 1, drift_at=(1, 12, 2))  # cell (1, 0) in 60×40/6×4
    tol = TemplateTolerance(
        max_pixel_mismatch_pct=1.0, fuzz_pct=25.0,
        region_grid={"cols": 6, "rows": 4, "per_cell": []},
    )
    result = run_region_grid_audit(
        baseline_png_dir=tmp_path,
        preview_png_dir=tmp_path,
        tolerance=tol,
        out_dir=tmp_path,
        template="t",
    )
    assert result["ok"] is False
    hot = result["pages"][0]["hot_regions"]
    assert any(h["col"] == 1 and h["row"] == 0 for h in hot)


def test_heatmap_pngs_written_per_page(tmp_path):
    _make_pages(tmp_path, 2)
    tol = TemplateTolerance(
        region_grid={"cols": 6, "rows": 4, "per_cell": []},
    )
    run_region_grid_audit(
        baseline_png_dir=tmp_path,
        preview_png_dir=tmp_path,
        tolerance=tol,
        out_dir=tmp_path,
        template="t",
    )
    assert (tmp_path / "visual_diff_heatmap-page-01.png").exists()
    assert (tmp_path / "visual_diff_heatmap-page-02.png").exists()


def test_per_cell_override_relaxes_threshold(tmp_path):
    """Drift cell (1, 0); per_cell override raises threshold so the cell passes."""
    _make_pages(tmp_path, 1, drift_at=(1, 12, 2))
    tol = TemplateTolerance(
        max_pixel_mismatch_pct=1.0, fuzz_pct=25.0,
        region_grid={
            "cols": 6, "rows": 4,
            "per_cell": [
                {"page": 0, "col": 1, "row": 0,
                 "max_pixel_mismatch_pct": 99.0},
            ],
        },
    )
    result = run_region_grid_audit(
        baseline_png_dir=tmp_path,
        preview_png_dir=tmp_path,
        tolerance=tol,
        out_dir=tmp_path,
        template="t",
    )
    assert result["ok"] is True  # 99 % threshold absorbs the small patch
    assert result["pages"][0]["hot_regions"] == []


def test_determinism(tmp_path):
    """Running the audit twice on the same inputs yields identical YAML."""
    _make_pages(tmp_path, 1, drift_at=(1, 12, 2))
    tol = TemplateTolerance(
        region_grid={"cols": 6, "rows": 4, "per_cell": []},
    )
    r1 = run_region_grid_audit(
        baseline_png_dir=tmp_path, preview_png_dir=tmp_path,
        tolerance=tol, out_dir=tmp_path, template="t",
    )
    r2 = run_region_grid_audit(
        baseline_png_dir=tmp_path, preview_png_dir=tmp_path,
        tolerance=tol, out_dir=tmp_path, template="t",
    )
    y1 = yaml.dump(r1, sort_keys=True, default_flow_style=False, allow_unicode=True)
    y2 = yaml.dump(r2, sort_keys=True, default_flow_style=False, allow_unicode=True)
    assert y1 == y2


def test_preflight_records_visual_diff_regions(tmp_path):
    """The preflight builder picks up visual_diff_regions.yml and records it."""
    from render_pipeline import _build_preflight

    vd_path = tmp_path / "visual_diff_regions.yml"
    vd_path.write_text(
        yaml.dump({
            "template": "t",
            "ok": False,
            "pages": [{"page": 0, "hot_regions": [{"col": 1, "row": 0, "mismatch_pct": 12.0}]}],
            "grid": {"cols": 6, "rows": 4},
        }, sort_keys=True, default_flow_style=False),
        encoding="utf-8",
    )
    pre = _build_preflight(
        tmp_path, "t",
        inventory_path=tmp_path / "inventory.yml",
        text_audit_path=tmp_path / "text_audit.yml",
        image_audit_path=tmp_path / "image_audit.yml",
        font_audit_path=tmp_path / "font_audit.yml",
        text_render_audit_path=tmp_path / "text_render_audit.yml",
        text_position_audit_path=tmp_path / "text_position_audit.yml",
        run_style_audit_path=tmp_path / "run_style_audit.yml",
        color_audit_path=tmp_path / "region_color_audit.yml",
        visual_diff_regions_path=vd_path,
    )
    assert "visual_diff_regions" in pre["audits"]
    assert pre["audits"]["visual_diff_regions"]["ok"] is False
    assert pre["audits"]["visual_diff_regions"]["issues"] == 1
    assert pre["ok"] is False
