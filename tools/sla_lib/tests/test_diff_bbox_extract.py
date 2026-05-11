"""Tests for tools/diff_bbox_extract.py (Issue #36).

Conventions match ``test_audit_alignment.py``:
- ``unittest.TestCase`` (not pytest), per locked decision 6.
- ``tempfile.mkdtemp()`` + try/finally rmtree.
- ``sys.path.insert(0, ROOT / "tools")`` bootstrap.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import diff_bbox_extract  # noqa: E402
from diff_bbox_extract import (  # noqa: E402
    DiffBBoxError, extract_bboxes_px, load_dpi, px_to_mm_bbox,
)


def _draw_delta(path: Path, size: tuple[int, int],
                rects: list[tuple[int, int, int, int]]) -> None:
    """Synthesise a delta PNG: white RGBA background + red (199,23,35,255) rectangles.

    ``rects`` is a list of ``(x, y, w, h)`` tuples in pixels.
    """
    im = Image.new("RGBA", size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(im)
    for x, y, w, h in rects:
        # ImageDraw.rectangle is inclusive on both ends, so subtract 1 to
        # land an exactly w x h pixel block.
        draw.rectangle([x, y, x + w - 1, y + h - 1],
                       fill=(199, 23, 35, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="PNG")


class ExtractBBoxesPxTests(unittest.TestCase):
    """Synthetic-fixture tests for ``extract_bboxes_px``."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="diff_bbox_t_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_synthetic_red_rect_one_bbox(self) -> None:
        png = self.tmpdir / "delta.png"
        _draw_delta(png, (200, 200), [(50, 60, 30, 20)])
        out = extract_bboxes_px(png, threshold=200, min_area_px=10)
        self.assertEqual(len(out), 1, f"expected 1 bbox, got {out}")
        b = out[0]
        self.assertEqual(b["x_px"], 50)
        self.assertEqual(b["y_px"], 60)
        self.assertEqual(b["w_px"], 30)
        self.assertEqual(b["h_px"], 20)
        self.assertEqual(b["area_px"], 600)

    def test_two_separated_rects_two_bboxes(self) -> None:
        png = self.tmpdir / "delta.png"
        # Two rects far enough apart that 8-connectivity does not merge them.
        _draw_delta(png, (300, 300), [(20, 30, 25, 25), (200, 150, 40, 40)])
        out = extract_bboxes_px(png, threshold=200, min_area_px=10)
        self.assertEqual(len(out), 2)
        # Sorted by (y, x); first rect has lower y.
        self.assertEqual((out[0]["x_px"], out[0]["y_px"]), (20, 30))
        self.assertEqual((out[1]["x_px"], out[1]["y_px"]), (200, 150))

    def test_below_min_area_filtered(self) -> None:
        png = self.tmpdir / "delta.png"
        _draw_delta(png, (100, 100), [(10, 10, 3, 3)])  # area 9
        out = extract_bboxes_px(png, threshold=200, min_area_px=100)
        self.assertEqual(out, [])

    def test_missing_delta_raises_DiffBBoxError(self) -> None:
        with self.assertRaises(DiffBBoxError) as ctx:
            extract_bboxes_px(self.tmpdir / "nope.png")
        self.assertIn("missing delta PNG", str(ctx.exception))


class DpiAndUnitsTests(unittest.TestCase):
    """Tests for ``load_dpi`` + ``px_to_mm_bbox`` (Issue #36 task 3)."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="diff_bbox_dpi_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_dpi_reads_value(self) -> None:
        (self.tmpdir / "visual_diff.json").write_text(
            json.dumps({"dpi": 96, "pages": []}), encoding="utf-8",
        )
        self.assertEqual(load_dpi(self.tmpdir), 96)

    def test_load_dpi_missing_file_raises(self) -> None:
        with self.assertRaises(DiffBBoxError) as ctx:
            load_dpi(self.tmpdir)
        self.assertIn("missing visual_diff.json", str(ctx.exception))

    def test_load_dpi_missing_key_raises(self) -> None:
        (self.tmpdir / "visual_diff.json").write_text(
            json.dumps({"pages": []}), encoding="utf-8",
        )
        with self.assertRaises(DiffBBoxError) as ctx:
            load_dpi(self.tmpdir)
        self.assertIn("missing 'dpi'", str(ctx.exception))

    def test_px_to_mm_at_96dpi(self) -> None:
        # 25.4 mm/inch / 96 dpi => 0.2645833... mm/px
        # 96 px -> 25.4 mm; 192 -> 50.8; 48 -> 12.7; 24 -> 6.35 -> 6.3 (banker)
        b = px_to_mm_bbox(
            {"x_px": 96, "y_px": 192, "w_px": 48, "h_px": 24}, dpi=96,
        )
        self.assertEqual(b["x"], 25.4)
        self.assertEqual(b["y"], 50.8)
        self.assertEqual(b["w"], 12.7)
        # 6.35 rounds to 6.3 under Python's round-half-to-even; either is
        # within the documented 0.1 mm tolerance.
        self.assertAlmostEqual(b["h"], 6.35, delta=0.1)

    def test_px_to_mm_at_150dpi(self) -> None:
        # Same input at 150 dpi scales by 96/150 = 0.64 relative to the
        # 96-dpi case (i.e. (25.4/150) mm/px).
        b96 = px_to_mm_bbox(
            {"x_px": 96, "y_px": 192, "w_px": 48, "h_px": 24}, dpi=96,
        )
        b150 = px_to_mm_bbox(
            {"x_px": 96, "y_px": 192, "w_px": 48, "h_px": 24}, dpi=150,
        )
        scale = 96.0 / 150.0
        for k in ("x", "y", "w", "h"):
            self.assertAlmostEqual(b150[k], b96[k] * scale, delta=0.15)


if __name__ == "__main__":
    unittest.main()
