"""Tests for multi-page DSL with master pages."""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib import SLADocument  # noqa: E402
from sla_lib.builder import Document, Color, Polygon, blocks  # noqa: E402


def _save(doc: Document):
    f = tempfile.NamedTemporaryFile(suffix=".sla", delete=False)
    f.close()
    doc.save(f.name)
    return SLADocument(f.name)


class MultipageTests(unittest.TestCase):
    def test_two_pages(self):
        doc = Document(title="x", template_id="x")
        doc.add_page(size="A4")
        doc.add_page(size="A4")
        parsed = _save(doc)
        self.assertEqual(parsed.page_count, 2)
        self.assertEqual(len(parsed.doc.findall("PAGE")), 2)

    def test_implicit_normal_master_always_present(self):
        doc = Document(title="x", template_id="x")
        doc.add_page(size="A4")
        parsed = _save(doc)
        masters = parsed.doc.findall("MASTERPAGE")
        names = [m.attrib.get("NAM") for m in masters]
        self.assertIn("Normal", names)

    def test_named_master_emitted(self):
        doc = Document(title="x", template_id="x")
        m = doc.add_master(name="rechts-3col", size="A4")
        m.add(Polygon(x_mm=180, y_mm=290, w_mm=15, h_mm=4,
                      fill=Color.GELB, layer=0, anname="m-akzent"))
        doc.add_page(size="A4", master="rechts-3col")
        parsed = _save(doc)
        names = [m.attrib.get("NAM") for m in parsed.doc.findall("MASTERPAGE")]
        self.assertIn("rechts-3col", names)
        # Master items emitted as MASTEROBJECT bound by OnMasterPage
        master_objs = parsed.doc.findall("MASTEROBJECT")
        self.assertEqual(len(master_objs), 1)
        self.assertEqual(master_objs[0].attrib.get("OnMasterPage"), "rechts-3col")
        # And no OwnPage on master objects
        self.assertNotIn("OwnPage", master_objs[0].attrib)

    def test_page_label_emits_visible_marker(self):
        doc = Document(title="x", template_id="x")
        doc.add_page(size="A4", label="Beispiel: Hauptartikel")
        parsed = _save(doc)
        # Label TextFrame exists with the prefix in CH
        label_objs = [o for o in parsed.page_objects()
                      if "Beispiel" in str(o.attrib.get("ANNAME", ""))]
        self.assertEqual(len(label_objs), 1)

    def test_label_on_hilfslinien_layer(self):
        doc = Document(title="x", template_id="x")
        doc.add_page(size="A4", label="LBL")
        parsed = _save(doc)
        label_obj = next(o for o in parsed.page_objects()
                         if "LBL" in str(o.attrib.get("ANNAME", "")))
        # Hilfslinien is index 3 in the default layer stack
        self.assertEqual(label_obj.attrib.get("LAYER"), "3")

    def test_page_mnam_defaults_to_normal(self):
        doc = Document(title="x", template_id="x")
        doc.add_page(size="A4")
        parsed = _save(doc)
        page = parsed.doc.find("PAGE")
        self.assertEqual(page.attrib.get("MNAM"), "Normal")

    def test_duplicate_master_raises(self):
        doc = Document(title="x", template_id="x")
        doc.add_master(name="rechts-3col", size="A4")
        with self.assertRaises(ValueError):
            doc.add_master(name="rechts-3col", size="A4")


if __name__ == "__main__":
    unittest.main()
