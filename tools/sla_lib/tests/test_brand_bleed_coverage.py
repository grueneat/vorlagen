"""Tests for brand:bleed_coverage (Issue #23, locked decision #1: 0.95 cutoff).

Generic tests using synthetic Document/Page/ImageFrame combinations.
No real-template coordinates.
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
    BRAND_CONSTRAINTS, BrandRule, _BleedCoverageRule,
)


def _find_rule(rid: str) -> BrandRule:
    for r in BRAND_CONSTRAINTS:
        if r.id == rid:
            return r
    raise AssertionError(f"rule {rid} not in BRAND_CONSTRAINTS")


def _facing_doc_with_cover():
    """Facing-pages A4 doc with a dummy cover already in place.

    The cover (own_page=0) is treated specially by the rule (both edges
    are outer), so tests targeting LEFT/RIGHT page semantics need a
    non-cover page. Adding the dummy cover first ensures subsequent
    add_page() calls return non-cover pages.
    """
    d = Document(title="t", template_id="t", facing_pages=True)
    # Dummy cover; never queried by tests.
    d.add_page(size="A4", bleed_mm=3.0, master="cover")
    return d


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class BleedCoverageRegistryTests(unittest.TestCase):
    def test_rule_in_registry(self):
        rule = _find_rule("brand:bleed_coverage")
        self.assertIsInstance(rule, _BleedCoverageRule)

    def test_severity_is_error(self):
        rule = _find_rule("brand:bleed_coverage")
        self.assertEqual(rule.severity, "error")


# ---------------------------------------------------------------------------
# Behavior
# ---------------------------------------------------------------------------
class BleedCoverageBehaviorTests(unittest.TestCase):
    def test_facing_pages_false_returns_zero_violations(self):
        """Single-page documents are exempt — facing-pages-only rule."""
        d = Document(title="t", template_id="t", facing_pages=False)
        d.add_page(size="A4", bleed_mm=3.0)
        # Add a frame that WOULD fail the rule on a facing-pages doc.
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=297, anname="X"))
        rule = _find_rule("brand:bleed_coverage")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_full_width_left_page_short_of_bleed_fires_error(self):
        """LEFT page (master='links'), w/page=1.0, x=0 (NOT -3) → ERROR."""
        d = _facing_doc_with_cover()
        d.add_page(size="A4", bleed_mm=3.0, master="links")
        d.pages[1].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=297, anname="X"))
        rule = _find_rule("brand:bleed_coverage")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "error")
        self.assertIn("LEFT", vs[0].message)

    def test_left_page_at_outer_bleed_passes(self):
        """LEFT page, x=-3, w=213 (extends to outer bleed) → no violation."""
        d = _facing_doc_with_cover()
        d.add_page(size="A4", bleed_mm=3.0, master="links")
        d.pages[1].add(ImageFrame(x_mm=-3, y_mm=0, w_mm=213, h_mm=297, anname="X"))
        rule = _find_rule("brand:bleed_coverage")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_right_page_short_of_bleed_fires_error(self):
        """RIGHT page (master='rechts'), x=0, w=210, x+w=210 (NOT 213) → ERROR."""
        d = _facing_doc_with_cover()
        d.add_page(size="A4", bleed_mm=3.0, master="rechts")
        d.pages[1].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=297, anname="X"))
        rule = _find_rule("brand:bleed_coverage")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertIn("RIGHT", vs[0].message)

    def test_right_page_at_outer_bleed_passes(self):
        """RIGHT page, x=0, w=213 → no violation."""
        d = _facing_doc_with_cover()
        d.add_page(size="A4", bleed_mm=3.0, master="rechts")
        d.pages[1].add(ImageFrame(x_mm=0, y_mm=0, w_mm=213, h_mm=297, anname="X"))
        rule = _find_rule("brand:bleed_coverage")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_below_cutoff_w_ratio_skipped(self):
        """w/page=0.81 (u918-shaped, interior margin polygon) → not flagged.

        Locked decision #1: the 0.95 cutoff dissolves the per-frame
        ``(no-bleed)`` exemption tag — interior frames fall below the
        cutoff naturally. Exact ratio: 170/210 ≈ 0.81.
        """
        d = _facing_doc_with_cover()
        d.add_page(size="A4", bleed_mm=3.0, master="links")
        # 170mm wide at x=20 → not full-width, never flagged.
        d.pages[1].add(ImageFrame(x_mm=20, y_mm=0, w_mm=170, h_mm=297, anname="X"))
        rule = _find_rule("brand:bleed_coverage")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_rotated_frame_skipped(self):
        """rotation_deg != 0 → skipped (rotated bbox semantics out of scope)."""
        d = _facing_doc_with_cover()
        d.add_page(size="A4", bleed_mm=3.0, master="links")
        d.pages[1].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=297,
                                  rotation_deg=90, anname="X"))
        rule = _find_rule("brand:bleed_coverage")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_spread_half_anname_skipped(self):
        """Frames with SpreadImage half suffix (` · left`/` · right`) → skipped."""
        d = _facing_doc_with_cover()
        d.add_page(size="A4", bleed_mm=3.0, master="links")
        d.pages[1].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=297,
                                  anname="P9 Spread · left"))
        rule = _find_rule("brand:bleed_coverage")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_cover_own_page_zero_both_edges_checked(self):
        """own_page=0 (cover) treats BOTH edges as outer — fires twice.

        Cover is the FIRST page added to a facing-pages doc, so we
        construct a fresh doc rather than reusing _facing_doc_with_cover.
        """
        d = Document(title="t", template_id="t", facing_pages=True)
        d.add_page(size="A4", bleed_mm=3.0, master="cover")
        d.pages[0].add(ImageFrame(x_mm=0, y_mm=0, w_mm=210, h_mm=297, anname="X"))
        rule = _find_rule("brand:bleed_coverage")
        vs = rule.check(list(d.iter_all_primitives()), d)
        # Two violations: LEFT (cover) and RIGHT (cover).
        self.assertEqual(len(vs), 2)
        labels = " ".join(v.message for v in vs)
        self.assertIn("LEFT (cover)", labels)
        self.assertIn("RIGHT (cover)", labels)

    def test_cover_at_both_outer_bleeds_passes(self):
        """own_page=0 (cover), x=-3, w=216 → both edges at bleed → no violation."""
        d = Document(title="t", template_id="t", facing_pages=True)
        d.add_page(size="A4", bleed_mm=3.0, master="cover")
        d.pages[0].add(ImageFrame(x_mm=-3, y_mm=0, w_mm=216, h_mm=297, anname="X"))
        rule = _find_rule("brand:bleed_coverage")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_unnamed_frame_still_flagged(self):
        """anname='' → violation message uses synthetic name with type+y."""
        d = _facing_doc_with_cover()
        d.add_page(size="A4", bleed_mm=3.0, master="links")
        # NB: Polygons with no anname are still flagged as full-width.
        d.pages[1].add(Polygon(x_mm=0, y_mm=0, w_mm=210, h_mm=297,
                               fill="Black", anname=""))
        rule = _find_rule("brand:bleed_coverage")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertIn("unnamed", vs[0].message)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
