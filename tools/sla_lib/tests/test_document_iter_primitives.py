"""Tests for Document.iter_all_primitives() — the structural_check anchor.

The method must:
- yield primitives across masters then pages
- preserve per-page order (page.items order)
- preserve anname through iteration
- treat composite/block emit() output as already flattened (Page.add does
  the flattening at insertion time)
- yield nothing on an empty doc
"""
from __future__ import annotations
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document  # noqa: E402
from sla_lib.builder.primitives import TextFrame, ImageFrame, Polygon  # noqa: E402


class DocumentIterAllPrimitivesTests(unittest.TestCase):
    def test_empty_doc_yields_nothing(self):
        # Doc must have at least one page to satisfy the format invariant
        # before save(); for iter_all_primitives we only require pages list.
        doc = Document(title="t", template_id="t")
        # No add_page yet — masters and pages both empty.
        self.assertEqual(list(doc.iter_all_primitives()), [])

    def test_single_page_three_frames_in_insertion_order(self):
        doc = Document(title="t", template_id="t")
        page = doc.add_page(size="A6")
        f1 = TextFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=10, anname="A")
        f2 = TextFrame(x_mm=10, y_mm=30, w_mm=20, h_mm=10, anname="B")
        f3 = TextFrame(x_mm=10, y_mm=50, w_mm=20, h_mm=10, anname="C")
        page.add(f1)
        page.add(f2)
        page.add(f3)
        result = list(doc.iter_all_primitives())
        self.assertEqual(result, [f1, f2, f3])
        self.assertEqual([p.anname for p in result], ["A", "B", "C"])

    def test_master_page_items_yielded_before_doc_page_items(self):
        doc = Document(title="t", template_id="t")
        master = doc.add_master(name="Normal", size="A6")
        page = doc.add_page(size="A6", master="Normal")
        m1 = TextFrame(x_mm=1, y_mm=1, w_mm=5, h_mm=5, anname="m1")
        m2 = ImageFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=20, anname="m2")
        master.add(m1)
        master.add(m2)
        p1 = TextFrame(x_mm=20, y_mm=20, w_mm=10, h_mm=10, anname="p1")
        p2 = Polygon(x_mm=30, y_mm=30, w_mm=10, h_mm=10, anname="p2", fill="Black")
        page.add(p1)
        page.add(p2)
        result = list(doc.iter_all_primitives())
        # Masters first
        self.assertEqual(result[0:2], [m1, m2])
        self.assertEqual(result[2:4], [p1, p2])
        self.assertEqual(len(result), 4)

    def test_anname_preserved_through_iteration(self):
        doc = Document(title="t", template_id="t")
        page = doc.add_page(size="A6")
        names = ["Logo", "Headline", "Body", "QR-Code"]
        frames = [
            TextFrame(x_mm=0, y_mm=i * 10, w_mm=10, h_mm=8, anname=n)
            for i, n in enumerate(names)
        ]
        for f in frames:
            page.add(f)
        result = list(doc.iter_all_primitives())
        self.assertEqual([p.anname for p in result], names)

    def test_composite_emit_already_flattened_by_page_add(self):
        """A stub composite-style object that yields multiple primitives
        from emit() — Page.add() flushes them at insertion. iter_all_primitives
        must see the flattened output, NOT the composite object."""
        doc = Document(title="t", template_id="t")
        page = doc.add_page(size="A6")

        @dataclass
        class _StubComposite:
            children: list

            def emit(self, page=None):
                yield from self.children

        a = TextFrame(x_mm=0, y_mm=0, w_mm=10, h_mm=10, anname="A")
        b = TextFrame(x_mm=20, y_mm=0, w_mm=10, h_mm=10, anname="B")
        page.add(_StubComposite(children=[a, b]))
        result = list(doc.iter_all_primitives())
        self.assertEqual(result, [a, b])
        # Stub object itself NOT in items
        for r in result:
            self.assertNotIsInstance(r, _StubComposite)

    def test_multiple_pages_iterated_in_order(self):
        doc = Document(title="t", template_id="t")
        p1 = doc.add_page(size="A6")
        p2 = doc.add_page(size="A6")
        f1 = TextFrame(x_mm=0, y_mm=0, w_mm=5, h_mm=5, anname="P1-1")
        f2 = TextFrame(x_mm=0, y_mm=10, w_mm=5, h_mm=5, anname="P1-2")
        f3 = TextFrame(x_mm=0, y_mm=0, w_mm=5, h_mm=5, anname="P2-1")
        p1.add(f1)
        p1.add(f2)
        p2.add(f3)
        result = list(doc.iter_all_primitives())
        self.assertEqual([p.anname for p in result], ["P1-1", "P1-2", "P2-1"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
