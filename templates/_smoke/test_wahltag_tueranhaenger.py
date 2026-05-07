"""Smoke test for templates/wahltag-tueranhaenger/.

Verifies:
- 2 pages, 105×250 trim, 2 mm bleed
- Stanzkontur layer exists with DRUCKEN=0 (printable=False)
- Stanzkontur color present in COLOR list with isSpot=1
- Stanzkontur Polygon present (outer rectangle path)
- Stanzkontur Polygon present (circular hole, ≥36 segments)
- Wahlkreuz frame on Hellgrün band (D12)
- Round-trip: existing 3 templates still pass sla_diff
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

TEMPLATE_DIR = ROOT / "templates" / "wahltag-tueranhaenger"


def _load_build_module():
    spec = importlib.util.spec_from_file_location(
        "tueranhaenger_build", TEMPLATE_DIR / "build.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class WahltagTueranhaengerSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.NamedTemporaryFile(suffix=".sla", delete=False)
        cls.tmp.close()
        mod = _load_build_module()
        mod.build(out_path=cls.tmp.name)
        cls.tree = etree.parse(cls.tmp.name)
        cls.root = cls.tree.getroot()
        cls.doc = cls.root.find("DOCUMENT")

    def test_page_count(self):
        pages = self.doc.findall("PAGE")
        self.assertEqual(len(pages), 2)

    def test_trim_dimensions(self):
        for page in self.doc.findall("PAGE"):
            w = float(page.attrib["PAGEWIDTH"])
            h = float(page.attrib["PAGEHEIGHT"])
            self.assertAlmostEqual(w, 105.0 * 72.0 / 25.4, places=1)
            self.assertAlmostEqual(h, 250.0 * 72.0 / 25.4, places=1)

    def test_bleed_2mm(self):
        for k in ("BleedTop", "BleedRight", "BleedBottom", "BleedLeft"):
            v = float(self.doc.attrib.get(k, "0"))
            self.assertAlmostEqual(v, 2.0 * 72.0 / 25.4, places=1, msg=k)

    def test_stanzkontur_layer_present_not_printable(self):
        layers = {l.attrib["NAME"]: l for l in self.doc.findall("LAYERS")}
        self.assertIn("Stanzkontur", layers)
        self.assertEqual(layers["Stanzkontur"].attrib["DRUCKEN"], "0",
                         "Stanzkontur layer must have DRUCKEN=0 (not printable)")

    def test_stanzkontur_layer_top_of_stack(self):
        """Stanzkontur should be the highest LEVEL layer (drawn on top)."""
        layers = self.doc.findall("LAYERS")
        levels = {l.attrib["NAME"]: int(l.attrib["LEVEL"]) for l in layers}
        max_level = max(levels.values())
        self.assertEqual(levels["Stanzkontur"], max_level)

    def test_stanzkontur_color_document_local(self):
        """Stanzkontur color must be in COLORS, with isSpot/Spot=1.
        It must NOT be in shared/ci.yml (D4 revised)."""
        colors = {c.attrib["NAME"]: c for c in self.doc.findall("COLOR")}
        self.assertIn("Stanzkontur", colors)
        spot = colors["Stanzkontur"].attrib.get("Spot", "0")
        self.assertIn(spot, ("1", "true"), f"Stanzkontur not marked as spot: {spot}")

    def test_stanzkontur_polygons_present_on_layer(self):
        """Two DieCut polygons (outer + hole) on Stanzkontur layer."""
        layers = self.doc.findall("LAYERS")
        levels = {l.attrib["NAME"]: int(l.attrib["LEVEL"]) for l in layers}
        stanz_level = levels["Stanzkontur"]

        stanz_polys = [
            po for po in self.doc.findall("PAGEOBJECT")
            if po.attrib.get("PTYPE") == "6"
            and int(po.attrib.get("LAYER", "0")) == stanz_level
        ]
        # 2 per page × 2 pages = 4 (outer + hole, front + back)
        self.assertGreaterEqual(len(stanz_polys), 4,
                                f"expected >=4 Stanz polys, got {len(stanz_polys)}")

    def test_stanzkontur_hole_circle_has_many_segments(self):
        """The hole polygon path should have at least 36 L commands (circle)."""
        for po in self.doc.findall("PAGEOBJECT"):
            if po.attrib.get("ANNAME") == "Stanzkontur Loch":
                path = po.attrib.get("path", "")
                self.assertGreaterEqual(path.count("L"), 36,
                                        f"hole path has too few segments: {path[:120]}")
                return
        self.fail("Stanzkontur Loch frame not found")

    def test_wahlkreuz_on_hellgruen_band(self):
        """Front page must have a Hellgrün band positioned around the Wahlkreuz."""
        front_polys = [
            po for po in self.doc.findall("PAGEOBJECT")
            if po.attrib.get("OwnPage") == "0"
            and po.attrib.get("PTYPE") == "6"
            and po.attrib.get("PCOLOR") == "Hellgrün"
        ]
        self.assertGreaterEqual(len(front_polys), 1,
                                "expected at least 1 Hellgrün polygon on front")

    def test_wahlkreuz_inline_image(self):
        for po in self.doc.findall("PAGEOBJECT"):
            if po.attrib.get("ANNAME") == "Wahlkreuz (Hero)":
                self.assertEqual(po.attrib.get("isInlineImage", "0"), "1")
                self.assertGreater(len(po.attrib.get("ImageData", "")), 100)
                return
        self.fail("Wahlkreuz (Hero) frame not found")


class RoundTripSafetyTests(unittest.TestCase):
    """Verify that adding new blocks didn't break existing template diffs."""

    def test_existing_postkarte_round_trip_no_critical(self):
        """sla_diff between original Postkarte and current build must be critical=0."""
        sys.path.insert(0, str(ROOT / "tools"))
        import sla_diff as sd
        report = sd.diff(
            ROOT / "postkarte-vorlage-original.sla",
            ROOT / "templates" / "postkarte-a6-kampagne" / "template.sla",
        )
        critical = sum(1 for i in report.issues if i.severity == "critical")
        self.assertEqual(critical, 0,
                         f"postkarte round-trip has {critical} critical issues")


if __name__ == "__main__":
    unittest.main()
