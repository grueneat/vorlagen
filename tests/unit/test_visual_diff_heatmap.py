"""Unit tests for render_grid_heatmap + _heatmap_color (Issue #37 P2 task 9)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from visual_diff import _heatmap_color, render_grid_heatmap  # noqa: E402


# ---------------------------------------------------------------------------
# _heatmap_color ramp
# ---------------------------------------------------------------------------

def test_heatmap_color_pct_zero_is_green():
    r, g, b, a = _heatmap_color(0.0, 5.0)
    assert (r, g, b) == (76, 175, 80)
    assert a == 180


def test_heatmap_color_at_threshold_is_amber():
    r, g, b, a = _heatmap_color(5.0, 5.0)
    assert (r, g, b) == (255, 193, 7)


def test_heatmap_color_at_double_threshold_is_red():
    r, g, b, _ = _heatmap_color(10.0, 5.0)
    assert (r, g, b) == (244, 67, 54)


def test_heatmap_color_midway_between_green_and_amber():
    r, g, b, _ = _heatmap_color(2.5, 5.0)
    # Midpoint between (76, 175, 80) and (255, 193, 7):
    # green channel: 175 + (193 - 175)/2 = 184; r: 76 + 179/2 = 165;
    # b: 80 + (7-80)/2 = 43; allow rounding tolerance.
    assert abs(r - 165) <= 1
    assert abs(g - 184) <= 1
    assert abs(b - 43) <= 1


def test_heatmap_color_ramp_segment_monotonic():
    """Within each linear segment (green→amber then amber→red), the channels
    move monotonically. The full ramp is two-segment so the OVERALL red
    channel is non-monotonic (it peaks at amber=255 then dips to 244 at red).
    Assert per-segment behaviour instead:

    - Green→amber (0..threshold): red ↑, green ↑, blue ↓
    - Amber→red  (threshold..2*threshold): red ↓ slightly, green ↓, blue ↑ slightly
    """
    threshold = 5.0
    segment1 = [_heatmap_color(p, threshold) for p in (0, 1, 2, 3, 4, 5)]
    for i in range(len(segment1) - 1):
        assert segment1[i + 1][0] >= segment1[i][0], (i, segment1)  # red ↑
        assert segment1[i + 1][1] >= segment1[i][1], (i, segment1)  # green ↑
        assert segment1[i + 1][2] <= segment1[i][2], (i, segment1)  # blue ↓
    segment2 = [_heatmap_color(p, threshold) for p in (5, 6, 7, 8, 9, 10)]
    for i in range(len(segment2) - 1):
        # red goes from 255 down to 244 — monotonic non-increasing
        assert segment2[i + 1][0] <= segment2[i][0], (i, segment2)
        # green strictly decreases 193 → 67
        assert segment2[i + 1][1] <= segment2[i][1], (i, segment2)
        # blue increases 7 → 54
        assert segment2[i + 1][2] >= segment2[i][2], (i, segment2)


def test_heatmap_color_threshold_zero_defensive():
    """threshold_pct=0 → any positive pct returns red."""
    assert _heatmap_color(0.01, 0.0)[:3] == (244, 67, 54)


# ---------------------------------------------------------------------------
# render_grid_heatmap
# ---------------------------------------------------------------------------

def _baseline_png(tmp_path: Path, size=(60, 40)) -> Path:
    img = Image.new("RGB", size, "white")
    p = tmp_path / "baseline.png"
    img.save(p)
    return p


def _grid_6x4(size=(60, 40)) -> list[dict]:
    w_px, h_px = size
    cols, rows = 6, 4
    col_widths = [w_px // cols] * cols
    col_widths[-1] += w_px % cols
    row_heights = [h_px // rows] * rows
    row_heights[-1] += h_px % rows
    out: list[dict] = []
    y = 0
    for row in range(rows):
        x = 0
        for col in range(cols):
            out.append({
                "col": col, "row": row,
                "mismatch_pixels": 0,
                "total_pixels": col_widths[col] * row_heights[row],
                "mismatch_pct": 0.0,
                "bbox_px": {"x": x, "y": y,
                            "w": col_widths[col], "h": row_heights[row]},
            })
            x += col_widths[col]
        y += row_heights[row]
    return out


def test_render_writes_valid_png(tmp_path):
    base = _baseline_png(tmp_path)
    cells = _grid_6x4()
    out = tmp_path / "heatmap.png"
    render_grid_heatmap(base, cells, threshold_pct=5.0, out_png=out)
    assert out.exists()
    img = Image.open(out)
    assert img.size == (60, 40)


def test_render_preserves_baseline_dimensions(tmp_path):
    base = _baseline_png(tmp_path, size=(123, 87))
    cells = _grid_6x4(size=(123, 87))
    out = tmp_path / "h.png"
    render_grid_heatmap(base, cells, threshold_pct=2.0, out_png=out)
    assert Image.open(out).size == (123, 87)


def test_render_cell_color_reflects_pct(tmp_path):
    """Place a high-pct cell at (col=2, row=1) and sample a pixel inside it
    after rendering — expect a reddish RGB (244, 67, 54) ± alpha blend."""
    base = _baseline_png(tmp_path)
    cells = _grid_6x4()
    # Set one cell to a hot value
    target = next(c for c in cells if c["col"] == 2 and c["row"] == 1)
    target["mismatch_pct"] = 20.0  # >> threshold=5 → red
    target["mismatch_pixels"] = target["total_pixels"]
    out = tmp_path / "h.png"
    render_grid_heatmap(base, cells, threshold_pct=5.0, out_png=out)
    rendered = Image.open(out).convert("RGBA")
    # Sample a pixel deep inside the target cell, away from the label/border.
    bx = target["bbox_px"]
    sample_x = bx["x"] + bx["w"] - 2
    sample_y = bx["y"] + bx["h"] - 2
    r, g, b, _ = rendered.getpixel((sample_x, sample_y))
    # The overlay alpha=180/255 ≈ 0.706 blends with grayscale-white background
    # (255, 255, 255). Expected: r ≈ 0.706*244 + 0.294*255 ≈ 247,
    # g ≈ 0.706*67 + 0.294*255 ≈ 122, b ≈ 0.706*54 + 0.294*255 ≈ 113.
    # Allow ±20 per channel for label edges and outline.
    assert 220 <= r <= 255, (r, g, b)
    assert 90 <= g <= 160, (r, g, b)
    assert 80 <= b <= 150, (r, g, b)
