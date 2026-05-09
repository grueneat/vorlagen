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


def _load_zeitung_preview_doc():
    """Load templates/zeitung-a4-grun/build.py and call build_preview().

    Different from _load_zeitung_doc which calls build_doc() (the clean
    end-user variant with empty inline_image_data on every photo frame).
    build_preview() runs the INJECT_MAP loop, populating inline JPEGs
    sized to live frame.w_mm / frame.h_mm at injection time (Issue #24
    fix). Required for ImageContentExtentInvariantTests below.
    """
    build_py = ROOT / "templates" / "zeitung-a4-grun" / "build.py"
    spec = importlib.util.spec_from_file_location(
        "zeitung_build_preview", build_py,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_preview()


def _content_extent_mm(frame):
    """Compute (rendered_w_mm, rendered_h_mm) of a frame's inline image.

    Decodes the qCompress-encoded inline_image_data (reverse of
    primitives.py::pack_inline_image), reads PIL native dims + JFIF
    density, returns rendered mm per Scribus draw matrix:

      - scale_type=0: nat_mm * local_scale (the inject_into_frame path).
      - scale_type=1, ratio=1: centred letterbox INSIDE; qMin scale.
      - scale_type=1, ratio=0: stretch fills exactly (returns frame mm).
    """
    import base64
    import struct
    import zlib
    from io import BytesIO
    from PIL import Image
    if not frame.inline_image_data:
        raise AssertionError(
            f"frame {frame.anname!r} has no inline_image_data — "
            "ImageContentExtentInvariantTests requires build_preview() "
            "output (Issue #24 INJECT_MAP loop)."
        )
    raw = base64.b64decode(frame.inline_image_data)
    _ = struct.unpack(">I", raw[:4])[0]   # uncompressed-length prefix
    img_bytes = zlib.decompress(raw[4:])
    im = Image.open(BytesIO(img_bytes))
    w_px, h_px = im.size
    dpi_pair = im.info.get("dpi", (300, 300))
    try:
        dpi = int(dpi_pair[0]) or 300
    except (TypeError, ValueError):
        dpi = 300
    scx, scy = frame.local_scale
    if frame.scale_type == 0:
        return (w_px * 25.4 / dpi * scx, h_px * 25.4 / dpi * scy)
    if frame.scale_type == 1 and frame.ratio == 1:
        nat_w_mm = w_px * 25.4 / dpi
        nat_h_mm = h_px * 25.4 / dpi
        s = min(frame.w_mm / nat_w_mm, frame.h_mm / nat_h_mm)
        return (nat_w_mm * s, nat_h_mm * s)
    # scale_type=1, ratio=0: stretch fills exactly.
    return (frame.w_mm, frame.h_mm)


_PREVIEW_DOC = None


def _preview_doc():
    global _PREVIEW_DOC
    if _PREVIEW_DOC is None:
        _PREVIEW_DOC = _load_zeitung_preview_doc()
    return _PREVIEW_DOC


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

    # Issue #25: P4 Foto-Spread and P11 Bottom no longer extend to
    # outer bleed. The band-consistency rule pins these frames inside
    # the body block (x=20-190, y inside free zone), superseding the
    # #23 bleed-coverage invariant. Their #23 tests are removed; the
    # post-#25 geometry is pinned by BandConsistencyInvariantTests
    # (T08).

    def test_p9_spread_left_at_outer_bleed(self):
        self._assert_at_outer_bleed("P9 Spread · left", "left")

    def test_p9_spread_right_at_outer_bleed(self):
        self._assert_at_outer_bleed("P9 Spread · right", "right")

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


# ---------------------------------------------------------------------------
# Issue #24: ImageContentExtentInvariantTests
# ---------------------------------------------------------------------------
class ImageContentExtentInvariantTests(unittest.TestCase):
    """For each fixed photo frame, rendered content extent ~= frame extent.

    Pinning style: relationship-pinning per #23 locked decision #7
    (and #24 locked decision #5). assertAlmostEqual with delta=0.5 mm.

    Excludes the 2 SpreadImage halves (P9 left/right) — they're
    SpreadImage primitives whose rendered-content extent uses a
    half-page offset_mm trick (see SpreadImage.emit math). The
    inject_into_frame path still applies (build_preview runs INJECT_MAP
    over them too) so they ARE in INJECT_MAP, but the rendered-content
    invariant for SpreadImage halves is NOT "rendered ~ frame extent"
    — it's "rendered ~ 2 * page_w_mm" (the full spread). Exclude them
    here; the SpreadImage geometry contract is pinned in
    test_spread_image.py.

    Excludes the 3 unnamed Dunkelgrün polygons on Zeitung pages
    12/13/14 — they're solid-fill image-less ImageFrames (the rule
    in #24 also skips them per locked decision #3); they have no
    inline_image_data so _content_extent_mm would raise.

    These 10 tests would FAIL on the pre-#24 INJECT_MAP literal-
    target state (7 of 10 frames had gap_w >= 3mm per RESEARCH.md
    root-cause table); they pass post-T05+T06.
    """

    def _assert_fills_frame(self, anname, tol_mm=0.5):
        doc = _preview_doc()
        item, _page = _frame_by_anname(doc, anname)
        rw, rh = _content_extent_mm(item)
        self.assertAlmostEqual(
            rw, item.w_mm, delta=tol_mm,
            msg=(f"{anname}: rendered_w {rw:.3f} != frame_w "
                 f"{item.w_mm:.3f} (gap {item.w_mm - rw:.3f} mm > "
                 f"tol {tol_mm} mm)"),
        )
        self.assertAlmostEqual(
            rh, item.h_mm, delta=tol_mm,
            msg=(f"{anname}: rendered_h {rh:.3f} != frame_h "
                 f"{item.h_mm:.3f} (gap {item.h_mm - rh:.3f} mm > "
                 f"tol {tol_mm} mm)"),
        )

    def test_cover_hero_fills_frame(self):
        self._assert_fills_frame("Cover Hero")

    def test_p1_hero_fills_frame(self):
        self._assert_fills_frame("P1 Hero")

    def test_p2_mid_fills_frame(self):
        self._assert_fills_frame("P2 Mid")

    def test_p3_hero_fills_frame(self):
        self._assert_fills_frame("P3 Hero")

    def test_p4_foto_spread_fills_frame(self):
        self._assert_fills_frame("P4 Foto-Spread")

    def test_p5_hero_fills_frame(self):
        self._assert_fills_frame("P5 Hero")

    def test_p7_portrait_fills_frame(self):
        self._assert_fills_frame("P7 Portrait")

    def test_p10_portrait_fills_frame(self):
        self._assert_fills_frame("P10 Portrait")

    def test_p11_bottom_fills_frame(self):
        self._assert_fills_frame("P11 Bottom")

    def test_p13_hero_fills_frame(self):
        self._assert_fills_frame("P13 Hero")


# ---------------------------------------------------------------------------
# Issue #25: band-consistency invariant pinning
# ---------------------------------------------------------------------------
class BandConsistencyInvariantTests(unittest.TestCase):
    """Pins the band/margin invariants on the Zeitung doc.

    These tests REPLACE the originally-planned three test classes for
    image-within-text-block, margin consistency, and text-card consistency
    (per RESEARCH.md §8). They lock the post-T06 geometry so future
    regressions are caught.

    Body-pool pages (1-indexed): 3, 4, 5, 6, 7, 8, 9, 12, 13.
    Feature pages (excluded): 1, 2, 10, 11, 14.
    Bands: header y=20-49, free y=49-283, footer y=283-297.
    Margins: 20mm L/R (symmetric Zeitung).
    """

    BODY_POOL_PAGES_1IDX = [3, 4, 5, 6, 7, 8, 9, 12, 13]
    HEADER_Y_TOP = 20.0
    HEADER_Y_BOT = 49.0
    FOOTER_Y_TOP = 283.0
    FOOTER_Y_BOT = 297.0
    LEFT_MARGIN = 20.0
    RIGHT_MARGIN = 20.0
    TOLERANCE = 0.5

    def _content_frames(self, page):
        """TextFrames + ImageFrames with image content (NOT decoration).

        Skips Polygons (decoration) and image-less ImageFrames with
        brand-color fill (also decoration). Mirrors the rule's
        ``_is_background_decoration`` carve-out.
        """
        from sla_lib.builder.primitives import TextFrame, ImageFrame
        bg_fills = {"Dunkelgrün", "Hellgrün", "Magenta", "Gelb", "White"}
        for item in page.items:
            if isinstance(item, TextFrame):
                yield item
            elif isinstance(item, ImageFrame):
                has_image = bool(
                    item.image or item.src
                    or getattr(item, "inline_image_data", None)
                )
                if not has_image and item.fill in bg_fills:
                    continue   # decoration
                yield item

    def _bbox(self, item, page):
        return frame_bbox_mm(item, page)

    def test_no_body_content_in_header_band(self):
        """No content frame's bbox crosses y=49 from above on body pages."""
        doc = _doc()
        for pn in self.BODY_POOL_PAGES_1IDX:
            page = doc.pages[pn - 1]
            for item in self._content_frames(page):
                if getattr(item, "anchor", None) is not None:
                    continue   # anchor-positioned skip
                bbox = self._bbox(item, page)
                if bbox is None:
                    continue
                y0, y1 = bbox[1], bbox[3]
                # Frame must be entirely in header (y1<=49) OR entirely in
                # free zone (y0>=49) OR entirely in footer (y0>=283).
                if y0 < self.HEADER_Y_BOT - self.TOLERANCE \
                        and y1 > self.HEADER_Y_BOT + self.TOLERANCE:
                    name = getattr(item, "anname", "") or "<unnamed>"
                    self.fail(
                        f"page {pn}: frame {name!r} y=[{y0:.1f}, {y1:.1f}] "
                        f"crosses header-band boundary y={self.HEADER_Y_BOT}"
                    )

    def test_no_body_content_in_footer_band(self):
        """Mirror: no content frame straddles y=283 boundary from above."""
        doc = _doc()
        for pn in self.BODY_POOL_PAGES_1IDX:
            page = doc.pages[pn - 1]
            for item in self._content_frames(page):
                if getattr(item, "anchor", None) is not None:
                    continue
                bbox = self._bbox(item, page)
                if bbox is None:
                    continue
                y0, y1 = bbox[1], bbox[3]
                if y0 < self.FOOTER_Y_TOP - self.TOLERANCE \
                        and y1 > self.FOOTER_Y_TOP + self.TOLERANCE:
                    name = getattr(item, "anname", "") or "<unnamed>"
                    self.fail(
                        f"page {pn}: frame {name!r} y=[{y0:.1f}, {y1:.1f}] "
                        f"crosses footer-band boundary y={self.FOOTER_Y_TOP}"
                    )

    def test_body_content_within_left_and_right_margins(self):
        """Free-zone content stays within x=[20, page_w-20] on every body page.

        Header/footer band frames (page numbers in outer-margin alley)
        are exempt — their horizontal placement is band-specific design
        per the rule's free-zone-only carve-out.
        """
        doc = _doc()
        for pn in self.BODY_POOL_PAGES_1IDX:
            page = doc.pages[pn - 1]
            pw_mm = page.width_pt * PT_TO_MM
            for item in self._content_frames(page):
                if getattr(item, "anchor", None) is not None:
                    continue
                bbox = self._bbox(item, page)
                if bbox is None:
                    continue
                x0, y0, x1, y1 = bbox
                # Apply margin check only to free-zone frames (the rule's
                # carve-out for band-zone frames).
                in_free = (y0 >= self.HEADER_Y_BOT - self.TOLERANCE
                           and y1 <= self.FOOTER_Y_TOP + self.TOLERANCE)
                if not in_free:
                    continue
                self.assertGreaterEqual(
                    x0, self.LEFT_MARGIN - self.TOLERANCE,
                    msg=f"page {pn}: frame "
                        f"{getattr(item, 'anname', '')!r} x_min={x0:.1f} "
                        f"< left margin {self.LEFT_MARGIN}",
                )
                self.assertLessEqual(
                    x1, pw_mm - self.RIGHT_MARGIN + self.TOLERANCE,
                    msg=f"page {pn}: frame "
                        f"{getattr(item, 'anname', '')!r} x_max={x1:.1f} "
                        f"> right margin {pw_mm - self.RIGHT_MARGIN}",
                )

    def test_specific_drift_fixes(self):
        """Pin the specific T06 fixes."""
        doc = _doc()
        # Page 5: P4 Foto-Spread y_bottom <= 283.5
        f, p = _frame_by_anname(doc, "P4 Foto-Spread")
        bbox = frame_bbox_mm(f, p)
        self.assertLessEqual(
            bbox[3], self.FOOTER_Y_TOP + self.TOLERANCE,
            msg=f"P4 Foto-Spread y_bottom={bbox[3]:.1f} should be <= 283",
        )
        # Page 5: P4 Foto-Spread x range fits body block
        self.assertGreaterEqual(
            bbox[0], self.LEFT_MARGIN - self.TOLERANCE,
            msg=f"P4 Foto-Spread x_min={bbox[0]:.1f} should be >= 20",
        )
        # Page 4: P3 Hero w == col-3 width (54.67mm) within tolerance
        f, p = _frame_by_anname(doc, "P3 Hero")
        bbox = frame_bbox_mm(f, p)
        self.assertLessEqual(
            bbox[2], 190.0 + self.TOLERANCE,
            msg=f"P3 Hero x_max={bbox[2]:.1f} should be <= 190 "
                f"(body-block inner margin)",
        )
        # Page 12: P11 Bottom y_bottom <= 283 + tol
        f, p = _frame_by_anname(doc, "P11 Bottom")
        bbox = frame_bbox_mm(f, p)
        self.assertLessEqual(
            bbox[3], self.FOOTER_Y_TOP + self.TOLERANCE,
            msg=f"P11 Bottom y_bottom={bbox[3]:.1f} should be <= 283",
        )

    def test_excluded_pages_match_meta_yml(self):
        """meta.yml::body_block_margins.excluded_pages == [1, 2, 10, 11, 14].

        Pins the feature-page list so any future change is a deliberate
        meta.yml edit, not an accidental drift.
        """
        from sla_lib.builder.meta_schema import load_band_spec
        spec = load_band_spec("zeitung-a4-grun")
        self.assertIsNotNone(spec, "Zeitung must declare body_block_margins")
        excluded = spec.get("excluded_pages", [])
        self.assertEqual(
            sorted(excluded), [1, 2, 10, 11, 14],
            msg=f"excluded_pages drifted: got {excluded}",
        )

    def test_background_decoration_full_bleed_OK(self):
        """Pages 12 (page11 var) and 13 (page12 var) have full-bleed
        Dunkelgrün decoration polygons / image-less ImageFrames; they
        are exempt from the band rule. Verify each page has at least
        one such full-bleed decoration AND the page passes
        ``_BandConsistencyRule`` (zero ERRORs).
        """
        from sla_lib.builder.brand_constraints import _BandConsistencyRule
        from sla_lib.builder.primitives import ImageFrame, Polygon
        doc = _doc()
        bg_fills = {"Dunkelgrün", "Hellgrün", "Magenta", "Gelb", "White"}
        # page11 (var) = page 12 (1-idx); page12 (var) = page 13 (1-idx).
        for own_page in (11, 12):
            page = doc.pages[own_page]
            decoration_count = 0
            for item in page.items:
                fill = getattr(item, "fill", None)
                if fill not in bg_fills:
                    continue
                if isinstance(item, Polygon):
                    decoration_count += 1
                elif isinstance(item, ImageFrame):
                    has_image = bool(
                        item.image or item.src
                        or getattr(item, "inline_image_data", None)
                    )
                    if not has_image:
                        decoration_count += 1
            self.assertGreaterEqual(
                decoration_count, 1,
                msg=f"page own_page={own_page} should have at least one "
                    f"background-decoration frame",
            )
        # And the rule itself must report zero ERRORs on body-pool pages.
        rule = _BandConsistencyRule(
            id="brand:band_consistency", name="", description="",
        )
        violations = rule.check(list(doc.iter_all_primitives()), doc)
        self.assertEqual(
            violations, [],
            msg=f"_BandConsistencyRule must pass post-T06; got "
                f"{[v.message for v in violations]}",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
