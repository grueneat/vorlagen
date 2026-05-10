"""Invariant tests for kandidat-falzflyer-din-lang V1 ("Falz-Rhythm").

Per #18/#19/#20/#23 pattern: pin RELATIONSHIPS not absolute COORDINATES.
SLA round-trip is float-imprecise; these tests survive any future legitimate
retuning that preserves V1 design intent.

Coverage (≥18 required by plan T11; 21 implemented to match #20):
  Top-Band uniformity (4 polygons share h=31)
  P1 Top-Band outer-bleed extends to x=-3, w=105
  P2 Top-Band inner flush x=99, w=99
  P4 Top-Band outer x=-3, w=105
  P5 Top-Band inner x=99, w=99
  P3 Hintergrund vollflächig (102×216)
  P6 Hintergrund vollflächig (102×216)
  P3↔P6 grüne-Klammer same_size
  P4 themen sub-layout mirror (Thema 1+2 photos same)
  P5 themen sub-layout mirror (Thema 3+4 photos same)
  Cross-panel themen photos same dims (87×44)
  P6 column-symmetry mirrored_x at axis_mm=247.5
  P6 baseline same_y (Adresse+Telefon, Email+Sprechtag)
  Logo Print-Soll same_size (P1+P6 logos w=38)
  P2 Logo absent (negative assertion)
  Falz LAYER integrity via lxml XPath (4 PAGEOBJECTs LAYER=3)
  ParaStyle existence (16 falzflyer/* styles registered)
  teaser-body retains align=0 (mutation only on fcolor)
  M-Basis-rule regression on all 5 V1 templates (parametric)
  P3 Top-Title fcolor='Gelb' override
  INJECT_MAP frame annames present + lib_id mapping correct
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

TEMPLATE_DIR = ROOT / "templates" / "kandidat-falzflyer-din-lang"
TOL_MM = 0.6

# V1 design constants
AXIS_P6_CENTER_X_MM = 247.5
TOP_BAND_H_MM = 31.0
THEMEN_PHOTO_W_MM = 87.0
THEMEN_PHOTO_H_MM = 44.0
LOGO_3M_MM = 37.8  # 0.06 * min(297, 210) * 3 = 37.8


def _load_build_module(slug: str = "kandidat-falzflyer-din-lang"):
    template_dir = ROOT / "templates" / slug
    spec = importlib.util.spec_from_file_location(
        f"{slug.replace('-', '_')}_build", template_dir / "build.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class KandidatFalzflyerGeometryTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        mod = _load_build_module()
        cls._mod = mod
        # build_template = clean doc (no library inject — geometry only).
        doc = mod.build_template()
        cls.items_by_anname = {
            getattr(it, "anname", ""): it
            for page in doc.pages
            for it in page.items
            if getattr(it, "anname", "")
        }
        # Save once for SLA-attribute assertions (Falz layer, ParaStyles).
        cls.tmp = tempfile.NamedTemporaryFile(suffix=".sla", delete=False)
        cls.tmp.close()
        doc.save(cls.tmp.name)
        cls.tree = etree.parse(cls.tmp.name)
        cls.doc_xml = cls.tree.getroot().find("DOCUMENT")

    def _f(self, anname):
        item = self.items_by_anname.get(anname)
        self.assertIsNotNone(item, f"frame missing: {anname}")
        return item

    # ── Top-Band uniformity (1) ───────────────────────────────────────────

    def test_top_bands_uniform_height(self):
        for an in ("P1 Top-Band", "P2 Top-Band",
                   "P4 Top-Band", "P5 Top-Band"):
            f = self._f(an)
            self.assertAlmostEqual(
                f.h_mm, TOP_BAND_H_MM, delta=TOL_MM,
                msg=f"{an} h_mm={f.h_mm} ≠ {TOP_BAND_H_MM}",
            )

    # ── Top-Band outer/inner geometry (2-5) ───────────────────────────────

    def test_p1_top_band_outer_bleed(self):
        f = self._f("P1 Top-Band")
        self.assertAlmostEqual(f.x_mm, -3.0, delta=TOL_MM)
        self.assertAlmostEqual(f.w_mm, 105.0, delta=TOL_MM)

    def test_p2_top_band_inner_flush(self):
        f = self._f("P2 Top-Band")
        self.assertAlmostEqual(f.x_mm, 99.0, delta=TOL_MM)
        self.assertAlmostEqual(f.w_mm, 99.0, delta=TOL_MM)

    def test_p4_top_band_outer_bleed(self):
        f = self._f("P4 Top-Band")
        self.assertAlmostEqual(f.x_mm, -3.0, delta=TOL_MM)
        self.assertAlmostEqual(f.w_mm, 105.0, delta=TOL_MM)

    def test_p5_top_band_inner_flush(self):
        f = self._f("P5 Top-Band")
        self.assertAlmostEqual(f.x_mm, 99.0, delta=TOL_MM)
        self.assertAlmostEqual(f.w_mm, 99.0, delta=TOL_MM)

    # ── P3/P6 vollflächig (6-7) ───────────────────────────────────────────

    def test_p3_hintergrund_vollflaechig(self):
        f = self._f("P3 Hintergrund")
        self.assertAlmostEqual(f.x_mm, 198.0, delta=TOL_MM)
        self.assertAlmostEqual(f.y_mm, -3.0, delta=TOL_MM)
        self.assertAlmostEqual(f.w_mm, 102.0, delta=TOL_MM)
        self.assertAlmostEqual(f.h_mm, 216.0, delta=TOL_MM)

    def test_p6_hintergrund_vollflaechig(self):
        f = self._f("P6 Hintergrund")
        self.assertAlmostEqual(f.x_mm, 198.0, delta=TOL_MM)
        self.assertAlmostEqual(f.y_mm, -3.0, delta=TOL_MM)
        self.assertAlmostEqual(f.w_mm, 102.0, delta=TOL_MM)
        self.assertAlmostEqual(f.h_mm, 216.0, delta=TOL_MM)

    # ── P3↔P6 grüne-Klammer (8) ───────────────────────────────────────────

    def test_gruene_klammer_p3_p6_same_size(self):
        a = self._f("P3 Hintergrund")
        b = self._f("P6 Hintergrund")
        self.assertAlmostEqual(a.w_mm, b.w_mm, delta=TOL_MM)
        self.assertAlmostEqual(a.h_mm, b.h_mm, delta=TOL_MM)

    # ── P4 themen sub-layout mirror (9) ───────────────────────────────────
    # Issue #26: Thema 2 Photo shrunk to make room for restored Body —
    # photos no longer same height; share x and w only.

    def test_p4_themen_photos_share_x_and_width(self):
        a = self._f("P4 Thema 1 — Photo")
        b = self._f("P4 Thema 2 — Photo")
        self.assertAlmostEqual(a.x_mm, b.x_mm, delta=TOL_MM)
        self.assertAlmostEqual(a.w_mm, b.w_mm, delta=TOL_MM)

    # ── P5 themen sub-layout mirror (10) ──────────────────────────────────

    def test_p5_themen_photos_share_x_and_width(self):
        a = self._f("P5 Thema 3 — Photo")
        b = self._f("P5 Thema 4 — Photo")
        self.assertAlmostEqual(a.x_mm, b.x_mm, delta=TOL_MM)
        self.assertAlmostEqual(a.w_mm, b.w_mm, delta=TOL_MM)

    # ── Cross-panel themen photo widths uniform (11) ──────────────────────
    # Issue #26: heights now vary (Thema 1+3 are h=44 hero; Thema 2+4
    # h=24 to accommodate Body below). Width stays uniform across the
    # 4 themen for consistent column rhythm.

    def test_cross_panel_themen_photos_uniform_width(self):
        for an in (
            "P4 Thema 1 — Photo", "P4 Thema 2 — Photo",
            "P5 Thema 3 — Photo", "P5 Thema 4 — Photo",
        ):
            f = self._f(an)
            self.assertAlmostEqual(
                f.w_mm, THEMEN_PHOTO_W_MM, delta=TOL_MM,
                msg=f"{an} w_mm={f.w_mm} ≠ {THEMEN_PHOTO_W_MM}",
            )
        # Thema 1 + 3 share photo h=44 (the "hero" themen pair).
        for an in ("P4 Thema 1 — Photo", "P5 Thema 3 — Photo"):
            f = self._f(an)
            self.assertAlmostEqual(
                f.h_mm, THEMEN_PHOTO_H_MM, delta=TOL_MM,
                msg=f"{an} h_mm={f.h_mm} ≠ {THEMEN_PHOTO_H_MM}",
            )

    # ── Issue #26: parallel thema-panel structure (12b) ───────────────────

    def test_all_themen_have_body(self):
        """Every Thema-N must carry an Eyebrow + Headline + Photo + Body
        (parallel structure across the 4 themen). Issue #26 — Thema 2 +
        Thema 4 Bodies were missing on the post-#21 ship; this pins them
        so future regressions fail loud."""
        for n_str, panel in (("1", "P4"), ("2", "P4"),
                              ("3", "P5"), ("4", "P5")):
            for suffix in ("Eyebrow", "Headline", "Photo", "Body"):
                an = f"{panel} Thema {n_str} — {suffix}"
                self.assertIsNotNone(
                    self._f(an),
                    msg=f"{an} missing — every Thema-N must carry "
                        f"Eyebrow + Headline + Photo + Body",
                )

    def test_p2_body_backing_extends_to_top_band_and_bleed(self):
        """Issue #26 — P2 Body-Backing extends from y=28 (flush below
        Top-Band) to y=213 (full bleed bottom). Fixes the user-cited
        "Hellgrün bar misalignment with everything" by satisfying §7
        ("Typografie auf Grün") for the Teaser-Headline and matching the
        vertical extent of P1 Name-Card / P3 Hintergrund."""
        f = self._f("P2 Body-Backing")
        self.assertAlmostEqual(f.y_mm, 28.0, delta=TOL_MM,
            msg=f"P2 Body-Backing y_mm={f.y_mm} ≠ 28")
        self.assertAlmostEqual(f.y_mm + f.h_mm, 213.0, delta=TOL_MM,
            msg=f"P2 Body-Backing y_max={f.y_mm + f.h_mm} ≠ 213 (bleed)")

    # ── P6 column-symmetry mirrored_x at 247.5 (12) ───────────────────────

    def test_p6_columns_mirrored_at_axis(self):
        pairs = [
            ("P6 Adresse", "P6 Telefon"),
            ("P6 Email", "P6 Sprechtag"),
            ("P6 QR-Code (mitmachen)", "P6 QR-Code (termine)"),
        ]
        for left, right in pairs:
            l = self._f(left)
            r = self._f(right)
            l_center = l.x_mm + l.w_mm / 2.0
            r_center = r.x_mm + r.w_mm / 2.0
            midpoint = (l_center + r_center) / 2.0
            self.assertAlmostEqual(
                midpoint, AXIS_P6_CENTER_X_MM, delta=TOL_MM,
                msg=f"{left}/{right} mirror midpoint {midpoint} ≠ "
                    f"{AXIS_P6_CENTER_X_MM}",
            )

    # ── P6 baseline same_y (13) ───────────────────────────────────────────

    def test_p6_baseline_same_y(self):
        # Row 1: Adresse + Telefon
        a = self._f("P6 Adresse")
        b = self._f("P6 Telefon")
        self.assertAlmostEqual(a.y_mm, b.y_mm, delta=TOL_MM)
        # Row 2: Email + Sprechtag
        c = self._f("P6 Email")
        d = self._f("P6 Sprechtag")
        self.assertAlmostEqual(c.y_mm, d.y_mm, delta=TOL_MM)

    # ── Logo Print-Soll same_size on width (14) ───────────────────────────

    def test_logos_print_soll_same_width(self):
        p1 = self._f("P1 Logo Grüne (weiss)")
        p6 = self._f("P6 Logo Grüne (weiss)")
        self.assertAlmostEqual(p1.w_mm, 38.0, delta=TOL_MM)
        self.assertAlmostEqual(p6.w_mm, 38.0, delta=TOL_MM)
        self.assertAlmostEqual(p1.w_mm, p6.w_mm, delta=TOL_MM)

    # ── P2 Logo absent — V1 deletion (15) ─────────────────────────────────

    def test_p2_logo_absent(self):
        for an in self.items_by_anname.keys():
            self.assertFalse(
                an.startswith("P2 Logo"),
                f"V0 'P2 Logo (klein)' must be deleted in V1; found: {an}",
            )

    # ── Falz LAYER integrity via lxml XPath (16) ──────────────────────────

    def test_falz_layer_integrity_lxml(self):
        falz_pageobjects = self.doc_xml.xpath('//PAGEOBJECT[@LAYER="3"]')
        self.assertEqual(
            len(falz_pageobjects), 4,
            f"LAYER=3 must contain exactly 4 fold lines (2 per page); got "
            f"{[p.attrib.get('ANNAME') for p in falz_pageobjects]}",
        )
        falz_annames = {p.attrib.get("ANNAME") for p in falz_pageobjects}
        self.assertEqual(
            falz_annames,
            {"Falz x=99 (Front)", "Falz x=198 (Front)",
             "Falz x=99 (Back)", "Falz x=198 (Back)"},
            "Falz LAYER spillover: only the 4 fold lines may live here",
        )

    # ── ParaStyle existence: 16 falzflyer/* (17) ──────────────────────────

    def test_para_style_count_16(self):
        styles = {s.attrib.get("NAME", "") for s in self.doc_xml.findall("STYLE")}
        falzflyer_styles = {s for s in styles if s.startswith("falzflyer/")}
        self.assertEqual(
            len(falzflyer_styles), 16,
            f"V1 expects 16 falzflyer/* styles, got {len(falzflyer_styles)}: "
            f"{sorted(falzflyer_styles)}",
        )
        for needed in (
            "falzflyer/cand-name", "falzflyer/slogan",
            "falzflyer/slogan-on-green", "falzflyer/teaser-headline",
            "falzflyer/teaser-body", "falzflyer/thema-headline",
            "falzflyer/thema-body", "falzflyer/themen-eyebrow",
            "falzflyer/top-title", "falzflyer/quote-on-green",
            "falzflyer/closer-headline", "falzflyer/closer-datum",
            "falzflyer/closer-url", "falzflyer/contact-headline",
            "falzflyer/contact-body", "falzflyer/impressum",
        ):
            self.assertIn(needed, falzflyer_styles,
                          f"missing ParaStyle: {needed}")

    # ── teaser-body align=0 contract (mutation only on fcolor) (18) ───────

    def test_teaser_body_align_zero_contract(self):
        doc = self._mod.build_template()
        ps = doc._extra_para_styles.get("falzflyer/teaser-body")
        self.assertIsNotNone(ps, "falzflyer/teaser-body missing")
        self.assertEqual(
            ps.align, 0,
            "teaser-body align=0 is contract (redaktioneller Charakter); "
            "V1 mutation is fcolor only (Black->White)",
        )
        self.assertEqual(ps.fcolor, "White",
                         "teaser-body fcolor must be White in V1")

    # ── M-Basis-rule regression on all 5 V1 templates (parametric) (19) ──

    def test_m_basis_rule_all_v1_templates(self):
        # Find the registered brand:logo_size_3M rule from the canonical
        # registry (avoids hand-instantiating a frozen dataclass).
        from sla_lib.builder.brand_constraints import (  # noqa: E402
            BRAND_CONSTRAINTS,
        )
        rule = next(
            (r for r in BRAND_CONSTRAINTS if r.id == "brand:logo_size_3M"),
            None,
        )
        self.assertIsNotNone(rule, "brand:logo_size_3M rule not registered")
        v1_slugs = (
            "wahlaufruf-postkarte-a6-quer",
            "wahltag-tueranhaenger",
            "themen-plakat-a3-quer",
            "infostand-tent-card-a5-quer",
            "kandidat-falzflyer-din-lang",
        )
        for slug in v1_slugs:
            with self.subTest(template=slug):
                mod = _load_build_module(slug)
                doc = mod.build_doc()
                primitives = [
                    it for page in doc.pages for it in page.items
                ]
                violations = rule.check(primitives, doc)
                self.assertEqual(
                    len(violations), 0,
                    f"{slug}: M-Basis rule violations: {violations}",
                )

    # ── P3 Top-Title fcolor='Gelb' override (20) ──────────────────────────

    def test_p3_top_title_fcolor_gelb(self):
        f = self._f("P3 Top-Title")
        # Per-frame fcolor override applied via TextFrame.fcolor field
        self.assertEqual(
            getattr(f, "fcolor", None), "Gelb",
            f"P3 Top-Title must carry fcolor='Gelb' override (per spec L78); "
            f"got {getattr(f, 'fcolor', None)}",
        )
        # Also check the frame is positioned within the Top-Band band
        # (y < 28 — within the 31mm band).
        self.assertLess(
            f.y_mm + f.h_mm, 28.0,
            f"P3 Top-Title must sit within Top-Band (bottom edge < 28mm); "
            f"got y={f.y_mm} h={f.h_mm}",
        )

    # ── INJECT_MAP frame annames + lib_id mapping (21) ────────────────────

    def test_inject_map_frame_anname_mapping(self):
        expected = {
            "P1 Kandidat-Portrait":  "portrait_maria",
            "P4 Thema 1 — Photo":    "themen_klimaschutz_solar",
            "P4 Thema 2 — Photo":    "themen_soziales_kaffeehaus",
            "P5 Thema 3 — Photo":    "themen_bildung_volksschule",
            "P5 Thema 4 — Photo":    "themen_wirtschaft_handwerk",
        }
        self.assertEqual(
            dict(self._mod.INJECT_MAP), expected,
            "INJECT_MAP must map exactly the 5 V1 photo annames to their "
            "central library asset ids",
        )
        for anname in expected:
            self.assertIn(
                anname, self.items_by_anname,
                f"INJECT_MAP frame missing in build_template(): {anname}",
            )


if __name__ == "__main__":
    unittest.main()
