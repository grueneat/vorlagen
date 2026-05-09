"""Tests for brand:spine_safety rule (Issue #22).

Synthetic facing-pages and single-page docs — independent of any real
template.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document  # noqa: E402
from sla_lib.builder.primitives import (  # noqa: E402
    ImageFrame, Polygon, TextFrame,
)
from sla_lib.builder.brand_constraints import (  # noqa: E402
    BRAND_CONSTRAINTS, BrandRule, _SpineSafetyRule,
)


def _find_rule(rid: str) -> BrandRule:
    for r in BRAND_CONSTRAINTS:
        if r.id == rid:
            return r
    raise AssertionError(f"rule {rid} not in BRAND_CONSTRAINTS")


def _facing_doc():
    """Three-page facing-pages doc: pages[0]=RIGHT (cover, alone),
    pages[1]=LEFT (own_page=1), pages[2]=RIGHT (own_page=2, paired
    with pages[1]).

    The rule SKIPS the cover page (own_page == 0) — see implementation
    note. So tests of spine-safety behavior on RIGHT pages must use
    pages[2], not pages[0]. Tests of LEFT pages use pages[1].

    Mirrors the zeitung layout convention. Master names embed
    'rechts'/'links' which the rule's regex picks up.
    """
    d = Document(title="t", template_id="t", facing_pages=True)
    d.add_master(name="Neue Musterseite rechts", facing="right")
    d.add_master(name="Neue Musterseite links", facing="left")
    d.add_page(size="A4", master="Neue Musterseite rechts")  # idx 0 = COVER (skipped)
    d.add_page(size="A4", master="Neue Musterseite links")   # idx 1 = LEFT
    d.add_page(size="A4", master="Neue Musterseite rechts")  # idx 2 = RIGHT
    return d


def _single_doc():
    """Single-page (non-facing) doc."""
    d = Document(title="t", template_id="t")
    d.add_page(size="A4")
    return d


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class SpineSafetyRegistryTests(unittest.TestCase):
    def test_rule_in_registry(self):
        rule = _find_rule("brand:spine_safety")
        self.assertIsInstance(rule, _SpineSafetyRule)


# ---------------------------------------------------------------------------
# Behavior
# ---------------------------------------------------------------------------
class SpineSafetyBehaviorTests(unittest.TestCase):
    def test_left_page_right_edge_at_spine_warns(self):
        """LEFT page (master 'links'), frame x=0, w=210 → right edge at
        spine → warning."""
        d = _facing_doc()
        d.pages[1].add(ImageFrame(
            x_mm=0, y_mm=0, w_mm=210, h_mm=100, anname="P1 Hero",
        ))
        rule = _find_rule("brand:spine_safety")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "warning")
        self.assertEqual(vs[0].rule_id, "brand:spine_safety")
        self.assertIn("P1 Hero", vs[0].message)
        self.assertIn("LEFT", vs[0].message)

    def test_right_page_left_edge_at_spine_warns(self):
        """RIGHT page (master 'rechts', own_page=2 paired), frame x=0 →
        left edge at spine → warning."""
        d = _facing_doc()
        d.pages[2].add(ImageFrame(
            x_mm=0, y_mm=0, w_mm=100, h_mm=100, anname="P3 Hero",
        ))
        rule = _find_rule("brand:spine_safety")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "warning")
        self.assertIn("P3 Hero", vs[0].message)
        self.assertIn("RIGHT", vs[0].message)

    def test_left_page_right_edge_well_inside_passes(self):
        """LEFT page, frame x=0, w=200 → right edge 10mm inside → no
        warning."""
        d = _facing_doc()
        d.pages[1].add(ImageFrame(
            x_mm=0, y_mm=0, w_mm=200, h_mm=100, anname="P1 Hero",
        ))
        rule = _find_rule("brand:spine_safety")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_right_page_left_edge_well_inside_passes(self):
        """RIGHT page (own_page=2), frame x=10 → 10mm inset → no
        warning."""
        d = _facing_doc()
        d.pages[2].add(ImageFrame(
            x_mm=10, y_mm=0, w_mm=100, h_mm=100, anname="P3 Hero",
        ))
        rule = _find_rule("brand:spine_safety")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_single_page_doc_is_no_op(self):
        """Single-page (facing_pages=False) doc → rule returns [] unconditionally,
        even for a frame at the spine-equivalent position."""
        d = _single_doc()
        d.pages[0].add(ImageFrame(
            x_mm=0, y_mm=0, w_mm=210, h_mm=100, anname="full-bleed",
        ))
        rule = _find_rule("brand:spine_safety")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_spread_image_halves_skipped(self):
        """Frames whose anname matches ' · (left|right)$' are exempt
        (intentional SpreadImage halves)."""
        d = _facing_doc()
        # LEFT page with a SpreadImage left-half: the anname suffix is
        # the exemption key.
        d.pages[1].add(ImageFrame(
            x_mm=0, y_mm=0, w_mm=210, h_mm=100,
            anname="P4 Foto-Spread · left",
        ))
        # RIGHT page (own_page=2, paired) with a SpreadImage right-half.
        d.pages[2].add(ImageFrame(
            x_mm=0, y_mm=0, w_mm=210, h_mm=100,
            anname="P4 Foto-Spread · right",
        ))
        rule = _find_rule("brand:spine_safety")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_unknown_master_emits_one_warning_per_page(self):
        """A page whose master_name doesn't match links/rechts → ONE
        warning per page so the bug surfaces. Cover page (own_page=0)
        is skipped — see implementation note."""
        d = Document(title="t", template_id="t", facing_pages=True)
        # Master without 'links'/'rechts' in its name.
        d.add_master(name="weird", facing="right")
        d.add_page(size="A4", master="weird")  # own_page=0 (cover, skipped)
        d.add_page(size="A4", master="weird")  # own_page=1 → warning
        d.add_page(size="A4", master="weird")  # own_page=2 → warning
        rule = _find_rule("brand:spine_safety")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 2)  # cover skipped, two non-cover warns
        for v in vs:
            self.assertEqual(v.severity, "warning")
            self.assertIn("could not be evaluated", v.message)
            self.assertIn("weird", v.message)

    def test_cover_page_skipped(self):
        """Page own_page == 0 in facing_pages mode stands alone (no
        facing partner) — spine bleed has nowhere to leak; cover-page
        spine-touching frames are NOT flagged."""
        d = _facing_doc()
        # Cover (RIGHT alone) with a frame at the spine-equivalent x=0.
        d.pages[0].add(ImageFrame(
            x_mm=0, y_mm=0, w_mm=210, h_mm=100, anname="Cover Hero",
        ))
        rule = _find_rule("brand:spine_safety")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_rotated_polygon_uses_bbox_not_raw(self):
        """A 90° rotated polygon's rotated bbox right edge approaches
        the spine even if its raw x+w would be far away. Uses
        _frame_bbox_mm internally."""
        d = _facing_doc()
        # Polygon at (x=180, y=0, w=10, h=210), rotation_deg=90 around
        # top-left. Rotated bbox: (180-210, 0)→(180, 0+10) = (-30, 0)→(180, 10).
        # That's far inside (right edge 180, not near spine 210).
        # We need a rotation that actually pushes the bbox toward the spine.
        # Place polygon at (x=20, y=0, w=10, h=190), rotation_deg=270:
        # corners CCW270: (px*cos270 - py*sin270, px*sin270 + py*cos270)
        #                 cos270=0, sin270=-1 → (py, -px)
        #   (0,0)     -> (0, 0)
        #   (10, 0)   -> (0, -10)
        #   (10, 190) -> (190, -10)
        #   (0, 190)  -> (190, 0)
        # Translated by (20, 0): bbox x in [20, 210], y in [-10, 0]
        # So right edge x1 = 210 = spine.
        d.pages[1].add(Polygon(
            x_mm=20, y_mm=0, w_mm=10, h_mm=190, rotation_deg=270,
            fill="Dunkelgrün", anname="rotated-band",
        ))
        rule = _find_rule("brand:spine_safety")
        vs = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(vs), 1)
        self.assertEqual(vs[0].severity, "warning")
        self.assertIn("rotated-band", vs[0].message)


# ---------------------------------------------------------------------------
# Master-page items skipped
# ---------------------------------------------------------------------------
class SpineSafetyMasterSkipTests(unittest.TestCase):
    def test_master_page_items_skipped(self):
        d = _facing_doc()
        # Add a spine-touching frame to the master itself.
        d.masters[1].add(ImageFrame(
            x_mm=0, y_mm=0, w_mm=210, h_mm=100, anname="master-bg",
        ))
        rule = _find_rule("brand:spine_safety")
        # Master pages are skipped — no violation.
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
