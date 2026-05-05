"""Smoke tests for sla_lib against the three originals in the repo root.
Run: python3 -m unittest discover tools/sla_lib/tests
"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib import SLADocument  # noqa: E402
from sla_lib.editor import SLAEditor  # noqa: E402

ORIGINALS = [
    ROOT / "plakat-a1-hochformat-original.sla",
    ROOT / "postkarte-vorlage-original.sla",
    ROOT / "gruene-zeitung-vorlage-original.sla",
]


class ReaderSmokeTests(unittest.TestCase):
    def test_all_parse(self):
        for p in ORIGINALS:
            with self.subTest(p.name):
                doc = SLADocument(p)
                self.assertEqual(doc.version[:3], "1.6")
                self.assertGreater(doc.page_count, 0)
                w, h = doc.page_size_pt
                self.assertGreater(w, 0)
                self.assertGreater(h, 0)
                self.assertGreater(len(doc.page_objects()), 0)

    def test_roundtrip_idempotent(self):
        """Read → write → read produces the same object count."""
        import tempfile
        for p in ORIGINALS:
            with self.subTest(p.name):
                doc = SLADocument(p)
                count_before = len(doc.page_objects())
                with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
                    doc.write(t.name)
                    doc2 = SLADocument(t.name)
                self.assertEqual(count_before, len(doc2.page_objects()))


class IteratorTests(unittest.TestCase):
    """Iterators used by sla_diff and sla_to_dsl. Counts come from RESEARCH.md
    §Per-original inventory, all measured directly via lxml on the originals.
    """

    EXPECTED = {
        # path: dict of (iterator name -> count)
        "postkarte-vorlage-original.sla": {
            "pages": 2, "masters": 1, "layers": 1, "colors": 8,
            "styles": 9, "charstyles": 2,
        },
        "plakat-a1-hochformat-original.sla": {
            "pages": 1, "masters": 1, "layers": 1, "colors": 5,
            "styles": 5, "charstyles": 1,
        },
        "gruene-zeitung-vorlage-original.sla": {
            "pages": 14, "masters": 2, "layers": 1, "colors": 8,
            "styles": 23, "charstyles": 1,
        },
    }

    def test_iter_counts_match_inventory(self):
        for p in ORIGINALS:
            with self.subTest(p.name):
                exp = self.EXPECTED[p.name]
                doc = SLADocument(p)
                self.assertEqual(len(list(doc.iter_pages())), exp["pages"])
                self.assertEqual(len(list(doc.iter_masters())), exp["masters"])
                self.assertEqual(len(list(doc.iter_layers())), exp["layers"])
                self.assertEqual(len(list(doc.iter_colors())), exp["colors"])
                self.assertEqual(len(list(doc.iter_styles())), exp["styles"])
                self.assertEqual(len(list(doc.iter_charstyles())), exp["charstyles"])

    def test_iter_pages_returns_elements_in_document_order(self):
        doc = SLADocument(ORIGINALS[2])  # Zeitung 14 pages
        nums = [int(p.attrib.get("NUM", "-1")) for p in doc.iter_pages()]
        self.assertEqual(nums, list(range(14)))

    def test_iter_styles_yields_style_elements(self):
        doc = SLADocument(ORIGINALS[1])  # Postkarte
        names = [s.attrib.get("NAME", "") for s in doc.iter_styles()]
        # Postkarte has these distinct style names per RESEARCH.md
        self.assertIn("Fließtext", names)
        self.assertIn("Headline sehr wichtig", names)

    def test_iter_colors_includes_per_doc_custom(self):
        doc = SLADocument(ORIGINALS[1])  # Postkarte: has Green RGB 153,102,51
        names = [c.attrib.get("NAME") for c in doc.iter_colors()]
        self.assertIn("Green", names)


class EditorTests(unittest.TestCase):
    def test_unnamed_frames_yield_no_slots(self):
        # Originals have no ANNAME slots yet — slot list should be empty.
        for p in ORIGINALS:
            doc = SLADocument(p)
            self.assertEqual(doc.slots(), [], f"{p.name} unexpectedly has named slots")

    def test_set_text_via_anname(self):
        """Add an ANNAME to one frame, then edit via the editor."""
        import tempfile
        doc = SLADocument(ORIGINALS[1])  # Postkarte
        # Pick first text frame, give it a slot name
        for o in doc.page_objects():
            if o.attrib.get("PTYPE") == "4":
                o.set("ANNAME", "text:headline")
                break
        ed = SLAEditor(doc)
        self.assertTrue(ed.set_text("headline", "Test Headline\nLine 2"))
        with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
            doc.write(t.name)
            doc2 = SLADocument(t.name)
        # Find that frame again
        frame = doc2.find_by_anname("text:headline")
        self.assertIsNotNone(frame)
        self.assertIn("Test Headline", doc2.frame_text(frame))


if __name__ == "__main__":
    unittest.main()
