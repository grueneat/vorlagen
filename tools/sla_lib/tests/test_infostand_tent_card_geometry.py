"""Invariant tests for infostand-tent-card-a5-quer V1 (#20 "Hero Band").

Per #18 / #19 / #23 pattern: pin RELATIONSHIPS not absolute COORDINATES.
SLA round-trip is float-imprecise; these tests survive any future legitimate
retuning that preserves V1 design intent.

Coverage (≥12 required by plan T08; 22 implemented):
  Cross-panel mirror at apex y=105 (Hero-Band, Photo-Backing, Footer-Strip)
  Cross-panel same-size (3 Polygon pairs)
  Panel A intra-panel containment (6 visual-bbox inside checks; rotation-aware
    after #32 — raw bbox math fails because Panel A text/image frames now
    carry rotation_deg=180 like Panel B)
  Panel A bullets/Termine baseline + height
  Logo width = 38 mm (3M ± tol; brand:logo_size_3M conformant)
  ParaStyle existence (6 V1 styles present, V0 tent/cta absent)
  Logo asset identity (gruene-weiss.png)
  Falz layer integrity (LAYER=3 exclusive to Mittelfalz)
  Panel A polygons rotation_deg=0
  Panel A Text/Image rotation_deg=180 (added in #32 — fixes tent-fold panel
    orientation so content reads right-side-up after folding)
  Panel B polygons rotation_deg=0 (rectangles need no visual rotation)
  Panel B Text/Image rotation_deg=180

Test setup uses build_template() (clean doc, no inline image IO during tests)
to avoid library.inject_into_frame photo crops in geometry assertions.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from lxml import etree  # noqa: E402

TEMPLATE_DIR = ROOT / "templates" / "infostand-tent-card-a5-quer"
TOL_MM = 0.6

# V1 mirror axis (Mittelfalz)
APEX_Y_MM = 105.0
PAGE_H_MM = 210.0


def _load_build_module():
    spec = importlib.util.spec_from_file_location(
        "infostand_tent_build", TEMPLATE_DIR / "build.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class InfostandTentCardGeometryTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        mod = _load_build_module()
        # build_template = clean doc (no photo bytes — library.inject_into_frame
        # only runs in build_preview).
        cls._mod = mod
        doc = mod.build_template()
        cls.items_by_anname = {
            getattr(it, "anname", ""): it
            for page in doc.pages
            for it in page.items
            if getattr(it, "anname", "")
        }
        # Save once for SLA-attribute assertions (Falz layer + ParaStyle existence).
        cls.tmp = tempfile.NamedTemporaryFile(suffix=".sla", delete=False)
        cls.tmp.close()
        doc.save(cls.tmp.name)
        cls.tree = etree.parse(cls.tmp.name)
        cls.doc_xml = cls.tree.getroot().find("DOCUMENT")

    def _f(self, anname):
        item = self.items_by_anname.get(anname)
        self.assertIsNotNone(item, f"frame missing: {anname}")
        return item

    def _bbox_center(self, item):
        return (item.x_mm + item.w_mm / 2.0, item.y_mm + item.h_mm / 2.0)

    def _right(self, item):
        return item.x_mm + item.w_mm

    def _bottom(self, item):
        return item.y_mm + item.h_mm

    def _visual_bbox(self, item):
        """Return (x, y, w, h) of the frame's VISUAL bbox (pre-rotation area).

        For frames with rotation_deg=180 the SLA anchor sits at the bottom-
        right corner of the visual area; subtract w/h to recover the visual
        top-left. Polygons (and frames with rotation_deg=0) report their
        stored coords verbatim.
        """
        rot = getattr(item, "rotation_deg", 0.0) or 0.0
        if abs(rot - 180.0) < 0.5:
            return (item.x_mm - item.w_mm, item.y_mm - item.h_mm,
                    item.w_mm, item.h_mm)
        return (item.x_mm, item.y_mm, item.w_mm, item.h_mm)

    # ── Cross-panel mirror around apex y=105 ──

    def test_hero_bands_mirror_around_apex(self):
        a = self._f("Hero-Band Panel A")
        b = self._f("Hero-Band Panel B")
        ay = a.y_mm + a.h_mm / 2.0
        by = b.y_mm + b.h_mm / 2.0
        midpoint = (ay + by) / 2.0
        self.assertAlmostEqual(midpoint, APEX_Y_MM, delta=TOL_MM,
                               msg=f"hero-band mirror midpoint y={midpoint} ≠ {APEX_Y_MM}")

    def test_photo_backings_mirror_around_apex(self):
        a = self._f("Photo-Backing Panel A")
        b = self._f("Photo-Backing Panel B")
        midpoint = (a.y_mm + a.h_mm / 2.0 + b.y_mm + b.h_mm / 2.0) / 2.0
        self.assertAlmostEqual(midpoint, APEX_Y_MM, delta=TOL_MM)

    def test_footer_strips_mirror_around_apex(self):
        a = self._f("Footer-Strip Panel A")
        b = self._f("Footer-Strip Panel B")
        midpoint = (a.y_mm + a.h_mm / 2.0 + b.y_mm + b.h_mm / 2.0) / 2.0
        self.assertAlmostEqual(midpoint, APEX_Y_MM, delta=TOL_MM)

    # ── Cross-panel same-size on Polygon pairs ──

    def test_hero_bands_same_size(self):
        a = self._f("Hero-Band Panel A")
        b = self._f("Hero-Band Panel B")
        self.assertAlmostEqual(a.w_mm, b.w_mm, delta=TOL_MM)
        self.assertAlmostEqual(a.h_mm, b.h_mm, delta=TOL_MM)

    def test_photo_backings_same_size(self):
        a = self._f("Photo-Backing Panel A")
        b = self._f("Photo-Backing Panel B")
        self.assertAlmostEqual(a.w_mm, b.w_mm, delta=TOL_MM)
        self.assertAlmostEqual(a.h_mm, b.h_mm, delta=TOL_MM)

    def test_footer_strips_same_size(self):
        a = self._f("Footer-Strip Panel A")
        b = self._f("Footer-Strip Panel B")
        self.assertAlmostEqual(a.w_mm, b.w_mm, delta=TOL_MM)
        self.assertAlmostEqual(a.h_mm, b.h_mm, delta=TOL_MM)

    # ── Panel A intra-panel containment (visual-bbox; rotation-aware) ──

    def _assert_inside(self, child_an, parent_an):
        """Assert child's VISUAL bbox is inside parent's VISUAL bbox.

        After #32 Panel A text/image frames carry rotation_deg=180 (SLA anchor
        at the bottom-right of the visual area). Raw x_mm/y_mm comparisons
        produce false negatives — use the visual bbox helper which subtracts
        w/h for rotated frames.
        """
        c = self._f(child_an)
        p = self._f(parent_an)
        cx, cy, cw, ch = self._visual_bbox(c)
        px, py, pw, ph = self._visual_bbox(p)
        self.assertGreaterEqual(cx, px - TOL_MM,
                                f"{child_an}.visual_x={cx} < {parent_an}.visual_x={px}")
        self.assertGreaterEqual(cy, py - TOL_MM,
                                f"{child_an}.visual_y={cy} < {parent_an}.visual_y={py}")
        self.assertLessEqual(cx + cw, px + pw + TOL_MM,
                             f"{child_an} visual right > {parent_an} visual right")
        self.assertLessEqual(cy + ch, py + ph + TOL_MM,
                             f"{child_an} visual bottom > {parent_an} visual bottom")

    def test_logo_panel_a_inside_hero_band_a(self):
        self._assert_inside("Logo Grüne (panel A)", "Hero-Band Panel A")

    def test_headline_panel_a_inside_hero_band_a(self):
        self._assert_inside("Headline Panel A", "Hero-Band Panel A")

    def test_payoff_panel_a_inside_hero_band_a(self):
        self._assert_inside("Pay-off Panel A", "Hero-Band Panel A")

    def test_photo_inside_photo_backing_a(self):
        self._assert_inside("Hintergrund-Mitmachen", "Photo-Backing Panel A")

    def test_cta_footer_a_inside_footer_strip_a(self):
        self._assert_inside("CTA-Footer Panel A", "Footer-Strip Panel A")

    def test_impressum_a_inside_footer_strip_a(self):
        self._assert_inside("Impressum (Tent)", "Footer-Strip Panel A")

    # ── Panel A bullets+Termine baseline + height ──

    def test_bullets_termine_baseline_a(self):
        b = self._f("Body Panel A")
        t = self._f("Termine Panel A")
        self.assertAlmostEqual(b.y_mm, t.y_mm, delta=TOL_MM)

    def test_bullets_termine_height_a(self):
        b = self._f("Body Panel A")
        t = self._f("Termine Panel A")
        self.assertAlmostEqual(b.h_mm, t.h_mm, delta=TOL_MM)

    # ── Logo width = 3M (brand:logo_size_3M conformant) ──

    def test_logo_width_3M(self):
        # 3M = 0.18 * shorter trim edge; for A4 quer 297×210 → 3M = 0.18 * 210 = 37.8 mm.
        # V1 frame width = 38 mm; tolerance 0.5 mm.
        logo = self._f("Logo Grüne (panel A)")
        self.assertAlmostEqual(logo.w_mm, 37.8, delta=0.5,
                               msg=f"Logo width {logo.w_mm} mm not within 3M ± 0.5")

    # ── ParaStyle existence (6 V1 styles present, V0 tent/cta dropped) ──

    def test_para_style_existence(self):
        # ParaStyles emit as <STYLE> elements at DOCUMENT root level.
        styles = {s.attrib.get("NAME", "") for s in self.doc_xml.findall("STYLE")}
        for needed in ("tent/headline", "tent/body", "tent/termine",
                       "tent/impressum", "tent/payoff", "tent/cta-footer"):
            self.assertIn(needed, styles, f"ParaStyle {needed} missing in SLA")
        self.assertNotIn("tent/cta", styles,
                         "V0 tent/cta ParaStyle still emitted in V1")

    # ── Logo asset identity (gruene-weiss.png) ──

    def test_logo_asset_is_gruene_weiss(self):
        logo = self._f("Logo Grüne (panel A)")
        self.assertEqual(logo.inline_image_ext, "png",
                         f"Logo extension {logo.inline_image_ext} ≠ png")
        self.assertIsNotNone(logo.inline_image_data,
                             "Logo Panel A has no inline_image_data")
        # Verify pack_inline_image of canonical asset matches.
        from sla_lib.builder import pack_inline_image
        canonical = ROOT / "shared" / "logos" / "gruene-weiss.png"
        self.assertTrue(canonical.exists(), f"canonical asset missing: {canonical}")
        expected_data, _ = pack_inline_image(canonical.read_bytes(), "png")
        self.assertEqual(logo.inline_image_data, expected_data,
                         "Logo inline data differs from gruene-weiss.png")

    # ── Falz layer integrity (LAYER=3 exclusive to Mittelfalz) ──

    def test_falz_layer_integrity(self):
        falz_pageobjects = [
            po for po in self.doc_xml.findall("PAGEOBJECT")
            if po.attrib.get("LAYER") == "3"
        ]
        self.assertEqual(len(falz_pageobjects), 1,
                         f"LAYER=3 must contain exactly Mittelfalz; got "
                         f"{[p.attrib.get('ANNAME') for p in falz_pageobjects]}")
        self.assertEqual(falz_pageobjects[0].attrib.get("ANNAME"),
                         "Mittelfalz (horizontal)")

        # All V1 polygons must be on LAYER=0 (Hintergrund).
        for an in ("Hero-Band Panel A", "Hero-Band Panel B",
                   "Photo-Backing Panel A", "Photo-Backing Panel B",
                   "Footer-Strip Panel A", "Footer-Strip Panel B"):
            po = next((p for p in self.doc_xml.findall("PAGEOBJECT")
                       if p.attrib.get("ANNAME") == an), None)
            self.assertIsNotNone(po, f"V1 polygon {an} not in SLA")
            self.assertEqual(po.attrib.get("LAYER"), "0",
                             f"V1 polygon {an} not on LAYER=0; on {po.attrib.get('LAYER')}")

    # ── Rotation contract ──

    def test_panel_a_polygons_rotation_zero(self):
        for an in ("Hero-Band Panel A", "Photo-Backing Panel A",
                   "Footer-Strip Panel A"):
            f = self._f(an)
            self.assertAlmostEqual(f.rotation_deg, 0.0, delta=0.1,
                                   msg=f"{an} rotation_deg={f.rotation_deg} ≠ 0")

    def test_panel_b_polygons_rotation_zero(self):
        # Polygons (rectangles) on Panel B carry rotation_deg=0 — only the
        # Text/Image frames need ROT=180 (locked decision #1).
        for an in ("Hero-Band Panel B", "Photo-Backing Panel B",
                   "Footer-Strip Panel B"):
            f = self._f(an)
            self.assertAlmostEqual(f.rotation_deg, 0.0, delta=0.1,
                                   msg=f"{an} rotation_deg={f.rotation_deg} ≠ 0")

    def test_panel_b_text_image_rotation_zero(self):
        """Issue #32 follow-up: Panel B text/image frames carry ROT=0.

        Panel B does NOT flip during the tent fold (only Panel A does), so its
        content reads in the natural flat-sheet direction from the viewer's
        perspective — no per-frame rotation needed.
        """
        for an in ("Logo Grüne (panel B)", "Headline Panel B",
                   "Pay-off Panel B", "Hintergrund-Mitmachen Panel B",
                   "QR-Code (mitmachen, panel B)", "Body Panel B",
                   "Termine Panel B", "CTA-Footer Panel B",
                   "Impressum (Tent, panel B)"):
            f = self._f(an)
            self.assertAlmostEqual(f.rotation_deg, 0.0, delta=0.1,
                                   msg=f"{an} rotation_deg={f.rotation_deg} ≠ 0")

    def test_panel_a_text_image_rotation_180(self):
        """Issue #32: Panel A text/image frames carry ROT=180.

        When the flat sheet is folded into a tent (apex up at y=105), Panel A's
        face is viewed with y=105 at the apex and y=0 at the table — INVERTED
        from the flat-sheet reading direction. Rotating each frame's content
        180° around its center compensates so content reads right-side-up on
        the assembled tent. Panel B does NOT flip and uses ROT=0; only Panel A
        carries the rotation.
        """
        for an in ("Logo Grüne (panel A)", "Headline Panel A",
                   "Pay-off Panel A", "Hintergrund-Mitmachen",
                   "QR-Code (mitmachen, panel A)", "Body Panel A",
                   "Termine Panel A", "CTA-Footer Panel A",
                   "Impressum (Tent)"):
            f = self._f(an)
            self.assertAlmostEqual(f.rotation_deg, 180.0, delta=0.1,
                                   msg=f"{an} rotation_deg={f.rotation_deg} ≠ 180")


if __name__ == "__main__":
    unittest.main()
