"""Tests for brand:band_consistency (Issue #25).

Synthetic Documents — no real-template coordinates. The rule's
behaviour is exercised by patching ``load_band_spec`` to feed a
known band/margin spec into the rule.

Coverage map (one method per ``<done>`` item in T01):
  - skip when template_id empty
  - skip when load_band_spec returns None
  - skip frame with is_full_bleed=True (per-frame opt-in)
  - ERROR when TextFrame y_top < header_y_bot (page-7 drift class)
  - ERROR when ImageFrame y_bottom > footer_y_top (P4 Foto-Spread class)
  - ERROR when content frame x_min < outer margin (LEFT page)
  - ERROR when content frame x_max exceeds inner-margin boundary (LEFT page)
  - skip Polygon with brand-fill full-bleed (background decoration)
  - skip image-less ImageFrame with brand-fill (background decoration)
  - skip content ImageFrame entirely inside free zone
  - skip is_master pages
  - skip pages whose master_name doesn't match links/rechts
  - skip anchor-positioned frames
  - registry presence + severity
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document  # noqa: E402
from sla_lib.builder.primitives import (  # noqa: E402
    Anchor, ImageFrame, Polygon, TextFrame,
)
from sla_lib.builder.brand_constraints import (  # noqa: E402
    BRAND_CONSTRAINTS, BrandRule, _BandConsistencyRule,
)


# Shared band spec mirroring Zeitung (RESEARCH §4) for synthetic tests.
ZEITUNG_LIKE_SPEC: dict = {
    "bands": {
        "header": {"y_top_mm": 20.0, "y_bottom_mm": 49.0},
        "footer": {"y_top_mm": 283.0, "y_bottom_mm": 297.0},
    },
    "margins": {
        "left":  {"outer_mm": 20.0, "inner_mm": 20.0},
        "right": {"outer_mm": 20.0, "inner_mm": 20.0},
    },
    "background_decoration": {
        "fills": ["Dunkelgrün", "Hellgrün", "Magenta", "Gelb", "White"],
    },
}


def _find_rule(rid: str) -> BrandRule:
    for r in BRAND_CONSTRAINTS:
        if r.id == rid:
            return r
    raise AssertionError(f"rule {rid} not in BRAND_CONSTRAINTS")


def _facing_doc(template_id: str = "synth-band-test"):
    """Facing-pages A4 doc with a dummy unknown-side first page.

    The first page uses ``master="cover"`` (no ``links``/``rechts``),
    which makes the rule treat it as unknown-side and skip it. Body-
    pool tests add pages with explicit ``master="links"`` /
    ``master="rechts"`` to exercise the rule.
    """
    d = Document(title="t", template_id=template_id, facing_pages=True)
    d.add_page(size="A4", bleed_mm=3.0, master="cover")  # unknown-side; skipped
    return d


def _patch_spec(spec):
    """Patch the meta_schema.load_band_spec used by the rule."""
    return patch(
        "sla_lib.builder.meta_schema.load_band_spec",
        return_value=spec,
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class BandConsistencyRegistryTests(unittest.TestCase):
    def test_rule_in_registry(self):
        rule = _find_rule("brand:band_consistency")
        self.assertIsInstance(rule, _BandConsistencyRule)

    def test_severity_is_error(self):
        rule = _find_rule("brand:band_consistency")
        self.assertEqual(rule.severity, "error")


# ---------------------------------------------------------------------------
# Skip semantics
# ---------------------------------------------------------------------------
class BandConsistencySkipTests(unittest.TestCase):
    def test_empty_template_id_returns_zero(self):
        d = Document(title="t", template_id="", facing_pages=True)
        d.add_page(size="A4", bleed_mm=3.0, master="links")
        d.pages[0].add(TextFrame(
            x_mm=10, y_mm=10, w_mm=20, h_mm=20, anname="X", text="x"))
        rule = _find_rule("brand:band_consistency")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_missing_spec_returns_zero(self):
        d = _facing_doc()
        d.add_page(size="A4", bleed_mm=3.0, master="rechts")
        d.pages[1].add(TextFrame(
            x_mm=10, y_mm=10, w_mm=20, h_mm=20, anname="X", text="x"))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(None):
            self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_is_full_bleed_frame_is_skipped(self):
        """Per-frame opt-in: is_full_bleed=True bypasses the rule."""
        d = _facing_doc()
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 2 LEFT
        # Frame WOULD violate (y_top=0 above header band, x_min=-3 past
        # outer margin) but is_full_bleed=True opts out.
        d.pages[1].add(ImageFrame(
            x_mm=-3, y_mm=0, w_mm=216, h_mm=160,
            image="cover.jpg", anname="CoverPhoto",
            is_full_bleed=True))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_unknown_side_master_returns_zero(self):
        d = _facing_doc()
        # master="something" doesn't match links|rechts — skip silently.
        d.add_page(size="A4", bleed_mm=3.0, master="weird")
        d.add_page(size="A4", bleed_mm=3.0, master="weird")
        d.add_page(size="A4", bleed_mm=3.0, master="weird")  # body page
        d.pages[3].add(TextFrame(
            x_mm=30, y_mm=10, w_mm=50, h_mm=10,
            anname="WouldDriftIfChecked", text="x"))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_master_pages_are_skipped(self):
        d = _facing_doc()
        # Add a page-level master in the masters list directly.
        d.add_master(name="master-links", size="A4", bleed_mm=3.0)
        d.masters[-1].master_name = "master-links"
        # Master pages are tracked separately; they have is_master=True
        # and won't appear in `doc.pages`. Verify the rule returns []
        # for a doc with only the dummy unknown-side page + masters.
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_anchor_positioned_frames_are_skipped(self):
        d = _facing_doc()
        d.add_page(size="A4", bleed_mm=3.0, master="links")
        d.add_page(size="A4", bleed_mm=3.0, master="rechts")  # page 3 RIGHT body
        # Frame with explicit anchor — would otherwise drift into header band.
        # ``anchor`` non-None marks the frame as anchor-positioned (mirrors
        # _BleedCoverageRule's anchor skip).
        d.pages[2].add(TextFrame(
            x_mm=10, y_mm=10, w_mm=20, h_mm=20,
            anchor=Anchor(h="center", v="center", margin_mm=10),
            anname="AnchoredIcon", text="x"))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])


# ---------------------------------------------------------------------------
# Band-intrusion (vertical) ERRORs
# ---------------------------------------------------------------------------
class BandConsistencyVerticalErrorTests(unittest.TestCase):
    def test_text_top_in_header_band_fires(self):
        """page-7 drift class: TextFrame y_top=37 < header band bottom=49."""
        d = _facing_doc()
        d.add_page(size="A4", bleed_mm=3.0, master="links")
        d.add_page(size="A4", bleed_mm=3.0, master="rechts")  # page 3
        # y_mm=37 with h=200 → y_top=37 (in header band), y_bottom=237.
        d.pages[2].add(TextFrame(
            x_mm=30, y_mm=37, w_mm=50, h_mm=200,
            anname="BodyText37", text="x"))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertGreaterEqual(len(vs), 1)
        self.assertTrue(any(v.severity == "error" for v in vs))
        self.assertTrue(any("BodyText37" in v.message for v in vs))
        self.assertTrue(any("page 3" in v.message for v in vs))

    def test_image_bottom_in_footer_band_fires(self):
        """P4 Foto-Spread class: ImageFrame y_bottom=297 > footer top=283."""
        d = _facing_doc()
        d.add_page(size="A4", bleed_mm=3.0, master="links")
        d.add_page(size="A4", bleed_mm=3.0, master="rechts")  # page 3
        # y_mm=189, h=108 → y_bottom=297 (intrudes into footer).
        d.pages[2].add(ImageFrame(
            x_mm=20, y_mm=189, w_mm=170, h_mm=108,
            image="dummy.jpg", anname="P4 Foto-Spread"))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertGreaterEqual(len(vs), 1)
        self.assertTrue(any("P4 Foto-Spread" in v.message for v in vs))


# ---------------------------------------------------------------------------
# Margin-drift (horizontal) ERRORs
# ---------------------------------------------------------------------------
class BandConsistencyHorizontalErrorTests(unittest.TestCase):
    def test_left_page_x_below_outer_margin_fires(self):
        """LEFT page: outer = left edge. x0=10 < outer_mm=20 → ERROR."""
        d = _facing_doc()
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 2 (ignored: is body LEFT but the body content is added to page 3)
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 3 - LEFT body
        # Wait - page 3 has master="links" so SIDE_RX matches "links" → LEFT.
        # But page 3 master detection needs links in the master_name. Yes.
        # x_mm=10 → drifts past LEFT outer margin (20mm).
        d.pages[2].add(TextFrame(
            x_mm=10, y_mm=60, w_mm=50, h_mm=100,
            anname="LeftDrift", text="x"))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            vs = rule.check(list(d.iter_all_primitives()), d)
        # Expect at least one margin-drift ERROR mentioning LeftDrift.
        msgs = [v.message for v in vs]
        self.assertTrue(any("LeftDrift" in m and "exceeds margin" in m
                            for m in msgs),
                        f"expected margin-drift ERROR, got: {msgs}")

    def test_left_page_x_max_exceeds_inner_boundary_fires(self):
        """LEFT page: inner = right edge. x_max=200 > 210-20=190 → ERROR."""
        d = _facing_doc()
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 2 (ignored: is body LEFT but the body content is added to page 3)
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 3 - LEFT body
        # x_mm=140, w=60 → x_max=200 → past inner boundary (190).
        d.pages[2].add(TextFrame(
            x_mm=140, y_mm=60, w_mm=60, h_mm=100,
            anname="RightInnerDrift", text="x"))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            vs = rule.check(list(d.iter_all_primitives()), d)
        msgs = [v.message for v in vs]
        self.assertTrue(any("RightInnerDrift" in m and "exceeds margin" in m
                            for m in msgs),
                        f"expected margin-drift ERROR, got: {msgs}")

    def test_footer_band_frame_outside_outer_margin_is_exempt(self):
        """Page-number frame entirely in footer band at x=8.5 (LEFT outer
        margin alley) is allowed — band content has its own placement.

        Body-margin spec applies to body content, not band content. Page
        numbers traditionally sit in the outer-margin alley below body.
        """
        d = _facing_doc()
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 2 (ignored: is body LEFT but the body content is added to page 3)
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 3 - LEFT body
        # Page-number frame: y=283.7, h=9.5 (entirely in footer band 283-297)
        # at x=8.5 (past LEFT outer margin 20mm). Allowed.
        d.pages[2].add(TextFrame(
            x_mm=8.5, y_mm=283.7, w_mm=12.8, h_mm=9.5,
            anname="page-num-left", text="3"))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(vs, [],
                         f"page-number frame in footer band should be exempt "
                         f"from horizontal margin check, got: "
                         f"{[v.message for v in vs]}")

    def test_header_band_frame_outside_outer_margin_is_exempt(self):
        """Symmetrically, header-band-only frames (breadcrumb headers)
        may extend past margins. Body-margin spec applies to free-zone
        content only."""
        d = _facing_doc()
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 2 (ignored: is body LEFT but the body content is added to page 3)
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 3 - LEFT body
        d.pages[2].add(TextFrame(
            x_mm=8.5, y_mm=25.0, w_mm=12.8, h_mm=9.5,
            anname="header-page-num", text="3"))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(vs, [],
                         f"header-band frame should be exempt from horizontal "
                         f"margin check, got: {[v.message for v in vs]}")


# ---------------------------------------------------------------------------
# Background-decoration exemption
# ---------------------------------------------------------------------------
class BandConsistencyDecorationTests(unittest.TestCase):
    def test_polygon_brand_fill_fullbleed_is_exempt(self):
        """Dunkelgrün polygon extending past bands is decoration → no ERROR."""
        d = _facing_doc()
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 2 (ignored: is body LEFT but the body content is added to page 3)
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 3 - LEFT body
        # Full-bleed Dunkelgrün polygon: x=-3, w=216, y=-3, h=303.
        d.pages[2].add(Polygon(
            x_mm=-3, y_mm=-3, w_mm=216, h_mm=303,
            fill="Dunkelgrün", anname="page-bg"))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(vs, [],
                         f"Polygon Dunkelgrün decoration should be exempt, "
                         f"got: {[v.message for v in vs]}")

    def test_imageless_imageframe_brand_fill_is_exempt(self):
        """Image-less ImageFrame with brand fill is treated as decoration."""
        d = _facing_doc()
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 2 (ignored: body content is added to page 3)
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 3
        # No image / src / inline_image_data → image-less.
        d.pages[2].add(ImageFrame(
            x_mm=-3, y_mm=-3, w_mm=216, h_mm=303,
            fill="Hellgrün", anname="imageless-bg"))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(vs, [],
                         f"image-less ImageFrame Hellgrün should be exempt, "
                         f"got: {[v.message for v in vs]}")

    def test_imageframe_with_image_is_NOT_decoration_even_if_brand_fill(self):
        """Image content + brand fill is NOT decoration — content frame."""
        d = _facing_doc()
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 2 (ignored: body content is added to page 3)
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 3
        # Image content + Dunkelgrün fill is still a content frame.
        # Place to drift outside margins to confirm non-decoration path.
        d.pages[2].add(ImageFrame(
            x_mm=10, y_mm=60, w_mm=50, h_mm=100,
            image="dummy.jpg", fill="Dunkelgrün", anname="contentful"))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertGreaterEqual(len(vs), 1,
                                "image-bearing frame must be checked even "
                                "with brand fill")
        self.assertTrue(any("contentful" in v.message for v in vs))


# ---------------------------------------------------------------------------
# Clean cases — no violations
# ---------------------------------------------------------------------------
class BandConsistencyCleanTests(unittest.TestCase):
    def test_content_frame_inside_free_zone_no_violations(self):
        """Image at y=60-200 inside free zone (49-283) and 20-190 → clean."""
        d = _facing_doc()
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 2 (ignored: body content is added to page 3)
        d.add_page(size="A4", bleed_mm=3.0, master="links")  # page 3 LEFT body
        d.pages[2].add(ImageFrame(
            x_mm=20, y_mm=60, w_mm=170, h_mm=140,
            image="dummy.jpg", anname="content-img"))
        d.pages[2].add(TextFrame(
            x_mm=20, y_mm=210, w_mm=170, h_mm=70,
            anname="body-text", text="x"))
        rule = _find_rule("brand:band_consistency")
        with _patch_spec(ZEITUNG_LIKE_SPEC):
            vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(vs, [], f"clean page must produce no ERRORs, "
                                 f"got: {[v.message for v in vs]}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
