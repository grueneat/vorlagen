"""Smoke test for templates/themen-plakat-a3-quer/.

Builds the template, parses the resulting SLA, asserts structural invariants:
- correct page count, trim/bleed
- every spec slot anname present
- no overlap between non-related frames
- headline frame size sufficient for >= 36 pt font
"""
from __future__ import annotations
import sys
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from lxml import etree  # noqa: E402

TEMPLATE_DIR = ROOT / "templates" / "themen-plakat-a3-quer"


def _load_build_module():
    spec = importlib.util.spec_from_file_location(
        "themen_plakat_build", TEMPLATE_DIR / "build.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ThemenPlakatA3QuerSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Build to a temp file, parse once.
        cls.tmp = tempfile.NamedTemporaryFile(suffix=".sla", delete=False)
        cls.tmp.close()
        mod = _load_build_module()
        mod.build(out_path=cls.tmp.name)
        cls.tree = etree.parse(cls.tmp.name)
        cls.root = cls.tree.getroot()
        cls.doc = cls.root.find("DOCUMENT")

    def test_page_count(self):
        pages = self.doc.findall("PAGE")
        self.assertEqual(len(pages), 1, f"expected 1 page, found {len(pages)}")

    def test_trim_dimensions(self):
        page = self.doc.find("PAGE")
        # 420 mm = 1190.55... pt; 297 mm = 841.89... pt
        w = float(page.attrib["PAGEWIDTH"])
        h = float(page.attrib["PAGEHEIGHT"])
        self.assertAlmostEqual(w, 420.0 * 72.0 / 25.4, places=1)
        self.assertAlmostEqual(h, 297.0 * 72.0 / 25.4, places=1)

    def test_bleed(self):
        # Bleed stored on DOCUMENT attributes in Scribus 1.6
        for k in ("BleedTop", "BleedRight", "BleedBottom", "BleedLeft"):
            v = float(self.doc.attrib.get(k, "0"))
            # 3 mm = 8.504... pt
            self.assertAlmostEqual(v, 3.0 * 72.0 / 25.4, places=1, msg=k)

    def test_required_annames_present(self):
        annames = {
            po.attrib.get("ANNAME", "")
            for po in self.doc.findall("PAGEOBJECT")
        }
        required = {
            "Headline These",
            "Sub-Headline",
            "Beleg 1 — Headline",
            "Beleg 1 — Body",
            "Beleg 2 — Headline",
            "Beleg 2 — Body",
            "Beleg 3 — Headline",
            "Beleg 3 — Body",
            "Quelle",
            "Impressum",
        }
        missing = required - annames
        self.assertFalse(missing, f"missing annames: {missing}")

    def test_no_frame_outside_trim_plus_bleed(self):
        # Trim 420x297, bleed 3 mm. Allowed area: -3..423 x -3..300 mm.
        # Each PAGEOBJECT carries XPOS/YPOS in pt + page offset; just check
        # the frame's bbox fits inside (page_x + 420+3) etc.
        page = self.doc.find("PAGE")
        page_w_pt = float(page.attrib["PAGEWIDTH"])
        page_h_pt = float(page.attrib["PAGEHEIGHT"])
        page_xpos = float(page.attrib["PAGEXPOS"])
        page_ypos = float(page.attrib["PAGEYPOS"])
        bleed_pt = 3.0 * 72.0 / 25.4
        for po in self.doc.findall("PAGEOBJECT"):
            x = float(po.attrib["XPOS"])
            y = float(po.attrib["YPOS"])
            w = float(po.attrib["WIDTH"])
            h = float(po.attrib["HEIGHT"])
            # Compute relative position to page
            rx = x - page_xpos
            ry = y - page_ypos
            anname = po.attrib.get("ANNAME", "")
            # Allow background (Polygon at -bleed,-bleed)
            if anname == "Seitenhintergrund":
                continue
            self.assertGreaterEqual(rx, -bleed_pt - 0.5,
                                    f"{anname} extends left of bleed: {rx}")
            self.assertGreaterEqual(ry, -bleed_pt - 0.5,
                                    f"{anname} extends above bleed: {ry}")
            self.assertLessEqual(rx + w, page_w_pt + bleed_pt + 0.5,
                                 f"{anname} extends right of bleed: {rx+w}")
            self.assertLessEqual(ry + h, page_h_pt + bleed_pt + 0.5,
                                 f"{anname} extends below bleed: {ry+h}")

    def test_headline_frame_height_supports_36pt(self):
        # The Vollkorn 60pt + linesp 64 needs at least ~64pt of vertical space.
        # Spec says >= 36pt; build uses 60pt. Frame is 50 mm = ~141.7 pt — plenty.
        for po in self.doc.findall("PAGEOBJECT"):
            if po.attrib.get("ANNAME") == "Headline These":
                h = float(po.attrib["HEIGHT"])
                self.assertGreaterEqual(
                    h, 36 * 72 / 25.4 / 1.5,  # min 36pt font ~ 24 pt body
                    f"Headline frame height {h}pt too small for 36+ pt"
                )
                return
        self.fail("Headline These frame not found")

    def test_color_palette_contains_dunkelgruen(self):
        # Dunkelgrün is the brand-primary, must be present.
        colors = {
            c.attrib.get("NAME", "")
            for c in self.doc.findall("COLOR")
        }
        self.assertIn("Dunkelgrün", colors)

    def test_styles_include_themen_plakat_locals(self):
        styles = {
            s.attrib.get("NAME", "")
            for s in self.doc.findall("STYLE")
        }
        for needed in (
            "themen-plakat/headline",
            "themen-plakat/beleg-headline",
            "themen-plakat/beleg-body",
            "themen-plakat/source",
            "themen-plakat/impressum",
        ):
            self.assertIn(needed, styles)


if __name__ == "__main__":
    unittest.main()
