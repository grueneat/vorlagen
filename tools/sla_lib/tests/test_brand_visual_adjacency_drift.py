"""Tests for brand:visual_adjacency_drift (Issue #23).

Replaces test_brand_undeclared_drift.py from Issue #22. The new rule
extends the prior heuristic with:

  - 4-axis checks (dx_left, dx_right, dy_top, dy_bottom) instead of
    just (dx_left, dy_top).
  - Declaration-disagreement detection: declarations whose own
    tolerance is breached by actual geometry STILL emit a warning
    (breaks the encode-and-silence escape).

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
from sla_lib.builder.constraints import (  # noqa: E402
    same_x, same_y, aligned_below,
)
from sla_lib.builder.brand_constraints import (  # noqa: E402
    BRAND_CONSTRAINTS, BrandRule, _VisualAdjacencyDriftRule,
)


def _find_rule(rid: str) -> BrandRule:
    for r in BRAND_CONSTRAINTS:
        if r.id == rid:
            return r
    raise AssertionError(f"rule {rid} not in BRAND_CONSTRAINTS")


def _doc():
    """One-page A4 doc."""
    d = Document(title="t", template_id="t")
    d.add_page(size="A4")
    return d


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class VisualAdjacencyDriftRegistryTests(unittest.TestCase):
    def test_rule_in_registry(self):
        rule = _find_rule("brand:visual_adjacency_drift")
        self.assertIsInstance(rule, _VisualAdjacencyDriftRule)

    def test_old_rule_not_in_registry(self):
        ids = [r.id for r in BRAND_CONSTRAINTS]
        self.assertNotIn("brand:undeclared_alignment_drift", ids)


# ---------------------------------------------------------------------------
# 4-axis behavior
# ---------------------------------------------------------------------------
class FourAxisDriftTests(unittest.TestCase):
    """Verify each of the 4 axes (left/right/top/bottom) is checked."""

    def test_axis_x_left_drift_fires(self):
        """A.x=20, B.x=23 (drift 3mm), other dims identical → axis-x-left fires."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=20, y_mm=10, w_mm=40, h_mm=40, anname="A"))
        d.pages[0].add(ImageFrame(x_mm=23, y_mm=10, w_mm=40, h_mm=40, anname="B"))
        rule = _find_rule("brand:visual_adjacency_drift")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertGreaterEqual(len(vs), 1)
        self.assertTrue(any("axis-x-left" in v.message for v in vs),
                        f"no axis-x-left in messages: {[v.message for v in vs]}")

    def test_axis_x_right_drift_fires(self):
        """Same left edge but different widths → right edges differ → axis-x-right fires.

        This is the page-8 Zeitung bug class — invisible to the old rule
        which only checked left edges.
        """
        d = _doc()
        # x=20, w=40 (right=60) vs x=20, w=43 (right=63) → dx_left=0, dx_right=3.
        # y=10, h=40 (bot=50) vs y=10, h=43 (bot=53) → dy_top=0, dy_bottom=3.
        # Rule iterates axes in order: x-left first → 0 (skipped, < min_drift),
        # then x-right → 3 (fires; break).
        d.pages[0].add(ImageFrame(x_mm=20, y_mm=10, w_mm=40, h_mm=40, anname="A"))
        d.pages[0].add(ImageFrame(x_mm=20, y_mm=10, w_mm=43, h_mm=43, anname="B"))
        rule = _find_rule("brand:visual_adjacency_drift")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertGreaterEqual(len(vs), 1)
        self.assertTrue(any("axis-x-right" in v.message for v in vs),
                        f"no axis-x-right in messages: {[v.message for v in vs]}")

    def test_axis_y_top_drift_fires(self):
        """Same x, w; different y_top → axis-y-top fires."""
        d = _doc()
        # dx_left=0, dx_right=0 (skipped); dy_top=3 (fires).
        d.pages[0].add(ImageFrame(x_mm=20, y_mm=10, w_mm=40, h_mm=40, anname="A"))
        d.pages[0].add(ImageFrame(x_mm=20, y_mm=13, w_mm=40, h_mm=40, anname="B"))
        rule = _find_rule("brand:visual_adjacency_drift")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertGreaterEqual(len(vs), 1)
        self.assertTrue(any("axis-y-top" in v.message for v in vs),
                        f"no axis-y-top in messages: {[v.message for v in vs]}")

    def test_axis_y_bottom_drift_fires(self):
        """Same x, y_top; different heights → axis-y-bottom fires."""
        d = _doc()
        # dx_left=0, dx_right=0, dy_top=0 (all skipped); dy_bottom=3 (fires).
        d.pages[0].add(ImageFrame(x_mm=20, y_mm=10, w_mm=40, h_mm=40, anname="A"))
        d.pages[0].add(ImageFrame(x_mm=20, y_mm=10, w_mm=40, h_mm=43, anname="B"))
        rule = _find_rule("brand:visual_adjacency_drift")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertGreaterEqual(len(vs), 1)
        self.assertTrue(any("axis-y-bottom" in v.message for v in vs),
                        f"no axis-y-bottom in messages: {[v.message for v in vs]}")

    def test_far_apart_no_warning(self):
        """All 4 axis drifts > axis_drift_max_mm (25mm) → 0 warnings."""
        d = _doc()
        # x: |10-100|=90; right: |30-120|=90; y: |10-100|=90; bottom: |30-120|=90.
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=20, anname="A"))
        d.pages[0].add(ImageFrame(x_mm=100, y_mm=100, w_mm=20, h_mm=20, anname="B"))
        rule = _find_rule("brand:visual_adjacency_drift")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])


# ---------------------------------------------------------------------------
# Declaration-disagreement detection
# ---------------------------------------------------------------------------
class DeclarationDisagreementTests(unittest.TestCase):
    """A declaration whose own tolerance is breached should STILL warn.

    Breaks the encode-and-silence escape: declaring
    aligned_below(A, B, tolerance_mm=4.0) against a 5mm actual drift no
    longer silences the warning.
    """

    def test_declaration_disagreement_emits_warning(self):
        """aligned_below(A, B, gap_mm=2, tolerance_mm=0.5), actual gap=5 → warn."""
        d = _doc()
        # B at y=10..30, A at y=35 → actual gap = 35 - 30 = 5mm (NOT 2mm).
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=50, h_mm=20, anname="B"))
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=35, w_mm=50, h_mm=20, anname="A"))
        rule = _find_rule("brand:visual_adjacency_drift")
        # aligned_below(below, above) — A hangs below B with declared gap=2 ± 0.5.
        c = aligned_below("A", "B", gap_mm=2.0, tolerance_mm=0.5,
                          name="A_below_B")
        vs = rule.check(list(d.iter_all_primitives()), d, constraints=[c])
        self.assertGreaterEqual(len(vs), 1)
        self.assertTrue(any("disagrees" in v.message.lower() for v in vs),
                        f"no 'disagrees' in messages: {[v.message for v in vs]}")

    def test_tight_declaration_matching_geometry_silent(self):
        """aligned_below(A, B, gap_mm=4, tolerance_mm=0.5), actual gap=4 → silent."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=50, h_mm=20, anname="B"))
        # A hanging below B with gap=4 (B ends y=30, A starts y=34).
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=34, w_mm=50, h_mm=20, anname="A"))
        rule = _find_rule("brand:visual_adjacency_drift")
        c = aligned_below("A", "B", gap_mm=4.0, tolerance_mm=0.5,
                          name="A_below_B")
        vs = rule.check(list(d.iter_all_primitives()), d, constraints=[c])
        self.assertEqual(vs, [])

    def test_widened_tolerance_still_catches_excess_drift(self):
        """aligned_below(A, B, gap_mm=2, tolerance_mm=1.0), actual gap=5 → warn.

        Locked decision #5: the declaration's own tolerance is the audit
        boundary. tolerance_mm=1.0 + actual_drift=3mm → exceeds tolerance.
        """
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=50, h_mm=20, anname="B"))
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=35, w_mm=50, h_mm=20, anname="A"))
        rule = _find_rule("brand:visual_adjacency_drift")
        c = aligned_below("A", "B", gap_mm=2.0, tolerance_mm=1.0,
                          name="A_below_B")
        vs = rule.check(list(d.iter_all_primitives()), d, constraints=[c])
        self.assertGreaterEqual(len(vs), 1)
        self.assertTrue(any("disagrees" in v.message.lower() for v in vs))

    def test_declared_pair_skips_heuristic_when_decl_passes(self):
        """Declared pair, declaration matches geometry → heuristic does NOT also fire."""
        d = _doc()
        # x=10 vs x=12 → axis-x-left drift = 2 → heuristic would fire.
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=50, h_mm=20, anname="A"))
        d.pages[0].add(ImageFrame(x_mm=12, y_mm=80, w_mm=50, h_mm=20, anname="B"))
        rule = _find_rule("brand:visual_adjacency_drift")
        # Declare with same_x tolerance_mm=3 → 2mm drift accepted by declaration.
        c = same_x("A", "B", tolerance_mm=3.0, name="ax")
        vs = rule.check(list(d.iter_all_primitives()), d, constraints=[c])
        # Declaration passes its own check; heuristic suppressed for declared pair.
        self.assertEqual(vs, [])


# ---------------------------------------------------------------------------
# Skip behavior (carried over from #22)
# ---------------------------------------------------------------------------
class SkipBehaviorTests(unittest.TestCase):
    def test_rotated_frame_skipped(self):
        """Rotated frames are filtered out of the spatial collection."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=50, h_mm=20, anname="A"))
        d.pages[0].add(Polygon(x_mm=12, y_mm=80, w_mm=50, h_mm=20,
                               rotation_deg=45, fill="Black", anname="B"))
        rule = _find_rule("brand:visual_adjacency_drift")
        # B filtered (rotation != 0); A alone → no pair.
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_master_page_skipped(self):
        """Pairs on master pages are skipped."""
        d = Document(title="t", template_id="t")
        master = d.add_master(name="OnlyMaster", size="A4")
        master.add(ImageFrame(x_mm=10, y_mm=10, w_mm=50, h_mm=50, anname="A"))
        master.add(ImageFrame(x_mm=12, y_mm=80, w_mm=50, h_mm=50, anname="B"))
        d.add_page(size="A4", master="OnlyMaster")
        rule = _find_rule("brand:visual_adjacency_drift")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_anonymous_frame_skipped(self):
        """Frames with anname='' are not collected into the spatial list."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=50, h_mm=50, anname="A"))
        d.pages[0].add(ImageFrame(x_mm=12, y_mm=80, w_mm=50, h_mm=50, anname=""))
        rule = _find_rule("brand:visual_adjacency_drift")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_brand_rule_in_constraints_list_is_ignored(self):
        """Non-Constraint object in constraints list (e.g. BrandRule) silently skipped."""
        d = _doc()
        # Far-apart frames so no warning fires regardless of the bogus constraint.
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=20, anname="A"))
        d.pages[0].add(ImageFrame(x_mm=100, y_mm=100, w_mm=20, h_mm=20, anname="B"))
        rule = _find_rule("brand:visual_adjacency_drift")
        bogus = object()  # No referenced_annames method.
        vs = rule.check(list(d.iter_all_primitives()), d, constraints=[bogus])
        # bogus skipped by try/except; far-apart pair doesn't trigger.
        self.assertEqual(vs, [])


# ---------------------------------------------------------------------------
# Adjacency (stacked-y)
# ---------------------------------------------------------------------------
class StackedAdjacencyTests(unittest.TestCase):
    def test_stacked_adjacency_fires(self):
        """A above B, gap=4, sharing x → adjacency-y warning."""
        d = _doc()
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=50, h_mm=20, anname="A"))
        # Same x → dx_left=0, dx_right=0 (both skipped). dy_top=24 (in range,
        # fires) → wait, that fires axis-y-top first. Need DIFFERENT y-top.
        # Actually: A.y_top=10, B.y_top=34 → dy_top=24mm in (0.5, 25) → fires.
        # The stacked-adjacency only fires when no axis fires. Let me make
        # dy_top > axis_drift_max_mm by setting B further down with same x.
        # Actually, the rule structure: 4 axes checked first, break on first
        # fire. To trigger adjacency-y exclusively, all 4 axis drifts must
        # be either < min (0.5) or > max (25). dx_left=0 (<min, ok), dx_right=0
        # (<min, ok), dy_top=24 (in range — fires). Hard to avoid.
        # Use bigger gap: A.y_top=10, B.y_top=40 → dy_top=30 (>max, skipped).
        # dy_bottom=|30-60|=30 (>max, skipped). gap = 40-30 = 10 (in range).
        d.pages[0].clear() if hasattr(d.pages[0], "clear") else None
        # Re-build with proper geometry.
        d2 = _doc()
        d2.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=50, h_mm=20, anname="A"))
        d2.pages[0].add(ImageFrame(x_mm=10, y_mm=40, w_mm=50, h_mm=20, anname="B"))
        rule = _find_rule("brand:visual_adjacency_drift")
        vs = rule.check(list(d2.iter_all_primitives()), d2)
        # Now: dy_top=30 (>max), dy_bottom=30 (>max), dx_left=0 (<min),
        # dx_right=0 (<min). Adjacency: A.y1=30 < B.y0=40, gap=10
        # (in (0.5, 30)), dx_left=0 < axis_max → adjacency-y fires.
        self.assertGreaterEqual(len(vs), 1)
        self.assertTrue(any("adjacency-y" in v.message for v in vs),
                        f"no adjacency-y in messages: {[v.message for v in vs]}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
