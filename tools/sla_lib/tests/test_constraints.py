"""Tests for free-form constraint factories.

Per CONTEXT D2/D5 (corrected): resolution by anname (string or Frame),
not Python id(). Each factory: happy/violation/tolerance-edge/missing.
"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import (  # noqa: E402
    same_y, same_x, same_size, mirrored_x, mirrored_y, inside,
    equal_gap, hierarchy, same_style, distance_y, distance_x,
    Constraint, Violation,
)
from sla_lib.builder.primitives import TextFrame, ImageFrame  # noqa: E402


def _frame(name: str, x=0, y=0, w=10, h=10, style="", fontsize=None):
    f = TextFrame(x_mm=x, y_mm=y, w_mm=w, h_mm=h, anname=name, style=style)
    if fontsize is not None:
        f.fontsize = fontsize
    return f


def _by_anname(*frames) -> dict:
    return {f.anname: f for f in frames}


class SameYTests(unittest.TestCase):
    def test_happy_path_passes(self):
        a = _frame("A", y=10)
        b = _frame("B", y=10)
        v = same_y(a, b).check(_by_anname(a, b))
        self.assertEqual(v, [])

    def test_violation(self):
        a = _frame("A", y=10)
        b = _frame("B", y=20)
        v = same_y(a, b).check(_by_anname(a, b))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].severity, "error")

    def test_tolerance_edge_passes_at_tolerance(self):
        a = _frame("A", y=10)
        b = _frame("B", y=10.5)
        v = same_y(a, b, tolerance_mm=0.5).check(_by_anname(a, b))
        self.assertEqual(v, [])

    def test_tolerance_exceeded_fails(self):
        a = _frame("A", y=10)
        b = _frame("B", y=10.6)
        v = same_y(a, b, tolerance_mm=0.5).check(_by_anname(a, b))
        self.assertEqual(len(v), 1)

    def test_string_targets_accepted(self):
        a = _frame("A", y=10)
        b = _frame("B", y=10)
        v = same_y("A", "B").check(_by_anname(a, b))
        self.assertEqual(v, [])

    def test_mixed_form_accepted(self):
        a = _frame("A", y=10)
        b = _frame("B", y=10)
        v = same_y(a, "B").check(_by_anname(a, b))
        self.assertEqual(v, [])

    def test_missing_anname_warns(self):
        a = _frame("A", y=10)
        v = same_y("A", "MissingFoo").check(_by_anname(a))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].severity, "warning")
        self.assertIn("MissingFoo", v[0].message)


class SameXTests(unittest.TestCase):
    def test_happy(self):
        a = _frame("A", x=5)
        b = _frame("B", x=5)
        self.assertEqual(same_x(a, b).check(_by_anname(a, b)), [])

    def test_violation(self):
        a = _frame("A", x=5)
        b = _frame("B", x=10)
        self.assertEqual(len(same_x(a, b).check(_by_anname(a, b))), 1)

    def test_tolerance_edge(self):
        a = _frame("A", x=5)
        b = _frame("B", x=5.5)
        self.assertEqual(same_x(a, b, tolerance_mm=0.5).check(_by_anname(a, b)), [])

    def test_missing_warns(self):
        v = same_x("X", "Y").check({})
        self.assertEqual(v[0].severity, "warning")


class SameSizeTests(unittest.TestCase):
    def test_both_passes(self):
        a = _frame("A", w=10, h=20)
        b = _frame("B", w=10, h=20)
        self.assertEqual(same_size(a, b, axis="both").check(_by_anname(a, b)), [])

    def test_width_only_passes_when_h_differs(self):
        a = _frame("A", w=10, h=20)
        b = _frame("B", w=10, h=999)
        self.assertEqual(same_size(a, b, axis="w").check(_by_anname(a, b)), [])

    def test_h_only_fails_on_w_diff_when_both(self):
        a = _frame("A", w=10, h=20)
        b = _frame("B", w=99, h=20)
        v = same_size(a, b, axis="both").check(_by_anname(a, b))
        self.assertEqual(len(v), 1)

    def test_invalid_axis_raises(self):
        with self.assertRaises(ValueError):
            same_size(_frame("A"), _frame("B"), axis="z")


class MirroredXTests(unittest.TestCase):
    def test_passes_when_centers_average_to_axis(self):
        a = _frame("A", x=0, w=20)   # center=10
        b = _frame("B", x=180, w=20)  # center=190
        # average = 100
        self.assertEqual(mirrored_x(a, b, axis_mm=100).check(_by_anname(a, b)), [])

    def test_passes_regardless_of_arg_order(self):
        a = _frame("A", x=0, w=20)
        b = _frame("B", x=180, w=20)
        v_ab = mirrored_x(a, b, axis_mm=100).check(_by_anname(a, b))
        v_ba = mirrored_x(b, a, axis_mm=100).check(_by_anname(a, b))
        self.assertEqual(v_ab, [])
        self.assertEqual(v_ba, [])

    def test_violation(self):
        a = _frame("A", x=0, w=20)
        b = _frame("B", x=200, w=20)  # center=210, avg=110
        self.assertEqual(len(mirrored_x(a, b, axis_mm=100).check(_by_anname(a, b))), 1)

    def test_tolerance_edge(self):
        a = _frame("A", x=0, w=20)
        b = _frame("B", x=181, w=20)  # avg = 100.5
        # default 0.5mm tolerance — passes at 0.5mm exactly
        self.assertEqual(mirrored_x(a, b, axis_mm=100).check(_by_anname(a, b)), [])


class MirroredYTests(unittest.TestCase):
    def test_passes(self):
        a = _frame("A", y=0, h=20)   # center=10
        b = _frame("B", y=180, h=20)  # center=190
        self.assertEqual(mirrored_y(a, b, axis_mm=100).check(_by_anname(a, b)), [])

    def test_violation(self):
        a = _frame("A", y=0, h=20)
        b = _frame("B", y=200, h=20)
        self.assertEqual(len(mirrored_y(a, b, axis_mm=100).check(_by_anname(a, b))), 1)

    def test_string_targets(self):
        a = _frame("A", y=0, h=20)
        b = _frame("B", y=180, h=20)
        self.assertEqual(mirrored_y("A", "B", axis_mm=100).check(_by_anname(a, b)), [])

    def test_missing_warns(self):
        v = mirrored_y("X", "Y", axis_mm=100).check({})
        self.assertEqual(v[0].severity, "warning")


class InsideTests(unittest.TestCase):
    def test_fully_inside_passes(self):
        c = _frame("C", x=20, y=20, w=10, h=10)
        p = _frame("P", x=0, y=0, w=100, h=100)
        self.assertEqual(inside(c, p).check(_by_anname(c, p)), [])

    def test_outside_fails(self):
        c = _frame("C", x=200, y=20, w=10, h=10)
        p = _frame("P", x=0, y=0, w=100, h=100)
        self.assertEqual(len(inside(c, p).check(_by_anname(c, p))), 1)

    def test_partial_overlap_fails(self):
        c = _frame("C", x=95, y=20, w=20, h=10)
        p = _frame("P", x=0, y=0, w=100, h=100)
        self.assertEqual(len(inside(c, p).check(_by_anname(c, p))), 1)

    def test_tolerance_edge(self):
        c = _frame("C", x=-0.4, y=0, w=100, h=100)
        p = _frame("P", x=0, y=0, w=100, h=100)
        self.assertEqual(inside(c, p, tolerance_mm=0.5).check(_by_anname(c, p)), [])


class EqualGapTests(unittest.TestCase):
    def test_uniform_gap_passes(self):
        a = _frame("A", y=0, h=10)
        b = _frame("B", y=15, h=10)  # gap=5
        c = _frame("C", y=30, h=10)  # gap=5
        self.assertEqual(equal_gap(a, b, c, axis="y", gap_mm=5).check(_by_anname(a, b, c)), [])

    def test_uneven_fails(self):
        a = _frame("A", y=0, h=10)
        b = _frame("B", y=15, h=10)  # gap=5
        c = _frame("C", y=40, h=10)  # gap=15 ≠ 5
        v = equal_gap(a, b, c, axis="y", gap_mm=5).check(_by_anname(a, b, c))
        self.assertEqual(len(v), 1)

    def test_x_axis(self):
        a = _frame("A", x=0, w=10)
        b = _frame("B", x=15, w=10)
        self.assertEqual(equal_gap(a, b, axis="x", gap_mm=5).check(_by_anname(a, b)), [])

    def test_missing_warns(self):
        v = equal_gap("X", "Y", axis="y", gap_mm=5).check({})
        self.assertEqual(v[0].severity, "warning")


class HierarchyTests(unittest.TestCase):
    def test_descending_passes(self):
        h = _frame("H", fontsize=24)
        s = _frame("S", fontsize=14)
        b = _frame("B", fontsize=10)
        self.assertEqual(hierarchy(h, s, b).check(_by_anname(h, s, b)), [])

    def test_ascending_fails(self):
        h = _frame("H", fontsize=10)
        s = _frame("S", fontsize=20)
        self.assertEqual(len(hierarchy(h, s).check(_by_anname(h, s))), 1)

    def test_equal_fails(self):
        a = _frame("A", fontsize=12)
        b = _frame("B", fontsize=12)
        self.assertEqual(len(hierarchy(a, b).check(_by_anname(a, b))), 1)

    def test_missing_attribute_fails(self):
        a = _frame("A", fontsize=12)
        b = _frame("B")  # no fontsize
        v = hierarchy(a, b).check(_by_anname(a, b))
        self.assertEqual(v[0].severity, "error")


class SameStyleTests(unittest.TestCase):
    def test_passes(self):
        a = _frame("A", style="ci/h1")
        b = _frame("B", style="ci/h1")
        self.assertEqual(same_style(a, b).check(_by_anname(a, b)), [])

    def test_fails_on_drift(self):
        a = _frame("A", style="ci/h1")
        b = _frame("B", style="ci/h2")
        self.assertEqual(len(same_style(a, b).check(_by_anname(a, b))), 1)

    def test_string_form(self):
        a = _frame("A", style="ci/body")
        b = _frame("B", style="ci/body")
        self.assertEqual(same_style("A", "B").check(_by_anname(a, b)), [])

    def test_missing_warns(self):
        v = same_style("X", "Y").check({})
        self.assertEqual(v[0].severity, "warning")


class DistanceYTests(unittest.TestCase):
    def test_passes(self):
        a = _frame("A", y=10)
        b = _frame("B", y=60)
        self.assertEqual(distance_y(a, b, equals=50).check(_by_anname(a, b)), [])

    def test_fails(self):
        a = _frame("A", y=10)
        b = _frame("B", y=80)
        self.assertEqual(len(distance_y(a, b, equals=50).check(_by_anname(a, b))), 1)

    def test_tolerance_edge(self):
        a = _frame("A", y=10)
        b = _frame("B", y=60.5)
        self.assertEqual(distance_y(a, b, equals=50, tolerance_mm=0.5).check(_by_anname(a, b)), [])

    def test_string_form(self):
        a = _frame("A", y=10)
        b = _frame("B", y=60)
        self.assertEqual(distance_y("A", "B", equals=50).check(_by_anname(a, b)), [])


class DistanceXTests(unittest.TestCase):
    def test_passes(self):
        a = _frame("A", x=10)
        b = _frame("B", x=60)
        self.assertEqual(distance_x(a, b, equals=50).check(_by_anname(a, b)), [])

    def test_fails(self):
        a = _frame("A", x=10)
        b = _frame("B", x=20)
        self.assertEqual(len(distance_x(a, b, equals=50).check(_by_anname(a, b))), 1)

    def test_tolerance_edge(self):
        a = _frame("A", x=10)
        b = _frame("B", x=60.4)
        self.assertEqual(distance_x(a, b, equals=50, tolerance_mm=0.5).check(_by_anname(a, b)), [])

    def test_missing_warns(self):
        v = distance_x("X", "Y", equals=50).check({})
        self.assertEqual(v[0].severity, "warning")


class ReferencedAnnamesTests(unittest.TestCase):
    """Per RESEARCH §10: orchestrator uses referenced_annames() for orphan check."""

    def test_returns_anname_strings(self):
        a = _frame("Logo")
        b = _frame("QR")
        c = same_y(a, b)
        self.assertEqual(c.referenced_annames(), ("Logo", "QR"))

    def test_string_input_preserved(self):
        c = same_y("X", "Y")
        self.assertEqual(c.referenced_annames(), ("X", "Y"))

    def test_unset_anname_raises(self):
        from sla_lib.builder import Constraint as _C  # noqa: F401
        f = TextFrame(x_mm=0, y_mm=0, w_mm=10, h_mm=10)  # anname=""
        with self.assertRaises(ValueError):
            same_y(f, "Other")


# ---------------------------------------------------------------------------
# aligned_below (Issue #14)
# ---------------------------------------------------------------------------
from sla_lib.builder.constraints import (  # noqa: E402
    aligned_below, _AlignedBelowConstraint,
)


class AlignedBelowTests(unittest.TestCase):
    def _pair(self, below_kwargs=None, above_kwargs=None):
        above_defaults = {"x_mm": 20, "y_mm": 10, "w_mm": 80, "h_mm": 30}
        above_defaults.update(above_kwargs or {})
        above = TextFrame(anname="above", **above_defaults)
        below_defaults = {"x_mm": 20, "y_mm": 45, "w_mm": 80, "h_mm": 60}
        below_defaults.update(below_kwargs or {})
        below = ImageFrame(anname="below", **below_defaults)
        return below, above, {"above": above, "below": below}

    def test_pass_when_aligned(self):
        below, above, by = self._pair()
        # gap = 5 mm: above.y(10) + above.h(30) + 5 = 45 = below.y; below.x == above.x.
        c = aligned_below(below, above, gap_mm=5)
        self.assertEqual(c.check(by), [])

    def test_x_drift_errors(self):
        below, above, by = self._pair(below_kwargs={"x_mm": 22})  # 2 mm drift
        c = aligned_below(below, above, gap_mm=5)
        vs = c.check(by)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "error")
        self.assertIn("x", vs[0].message)

    def test_y_drift_errors(self):
        below, above, by = self._pair(below_kwargs={"y_mm": 50})  # gap=10, expected 5
        c = aligned_below(below, above, gap_mm=5)
        vs = c.check(by)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "error")
        self.assertIn("y", vs[0].message)

    def test_within_tolerance_passes(self):
        below, above, by = self._pair(below_kwargs={"x_mm": 20.4, "y_mm": 45.4})
        c = aligned_below(below, above, gap_mm=5, tolerance_mm=0.5)
        self.assertEqual(c.check(by), [])

    def test_missing_anname_warns(self):
        _, above, _ = self._pair()
        by_only_above = {"above": above}  # 'below' missing
        c = aligned_below("below", "above", gap_mm=5)
        vs = c.check(by_only_above)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "warning")

    def test_rotated_frame_warn_skip(self):
        below, above, by = self._pair(above_kwargs={"rotation_deg": 90})
        c = aligned_below(below, above, gap_mm=5)
        vs = c.check(by)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "warning")
        self.assertIn("rotated", vs[0].message)

    def test_string_form_accepts_annames(self):
        _, _, by = self._pair()
        c = aligned_below("below", "above", gap_mm=5)
        self.assertEqual(c.check(by), [])

    def test_factory_id_uses_autoname(self):
        below, above, _ = self._pair()
        c = aligned_below(below, above, gap_mm=5)
        self.assertTrue(c.id.startswith("aligned_below"))
        self.assertEqual(c.targets, ("below", "above"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
