"""Geometry invariant tests for themen-plakat-a3-quer V1 (#19 Evidence Cards).

Per #23 pattern: pin RELATIONSHIPS not absolute COORDINATES. If V2 / V3
layouts move frames, these tests should still pass as long as the
relational invariants of the V1 design intent are preserved.

Invariants tested (>=10):
  1. Three Beleg cards share top y (row alignment)
  2. Three Beleg cards share width (uniform sizing)
  3. Three Beleg cards share height (uniform sizing)
  4. Card 1 left edge sits at MARGIN_X
  5. Card 3 right edge sits at page_w - MARGIN_X (within tolerance)
  6. Card 1 + Card 3 mirror around page horizontal centre (axis = page_w/2)
  7. Per-card Stat / Label / Body share inner-left x = card.x + 5mm
  8. Per-card Stat / Label / Body sit fully inside Card (containment)
  9. Themen-Hero sits inside Hero-Foto-Card (containment)
 10. Hero-Foto-Card left edge sits at MARGIN_X
 11. Headline These + Sub-Headline share left x (right-half AXIS_HEADLINE_LEFT)
 12. Logo width is 3M = 0.06 * 297 = 53.46 mm (within tolerance)
"""
from __future__ import annotations
import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

TEMPLATE_DIR = ROOT / "templates" / "themen-plakat-a3-quer"

# Page constants (must match build.py)
PAGE_W_MM = 420.0
PAGE_H_MM = 297.0
MARGIN_X_MM = 15.0
TOL_MM = 0.6   # slightly looser than 0.5 to absorb COL_W rounding (124.6667)


def _load_build_module():
    spec = importlib.util.spec_from_file_location(
        "themen_plakat_build", TEMPLATE_DIR / "build.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ThemenPlakatGeometryTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        mod = _load_build_module()
        # Use clean template (no photo bytes) for geometry assertions
        doc = mod.build_template()
        cls.items_by_anname = {
            getattr(it, "anname", ""): it
            for page in doc.pages
            for it in page.items
            if getattr(it, "anname", "")
        }

    def _f(self, anname):
        item = self.items_by_anname.get(anname)
        self.assertIsNotNone(item, f"frame missing: {anname}")
        return item

    def _right(self, item):
        return item.x_mm + item.w_mm

    def _bottom(self, item):
        return item.y_mm + item.h_mm

    # -------- Card row + size invariants --------

    def test_cards_share_top_y(self):
        c1, c2, c3 = (self._f(f"Beleg {i} — Card") for i in (1, 2, 3))
        self.assertAlmostEqual(c1.y_mm, c2.y_mm, delta=TOL_MM)
        self.assertAlmostEqual(c2.y_mm, c3.y_mm, delta=TOL_MM)

    def test_cards_share_width(self):
        c1, c2, c3 = (self._f(f"Beleg {i} — Card") for i in (1, 2, 3))
        self.assertAlmostEqual(c1.w_mm, c2.w_mm, delta=TOL_MM)
        self.assertAlmostEqual(c2.w_mm, c3.w_mm, delta=TOL_MM)

    def test_cards_share_height(self):
        c1, c2, c3 = (self._f(f"Beleg {i} — Card") for i in (1, 2, 3))
        self.assertAlmostEqual(c1.h_mm, c2.h_mm, delta=TOL_MM)
        self.assertAlmostEqual(c2.h_mm, c3.h_mm, delta=TOL_MM)

    # -------- Card edge anchoring --------

    def test_card_1_left_at_margin(self):
        c1 = self._f("Beleg 1 — Card")
        self.assertAlmostEqual(c1.x_mm, MARGIN_X_MM, delta=TOL_MM)

    def test_card_3_right_at_page_minus_margin(self):
        c3 = self._f("Beleg 3 — Card")
        self.assertAlmostEqual(self._right(c3), PAGE_W_MM - MARGIN_X_MM,
                               delta=TOL_MM)

    def test_cards_mirror_around_page_center(self):
        c1 = self._f("Beleg 1 — Card")
        c3 = self._f("Beleg 3 — Card")
        axis = (c1.x_mm + self._right(c3)) / 2.0
        self.assertAlmostEqual(axis, PAGE_W_MM / 2.0, delta=TOL_MM)

    # -------- Per-card inner-axis sharing --------

    def test_per_card_inner_left_axis(self):
        for i in (1, 2, 3):
            card = self._f(f"Beleg {i} — Card")
            inner_x = card.x_mm + 5.0
            for inner in ("Stat", "Label", "Body"):
                f = self._f(f"Beleg {i} — {inner}")
                self.assertAlmostEqual(
                    f.x_mm, inner_x, delta=TOL_MM,
                    msg=f"Beleg {i} — {inner} x={f.x_mm} != card+5={inner_x}",
                )

    def test_per_card_containment(self):
        for i in (1, 2, 3):
            card = self._f(f"Beleg {i} — Card")
            for inner in ("Stat", "Label", "Body"):
                f = self._f(f"Beleg {i} — {inner}")
                self.assertGreaterEqual(f.x_mm, card.x_mm - TOL_MM)
                self.assertGreaterEqual(f.y_mm, card.y_mm - TOL_MM)
                self.assertLessEqual(self._right(f), self._right(card) + TOL_MM)
                self.assertLessEqual(self._bottom(f), self._bottom(card) + TOL_MM)

    # -------- Hero containment --------

    def test_hero_inside_hero_foto_card(self):
        hero = self._f("Themen-Hero")
        card = self._f("Hero-Foto-Card")
        self.assertGreaterEqual(hero.x_mm, card.x_mm - TOL_MM)
        self.assertGreaterEqual(hero.y_mm, card.y_mm - TOL_MM)
        self.assertLessEqual(self._right(hero), self._right(card) + TOL_MM)
        self.assertLessEqual(self._bottom(hero), self._bottom(card) + TOL_MM)

    def test_hero_foto_card_left_at_margin(self):
        card = self._f("Hero-Foto-Card")
        self.assertAlmostEqual(card.x_mm, MARGIN_X_MM, delta=TOL_MM)

    # -------- Headline-stack column --------

    def test_headline_and_sub_share_left_x(self):
        hl = self._f("Headline These")
        sub = self._f("Sub-Headline")
        self.assertAlmostEqual(hl.x_mm, sub.x_mm, delta=TOL_MM)

    def test_headline_stack_in_right_half(self):
        # Per V1 60/40 split, headline-stack left edge sits past page_w/2.
        hl = self._f("Headline These")
        self.assertGreater(hl.x_mm, PAGE_W_MM / 2.0)

    # -------- Logo brand-rule conformance --------

    def test_logo_width_is_3M(self):
        # 3M = 0.06 * min(420, 297) = 0.06 * 297 = 17.82; 3M = 53.46
        logo = self._f("Logo Grüne (top-left)")
        self.assertAlmostEqual(logo.w_mm, 53.46, delta=0.5)


if __name__ == "__main__":
    unittest.main()
