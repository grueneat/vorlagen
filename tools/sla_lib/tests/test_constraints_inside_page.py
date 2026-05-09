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
    BRAND_CONSTRAINTS, _InsidePageRule,
)


def _find_rule(rid: str):
    for r in BRAND_CONSTRAINTS:
        if r.id == rid:
            return r
    raise AssertionError(f"rule {rid} not in BRAND_CONSTRAINTS")


def _doc_with(size="A4", bleed_mm=3.0):
    """Helper: minimal Document with one doc page of the given size."""
    d = Document(title="t", template_id="t")
    d.add_page(size=size, bleed_mm=bleed_mm)
    return d


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


# ---------------------------------------------------------------------------
# brand:inside_page rule
# ---------------------------------------------------------------------------
class InsidePageRulePassTests(unittest.TestCase):
    def test_inbounds_frame_passes(self):
        d = _doc_with(size="A4")
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=100, h_mm=100,
                                 anname="ok"))
        rule = _find_rule("brand:inside_page")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_at_bleed_edge_passes(self):
        d = _doc_with(size="A4", bleed_mm=3.0)
        # Bleed rectangle: (-3, -3) → (213, 300) on a 210×297 A4. Worst
        # overshoot 0 → rule passes.
        d.pages[0].add(Polygon(x_mm=-3, y_mm=-3, w_mm=216, h_mm=303,
                                anname="bleed-bg"))
        rule = _find_rule("brand:inside_page")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_anchored_frame_passes(self):
        d = _doc_with(size="A4")
        d.pages[0].add(Polygon(
            anchor=Anchor(h="right", v="top", margin_mm=10),
            w_mm=20, h_mm=20, anname="anch",
        ))
        rule = _find_rule("brand:inside_page")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])


class InsidePageRuleErrorTests(unittest.TestCase):
    def test_overflow_right_more_than_1mm_is_error(self):
        d = _doc_with(size="A4")
        d.pages[0].add(ImageFrame(x_mm=210, y_mm=0, w_mm=210, h_mm=100,
                                   anname="P9 Spread"))
        rule = _find_rule("brand:inside_page")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "error")
        self.assertEqual(vs[0].rule_id, "brand:inside_page")
        self.assertTrue(vs[0].targets)
        self.assertIn("exceeds page", vs[0].message)
        self.assertIn("P9 Spread", vs[0].message)

    def test_overflow_left(self):
        d = _doc_with(size="A4")
        d.pages[0].add(ImageFrame(x_mm=-10, y_mm=0, w_mm=50, h_mm=50,
                                   anname="left-overflow"))
        rule = _find_rule("brand:inside_page")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "error")

    def test_overflow_top(self):
        d = _doc_with(size="A4")
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=-10, w_mm=50, h_mm=50,
                                   anname="top-overflow"))
        rule = _find_rule("brand:inside_page")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "error")

    def test_overflow_bottom(self):
        d = _doc_with(size="A4")
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=250, w_mm=50, h_mm=80,
                                   anname="bottom-overflow"))
        rule = _find_rule("brand:inside_page")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "error")


class InsidePageRuleWarningTests(unittest.TestCase):
    def test_bleed_nudge_within_1mm_is_warning(self):
        # A4 page, bleed=3, edge of bleed rect at x=213.
        # Frame at x=0, w=210.8 → x1=210.8 (still inside trim+bleed). Use
        # a wider frame so we cross into the warning band.
        # x=0, w=213.8 → x1=213.8 (overshoot ~0.8 mm).
        d = _doc_with(size="A4", bleed_mm=3.0)
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=0, w_mm=213.8, h_mm=100,
                                   anname="nudge"))
        rule = _find_rule("brand:inside_page")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "warning")

    def test_within_tolerance_passes(self):
        # Overshoot ~0.4 mm is within tolerance: x=0, w=213.4 → x1=213.4.
        d = _doc_with(size="A4", bleed_mm=3.0)
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=0, w_mm=213.4, h_mm=100,
                                   anname="micro-nudge"))
        rule = _find_rule("brand:inside_page")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])


class InsidePageRuleMasterSkipTests(unittest.TestCase):
    def test_master_page_items_skipped(self):
        d = Document(title="t", template_id="t")
        master = d.add_master(name="OnlyMaster", size="A4", bleed_mm=3.0)
        # Add an overflowing frame to the master.
        master.add(ImageFrame(x_mm=210, y_mm=0, w_mm=210, h_mm=100,
                              anname="master-overflow"))
        d.add_page(size="A4", master="OnlyMaster")
        rule = _find_rule("brand:inside_page")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(vs, [])


class InsidePageRuleRotationTests(unittest.TestCase):
    def test_rotation_270_fits_when_unrotated_origin_outside(self):
        # Replicate the plakat Impressum case: A1 page (594×841 mm),
        # frame at (563.69, 832.69) with size (377.38, 21.02), rotated
        # 270° CCW. Un-rotated bbox would extend to x=941 (overshoot
        # ~350 mm); rotated bbox via CCW270 with top-left pivot:
        #   corners: (0,0), (w,0), (w,h), (0,h)
        #   CCW270:  (px*cos270 - py*sin270, px*sin270 + py*cos270)
        #            cos270 = 0, sin270 = -1
        #          = (-py * -1, px * -1)  = (py, -px)
        #     (0, 0)   → (0, 0)
        #     (377.38, 0)   → (0, -377.38)
        #     (377.38, 21.02) → (21.02, -377.38)
        #     (0, 21.02) → (21.02, 0)
        #   Translated by pivot (563.69, 832.69):
        #     bbox: x in [563.69, 584.71], y in [455.31, 832.69]
        # Both ranges fit inside [-3, 597] × [-3, 844] for A1 with bleed=3.
        d = Document(title="t", template_id="t")
        # Custom A1 portrait via tuple (594×841 mm).
        d.add_page(size=(594, 841), bleed_mm=3.0)
        d.pages[0].add(TextFrame(
            x_mm=563.69, y_mm=832.69, w_mm=377.38, h_mm=21.02,
            rotation_deg=270, anname="Impressum",
        ))
        rule = _find_rule("brand:inside_page")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_rotated_bbox_overshoot_is_error(self):
        d = _doc_with(size="A4", bleed_mm=3.0)
        # Frame rotated 45° far to the right of the page; bbox sticks out.
        d.pages[0].add(ImageFrame(x_mm=200, y_mm=0, w_mm=100, h_mm=50,
                                   rotation_deg=45, anname="rotated-overflow"))
        rule = _find_rule("brand:inside_page")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "error")


class InsidePageRuleRegistryTests(unittest.TestCase):
    def test_rule_in_registry(self):
        rule = _find_rule("brand:inside_page")
        self.assertIsInstance(rule, _InsidePageRule)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
