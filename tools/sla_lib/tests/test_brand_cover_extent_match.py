"""Tests for brand:cover_extent_match (Issue #23).

For pairs of full-width frames (w >= 0.95 * page_w) on the same page
that touch each other vertically (one's bottom == other's top within
0.5mm), the rule asserts both outer-bbox extents (left + right) match
within 0.5mm.

Synthetic mini-docs only — no real-template coordinates.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document  # noqa: E402
from sla_lib.builder.primitives import ImageFrame, Polygon  # noqa: E402
from sla_lib.builder.brand_constraints import (  # noqa: E402
    BRAND_CONSTRAINTS, BrandRule, _CoverExtentMatchRule,
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
class CoverExtentMatchRegistryTests(unittest.TestCase):
    def test_rule_in_registry(self):
        rule = _find_rule("brand:cover_extent_match")
        self.assertIsInstance(rule, _CoverExtentMatchRule)

    def test_severity_is_warning(self):
        """Locked decision: WARNING initially, ERROR after audit."""
        rule = _find_rule("brand:cover_extent_match")
        self.assertEqual(rule.severity, "warning")


# ---------------------------------------------------------------------------
# Behavior
# ---------------------------------------------------------------------------
class CoverExtentMatchBehaviorTests(unittest.TestCase):
    def test_two_full_width_touching_frames_with_matching_extents_pass(self):
        """A.bottom == B.top, A and B share outer extents → no violation."""
        d = _doc()
        # Both full-width (>= 0.95 * 210 = 199.5).
        d.pages[0].add(ImageFrame(x_mm=-3, y_mm=0, w_mm=216, h_mm=100, anname="A"))
        # A.bottom = 100, B.top = 100 → touching.
        d.pages[0].add(ImageFrame(x_mm=-3, y_mm=100, w_mm=216, h_mm=100, anname="B"))
        rule = _find_rule("brand:cover_extent_match")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_touching_frames_with_mismatched_left_edge_warn(self):
        """A.left=0 vs B.left=-3 → WARNING (page-1 cover bug class)."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=100, anname="A"))
        d.pages[0].add(Polygon(x_mm=-3, y_mm=100, w_mm=216, h_mm=100,
                               fill="Dunkelgrün", anname="B"))
        rule = _find_rule("brand:cover_extent_match")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "warning")
        self.assertIn("extents differ", vs[0].message)

    def test_touching_frames_with_mismatched_right_edge_warn(self):
        """A.right=210 vs B.right=213 → WARNING."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=-3, y_mm=0, w_mm=213, h_mm=100, anname="A"))
        # B left=-3 (matches), but right = -3+216 = 213 vs A right = 210. Wait,
        # A: x=-3, w=213, right=210. B: x=-3, w=216, right=213. Mismatch on right.
        d.pages[0].add(Polygon(x_mm=-3, y_mm=100, w_mm=216, h_mm=100,
                               fill="Dunkelgrün", anname="B"))
        rule = _find_rule("brand:cover_extent_match")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)

    def test_non_touching_frames_skipped(self):
        """A.bottom and B.top differ by > 0.5mm → no warning even if extents differ."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=100, anname="A"))
        # 5mm gap → not touching.
        d.pages[0].add(ImageFrame(x_mm=-3, y_mm=105, w_mm=216, h_mm=100, anname="B"))
        rule = _find_rule("brand:cover_extent_match")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_non_full_width_pair_skipped(self):
        """Both frames w/page=0.5 → not flagged (cutoff 0.95)."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=0, w_mm=100, h_mm=100, anname="A"))
        # Touching, but neither full-width.
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=100, w_mm=100, h_mm=100, anname="B"))
        rule = _find_rule("brand:cover_extent_match")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_master_page_skipped(self):
        """Pairs on master pages are skipped."""
        d = Document(title="t", template_id="t")
        master = d.add_master(name="OnlyMaster", size="A4")
        master.add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=100, anname="A"))
        master.add(ImageFrame(x_mm=-3, y_mm=100, w_mm=216, h_mm=100, anname="B"))
        d.add_page(size="A4", master="OnlyMaster")
        rule = _find_rule("brand:cover_extent_match")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_b_top_touches_a_bottom_either_order(self):
        """Touching detection works regardless of pair iteration order."""
        d = _doc()
        # B at top, A at bottom: B.bottom == A.top.
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=100, w_mm=210, h_mm=100, anname="A"))
        d.pages[0].add(ImageFrame(x_mm=-3, y_mm=0, w_mm=216, h_mm=100, anname="B"))
        rule = _find_rule("brand:cover_extent_match")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
