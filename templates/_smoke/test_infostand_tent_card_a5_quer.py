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
        """Impressum frame must end at or before y=100 mm (3 mm clear of fold y=105)."""
        for po in self.doc.findall("PAGEOBJECT"):
            if po.attrib.get("ANNAME") == "Impressum (Tent)":
                page = self.doc.find("PAGE")
                page_y = float(page.attrib["PAGEYPOS"])
                ypos = float(po.attrib["YPOS"])
                h_pt = float(po.attrib["HEIGHT"])
                bottom_pt = ypos + h_pt - page_y
                bottom_mm = bottom_pt * 25.4 / 72.0
                self.assertLessEqual(bottom_mm, 102.0,
                                     f"Impressum bottom at y={bottom_mm}mm — must be <= 102 (3 mm clear of fold)")
                return
        self.fail("Impressum frame not found")


if __name__ == "__main__":
    unittest.main()
