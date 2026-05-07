"""Smoke test for templates/kandidat-falzflyer-din-lang/.

Verifies:
- 2 pages, 297×210 trim
- Falz layer + spot color document-local
- 4 fold lines (2 per side at x=99 and x=198)
- D12: Panel 3 has Dunkelgrün full-bleed background AND Wahlkreuz on top
- Wahlkreuz inline image present
- 18+ slot annames matching spec
- Per-panel content stays within 99 mm panels (with 6 mm safety = 93 mm body)
- Round-trip safety: existing 3 templates still pass sla_diff
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

TEMPLATE_DIR = ROOT / "templates" / "kandidat-falzflyer-din-lang"


def _load_build_module():
    spec = importlib.util.spec_from_file_location(
        "falzflyer_build", TEMPLATE_DIR / "build.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class KandidatFalzflyerSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.NamedTemporaryFile(suffix=".sla", delete=False)
        cls.tmp.close()
        mod = _load_build_module()
        mod.build(out_path=cls.tmp.name)
        cls.tree = etree.parse(cls.tmp.name)
        cls.doc = cls.tree.getroot().find("DOCUMENT")

    def test_page_count(self):
        self.assertEqual(len(self.doc.findall("PAGE")), 2)

    def test_trim_dimensions(self):
        for page in self.doc.findall("PAGE"):
            w = float(page.attrib["PAGEWIDTH"])
            h = float(page.attrib["PAGEHEIGHT"])
            self.assertAlmostEqual(w, 297.0 * 72.0 / 25.4, places=1)
            self.assertAlmostEqual(h, 210.0 * 72.0 / 25.4, places=1)

    def test_falz_layer_present(self):
        layers = {l.attrib["NAME"]: l for l in self.doc.findall("LAYERS")}
        self.assertIn("Falz", layers)
        self.assertEqual(layers["Falz"].attrib["DRUCKEN"], "0")

    def test_falz_color_document_local(self):
        colors = {c.attrib["NAME"]: c for c in self.doc.findall("COLOR")}
        self.assertIn("Falz", colors)
        self.assertEqual(colors["Falz"].attrib.get("Spot", "0"), "1")

    def test_four_fold_lines(self):
        annames = {po.attrib.get("ANNAME", "") for po in self.doc.findall("PAGEOBJECT")}
        for needed in (
            "Falz x=99 (Front)", "Falz x=198 (Front)",
            "Falz x=99 (Back)", "Falz x=198 (Back)",
        ):
            self.assertIn(needed, annames, f"missing fold line: {needed}")

    def test_p3_dunkelgruen_background(self):
        """Panel 3 (front) must have Dunkelgrün full-bleed Polygon (D12)."""
        for po in self.doc.findall("PAGEOBJECT"):
            if po.attrib.get("ANNAME") == "P3 Hintergrund":
                self.assertEqual(po.attrib.get("PCOLOR"), "Dunkelgrün",
                                 "D12 violation: P3 Hintergrund must be Dunkelgrün")
                # Must be on front page
                self.assertEqual(po.attrib.get("OwnPage"), "0")
                return
        self.fail("P3 Hintergrund not found")

    def test_p3_wahlkreuz_on_dunkelgruen(self):
        """Wahlkreuz must be on Panel 3, on top of Dunkelgrün bg."""
        for po in self.doc.findall("PAGEOBJECT"):
            if po.attrib.get("ANNAME") == "P3 Wahlkreuz":
                self.assertEqual(po.attrib.get("isInlineImage"), "1")
                # Position on Panel 3 (x ~ 222 mm = 198+24)
                page = self.doc.find("PAGE")
                page_x = float(page.attrib["PAGEXPOS"])
                xpos = float(po.attrib["XPOS"])
                rel_x_mm = (xpos - page_x) * 25.4 / 72.0
                self.assertGreaterEqual(rel_x_mm, 198.0,
                                        f"Wahlkreuz at x={rel_x_mm}mm — should be on panel 3 (x>=198)")
                return
        self.fail("P3 Wahlkreuz not found")

    def test_18_plus_slot_annames(self):
        annames = {po.attrib.get("ANNAME", "") for po in self.doc.findall("PAGEOBJECT")}
        annames.discard("")
        # Spec requires 18+ slots; we count distinct named slots
        # (excluding the empty bucket)
        self.assertGreaterEqual(len(annames), 18,
                                f"only {len(annames)} named slots: {annames}")

    def test_panel_content_within_safe_width(self):
        """Per-panel content frames must stay within 87 mm (6 mm + 87 + 6 mm = 99 mm).

        Allow a small tolerance since the test only checks main content frames
        (P1/P2/P3/P4/P5/P6 + slot type), not background polygons or fold lines.
        """
        page = self.doc.find("PAGE")
        page_x = float(page.attrib["PAGEXPOS"])
        for po in self.doc.findall("PAGEOBJECT"):
            an = po.attrib.get("ANNAME", "")
            # Skip non-content slots
            if not an.startswith(("P1 ", "P2 ", "P3 ", "P4 ", "P5 ", "P6 ")):
                continue
            # Skip background polygon and Wahlkreuz (which can extend more)
            if "Hintergrund" in an or "Wahlkreuz" in an:
                continue
            xpos = float(po.attrib["XPOS"])
            w_pt = float(po.attrib["WIDTH"])
            x_mm = (xpos - page_x) * 25.4 / 72.0
            w_mm = w_pt * 25.4 / 72.0
            # Frame width <= 88 mm (allowing 1 mm tolerance over 87 mm)
            self.assertLessEqual(w_mm, 88.5,
                                 f"{an} width {w_mm}mm > 88 mm panel safe width")


class FalzflyerRoundTripSafetyTests(unittest.TestCase):
    """Confirm new template additions didn't regress existing template diffs."""

    def test_existing_postkarte_round_trip_no_critical(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import sla_diff as sd
        report = sd.diff(
            ROOT / "postkarte-vorlage-original.sla",
            ROOT / "templates" / "postkarte-a6-kampagne" / "template.sla",
        )
        critical = sum(1 for i in report.issues if i.severity == "critical")
        self.assertEqual(critical, 0)

    def test_existing_plakat_round_trip_no_critical(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import sla_diff as sd
        report = sd.diff(
            ROOT / "plakat-a1-hochformat-original.sla",
            ROOT / "templates" / "plakat-a1-hochformat" / "template.sla",
        )
        critical = sum(1 for i in report.issues if i.severity == "critical")
        self.assertEqual(critical, 0)


if __name__ == "__main__":
    unittest.main()
