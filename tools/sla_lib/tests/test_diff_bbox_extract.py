"""Tests for tools/diff_bbox_extract.py (Issue #36).

Conventions match ``test_audit_alignment.py``:
- ``unittest.TestCase`` (not pytest), per locked decision 6.
- ``tempfile.mkdtemp()`` + try/finally rmtree.
- ``sys.path.insert(0, ROOT / "tools")`` bootstrap.
"""
from __future__ import annotations

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
from diff_bbox_extract import DiffBBoxError, extract_bboxes_px  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
