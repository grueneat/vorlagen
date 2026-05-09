"""Invariant tests for Zeitung geometry — pin RELATIONSHIPS, not coordinates.

Per Issue #23 locked decision #7. Float-imprecise SLA round-trip
(Cover Hero.w_mm = 209.9999999999361) makes coordinate-pinning brittle.
These tests survive any future legitimate Phase 4 retuning that
preserves the alignment intent.

Pinning style:
  - bbox-relationship: assertAlmostEqual(a_bbox[0], b_bbox[0], delta=0.5)
  - page-derived constants: page.width_pt * PT_TO_MM + page.bleed_mm
  - never absolute literals (assertEqual(x_mm, -3.0))

Coverage:
  - Cover Hero outer extents match u2950 (page-1 cover_extent_match invariant).
  - P7 Portrait flush with u918 (top + right).
  - P10 Portrait right edge at outer bleed.
  - 11 outer-bleed-gap frames (named + unnamed Dunkelgrün polygons).
  - Page-9 text columns end above the Kopie von u1529 green card
    (page-10 image_text_overlap fix).
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder.bbox import frame_bbox_mm  # noqa: E402
from sla_lib.builder.document import PT_TO_MM  # noqa: E402


def _load_zeitung_doc():
    """Load templates/zeitung-a4-grun/build.py and build the doc."""
    build_py = ROOT / "templates" / "zeitung-a4-grun" / "build.py"
    spec = importlib.util.spec_from_file_location("zeitung_build", build_py)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_doc()


def _frame_by_anname(doc, anname):
    """Return (item, page). Raises if not found in non-master pages."""
    for page in doc.pages:
        if page.is_master:
            continue
        for item in page.items:
            if getattr(item, "anname", "") == anname:
                return item, page
    raise AssertionError(
        f"frame {anname!r} not found in zeitung doc (non-master pages)"
    )


def _unnamed_dunkelgruen_on_page(doc, own_page):
    """Find the unnamed Dunkelgrün ImageFrame/Polygon on the given own_page."""
    for page in doc.pages:
        if page.is_master:
            continue
        if page.own_page != own_page:
            continue
        for item in page.items:
            an = getattr(item, "anname", "") or ""
            if not an and getattr(item, "fill", None) == "Dunkelgrün":
                return item, page
    raise AssertionError(
        f"no unnamed Dunkelgrün frame found on own_page={own_page}"
    )


# Cache the doc once per process — speed up the suite.
_DOC = None


def _doc():
    global _DOC
    if _DOC is None:
        _DOC = _load_zeitung_doc()
    return _DOC


# ---------------------------------------------------------------------------
# Cover (page 1, own_page=0): Cover Hero outer extents match u2950
# ---------------------------------------------------------------------------
class CoverExtentMatchInvariantTests(unittest.TestCase):
    def test_cover_hero_outer_extent_matches_u2950(self):
        """Page 1: Cover Hero and u2950 share outer-bbox extents."""
        doc = _doc()
        ch, p_ch = _frame_by_anname(doc, "Cover Hero")
        u, p_u = _frame_by_anname(doc, "u2950")
        ch_bbox = frame_bbox_mm(ch, p_ch)
        u_bbox = frame_bbox_mm(u, p_u)   # rotation-aware (u2950 is rotated 90°)
        self.assertAlmostEqual(ch_bbox[0], u_bbox[0], delta=0.5,
                               msg=f"left edges differ: {ch_bbox[0]} vs {u_bbox[0]}")
        self.assertAlmostEqual(ch_bbox[2], u_bbox[2], delta=0.5,
                               msg=f"right edges differ: {ch_bbox[2]} vs {u_bbox[2]}")

    def test_cover_hero_extends_to_both_outer_bleeds(self):
        """Cover Hero left==-bleed AND right==page_w+bleed (own_page=0 cover)."""
        doc = _doc()
        ch, page = _frame_by_anname(doc, "Cover Hero")
        bbox = frame_bbox_mm(ch, page)
        bleed = float(page.bleed_mm or 0)
        pw = page.width_pt * PT_TO_MM
        self.assertAlmostEqual(bbox[0], -bleed, delta=0.5)
        self.assertAlmostEqual(bbox[2], pw + bleed, delta=0.5)


# ---------------------------------------------------------------------------
# Page 8: P7 Portrait flush with u918 (top + right)
# ---------------------------------------------------------------------------
class P7PortraitFlushWithU918Tests(unittest.TestCase):
    def test_p7_portrait_top_flush_with_u918(self):
        doc = _doc()
        portrait, p_pt = _frame_by_anname(doc, "P7 Portrait")
        u918, p_u = _frame_by_anname(doc, "u918")
        pt_bbox = frame_bbox_mm(portrait, p_pt)
        u_bbox = frame_bbox_mm(u918, p_u)
        # Top edges (y_min) match within 0.5mm.
        self.assertAlmostEqual(pt_bbox[1], u_bbox[1], delta=0.5,
                               msg=f"top edges: {pt_bbox[1]} vs {u_bbox[1]}")

    def test_p7_portrait_right_flush_with_u918(self):
        doc = _doc()
        portrait, p_pt = _frame_by_anname(doc, "P7 Portrait")
        u918, p_u = _frame_by_anname(doc, "u918")
        pt_bbox = frame_bbox_mm(portrait, p_pt)
        u_bbox = frame_bbox_mm(u918, p_u)
        # Right edges (x_max) match within 0.5mm.
        self.assertAlmostEqual(pt_bbox[2], u_bbox[2], delta=0.5,
                               msg=f"right edges: {pt_bbox[2]} vs {u_bbox[2]}")

    def test_p7_portrait_bottom_flush_with_u918(self):
        doc = _doc()
        portrait, p_pt = _frame_by_anname(doc, "P7 Portrait")
        u918, p_u = _frame_by_anname(doc, "u918")
        pt_bbox = frame_bbox_mm(portrait, p_pt)
        u_bbox = frame_bbox_mm(u918, p_u)
        # Bottom edges match within 0.5mm.
        self.assertAlmostEqual(pt_bbox[3], u_bbox[3], delta=0.5)


# ---------------------------------------------------------------------------
# Page 11: P10 Portrait right edge at outer bleed
# ---------------------------------------------------------------------------
class P10PortraitOuterBleedTests(unittest.TestCase):
    def test_p10_portrait_right_at_outer_bleed(self):
        """P10 Portrait right edge at page_w + bleed (213 on A4)."""
        doc = _doc()
        portrait, page = _frame_by_anname(doc, "P10 Portrait")
        bbox = frame_bbox_mm(portrait, page)
        expected_right = page.width_pt * PT_TO_MM + float(page.bleed_mm or 0)
        self.assertAlmostEqual(bbox[2], expected_right, delta=0.5,
                               msg=f"right edge {bbox[2]} != bleed {expected_right}")

    def test_p10_portrait_left_preserves_column_axis(self):
        """P10 Portrait left edge stays at column-3 axis (~135.3)."""
        doc = _doc()
        portrait, page = _frame_by_anname(doc, "P10 Portrait")
        bbox = frame_bbox_mm(portrait, page)
        # Pinned by relationship to the column-3 caption text frame
        # (Kopie von u2da1 (19)) on the same page.
        col3, p_c = _frame_by_anname(doc, "Kopie von u2da1 (19)")
        col3_bbox = frame_bbox_mm(col3, p_c)
        self.assertAlmostEqual(bbox[0], col3_bbox[0], delta=0.5)


# ---------------------------------------------------------------------------
# Outer-bleed coverage: 11 frames extend to outer bleed on facing-pages
# ---------------------------------------------------------------------------
class OuterBleedCoverageInvariantTests(unittest.TestCase):
    """Every frame in the documented 11-frame set extends to its outer bleed.

    Each test pins ONE frame's relationship: bbox[0] == -bleed (LEFT)
    OR bbox[2] == page_w + bleed (RIGHT). Coordinates are computed from
    page metadata, not literal numbers.
    """

    def _assert_at_outer_bleed(self, anname, side):
        doc = _doc()
        item, page = _frame_by_anname(doc, anname)
        bbox = frame_bbox_mm(item, page)
        bleed = float(page.bleed_mm or 0)
        pw = page.width_pt * PT_TO_MM
        if side in ("left", "both"):
            self.assertAlmostEqual(
                bbox[0], -bleed, delta=0.5,
                msg=f"{anname!r} left edge {bbox[0]} != -bleed {-bleed}",
            )
        if side in ("right", "both"):
            self.assertAlmostEqual(
                bbox[2], pw + bleed, delta=0.5,
                msg=f"{anname!r} right edge {bbox[2]} != page_w+bleed {pw + bleed}",
            )

    def _assert_unnamed_at_outer_bleed(self, own_page, side):
        doc = _doc()
        item, page = _unnamed_dunkelgruen_on_page(doc, own_page)
        bbox = frame_bbox_mm(item, page)
        bleed = float(page.bleed_mm or 0)
        pw = page.width_pt * PT_TO_MM
        if side in ("left", "both"):
            self.assertAlmostEqual(
                bbox[0], -bleed, delta=0.5,
                msg=f"unnamed on own_page={own_page} left edge {bbox[0]} != -bleed",
            )
        if side in ("right", "both"):
            self.assertAlmostEqual(
                bbox[2], pw + bleed, delta=0.5,
                msg=f"unnamed on own_page={own_page} right edge {bbox[2]} != page_w+bleed",
            )

    def test_cover_hero_both_outer_edges(self):
        self._assert_at_outer_bleed("Cover Hero", "both")

    def test_p1_hero_left_outer(self):
        self._assert_at_outer_bleed("P1 Hero", "left")

    def test_p4_foto_spread_right_outer(self):
        self._assert_at_outer_bleed("P4 Foto-Spread", "right")

    def test_p9_spread_left_at_outer_bleed(self):
        self._assert_at_outer_bleed("P9 Spread · left", "left")

    def test_p9_spread_right_at_outer_bleed(self):
        self._assert_at_outer_bleed("P9 Spread · right", "right")

    def test_p11_bottom_left_outer(self):
        self._assert_at_outer_bleed("P11 Bottom", "left")

    def test_p13_hero_left_outer(self):
        self._assert_at_outer_bleed("P13 Hero", "left")

    def test_unnamed_dunkelgruen_page_11_left_outer(self):
        # own_page=11 → LEFT page (page 12 in print order).
        self._assert_unnamed_at_outer_bleed(11, "left")

    def test_unnamed_dunkelgruen_page_12_right_outer(self):
        # own_page=12 → RIGHT page (page 13 in print order).
        self._assert_unnamed_at_outer_bleed(12, "right")

    def test_unnamed_dunkelgruen_page_13_left_outer(self):
        # own_page=13 → LEFT page (page 14 in print order).
        self._assert_unnamed_at_outer_bleed(13, "left")


# ---------------------------------------------------------------------------
# Page-9 text columns above the green card (Kopie von u1529)
# ---------------------------------------------------------------------------
class Page9TextColumnsAboveGreenCardTests(unittest.TestCase):
    def test_text_column_1_ends_above_green_card(self):
        """Kopie von u2d5c (13) bottom is at least 0.5mm above
        Kopie von u1529 top."""
        doc = _doc()
        green, p_g = _frame_by_anname(doc, "Kopie von u1529")
        green_top = frame_bbox_mm(green, p_g)[1]
        col, p_c = _frame_by_anname(doc, "Kopie von u2d5c (13)")
        col_bottom = frame_bbox_mm(col, p_c)[3]
        self.assertLess(
            col_bottom, green_top - 0.5,
            msg=f"col bottom {col_bottom} not above green card top {green_top}",
        )

    def test_text_column_2_ends_above_green_card(self):
        """Kopie von u2da1 (16) bottom is at least 0.5mm above
        Kopie von u1529 top."""
        doc = _doc()
        green, p_g = _frame_by_anname(doc, "Kopie von u1529")
        green_top = frame_bbox_mm(green, p_g)[1]
        col, p_c = _frame_by_anname(doc, "Kopie von u2da1 (16)")
        col_bottom = frame_bbox_mm(col, p_c)[3]
        self.assertLess(col_bottom, green_top - 0.5)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
