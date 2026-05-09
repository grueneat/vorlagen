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


# ---------------------------------------------------------------------------
# Issue #23 T05: outer_bleed_mm extension
# ---------------------------------------------------------------------------
class SpreadImageOuterBleedTests(unittest.TestCase):
    """outer_bleed_mm extends each half outward by N mm.

    Locked decision #11. The math:
      - LEFT half:  x = -outer_bleed,  w = page_w + outer_bleed,
                    local_offset_mm = (0, 0).
      - RIGHT half: x = 0,             w = page_w + outer_bleed,
                    local_offset_mm = (-(page_w + outer_bleed), 0).
    Default outer_bleed_mm = 0.0 preserves prior call-site behavior.
    """

    def test_default_outer_bleed_zero_unchanged(self):
        """outer_bleed_mm=0 → halves at x=0, w=page_w; right local_offset=(-page_w, 0)."""
        s = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=126.0,
                        base_anname="P9 Spread")
        left, right = s.emit()
        self.assertAlmostEqual(left.x_mm, 0.0)
        self.assertAlmostEqual(left.w_mm, 210.0)
        self.assertEqual(left.local_offset_mm, (0.0, 0.0))
        self.assertAlmostEqual(right.x_mm, 0.0)
        self.assertAlmostEqual(right.w_mm, 210.0)
        self.assertAlmostEqual(right.local_offset_mm[0], -210.0)
        self.assertAlmostEqual(right.local_offset_mm[1], 0.0)

    def test_outer_bleed_3_shifts_left_half_left(self):
        """outer_bleed_mm=3 → LEFT half x=-3, w=213, local_offset (0,0)."""
        s = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=126.0,
                        base_anname="X", outer_bleed_mm=3.0)
        left, _right = s.emit()
        self.assertAlmostEqual(left.x_mm, -3.0)
        self.assertAlmostEqual(left.w_mm, 213.0)
        self.assertEqual(left.local_offset_mm, (0.0, 0.0))

    def test_outer_bleed_3_extends_right_half_to_bleed(self):
        """outer_bleed_mm=3 → RIGHT half x=0, w=213, local_offset_mm=(-213, 0).

        The local_offset_mm adjustment is load-bearing per pitfall B10 —
        without it, the source image would scroll past the bleed area
        and visible content would shift left.
        """
        s = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=126.0,
                        base_anname="X", outer_bleed_mm=3.0)
        _left, right = s.emit()
        self.assertAlmostEqual(right.x_mm, 0.0)
        self.assertAlmostEqual(right.w_mm, 213.0)
        self.assertAlmostEqual(right.local_offset_mm[0], -213.0)
        self.assertAlmostEqual(right.local_offset_mm[1], 0.0)

    def test_anname_suffix_preserved_with_outer_bleed(self):
        """SPREAD_HALF_RX-friendly suffixes still applied with outer_bleed_mm."""
        s = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=126.0,
                        base_anname="P9 Spread", outer_bleed_mm=3.0)
        left, right = s.emit()
        self.assertEqual(left.anname, "P9 Spread · left")
        self.assertEqual(right.anname, "P9 Spread · right")

    def test_outer_bleed_does_not_affect_height_or_y(self):
        """Bleed extension is HORIZONTAL only; h_mm / y_mm unchanged."""
        s = SpreadImage(image="x.jpg", page_w_mm=210, page_h_mm=297, h_mm=126.0,
                        y_mm=10.0, outer_bleed_mm=3.0)
        left, right = s.emit()
        self.assertAlmostEqual(left.h_mm, 126.0)
        self.assertAlmostEqual(left.y_mm, 10.0)
        self.assertAlmostEqual(right.h_mm, 126.0)
        self.assertAlmostEqual(right.y_mm, 10.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
