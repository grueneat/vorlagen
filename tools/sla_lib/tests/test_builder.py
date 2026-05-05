"""Smoke tests for the DSL builder package.

Verifies that:
- Document → Page → save() emits valid Scribus 1.6 SLA XML
- The emitted SLA can be parsed back through SLADocument
- Brand colors and styles round-trip correctly
- Frame primitives produce correct PAGEOBJECT attributes
"""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib import SLADocument  # noqa: E402
from sla_lib.builder import (  # noqa: E402
    Document, Color, Style, TextFrame, ImageFrame, Polygon, Line,
)


class DocumentTests(unittest.TestCase):
    def test_empty_a6_document(self):
        doc = Document(title="Test", template_id="empty-a6")
        doc.add_page(size="A6", orientation="portrait", bleed_mm=3)
        with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
            doc.save(t.name)
            parsed = SLADocument(t.name)
        self.assertEqual(parsed.version, "1.6.5")
        self.assertEqual(parsed.page_count, 1)
        w, h = parsed.page_size_pt
        self.assertAlmostEqual(w, 297.638, places=2)
        self.assertAlmostEqual(h, 419.528, places=2)

    def test_brand_colors_present(self):
        doc = Document(title="x", template_id="x")
        doc.add_page(size="A6")
        with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
            doc.save(t.name)
            parsed = SLADocument(t.name)
        # All brand colors should be in the COLOR list
        colors = [c.attrib.get("NAME") for c in parsed.doc.findall("COLOR")]
        for required in ("Black", "White", "Dunkelgrün", "Hellgrün", "Gelb", "Magenta"):
            self.assertIn(required, colors)

    def test_styles_present_with_inheritance(self):
        doc = Document(title="x", template_id="x")
        doc.add_page(size="A6")
        with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
            doc.save(t.name)
            parsed = SLADocument(t.name)
        styles = parsed.doc.findall("STYLE")
        names = [s.attrib.get("NAME") for s in styles]
        for required in ("ci/default", "ci/headline-ultra", "ci/body-12",
                         "ci/impressum", "ci/stoerer", "ci/cta"):
            self.assertIn(required, names)
        # Check parent inheritance
        for s in styles:
            if s.attrib.get("NAME") == "ci/headline-ultra":
                self.assertEqual(s.attrib.get("PARENT"), "ci/default")
                break
        else:
            self.fail("ci/headline-ultra not found")

    def test_layers_default_stack(self):
        doc = Document(title="x", template_id="x")
        doc.add_page(size="A6")
        with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
            doc.save(t.name)
            parsed = SLADocument(t.name)
        layers = parsed.doc.findall("LAYERS")
        names = [l.attrib.get("NAME") for l in layers]
        self.assertEqual(names, ["Hintergrund", "Bilder", "Text", "Hilfslinien"])
        # Hilfslinien should be hidden + non-printable
        for l in layers:
            if l.attrib.get("NAME") == "Hilfslinien":
                self.assertEqual(l.attrib.get("SICHTBAR"), "0")
                self.assertEqual(l.attrib.get("DRUCKEN"), "0")


class PrimitivesTests(unittest.TestCase):
    def test_textframe_emits_pageobject(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(TextFrame(x_mm=10, y_mm=10, w_mm=80, h_mm=20,
                           text="hello", style=Style.BODY_12,
                           anname="test-text"))
        with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
            doc.save(t.name)
            parsed = SLADocument(t.name)
        objs = parsed.page_objects()
        self.assertEqual(len(objs), 1)
        o = objs[0]
        self.assertEqual(o.attrib.get("PTYPE"), "4")
        self.assertEqual(o.attrib.get("ANNAME"), "test-text")
        # Story text content
        story = o.find("StoryText")
        itexts = story.findall("ITEXT")
        self.assertEqual(itexts[0].attrib.get("CH"), "hello")

    def test_polygon_emits_with_fill(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(Polygon(x_mm=0, y_mm=0, w_mm=50, h_mm=30,
                         fill=Color.DUNKELGRUEN, layer=0,
                         anname="bg"))
        with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
            doc.save(t.name)
            parsed = SLADocument(t.name)
        objs = parsed.page_objects()
        self.assertEqual(objs[0].attrib.get("PTYPE"), "6")
        self.assertEqual(objs[0].attrib.get("PCOLOR"), "Dunkelgrün")
        self.assertEqual(objs[0].attrib.get("LAYER"), "0")

    def test_polygon_ellipse_shape(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(Polygon(x_mm=0, y_mm=0, w_mm=20, h_mm=20,
                         fill=Color.MAGENTA, shape="ellipse"))
        with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
            doc.save(t.name)
            parsed = SLADocument(t.name)
        o = parsed.page_objects()[0]
        self.assertEqual(o.attrib.get("FRTYPE"), "1")
        # Bezier path with 4 'C' commands
        self.assertEqual(o.attrib.get("path", "").count("C"), 4)

    def test_imageframe_carries_pfile(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(ImageFrame(x_mm=10, y_mm=10, w_mm=40, h_mm=40,
                            src="/path/to/img.png", anname="hero"))
        with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
            doc.save(t.name)
            parsed = SLADocument(t.name)
        o = parsed.page_objects()[0]
        self.assertEqual(o.attrib.get("PTYPE"), "2")
        self.assertEqual(o.attrib.get("PFILE"), "/path/to/img.png")
        self.assertEqual(o.attrib.get("ANNAME"), "hero")


class AnchorTests(unittest.TestCase):
    def test_center_anchor(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(TextFrame(anchor="center", w_mm=50, h_mm=20, text="x"))
        with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
            doc.save(t.name)
            parsed = SLADocument(t.name)
        o = parsed.page_objects()[0]
        # Page is 297.6 × 419.5 pt, frame is 141.7 × 56.7 pt
        # local x = (297.6 - 141.7) / 2 = 77.95
        # local y = (419.5 - 56.7) / 2 = 181.4
        # XPOS = page_xpos (100) + 77.95 = 177.95
        x = float(o.attrib.get("XPOS"))
        self.assertAlmostEqual(x, 100 + (297.638 - 50 * 72 / 25.4) / 2, places=1)


if __name__ == "__main__":
    unittest.main()
