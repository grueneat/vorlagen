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

    # ── Issue #27: 1-thema-per-panel layout ──────────────────────────────
    # P4 has Thema 1 only; P5 has Thema 3 only. Trenner polygons +
    # Thema 2 + Thema 4 are removed. Each remaining thema has a full-
    # bleed photo + longer body text.

    def test_p4_thema1_photo_full_bleed(self):
        f = self._f("P4 Thema 1 — Photo")
        self.assertAlmostEqual(f.x_mm, -3.0, delta=TOL_MM,
            msg=f"P4 Thema 1 Photo x={f.x_mm} ≠ -3 (outer bleed)")
        self.assertAlmostEqual(f.x_mm + f.w_mm, 99.0, delta=TOL_MM,
            msg=f"P4 Thema 1 Photo right={f.x_mm + f.w_mm} ≠ 99 (Falz)")

    def test_p5_thema3_photo_full_panel_width(self):
        f = self._f("P5 Thema 3 — Photo")
        self.assertAlmostEqual(f.x_mm, 99.0, delta=TOL_MM,
            msg=f"P5 Thema 3 Photo x={f.x_mm} ≠ 99 (left Falz)")
        self.assertAlmostEqual(f.x_mm + f.w_mm, 198.0, delta=TOL_MM,
            msg=f"P5 Thema 3 Photo right={f.x_mm + f.w_mm} ≠ 198 (right Falz)")

    def test_cross_panel_themen_photos_uniform_height(self):
        a = self._f("P4 Thema 1 — Photo")
        b = self._f("P5 Thema 3 — Photo")
        self.assertAlmostEqual(a.h_mm, b.h_mm, delta=TOL_MM,
            msg=f"P4/P5 Thema photos heights differ: {a.h_mm} vs {b.h_mm}")
        self.assertAlmostEqual(a.y_mm, b.y_mm, delta=TOL_MM,
            msg="P4/P5 Thema photos y-baseline drifts")

    def test_p4_p5_themen_have_body(self):
        """P4 Thema 1 + P5 Thema 3 each carry Eyebrow + Headline + Photo
        + Body (1-thema-per-panel layout per Issue #27). Pins the
        single-thema structure so the prior 4-thema asymmetry doesn't
        regress."""
        for n_str, panel in (("1", "P4"), ("3", "P5")):
            for suffix in ("Eyebrow", "Headline", "Photo", "Body"):
                an = f"{panel} Thema {n_str} — {suffix}"
                self.assertIsNotNone(
                    self._f(an),
                    msg=f"{an} missing — single-thema panel must carry "
                        f"Eyebrow + Headline + Photo + Body",
                )

    def test_thema_2_and_4_removed(self):
        """Issue #27: Thema 2 + Thema 4 (the second thema per panel)
        were removed in favour of one richer thema per panel. Pins
        their absence so future edits don't accidentally reintroduce
        them as half-empty stubs."""
        for an in ("P4 Thema 2 — Eyebrow", "P4 Thema 2 — Headline",
                   "P4 Thema 2 — Photo", "P4 Thema 2 — Body",
                   "P5 Thema 4 — Eyebrow", "P5 Thema 4 — Headline",
                   "P5 Thema 4 — Photo", "P5 Thema 4 — Body",
                   "P4 Thema 1·2 Trenner", "P5 Thema 3·4 Trenner"):
            self.assertIsNone(
                self.items_by_anname.get(an),
                msg=f"{an!r} should be removed (Issue #27 1-thema layout)",
            )

    def test_p1_kandidat_portrait_full_panel_width(self):
        """Issue #27: P1 Portrait fills the entire panel between the
        left bleed and the right Falz. User-cited "profile image still
        does not fill the whole width" fix."""
        f = self._f("P1 Kandidat-Portrait")
        self.assertAlmostEqual(f.x_mm, -3.0, delta=TOL_MM,
            msg=f"P1 Portrait x={f.x_mm} ≠ -3 (outer bleed)")
        self.assertAlmostEqual(f.x_mm + f.w_mm, 99.0, delta=TOL_MM,
            msg=f"P1 Portrait right={f.x_mm + f.w_mm} ≠ 99 (Falz)")

    def test_logos_use_bund_brushstroke_asset(self):
        """Issue #27: P1 + P6 logos must use gruene-logo-bund-weiss.png
        (the actual G-brushstroke logo, white version) — not the
        gruene-weiss.png wordmark which letterboxes and reads as "just
        Die Grünen text"."""
        from pathlib import Path
        expected = (Path(__file__).resolve().parents[3] / "shared" /
                    "logos" / "gruene-logo-bund-weiss.png")
        self.assertTrue(expected.exists(),
            msg=f"Required brand asset missing at {expected}")
        wordmark = (Path(__file__).resolve().parents[3] / "shared" /
                    "logos" / "gruene-weiss.png")
        # Logos are inlined; assert the inlined bytes match the bund
        # asset, NOT the wordmark.
        for an in ("P1 Logo Grüne (weiss)", "P6 Logo Grüne (weiss)"):
            f = self._f(an)
            self.assertIsNotNone(f, msg=f"{an} missing")
            from sla_lib.builder.primitives import pack_inline_image
            expected_data, _ = pack_inline_image(expected.read_bytes(), "png")
            wordmark_data, _ = pack_inline_image(wordmark.read_bytes(), "png")
            self.assertEqual(
                f.inline_image_data, expected_data,
                msg=f"{an} inline data does not match gruene-logo-bund-weiss.png",
            )
            self.assertNotEqual(
                f.inline_image_data, wordmark_data,
                msg=f"{an} still uses the gruene-weiss.png wordmark "
                    f"(should be the brushstroke G).",
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

    # ── ParaStyle existence: 17 falzflyer/* (17) ──────────────────────────
    # Issue #27 added falzflyer/schlagwort for the P2 Hellgrün backing
    # slogans (replaces long Teaser-Body paragraph). Count 16 → 17.

    def test_para_style_count_17(self):
        styles = {s.attrib.get("NAME", "") for s in self.doc_xml.findall("STYLE")}
        falzflyer_styles = {s for s in styles if s.startswith("falzflyer/")}
        self.assertEqual(
            len(falzflyer_styles), 17,
            f"V1.1 expects 17 falzflyer/* styles, got "
            f"{len(falzflyer_styles)}: {sorted(falzflyer_styles)}",
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
            "falzflyer/schlagwort",
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
        # Issue #27: 1-thema-per-panel — INJECT_MAP shrinks from 5 to 3
        # entries (Portrait + P4 Thema 1 + P5 Thema 3).
        expected = {
            "P1 Kandidat-Portrait":  "portrait_maria",
            "P4 Thema 1 — Photo":    "themen_klimaschutz_solar",
            "P5 Thema 3 — Photo":    "themen_bildung_volksschule",
        }
        self.assertEqual(
            dict(self._mod.INJECT_MAP), expected,
            "INJECT_MAP must map exactly the 3 V1.1 photo annames to "
            "their central library asset ids",
        )
        for anname in expected:
            self.assertIn(
                anname, self.items_by_anname,
                f"INJECT_MAP frame missing in build_template(): {anname}",
            )


if __name__ == "__main__":
    unittest.main()
