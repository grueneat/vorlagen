"""Unit tests for TemplateTolerance.region_grid (Issue #37 P2 task 7)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from visual_diff import (  # noqa: E402
    DEFAULT_GRID_COLS,
    DEFAULT_GRID_ROWS,
    TemplateTolerance,
)


def test_defaults_have_empty_region_grid():
    """A bare TemplateTolerance() has no region_grid configured."""
    t = TemplateTolerance()
    assert t.region_grid == {}


def test_load_no_region_grid_block(tmp_path):
    """A diff.yml with no region_grid block → region_grid stays empty."""
    diff_yml = tmp_path / "diff.yml"
    diff_yml.write_text(
        "visual_diff:\n  max_pixel_mismatch_pct: 5.0\n  fuzz_pct: 30.0\n",
        encoding="utf-8",
    )
    t = TemplateTolerance.load(diff_yml)
    assert t.region_grid == {}
    assert t.max_pixel_mismatch_pct == 5.0


def test_load_region_grid_custom_size(tmp_path):
    """Loading a custom cols/rows yields the configured grid shape."""
    diff_yml = tmp_path / "diff.yml"
    diff_yml.write_text(
        "visual_diff:\n"
        "  region_grid:\n"
        "    cols: 8\n"
        "    rows: 6\n",
        encoding="utf-8",
    )
    t = TemplateTolerance.load(diff_yml)
    assert t.region_grid["cols"] == 8
    assert t.region_grid["rows"] == 6
    # per_cell defaults to empty list
    assert t.region_grid["per_cell"] == []


def test_load_region_grid_defaults_filled_in(tmp_path):
    """An empty (but present) region_grid block defaults cols=6, rows=4."""
    diff_yml = tmp_path / "diff.yml"
    diff_yml.write_text(
        "visual_diff:\n  region_grid:\n    per_cell: []\n",
        encoding="utf-8",
    )
    t = TemplateTolerance.load(diff_yml)
    assert t.region_grid["cols"] == DEFAULT_GRID_COLS
    assert t.region_grid["rows"] == DEFAULT_GRID_ROWS


def test_for_cell_uses_per_cell_override(tmp_path):
    """When a per_cell override matches (page, col, row), use its thresholds."""
    diff_yml = tmp_path / "diff.yml"
    diff_yml.write_text(
        "visual_diff:\n"
        "  max_pixel_mismatch_pct: 1.0\n"
        "  fuzz_pct: 25.0\n"
        "  region_grid:\n"
        "    cols: 6\n"
        "    rows: 4\n"
        "    per_cell:\n"
        "      - page: 0\n"
        "        col: 3\n"
        "        row: 2\n"
        "        max_pixel_mismatch_pct: 10.0\n"
        "        fuzz_pct: 30.0\n",
        encoding="utf-8",
    )
    t = TemplateTolerance.load(diff_yml)
    max_pct, fuzz = t.for_cell(0, 3, 2)
    assert max_pct == 10.0
    assert fuzz == 30.0


def test_for_cell_falls_back_to_page_defaults(tmp_path):
    """When no per_cell matches, for_cell returns the page-level defaults."""
    diff_yml = tmp_path / "diff.yml"
    diff_yml.write_text(
        "visual_diff:\n"
        "  max_pixel_mismatch_pct: 1.5\n"
        "  fuzz_pct: 20.0\n"
        "  region_grid:\n"
        "    cols: 6\n"
        "    rows: 4\n",
        encoding="utf-8",
    )
    t = TemplateTolerance.load(diff_yml)
    # No per_cell, no grid defaults → falls all the way back to page defaults.
    max_pct, fuzz = t.for_cell(0, 0, 0)
    assert max_pct == 1.5
    assert fuzz == 20.0


def test_for_cell_uses_grid_defaults_when_no_per_cell(tmp_path):
    """When region_grid carries default_* but no per_cell, those defaults apply."""
    diff_yml = tmp_path / "diff.yml"
    diff_yml.write_text(
        "visual_diff:\n"
        "  max_pixel_mismatch_pct: 1.0\n"
        "  fuzz_pct: 25.0\n"
        "  region_grid:\n"
        "    cols: 6\n"
        "    rows: 4\n"
        "    default_max_pixel_mismatch_pct: 8.0\n"
        "    default_fuzz_pct: 35.0\n",
        encoding="utf-8",
    )
    t = TemplateTolerance.load(diff_yml)
    max_pct, fuzz = t.for_cell(0, 0, 0)
    assert max_pct == 8.0
    assert fuzz == 35.0


def test_for_cell_returns_page_defaults_when_no_grid():
    """No region_grid configured at all → for_cell still works, returns page defaults."""
    t = TemplateTolerance(max_pixel_mismatch_pct=3.0, fuzz_pct=12.0)
    max_pct, fuzz = t.for_cell(0, 1, 1)
    assert max_pct == 3.0
    assert fuzz == 12.0


def test_invalid_cols_zero_raises(tmp_path):
    """cols=0 fails the validation assertion at load time."""
    diff_yml = tmp_path / "diff.yml"
    diff_yml.write_text(
        "visual_diff:\n  region_grid:\n    cols: 0\n    rows: 4\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError):
        TemplateTolerance.load(diff_yml)


def test_invalid_rows_negative_raises(tmp_path):
    """rows=-1 fails the validation assertion."""
    diff_yml = tmp_path / "diff.yml"
    diff_yml.write_text(
        "visual_diff:\n  region_grid:\n    cols: 6\n    rows: -1\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError):
        TemplateTolerance.load(diff_yml)


def test_module_constants_correct():
    """DEFAULT_GRID_COLS/ROWS are 6/4 per plan."""
    assert DEFAULT_GRID_COLS == 6
    assert DEFAULT_GRID_ROWS == 4
