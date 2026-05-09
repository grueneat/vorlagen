"""Tests for SpreadImage block (Issue #14)."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document  # noqa: E402
from sla_lib.builder.blocks import SpreadImage  # noqa: E402
from sla_lib.builder.primitives import ImageFrame  # noqa: E402
from sla_lib.builder.brand_constraints import _frame_bbox_mm  # noqa: E402


class SpreadImageEmitTests(unittest.TestCase):
    def test_emit_returns_two_image_frames(self):
        si = SpreadImage(image="img/cover.jpg",
                         page_w_mm=210, page_h_mm=297, h_mm=297,
                         base_anname="P9 Spread")
        left, right = si.emit()
        self.assertIsInstance(left, ImageFrame)
        self.assertIsInstance(right, ImageFrame)

    def test_anname_pattern(self):
        si = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297,
                         h_mm=297, base_anname="Cover")
        left, right = si.emit()
        self.assertEqual(left.anname, "Cover · left")
        self.assertEqual(right.anname, "Cover · right")

    def test_anname_empty_when_no_base(self):
        si = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=297)
        left, right = si.emit()
        self.assertEqual(left.anname, "")
        self.assertEqual(right.anname, "")

    def test_right_half_local_offset_is_negative_x(self):
        si = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=297)
        left, right = si.emit()
        self.assertEqual(left.local_offset_mm, (0.0, 0.0))
        self.assertEqual(right.local_offset_mm, (-210.0, 0.0))

    def test_scale_type_pinned_to_zero(self):
        si = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=297)
        left, right = si.emit()
        self.assertEqual(left.scale_type, 0)
        self.assertEqual(right.scale_type, 0)

    def test_both_halves_inside_page_clean(self):
        # Build a tiny doc with two A4 facing pages, place the spread,
        # run the bbox helper to confirm both frames sit inside
        # [-bleed, w+bleed].
        doc = Document(facing_pages=True)
        pl = doc.add_page(size="A4", bleed_mm=3, label="L")
        pr = doc.add_page(size="A4", bleed_mm=3, label="R")
        si = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297,
                         h_mm=297, base_anname="P9 Spread")
        l, r = si.place(pl, pr)
        for frame, page in ((l, pl), (r, pr)):
            x0, y0, x1, y1 = _frame_bbox_mm(frame, page)
            self.assertGreaterEqual(x0, -3.0)
            self.assertLessEqual(x1, 213.0)
            self.assertGreaterEqual(y0, -3.0)
            self.assertLessEqual(y1, 300.0)

    def test_place_appends_to_pages(self):
        doc = Document(facing_pages=True)
        pl = doc.add_page(size="A4", bleed_mm=3)
        pr = doc.add_page(size="A4", bleed_mm=3)
        before_l, before_r = len(pl.items), len(pr.items)
        SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=297).place(pl, pr)
        self.assertEqual(len(pl.items), before_l + 1)
        self.assertEqual(len(pr.items), before_r + 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
