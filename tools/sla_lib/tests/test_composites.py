"""Tests for composite blocks (CONTEXT D1 — constraint-by-construction).

Each composite has >=6 tests covering happy path, mutation safety,
edge cases (empty, single child, mixed types), axis variants, and
error conditions where applicable.
"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import (  # noqa: E402
    AlignedRow, AlignedColumn, MirroredPair, EqualGapStack,
    GridSpec, GridCell, HierarchyBlock,
)
from sla_lib.builder.primitives import TextFrame, ImageFrame, Polygon  # noqa: E402


def _tf(x=0, y=0, w=10, h=10, name="", fontsize=None, **kw):
    f = TextFrame(x_mm=x, y_mm=y, w_mm=w, h_mm=h, anname=name, **kw)
    if fontsize is not None:
        f.fontsize = fontsize
    return f


def _img(x=0, y=0, w=10, h=10, name=""):
    return ImageFrame(x_mm=x, y_mm=y, w_mm=w, h_mm=h, anname=name)


class AlignedRowTests(unittest.TestCase):
    def test_happy_path_forces_y_on_three_children(self):
        a = _tf(x=0, y=5)
        b = _tf(x=20, y=15)
        c = _tf(x=40, y=999)
        out = list(AlignedRow(y_mm=100, children=[a, b, c]).emit())
        self.assertEqual([f.y_mm for f in out], [100, 100, 100])

    def test_originals_not_mutated(self):
        a = _tf(x=0, y=5)
        b = _tf(x=20, y=15)
        list(AlignedRow(y_mm=100, children=[a, b]).emit())
        self.assertEqual((a.y_mm, b.y_mm), (5, 15))

    def test_empty_children_yields_nothing(self):
        self.assertEqual(list(AlignedRow(y_mm=10, children=[]).emit()), [])

    def test_single_child_yielded(self):
        a = _tf(y=999)
        out = list(AlignedRow(y_mm=42, children=[a]).emit())
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].y_mm, 42)

    def test_mixed_frame_types(self):
        t = _tf(y=10)
        i = _img(y=20)
        p = Polygon(x_mm=30, y_mm=30, w_mm=10, h_mm=10, fill="Black")
        out = list(AlignedRow(y_mm=88, children=[t, i, p]).emit())
        self.assertEqual([f.y_mm for f in out], [88, 88, 88])
        self.assertIsInstance(out[0], TextFrame)
        self.assertIsInstance(out[1], ImageFrame)
        self.assertIsInstance(out[2], Polygon)

    def test_x_w_h_preserved(self):
        a = _tf(x=15, y=0, w=33, h=44)
        out = list(AlignedRow(y_mm=99, children=[a]).emit())
        self.assertEqual((out[0].x_mm, out[0].w_mm, out[0].h_mm), (15, 33, 44))


class AlignedColumnTests(unittest.TestCase):
    def test_happy_path_forces_x(self):
        a = _tf(x=999, y=10)
        b = _tf(x=999, y=20)
        out = list(AlignedColumn(x_mm=12, children=[a, b]).emit())
        self.assertEqual([f.x_mm for f in out], [12, 12])

    def test_originals_not_mutated(self):
        a = _tf(x=999)
        list(AlignedColumn(x_mm=10, children=[a]).emit())
        self.assertEqual(a.x_mm, 999)

    def test_empty_yields_nothing(self):
        self.assertEqual(list(AlignedColumn(x_mm=10, children=[]).emit()), [])

    def test_single_child(self):
        a = _tf(x=999)
        out = list(AlignedColumn(x_mm=5, children=[a]).emit())
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].x_mm, 5)

    def test_mixed_types(self):
        t = _tf(x=11)
        i = _img(x=22)
        out = list(AlignedColumn(x_mm=7, children=[t, i]).emit())
        self.assertEqual([f.x_mm for f in out], [7, 7])

    def test_y_w_h_preserved(self):
        a = _tf(x=999, y=42, w=15, h=20)
        out = list(AlignedColumn(x_mm=10, children=[a]).emit())
        self.assertEqual((out[0].y_mm, out[0].w_mm, out[0].h_mm), (42, 15, 20))


class MirroredPairTests(unittest.TestCase):
    def test_x_axis_mirror_centers_average_to_axis_mm(self):
        # axis = vertical line at x=100; left center at x=20; right.w_mm=20
        # so its center should be at x=180 (left_center + right_center = 200).
        left = _tf(x=10, y=0, w=20, h=10)
        right = _tf(x=999, y=0, w=20, h=10)
        out = list(MirroredPair(left=left, right=right, axis_mm=100, axis="x").emit())
        new_right = out[1]
        # right new center-x should be 180, so x_mm = 180 - 10 = 170
        self.assertAlmostEqual(new_right.x_mm + new_right.w_mm / 2, 180)
        # axis-line average:
        self.assertAlmostEqual(
            (left.x_mm + left.w_mm / 2 + new_right.x_mm + new_right.w_mm / 2) / 2,
            100,
        )

    def test_y_axis_mirror(self):
        top = _tf(x=0, y=20, w=10, h=10)
        bot = _tf(x=0, y=999, w=10, h=10)
        out = list(MirroredPair(left=top, right=bot, axis_mm=50, axis="y").emit())
        new_bot = out[1]
        self.assertAlmostEqual(new_bot.y_mm + new_bot.h_mm / 2, 75)

    def test_originals_not_mutated(self):
        left = _tf(x=10, y=0, w=20, h=10)
        right = _tf(x=999, y=0, w=20, h=10)
        list(MirroredPair(left=left, right=right, axis_mm=100, axis="x").emit())
        self.assertEqual(right.x_mm, 999)

    def test_emits_two_frames_in_order_left_then_right(self):
        left = _tf(name="L")
        right = _tf(name="R")
        out = list(MirroredPair(left=left, right=right, axis_mm=50, axis="x").emit())
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].anname, "L")
        self.assertEqual(out[1].anname, "R")

    def test_invalid_axis_raises(self):
        with self.assertRaises(ValueError):
            list(MirroredPair(left=_tf(), right=_tf(), axis_mm=10, axis="z").emit())

    def test_none_left_or_right_emits_nothing(self):
        out = list(MirroredPair(left=None, right=_tf(), axis_mm=10).emit())
        self.assertEqual(out, [])
        out = list(MirroredPair(left=_tf(), right=None, axis_mm=10).emit())
        self.assertEqual(out, [])


class EqualGapStackTests(unittest.TestCase):
    def test_y_axis_uniform_gap(self):
        a = _tf(y=999, w=10, h=20)
        b = _tf(y=999, w=10, h=30)
        c = _tf(y=999, w=10, h=10)
        out = list(EqualGapStack(gap_mm=5, children=[a, b, c], axis="y", start_mm=10).emit())
        # a at 10; b at 10+20+5=35; c at 35+30+5=70
        self.assertEqual([f.y_mm for f in out], [10, 35, 70])

    def test_x_axis_uniform_gap(self):
        a = _tf(x=999, w=20, h=10)
        b = _tf(x=999, w=15, h=10)
        out = list(EqualGapStack(gap_mm=5, children=[a, b], axis="x", start_mm=0).emit())
        self.assertEqual([f.x_mm for f in out], [0, 25])

    def test_empty_yields_nothing(self):
        self.assertEqual(list(EqualGapStack(gap_mm=5, children=[], axis="y").emit()), [])

    def test_single_child(self):
        a = _tf(y=999, w=10, h=20)
        out = list(EqualGapStack(gap_mm=5, children=[a], axis="y", start_mm=12).emit())
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].y_mm, 12)

    def test_originals_not_mutated(self):
        a = _tf(y=999, w=10, h=20)
        list(EqualGapStack(gap_mm=5, children=[a], axis="y", start_mm=10).emit())
        self.assertEqual(a.y_mm, 999)

    def test_invalid_axis_raises(self):
        with self.assertRaises(ValueError):
            list(EqualGapStack(gap_mm=5, children=[_tf()], axis="z").emit())


class GridSpecTests(unittest.TestCase):
    def test_cell_xy_for_2x2(self):
        g = GridSpec(cols=2, rows=2, gutter_mm=10, margin_mm=12, page_w_mm=200, page_h_mm=200)
        x, y, w, h = g.cell_xy(0, 0)
        # usable_w = 200 - 24 - 10 = 166; cell_w = 83. x = 12, y = 12
        self.assertAlmostEqual(x, 12)
        self.assertAlmostEqual(y, 12)
        self.assertAlmostEqual(w, 83)

    def test_cell_xy_span_cols_wider(self):
        g = GridSpec(cols=3, rows=2, gutter_mm=10, margin_mm=10, page_w_mm=200, page_h_mm=100)
        # usable_w = 200 - 20 - 20 = 160; cell_w = 53.33...
        x1, _, w1, _ = g.cell_xy(0, 0, span_cols=1)
        x2, _, w2, _ = g.cell_xy(0, 0, span_cols=2)
        self.assertGreater(w2, w1)

    def test_cell_xy_span_rows_taller(self):
        g = GridSpec(cols=2, rows=3, gutter_mm=10, margin_mm=10, page_w_mm=100, page_h_mm=300)
        _, _, _, h1 = g.cell_xy(0, 0, span_rows=1)
        _, _, _, h2 = g.cell_xy(0, 0, span_rows=2)
        self.assertGreater(h2, h1)

    def test_out_of_range_raises(self):
        g = GridSpec(cols=2, rows=2, page_w_mm=100, page_h_mm=100)
        with self.assertRaises(ValueError):
            g.cell_xy(2, 0)
        with self.assertRaises(ValueError):
            g.cell_xy(0, 2)

    def test_zero_cols_raises(self):
        g = GridSpec(cols=0, rows=1, page_w_mm=100, page_h_mm=100)
        with self.assertRaises(ValueError):
            g.cell_xy(0, 0)

    def test_grid_cell_emit_forces_xywh(self):
        g = GridSpec(cols=2, rows=2, gutter_mm=0, margin_mm=0, page_w_mm=100, page_h_mm=100)
        child = _tf(x=999, y=999, w=999, h=999)
        out = list(GridCell(grid=g, row=0, col=0, child=child).emit())
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0].x_mm, out[0].y_mm, out[0].w_mm, out[0].h_mm), (0, 0, 50, 50))

    def test_grid_cell_emit_none_child(self):
        g = GridSpec(cols=2, rows=2, page_w_mm=100, page_h_mm=100)
        out = list(GridCell(grid=g, row=0, col=0, child=None).emit())
        self.assertEqual(out, [])

    def test_grid_cell_originals_not_mutated(self):
        g = GridSpec(cols=2, rows=2, gutter_mm=0, margin_mm=0, page_w_mm=100, page_h_mm=100)
        child = _tf(x=999, y=999, w=999, h=999)
        list(GridCell(grid=g, row=0, col=0, child=child).emit())
        self.assertEqual(child.x_mm, 999)


class HierarchyBlockTests(unittest.TestCase):
    def test_valid_descending_fontsize_passes(self):
        h = _tf(name="hl", fontsize=24)
        s = _tf(name="sl", fontsize=14)
        b = _tf(name="bd", fontsize=10)
        out = list(HierarchyBlock(headline=h, subline=s, body=b).emit())
        self.assertEqual([f.anname for f in out], ["hl", "sl", "bd"])

    def test_invalid_ascending_raises(self):
        h = _tf(name="hl", fontsize=10)
        s = _tf(name="sl", fontsize=20)
        with self.assertRaises(ValueError):
            list(HierarchyBlock(headline=h, subline=s).emit())

    def test_partial_subline_none(self):
        h = _tf(name="hl", fontsize=24)
        b = _tf(name="bd", fontsize=10)
        out = list(HierarchyBlock(headline=h, subline=None, body=b).emit())
        self.assertEqual([f.anname for f in out], ["hl", "bd"])

    def test_only_headline(self):
        h = _tf(name="hl", fontsize=24)
        out = list(HierarchyBlock(headline=h).emit())
        self.assertEqual([f.anname for f in out], ["hl"])

    def test_no_fontsize_skips_check(self):
        # ImageFrame without fontsize attribute — must not raise.
        h = _img(name="hl")
        s = _tf(name="sl", fontsize=14)
        out = list(HierarchyBlock(headline=h, subline=s).emit())
        self.assertEqual([f.anname for f in out], ["hl", "sl"])

    def test_equal_fontsize_raises(self):
        # equal fontsize is NOT strict descending → ValueError.
        h = _tf(fontsize=12)
        s = _tf(fontsize=12)
        with self.assertRaises(ValueError):
            list(HierarchyBlock(headline=h, subline=s).emit())

    def test_originals_not_mutated(self):
        # HierarchyBlock yields originals (no positional override). Sanity:
        # mutation isn't introduced by the block.
        h = _tf(name="hl", fontsize=24, y=99)
        list(HierarchyBlock(headline=h).emit())
        self.assertEqual(h.y_mm, 99)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
