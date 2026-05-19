"""Smoke test for templates/infostand-tent-card-a5-quer/.

Verifies:
- 1 page, 297×210 trim
- Falz layer present, document-local Falz spot color
- Mittelfalz polygon at y=105
- 4 main text frames (Headline A, Body A, Headline B, Body B)
- Panel B frames have rotation_deg=180
"""
from __future__ import annotations
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from lxml import etree  # noqa: E402

TEMPLATE_DIR = ROOT / "templates" / "infostand-tent-card-a5-quer"


def _load_build_module():
    spec = importlib.util.spec_from_file_location(
        "tent_build", TEMPLATE_DIR / "build.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class InfostandTentCardSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.NamedTemporaryFile(suffix=".sla", delete=False)
        cls.tmp.close()
        mod = _load_build_module()
        mod.build(out_path=cls.tmp.name)
        cls.tree = etree.parse(cls.tmp.name)
        cls.doc = cls.tree.getroot().find("DOCUMENT")

    def test_page_count(self):
        self.assertEqual(len(self.doc.findall("PAGE")), 1)

    def test_trim_dimensions(self):
        page = self.doc.find("PAGE")
        w = float(page.attrib["PAGEWIDTH"])
        h = float(page.attrib["PAGEHEIGHT"])
        self.assertAlmostEqual(w, 297.0 * 72.0 / 25.4, places=1)
        self.assertAlmostEqual(h, 210.0 * 72.0 / 25.4, places=1)

    def test_falz_layer_present_not_printable(self):
        layers = {l.attrib["NAME"]: l for l in self.doc.findall("LAYERS")}
        self.assertIn("Falz", layers)
        self.assertEqual(layers["Falz"].attrib["DRUCKEN"], "0")

    def test_falz_color_document_local_spot(self):
        colors = {c.attrib["NAME"]: c for c in self.doc.findall("COLOR")}
        self.assertIn("Falz", colors)
        self.assertEqual(colors["Falz"].attrib.get("Spot", "0"), "1")

    def test_mittelfalz_polygon_at_y_105(self):
        for po in self.doc.findall("PAGEOBJECT"):
            if po.attrib.get("ANNAME") == "Mittelfalz (horizontal)":
                # YPOS = page_y_origin + 105*72/25.4
                page = self.doc.find("PAGE")
                page_y = float(page.attrib["PAGEYPOS"])
                ypos = float(po.attrib["YPOS"])
                rel_y_pt = ypos - page_y
                rel_y_mm = rel_y_pt * 25.4 / 72.0
                self.assertAlmostEqual(rel_y_mm, 105.0, places=1)
                # Width should span full 297 mm
                w_pt = float(po.attrib["WIDTH"])
                self.assertAlmostEqual(w_pt * 25.4 / 72.0, 297.0, places=1)
                return
        self.fail("Mittelfalz polygon not found")

    def test_four_main_text_frames_present(self):
        annames = {po.attrib.get("ANNAME", "") for po in self.doc.findall("PAGEOBJECT")}
        for needed in ("Headline Panel A", "Body Panel A",
                       "Headline Panel B", "Body Panel B"):
            self.assertIn(needed, annames)

    def test_panel_b_frames_rotated_180(self):
        for po in self.doc.findall("PAGEOBJECT"):
            an = po.attrib.get("ANNAME", "")
            if an in ("Headline Panel B", "Body Panel B"):
                rot = float(po.attrib.get("ROT", "0"))
                self.assertAlmostEqual(rot, 180.0, places=1,
                                       msg=f"{an} not rotated 180°")

    def test_panel_a_frames_not_rotated(self):
        for po in self.doc.findall("PAGEOBJECT"):
            an = po.attrib.get("ANNAME", "")
            if an in ("Headline Panel A", "Body Panel A"):
                rot = float(po.attrib.get("ROT", "0"))
                self.assertAlmostEqual(rot, 0.0, places=1,
                                       msg=f"{an} unexpectedly rotated")

    def test_impressum_above_fold(self):
        """Impressum sits inside Footer-Strip Panel A which extends to apex y=105;
        bound relaxed in V1 (Hero Band)."""
        for po in self.doc.findall("PAGEOBJECT"):
            if po.attrib.get("ANNAME") == "Impressum (Tent)":
                page = self.doc.find("PAGE")
                page_y = float(page.attrib["PAGEYPOS"])
                ypos = float(po.attrib["YPOS"])
                h_pt = float(po.attrib["HEIGHT"])
                bottom_pt = ypos + h_pt - page_y
                bottom_mm = bottom_pt * 25.4 / 72.0
                self.assertLessEqual(bottom_mm, 105.0,
                                     f"Impressum bottom at y={bottom_mm}mm — must be <= 105 (apex)")
                return
        self.fail("Impressum frame not found")

    # ── V1 "Hero Band" structural assertions (#20 locked decision #11) ──

    def _po_by_anname(self, anname: str):
        for po in self.doc.findall("PAGEOBJECT"):
            if po.attrib.get("ANNAME") == anname:
                return po
        return None

    def test_hero_band_polygons_present(self):
        """Both Hero-Band polygons present, Dunkelgrün, on Hintergrund layer."""
        for an in ("Hero-Band Panel A", "Hero-Band Panel B"):
            po = self._po_by_anname(an)
            self.assertIsNotNone(po, f"{an} polygon missing")
            self.assertEqual(po.attrib.get("PCOLOR"), "Dunkelgrün",
                             f"{an} fill not Dunkelgrün: {po.attrib.get('PCOLOR')}")
            self.assertEqual(po.attrib.get("LAYER"), "0",
                             f"{an} not on LAYER=0 (Hintergrund)")

    def test_photo_backing_polygons_present(self):
        """Both Photo-Backing polygons present, Dunkelgrün, on Hintergrund layer."""
        for an in ("Photo-Backing Panel A", "Photo-Backing Panel B"):
            po = self._po_by_anname(an)
            self.assertIsNotNone(po, f"{an} polygon missing")
            self.assertEqual(po.attrib.get("PCOLOR"), "Dunkelgrün",
                             f"{an} fill not Dunkelgrün")
            self.assertEqual(po.attrib.get("LAYER"), "0",
                             f"{an} not on LAYER=0 (Hintergrund)")

    def test_footer_strip_polygons_present(self):
        """Both Footer-Strip polygons present, Hellgrün, on Hintergrund layer."""
        for an in ("Footer-Strip Panel A", "Footer-Strip Panel B"):
            po = self._po_by_anname(an)
            self.assertIsNotNone(po, f"{an} polygon missing")
            self.assertEqual(po.attrib.get("PCOLOR"), "Hellgrün",
                             f"{an} fill not Hellgrün")
            self.assertEqual(po.attrib.get("LAYER"), "0",
                             f"{an} not on LAYER=0 (Hintergrund)")

    def test_payoff_panel_a_present(self):
        """Pay-off Panel A text frame present with tent/payoff style reference."""
        po = self._po_by_anname("Pay-off Panel A")
        self.assertIsNotNone(po, "Pay-off Panel A frame missing")
        # Text frame: paragraph-style PARENT attribute lives on
        # StoryText/DefaultStyle (and may also appear on inner para elements).
        styles = set()
        for default_style in po.iter("DefaultStyle"):
            ps = default_style.attrib.get("PARENT")
            if ps:
                styles.add(ps)
        for para in po.iter("para"):
            ps = para.attrib.get("PARENT")
            if ps:
                styles.add(ps)
        self.assertIn("tent/payoff", styles,
                      f"Pay-off Panel A does not reference tent/payoff style; saw {styles}")

    def test_logo_asset_is_gruene_weiss(self):
        """Logo Grüne (panel A) inline image data is the gruene-weiss.png asset.

        Verification path: load the canonical asset, base64-encode + zlib-compress
        via pack_inline_image, compare the resulting payload to the SLA's
        ImageData attribute. Stable identity check that does not depend on
        SLA emitter encoding details beyond pack_inline_image's contract.
        """
        po = self._po_by_anname("Logo Grüne (panel A)")
        self.assertIsNotNone(po, "Logo Grüne (panel A) frame missing")
        sla_data = po.attrib.get("ImageData", "")
        self.assertGreater(len(sla_data), 1000,
                           "Logo inline image data implausibly small (asset missing?)")
        # Recompute from canonical asset and compare.
        from sla_lib.builder import pack_inline_image
        canonical_path = ROOT / "shared" / "logos" / "gruene-weiss.png"
        self.assertTrue(canonical_path.exists(),
                        f"canonical asset missing: {canonical_path}")
        expected_data, expected_ext = pack_inline_image(
            canonical_path.read_bytes(), "png"
        )
        self.assertEqual(po.attrib.get("inlineImageExt"), expected_ext,
                         "Logo extension mismatch")
        self.assertEqual(sla_data, expected_data,
                         "Logo inline image data does not match gruene-weiss.png")

    def test_falz_layer_integrity(self):
        """LAYER=3 is exclusive to Mittelfalz (horizontal); no V1 polygon leaks
        onto the Falz spot-color layer (per pitfall P13 / locked decision #13).
        """
        falz_pageobjects = [
            po for po in self.doc.findall("PAGEOBJECT")
            if po.attrib.get("LAYER") == "3"
        ]
        self.assertEqual(len(falz_pageobjects), 1,
                         f"Expected exactly 1 PAGEOBJECT on LAYER=3, got "
                         f"{len(falz_pageobjects)}: "
                         f"{[p.attrib.get('ANNAME') for p in falz_pageobjects]}")
        self.assertEqual(falz_pageobjects[0].attrib.get("ANNAME"),
                         "Mittelfalz (horizontal)",
                         "LAYER=3 PAGEOBJECT is not Mittelfalz (horizontal)")


if __name__ == "__main__":
    unittest.main()
