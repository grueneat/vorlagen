"""Tests for brand:undeclared_alignment_drift rule (Issue #22).

Synthetic doc with two ImageFrames per page — verifies the heuristic
triggers when alignment relationships aren't declared in CONSTRAINTS,
and stays silent when they are declared.
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
    BRAND_CONSTRAINTS, BrandRule, _UndeclaredDriftRule,
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
class UndeclaredDriftRegistryTests(unittest.TestCase):
    def test_rule_in_registry(self):
        rule = _find_rule("brand:undeclared_alignment_drift")
        self.assertIsInstance(rule, _UndeclaredDriftRule)


# ---------------------------------------------------------------------------
# Behavior
# ---------------------------------------------------------------------------
class UndeclaredDriftBehaviorTests(unittest.TestCase):
    def test_axis_near_pair_without_constraint_warns(self):
        """Two frames at x=10 and x=12 (drift 2mm) → axis-x warning
        suggesting same_x."""
        d = _doc()
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=50, h_mm=50, anname="A",
        ))
        d.pages[0].add(ImageFrame(
            x_mm=12, y_mm=80, w_mm=50, h_mm=50, anname="B",
        ))
        rule = _find_rule("brand:undeclared_alignment_drift")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "warning")
        self.assertIn("axis-x", vs[0].message)
        self.assertIn("same_x", vs[0].message)
        self.assertEqual(set(vs[0].targets), {"A", "B"})

    def test_axis_near_pair_with_same_x_constraint_silent(self):
        """Same geometry, but constraints=[same_x('A','B')] → 0 warnings."""
        d = _doc()
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=50, h_mm=50, anname="A",
        ))
        d.pages[0].add(ImageFrame(
            x_mm=12, y_mm=80, w_mm=50, h_mm=50, anname="B",
        ))
        rule = _find_rule("brand:undeclared_alignment_drift")
        vs = rule.check(
            list(d.iter_all_primitives()), d,
            constraints=[same_x("A", "B", name="ab_x")],
        )
        self.assertEqual(vs, [])

    def test_far_apart_no_warning(self):
        """x=10 and x=100 (drift 90mm > axis_tol 5mm) AND y=10 and
        y=100 (drift 90mm > 5mm) AND not adjacent → 0 warnings."""
        d = _doc()
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=20, h_mm=20, anname="A",
        ))
        d.pages[0].add(ImageFrame(
            x_mm=100, y_mm=100, w_mm=20, h_mm=20, anname="B",
        ))
        rule = _find_rule("brand:undeclared_alignment_drift")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_stacked_near_with_aligned_below_silent(self):
        """A above B (gap 4mm, same x=10) + aligned_below('B','A',gap=4)
        constraint → 0 warnings."""
        d = _doc()
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=50, h_mm=20, anname="A",
        ))
        # B is at y=34 (4mm gap below A which ends at y=30).
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=34, w_mm=50, h_mm=20, anname="B",
        ))
        rule = _find_rule("brand:undeclared_alignment_drift")
        # Note: same_x dx=0 < min_drift, so axis-x test won't fire.
        # Adjacency: gap=4mm, dx=0 < 5mm → would fire IF undeclared.
        vs = rule.check(
            list(d.iter_all_primitives()), d,
            constraints=[
                aligned_below("B", "A", gap_mm=4.0, name="b_below_a"),
            ],
        )
        self.assertEqual(vs, [])

    def test_stacked_near_without_constraint_warns(self):
        """A above B with gap 4mm and dx=2 (< axis_tol 5) and no
        constraint → adjacency-y warning suggesting aligned_below.
        (dx=2 IS in (0.5, 5) so axis-x fires first via continue.)"""
        d = _doc()
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=50, h_mm=20, anname="A",
        ))
        # B at x=12 → dx=2 (axis-x fires first via the continue).
        d.pages[0].add(ImageFrame(
            x_mm=12, y_mm=34, w_mm=50, h_mm=20, anname="B",
        ))
        rule = _find_rule("brand:undeclared_alignment_drift")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertIn("axis-x", vs[0].message)
        self.assertIn("same_x", vs[0].message)

    def test_stacked_aligned_only_adjacency_warns(self):
        """A above B with same x (dx=0 < min_drift) and gap 4mm → only
        adjacency-y warning suggesting aligned_below."""
        d = _doc()
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=50, h_mm=20, anname="A",
        ))
        # Same x → dx=0, no axis-x warning.
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=34, w_mm=50, h_mm=20, anname="B",
        ))
        rule = _find_rule("brand:undeclared_alignment_drift")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertIn("adjacency-y", vs[0].message)
        self.assertIn("aligned_below", vs[0].message)

    def test_rotated_frame_skipped(self):
        """If either frame in a pair has rotation_deg != 0, skip."""
        d = _doc()
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=50, h_mm=20, anname="A",
        ))
        d.pages[0].add(Polygon(
            x_mm=12, y_mm=80, w_mm=50, h_mm=20, rotation_deg=45,
            fill="Black", anname="B",
        ))
        rule = _find_rule("brand:undeclared_alignment_drift")
        # dx=2 would normally trigger; rotated B → skip → no warning.
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_master_page_skipped(self):
        """Pair on a master page is skipped (master pages excluded)."""
        d = Document(title="t", template_id="t")
        master = d.add_master(name="OnlyMaster", size="A4")
        master.add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=50, h_mm=50, anname="A",
        ))
        master.add(ImageFrame(
            x_mm=12, y_mm=80, w_mm=50, h_mm=50, anname="B",
        ))
        d.add_page(size="A4", master="OnlyMaster")
        rule = _find_rule("brand:undeclared_alignment_drift")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_anonymous_frame_skipped(self):
        """If a frame in the pair has anname='' → skipped."""
        d = _doc()
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=50, h_mm=50, anname="A",
        ))
        # Anonymous frame — no anname.
        d.pages[0].add(ImageFrame(
            x_mm=12, y_mm=80, w_mm=50, h_mm=50, anname="",
        ))
        rule = _find_rule("brand:undeclared_alignment_drift")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_single_target_witness_constraint_doesnt_block(self):
        """A single-target witness constraint (e.g. same_size('X')) yields
        no pair — so axis-x drift between two other frames still fires."""
        from sla_lib.builder.constraints import same_size
        d = _doc()
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=50, h_mm=50, anname="A",
        ))
        d.pages[0].add(ImageFrame(
            x_mm=12, y_mm=80, w_mm=50, h_mm=50, anname="B",
        ))
        rule = _find_rule("brand:undeclared_alignment_drift")
        vs = rule.check(
            list(d.iter_all_primitives()), d,
            # Single-target witness: only references 'A'.
            constraints=[same_size("A", name="A_size")],
        )
        self.assertEqual(len(vs), 1)
        self.assertIn("axis-x", vs[0].message)

    def test_brand_rule_in_constraints_list_is_ignored(self):
        """Any non-Constraint object in `constraints` (e.g. a stray
        BrandRule) must be skipped silently via try/except."""
        d = _doc()
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=50, h_mm=50, anname="A",
        ))
        d.pages[0].add(ImageFrame(
            x_mm=12, y_mm=80, w_mm=50, h_mm=50, anname="B",
        ))
        rule = _find_rule("brand:undeclared_alignment_drift")
        bogus = object()  # No referenced_annames method.
        vs = rule.check(
            list(d.iter_all_primitives()), d,
            constraints=[bogus, same_x("A", "B", name="ok")],
        )
        # The bogus entry skipped via try/except, the same_x suppresses.
        self.assertEqual(vs, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
