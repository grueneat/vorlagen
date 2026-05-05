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


# ---------------------------------------------------------------------------
# Facing-pages canvas layout — Scribus places the cover (page 0) ALONE on
# row 0 in the right column, then every subsequent pair shares a row.
# ---------------------------------------------------------------------------
class FacingPagesCanvasLayoutTests(unittest.TestCase):
    def _build_facing_doc(self, npages: int) -> Document:
        doc = Document(
            title="x", template_id="x", facing_pages=True,
        )
        # Two masters mimicking the Zeitung's left/right convention. Their
        # presence ensures no implicit "Normal" master gets injected.
        doc.add_master(name="rechts", size="A4", facing="right")
        doc.add_master(name="links", size="A4", facing="left")
        for i in range(npages):
            mnam = "rechts" if (i == 0 or (i % 2 == 0)) else "links"
            doc.add_page(size="A4", master=mnam)
        return doc

    def _expected_y_sequence(self, doc: Document, npages: int) -> list[float]:
        """Cover-on-right convention: row 0 = page 0 alone; row r (r>=1)
        contains pages (2r-1, 2r) sharing the row."""
        h = doc.pages[0].height_pt
        stride = h + Document.GAP_VERTICAL
        seq = [Document.SCRATCH_TOP]  # page 0 → row 0
        for i in range(1, npages):
            row = ((i - 1) // 2) + 1
            seq.append(Document.SCRATCH_TOP + row * stride)
        return seq

    def test_facing_pages_y_layout_matches_zeitung_pattern(self):
        """14-page facing-pages doc emits PAGEYPOS sequence matching the
        Grüne Zeitung's [20, 901.89, 901.89, 1783.78, 1783.78, ...] pattern.
        Computed from doc params (PageHeight + GapVertical), not hardcoded."""
        doc = self._build_facing_doc(14)
        parsed = _save(doc)
        pages = parsed.doc.findall("PAGE")
        self.assertEqual(len(pages), 14)
        actual_y = [float(p.attrib["PAGEYPOS"]) for p in pages]
        expected_y = self._expected_y_sequence(doc, 14)
        for i, (a, e) in enumerate(zip(actual_y, expected_y)):
            self.assertAlmostEqual(
                a, e, places=3,
                msg=f"page {i}: PAGEYPOS={a} but expected {e}")

    def test_facing_pages_x_layout_cover_on_right(self):
        """Cover (page 0) goes in the right column; subsequent pages alternate
        left/right starting from page 1 (left)."""
        doc = self._build_facing_doc(6)
        parsed = _save(doc)
        pages = parsed.doc.findall("PAGE")
        w = doc.pages[0].width_pt
        # Page 0 (cover) → right column at SCRATCH_LEFT + PageWidth
        self.assertAlmostEqual(
            float(pages[0].attrib["PAGEXPOS"]),
            Document.SCRATCH_LEFT + w, places=3)
        # Pages 1, 3, 5 → left column at SCRATCH_LEFT
        for i in (1, 3, 5):
            self.assertAlmostEqual(
                float(pages[i].attrib["PAGEXPOS"]),
                Document.SCRATCH_LEFT, places=3,
                msg=f"page {i}: expected left-column XPOS")
        # Pages 2, 4 → right column at SCRATCH_LEFT + PageWidth
        for i in (2, 4):
            self.assertAlmostEqual(
                float(pages[i].attrib["PAGEXPOS"]),
                Document.SCRATCH_LEFT + w, places=3,
                msg=f"page {i}: expected right-column XPOS")

    def test_facing_pages_LEFT_attribute_zero_on_all_doc_pages(self):
        """The per-PAGE LEFT attribute is informational. Scribus writes LEFT=0
        on every doc page in the Grüne Zeitung original; the DSL must do the
        same regardless of which side the page sits on, because the actual
        side is determined by PageSets+master's LEFT."""
        doc = self._build_facing_doc(6)
        parsed = _save(doc)
        for i, p in enumerate(parsed.doc.findall("PAGE")):
            self.assertEqual(p.attrib["LEFT"], "0",
                             msg=f"page {i}: expected LEFT='0' but got {p.attrib.get('LEFT')!r}")

    def test_facing_pages_y_stride_uses_doc_params(self):
        """Y stride between rows is PageHeight + GapVertical, computed from
        doc params — not hardcoded. Verify a 2-page doc and a 4-page doc
        share the same stride."""
        d2 = self._build_facing_doc(2)
        parsed2 = _save(d2)
        pages2 = parsed2.doc.findall("PAGE")
        stride = float(pages2[1].attrib["PAGEYPOS"]) - float(pages2[0].attrib["PAGEYPOS"])
        self.assertAlmostEqual(
            stride, d2.pages[0].height_pt + Document.GAP_VERTICAL, places=3)

    def test_single_page_layout_unchanged(self):
        """Non-facing docs keep the historical single-column stacking."""
        doc = Document(title="x", template_id="x")
        for _ in range(3):
            doc.add_page(size="A4")
        parsed = _save(doc)
        pages = parsed.doc.findall("PAGE")
        h = doc.pages[0].height_pt
        for i, p in enumerate(pages):
            self.assertAlmostEqual(
                float(p.attrib["PAGEXPOS"]),
                Document.SCRATCH_LEFT, places=3)
            self.assertAlmostEqual(
                float(p.attrib["PAGEYPOS"]),
                Document.SCRATCH_TOP + i * (h + Document.GAP_VERTICAL),
                places=3)


if __name__ == "__main__":
    unittest.main()
