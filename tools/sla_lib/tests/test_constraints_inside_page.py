"""Tests for rotation-aware bbox helpers and brand:inside_page rule (Issue #14)."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document  # noqa: E402
from sla_lib.builder.primitives import (  # noqa: E402
    TextFrame, ImageFrame, Polygon, Anchor, Run,
)
from sla_lib.builder.brand_constraints import (  # noqa: E402
    _rotated_bbox, _frame_bbox_mm,
)


# ---------------------------------------------------------------------------
# _rotated_bbox
# ---------------------------------------------------------------------------
class RotatedBboxTests(unittest.TestCase):
    def test_no_rotation_returns_corners(self):
        self.assertEqual(_rotated_bbox(10, 20, 50, 30, 0), (10, 20, 60, 50))

    def test_rotation_90_ccw(self):
        # Pivot at (0, 0), rotate (w, 0)→(0, w); (w, h)→(-h, w); (0, h)→(-h, 0).
        x0, y0, x1, y1 = _rotated_bbox(0, 0, 50, 30, 90)
        self.assertAlmostEqual(x0, -30.0, places=9)
        self.assertAlmostEqual(x1, 0.0, places=9)
        self.assertAlmostEqual(y0, 0.0, places=9)
        self.assertAlmostEqual(y1, 50.0, places=9)

    def test_rotation_180(self):
        x0, y0, x1, y1 = _rotated_bbox(0, 0, 50, 30, 180)
        self.assertAlmostEqual(x0, -50.0, places=9)
        self.assertAlmostEqual(x1, 0.0, places=9)
        self.assertAlmostEqual(y0, -30.0, places=9)
        self.assertAlmostEqual(y1, 0.0, places=9)

    def test_rotation_270_ccw(self):
        # corner (w, 0) → (0, -w); corner (w, h) → (h, -w); corner (0, h) → (h, 0).
        x0, y0, x1, y1 = _rotated_bbox(0, 0, 50, 30, 270)
        self.assertAlmostEqual(x0, 0.0, places=9)
        self.assertAlmostEqual(x1, 30.0, places=9)
        self.assertAlmostEqual(y0, -50.0, places=9)
        self.assertAlmostEqual(y1, 0.0, places=9)

    def test_rotation_45_arbitrary(self):
        x0, y0, x1, y1 = _rotated_bbox(0, 0, 10, 10, 45)
        # Corners after CCW45 around (0, 0):
        #  (0, 0) → (0, 0)
        #  (10, 0) → (10·cos45, 10·sin45) ≈ (7.071, 7.071)
        #  (10, 10) → (10·cos45 - 10·sin45, 10·sin45 + 10·cos45) ≈ (0, 14.142)
        #  (0, 10) → (-10·sin45, 10·cos45) ≈ (-7.071, 7.071)
        s = 10 * math.sin(math.radians(45))
        self.assertAlmostEqual(x0, -s, places=6)
        self.assertAlmostEqual(x1, s, places=6)
        self.assertAlmostEqual(y0, 0.0, places=6)
        self.assertAlmostEqual(y1, 2 * s, places=6)

    def test_rotation_355_small_ccw(self):
        # 355° CCW = -5° rotation: a 25×25 bbox grows by sin(5°) on each side
        # (~ 25 * 0.0872 = 2.18 mm) but its size stays close to 25 mm.
        # Per pitfall P-1, sub-5° rotations stay within ~0.4 mm overshoot
        # for compact frames; verify the bbox is small.
        x0, y0, x1, y1 = _rotated_bbox(0, 0, 25, 25, 355)
        # Width and height of axis-aligned bbox:
        w = x1 - x0
        h = y1 - y0
        # Both dimensions should be only marginally larger than 25 mm.
        self.assertLess(w, 25 + 3.0)
        self.assertLess(h, 25 + 3.0)
        # And each side should have moved by less than ~3 mm:
        self.assertLess(abs(x0), 3.0)
        self.assertLess(abs(y0), 3.0)

    def test_translation_offset(self):
        self.assertEqual(_rotated_bbox(100, 200, 10, 10, 0), (100, 200, 110, 210))


# ---------------------------------------------------------------------------
# _frame_bbox_mm
# ---------------------------------------------------------------------------
class FrameBboxMmTests(unittest.TestCase):
    def _doc(self, size="A4"):
        d = Document(title="t", template_id="t")
        page = d.add_page(size=size)
        return d, page

    def test_unrotated_textframe(self):
        _, page = self._doc(size="A6")
        f = TextFrame(x_mm=10, y_mm=20, w_mm=50, h_mm=30, anname="x")
        bbox = _frame_bbox_mm(f, page)
        self.assertEqual(bbox, (10, 20, 60, 50))

    def test_anchored_frame_uses_resolve_anchor(self):
        _, page = self._doc(size="A4")
        # Anchor obliterates x_mm/y_mm: -999 must be ignored.
        f = Polygon(
            anchor=Anchor(h="left", v="top", margin_mm=5),
            w_mm=10, h_mm=10, x_mm=-999, y_mm=-999, anname="anch",
        )
        bbox = _frame_bbox_mm(f, page)
        self.assertIsNotNone(bbox)
        x0, y0, x1, y1 = bbox
        self.assertAlmostEqual(x0, 5.0, places=6)
        self.assertAlmostEqual(y0, 5.0, places=6)
        self.assertAlmostEqual(x1, 15.0, places=6)
        self.assertAlmostEqual(y1, 15.0, places=6)

    def test_rotated_frame(self):
        _, page = self._doc(size="A4")
        f = TextFrame(x_mm=100, y_mm=100, w_mm=50, h_mm=20,
                      rotation_deg=90, anname="r")
        x0, y0, x1, y1 = _frame_bbox_mm(f, page)
        # Pivot (100, 100), CCW90:
        #  (0, 0) → (0, 0) → (100, 100)
        #  (50, 0) → (0, 50) → (100, 150)
        #  (50, 20) → (-20, 50) → (80, 150)
        #  (0, 20) → (-20, 0) → (80, 100)
        self.assertAlmostEqual(x0, 80.0, places=9)
        self.assertAlmostEqual(y0, 100.0, places=9)
        self.assertAlmostEqual(x1, 100.0, places=9)
        self.assertAlmostEqual(y1, 150.0, places=9)

    def test_non_frame_returns_none(self):
        _, page = self._doc(size="A4")
        run = Run(text="x")
        self.assertIsNone(_frame_bbox_mm(run, page))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
