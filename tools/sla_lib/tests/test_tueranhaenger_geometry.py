"""Invariant tests for wahltag-tueranhaenger V1 geometry — pin RELATIONSHIPS.

Per Issue #18 locked decision #14 + Issue #23 pattern. Float-imprecise
SLA round-trip makes coordinate-pinning brittle. These tests survive any
future legitimate retuning that preserves V1 alignment intent.

Pinning style:
  - bbox-relationship via assertAlmostEqual(..., delta=0.5)
  - assertGreater[Equal]/assertLessEqual for ordering and containment
  - never absolute literals like assertEqual(x_mm, 25.0)

Coverage (12 invariants, ≥10 required by plan T08):
  1. Brand-Bar heights match across pages (mirror pair)
  2. Hellgrün-Akzent touches Brand-Bar bottom (gap 0)
  3. Wahlkreuz horizontally centered on panel (x=52.5)
  4. Wahlkreuz fully inside Hellgrün-Band (containment)
  5. Portrait fully inside Portrait-Card (containment)
  6. QR-Code inside QR White-Backing (containment)
  7. Visitenkarten-Footer encloses 5 back text frames (sub-tests)
  8. Bullets-Card encloses 2 front text frames (sub-tests)
  9. Full-bleed polygons extend to outer edge ±2mm (5 polygons)
 10. Vertical order preserved (Sub > HL+h, Bullets > Sub+h, Footer > Card+h)
 11. Logos (top + back-band) mirror x and y (white logos)
 12. Logo (weiss, top) width == 18.9mm (3×M Quickguide-konform)
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))


def _load_doc():
    build_py = ROOT / "templates" / "wahltag-tueranhaenger" / "build.py"
    spec = importlib.util.spec_from_file_location("tueranhaenger_build", build_py)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_doc()


def _frame_by_anname(doc, anname):
    for page in doc.pages:
        if getattr(page, "is_master", False):
            continue
        for item in page.items:
            if getattr(item, "anname", "") == anname:
                return item, page
    raise AssertionError(f"frame {anname!r} not found in tueranhaenger doc")


_DOC = None


def _doc():
    global _DOC
    if _DOC is None:
        _DOC = _load_doc()
    return _DOC


# Doc geometry constants (mirror build.py — used for full-bleed checks)
TRIM_W_MM = 105.0
BLEED_MM = 2.0


class WahltagTueranhaengerGeometryTests(unittest.TestCase):
    """V1 invariant pins (relationship-based)."""

    # -- Helpers ----------------------------------------------------------
    def _assert_inside(self, child_anname: str, parent_anname: str) -> None:
        """Assert `child` bbox lies inside `parent` bbox within ±0.5mm."""
        child, _ = _frame_by_anname(_doc(), child_anname)
        parent, _ = _frame_by_anname(_doc(), parent_anname)
        self.assertGreaterEqual(child.x_mm, parent.x_mm - 0.5,
                                f"{child_anname} left of {parent_anname}")
        self.assertGreaterEqual(child.y_mm, parent.y_mm - 0.5,
                                f"{child_anname} above {parent_anname}")
        self.assertLessEqual(child.x_mm + child.w_mm,
                             parent.x_mm + parent.w_mm + 0.5,
                             f"{child_anname} right of {parent_anname}")
        self.assertLessEqual(child.y_mm + child.h_mm,
                             parent.y_mm + parent.h_mm + 0.5,
                             f"{child_anname} below {parent_anname}")

    # -- Invariant tests --------------------------------------------------
    def test_brand_bar_heights_match(self):
        front, _ = _frame_by_anname(_doc(), "Brand-Bar (Vorderseite)")
        back, _ = _frame_by_anname(_doc(), "Brand-Bar (Rückseite)")
        self.assertAlmostEqual(front.h_mm, back.h_mm, delta=0.5)

    def test_akzent_touches_brand_bar(self):
        bar, _ = _frame_by_anname(_doc(), "Brand-Bar (Vorderseite)")
        akzent, _ = _frame_by_anname(_doc(), "Hellgrün-Akzent")
        # Brand-Bar bottom y == akzent top y (gap 0)
        self.assertAlmostEqual(bar.y_mm + bar.h_mm, akzent.y_mm, delta=0.5)

    def test_wahlkreuz_horizontally_centered(self):
        wk, _ = _frame_by_anname(_doc(), "Wahlkreuz (Hero)")
        # Panel center x = TRIM_W_MM / 2 = 52.5
        self.assertAlmostEqual(wk.x_mm + wk.w_mm / 2,
                               TRIM_W_MM / 2, delta=0.5)

    def test_wahlkreuz_inside_hellgruen_band(self):
        self._assert_inside("Wahlkreuz (Hero)", "Hellgrün-Band (Wahlkreuz)")

    def test_portrait_inside_portrait_card(self):
        self._assert_inside("Kandidat-Portrait", "Portrait-Card")

    def test_qr_inside_qr_backing(self):
        self._assert_inside("QR-Code (back)", "QR White-Backing")

    def test_visitenkarten_footer_encloses_back_text(self):
        for anname in ("Kandidat-Name", "Kandidat-Position",
                       "Kontakt-URL", "Kontakt-Info", "Impressum (back)"):
            with self.subTest(anname=anname):
                self._assert_inside(anname, "Visitenkarten-Footer")

    def test_bullets_card_encloses_front_text(self):
        for anname in ("Bullet-Liste", "Impressum"):
            with self.subTest(anname=anname):
                self._assert_inside(anname, "Bullets-Card")

    def test_full_bleed_polygons_extend_to_outer_edge(self):
        # outer right edge = TRIM_W_MM + BLEED_MM = 107
        # outer left edge  = -BLEED_MM = -2
        right_edge = TRIM_W_MM + BLEED_MM
        left_edge = -BLEED_MM
        for anname in ("Visitenkarten-Footer", "Bullets-Card",
                       "Hellgrün-Akzent", "Brand-Bar (Vorderseite)",
                       "Brand-Bar (Rückseite)"):
            p, _ = _frame_by_anname(_doc(), anname)
            with self.subTest(anname=anname):
                self.assertGreaterEqual(p.x_mm + p.w_mm, right_edge - 0.5)
                self.assertLessEqual(p.x_mm, left_edge + 0.5)

    def test_vertical_order_preserved(self):
        # Sub.y > HL.y + HL.h
        hl, _ = _frame_by_anname(_doc(), "Headline-Wahltag")
        sub, _ = _frame_by_anname(_doc(), "Sub-Headline")
        self.assertGreater(sub.y_mm, hl.y_mm + hl.h_mm)
        # Bullets-Card.y > Sub.y + Sub.h
        card, _ = _frame_by_anname(_doc(), "Bullets-Card")
        self.assertGreater(card.y_mm, sub.y_mm + sub.h_mm)
        # Visitenkarten-Footer.y > Portrait-Card.y + Portrait-Card.h
        pcard, _ = _frame_by_anname(_doc(), "Portrait-Card")
        footer, _ = _frame_by_anname(_doc(), "Visitenkarten-Footer")
        self.assertGreater(footer.y_mm, pcard.y_mm + pcard.h_mm)

    def test_logos_mirror_x_y(self):
        top, _ = _frame_by_anname(_doc(), "Logo Grüne (weiss, top)")
        back, _ = _frame_by_anname(_doc(), "Logo Grüne (weiss, back-band)")
        self.assertAlmostEqual(top.x_mm, back.x_mm, delta=0.5)
        self.assertAlmostEqual(top.y_mm, back.y_mm, delta=0.5)

    def test_logo_size_3m_compliance(self):
        # kurze_kante=105mm, M=6.3mm, 3M=18.9mm
        top, _ = _frame_by_anname(_doc(), "Logo Grüne (weiss, top)")
        self.assertAlmostEqual(top.w_mm, 18.9, delta=0.5)


if __name__ == "__main__":
    unittest.main()
