"""Tests for brand:image_text_overlap (Issue #23).

Locked decision #2: scope = (ImageFrame OR filled-Polygon, TextFrame).
Filled-Polygon = fill in {Dunkelgrün, Hellgrün, Magenta, Gelb}.
The page-10 Zeitung bug is Polygon×Text (Dunkelgrün card vs body text).

Synthetic mini-docs only — no real-template coordinates.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document  # noqa: E402
from sla_lib.builder.primitives import ImageFrame, TextFrame, Polygon  # noqa: E402
from sla_lib.builder.brand_constraints import (  # noqa: E402
    BRAND_CONSTRAINTS, BrandRule, _ImageTextOverlapRule,
)


def _find_rule(rid: str) -> BrandRule:
    for r in BRAND_CONSTRAINTS:
        if r.id == rid:
            return r
    raise AssertionError(f"rule {rid} not in BRAND_CONSTRAINTS")


def _doc():
    d = Document(title="t", template_id="t")
    d.add_page(size="A4")
    return d


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class ImageTextOverlapRegistryTests(unittest.TestCase):
    def test_rule_in_registry(self):
        rule = _find_rule("brand:image_text_overlap")
        self.assertIsInstance(rule, _ImageTextOverlapRule)

    def test_severity_is_error(self):
        rule = _find_rule("brand:image_text_overlap")
        self.assertEqual(rule.severity, "error")


# ---------------------------------------------------------------------------
# Allowed configurations
# ---------------------------------------------------------------------------
class AllowedConfigsTests(unittest.TestCase):
    def test_zero_overlap_passes(self):
        """Image and text with disjoint bboxes → no violation."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=50, h_mm=50, anname="img"))
        d.pages[0].add(TextFrame(x_mm=100, y_mm=100, w_mm=50, h_mm=50, anname="txt"))
        rule = _find_rule("brand:image_text_overlap")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_text_fully_inside_image_passes(self):
        """Caption-on-photo: text bbox contained in image bbox → no violation."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=0, w_mm=100, h_mm=100, anname="img"))
        d.pages[0].add(TextFrame(x_mm=10, y_mm=80, w_mm=80, h_mm=15, anname="caption"))
        rule = _find_rule("brand:image_text_overlap")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_image_fully_inside_text_passes(self):
        """Drop-cap-style: image inside text → no violation (rare but allowed)."""
        d = _doc()
        d.pages[0].add(TextFrame(x_mm=0, y_mm=0, w_mm=100, h_mm=100, anname="txt"))
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=20, anname="dropcap"))
        rule = _find_rule("brand:image_text_overlap")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])


# ---------------------------------------------------------------------------
# Forbidden: partial overlap
# ---------------------------------------------------------------------------
class PartialOverlapTests(unittest.TestCase):
    def test_partial_overlap_image_text_fires_error(self):
        """Image and text with partial overlap → ERROR."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=50, h_mm=50, anname="img"))
        # Text bbox crosses image right edge.
        d.pages[0].add(TextFrame(x_mm=40, y_mm=20, w_mm=50, h_mm=20, anname="txt"))
        rule = _find_rule("brand:image_text_overlap")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "error")
        self.assertIn("partially overlaps", vs[0].message)

    def test_partial_overlap_filled_polygon_text_fires_error(self):
        """Page-10-bug class: filled Polygon (Dunkelgrün) × TextFrame partial overlap.

        Locked decision #2: this is the scope expansion that catches the
        page-10 Zeitung bug. Without filled-Polygon scope, the rule
        would miss the documented case.
        """
        d = _doc()
        d.pages[0].add(Polygon(x_mm=0, y_mm=80, w_mm=200, h_mm=100,
                               fill="Dunkelgrün", anname="card"))
        # Text crosses card top boundary.
        d.pages[0].add(TextFrame(x_mm=10, y_mm=50, w_mm=180, h_mm=80, anname="body"))
        rule = _find_rule("brand:image_text_overlap")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertIn("filled-polygon", vs[0].message)


# ---------------------------------------------------------------------------
# Out-of-scope shapes
# ---------------------------------------------------------------------------
class OutOfScopeShapesTests(unittest.TestCase):
    def test_polygon_with_no_fill_skipped(self):
        """Polygon with fill=None or '' → not in scope (decorative outline)."""
        d = _doc()
        d.pages[0].add(Polygon(x_mm=0, y_mm=80, w_mm=200, h_mm=100,
                               fill=None, anname="outline"))
        d.pages[0].add(TextFrame(x_mm=10, y_mm=50, w_mm=180, h_mm=80, anname="body"))
        rule = _find_rule("brand:image_text_overlap")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_polygon_with_other_color_skipped(self):
        """Polygon fill='Black' → not in FILLED_POLYGON_FILLS, skipped."""
        d = _doc()
        d.pages[0].add(Polygon(x_mm=0, y_mm=80, w_mm=200, h_mm=100,
                               fill="Black", anname="black_box"))
        d.pages[0].add(TextFrame(x_mm=10, y_mm=50, w_mm=180, h_mm=80, anname="body"))
        rule = _find_rule("brand:image_text_overlap")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_overlap_below_tolerance_skipped(self):
        """Intersection 0.05 mm < 0.1 mm tolerance → skipped (numerical noise)."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=0, w_mm=50, h_mm=50, anname="img"))
        # Text overlaps by 0.05 mm into the image.
        d.pages[0].add(TextFrame(x_mm=49.95, y_mm=10, w_mm=50, h_mm=20, anname="txt"))
        rule = _find_rule("brand:image_text_overlap")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_master_page_skipped(self):
        """Pairs on master pages are skipped."""
        d = Document(title="t", template_id="t")
        master = d.add_master(name="OnlyMaster", size="A4")
        master.add(ImageFrame(x_mm=10, y_mm=10, w_mm=50, h_mm=50, anname="img"))
        master.add(TextFrame(x_mm=40, y_mm=20, w_mm=50, h_mm=20, anname="txt"))
        d.add_page(size="A4", master="OnlyMaster")
        rule = _find_rule("brand:image_text_overlap")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])


# ---------------------------------------------------------------------------
# Multiple pairs
# ---------------------------------------------------------------------------
class MultiplePairsTests(unittest.TestCase):
    def test_multiple_partial_overlaps_each_fire(self):
        """Two text frames each partially overlapping the same image → 2 violations."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=80, h_mm=80, anname="img"))
        d.pages[0].add(TextFrame(x_mm=70, y_mm=20, w_mm=40, h_mm=20, anname="t1"))
        d.pages[0].add(TextFrame(x_mm=70, y_mm=60, w_mm=40, h_mm=20, anname="t2"))
        rule = _find_rule("brand:image_text_overlap")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
