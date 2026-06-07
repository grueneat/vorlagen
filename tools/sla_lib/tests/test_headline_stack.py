"""Tests for the metric-driven stacked-headline baseline corrector.

The corrector emits one single-line TextFrame per visual headline line and
derives each frame's top from the REAL installed-font ascent (FLOP=1), so the
visible inter-baseline gaps are even by construction regardless of which font
sits on which line. These tests pin the SOLVE relation, not magic constants:
for any per-line font mix, `baseline_k = frame_top_k + ascent(font_k, size_k)`
must be evenly spaced by exactly `linesp_pt`.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder.headline import (  # noqa: E402
    font_ascent_mm,
    font_ascent_pt,
    headline_stack,
)
from sla_lib.builder.primitives import Run, TextFrame  # noqa: E402

MM_TO_PT = 72.0 / 25.4

# Fonts the templates actually use. These resolve to committed TTFs in the
# container; the SOLVE-relation assertions below stay font-agnostic so they
# hold even if a metric shifts.
BARLOW = "Barlow Semi Condensed Black"
VOLLKORN = "Vollkorn Black Italic"


def _baselines_pt(frames: list[TextFrame], fonts: list[str], sizes: list[float]) -> list[float]:
    """Compute each frame's rendered baseline (pt) from frame top + ascent."""
    out = []
    for frame, font, size in zip(frames, fonts, sizes):
        out.append(frame.y_mm * MM_TO_PT + font_ascent_pt(font, size))
    return out


class TestFontAscentReader(unittest.TestCase):
    def test_barlow_ascent_is_full_em(self) -> None:
        # Barlow Semi Condensed hhea.ascent == unitsPerEm -> 1.0 * size.
        self.assertAlmostEqual(font_ascent_pt(BARLOW, 30.0), 30.0, places=3)

    def test_vollkorn_ascent_below_em(self) -> None:
        # Vollkorn hhea.ascent == 0.952 * unitsPerEm.
        self.assertAlmostEqual(font_ascent_pt(VOLLKORN, 30.0), 0.952 * 30.0, places=3)

    def test_ascent_scales_linearly_with_size(self) -> None:
        a30 = font_ascent_pt(BARLOW, 30.0)
        a60 = font_ascent_pt(BARLOW, 60.0)
        self.assertAlmostEqual(a60, 2.0 * a30, places=3)

    def test_ascent_mm_matches_pt_conversion(self) -> None:
        self.assertAlmostEqual(
            font_ascent_mm(VOLLKORN, 30.0),
            font_ascent_pt(VOLLKORN, 30.0) / MM_TO_PT,
            places=6,
        )

    def test_reader_is_cached(self) -> None:
        # Repeated calls must not re-shell fc-match; just assert stable values.
        self.assertEqual(font_ascent_pt(BARLOW, 30.0), font_ascent_pt(BARLOW, 30.0))


class TestHeadlineStack(unittest.TestCase):
    def test_mixed_font_stack_has_even_baselines(self) -> None:
        """The canonical dreizeilige case: [Barlow, Vollkorn, Barlow] @ 30pt,
        linesp 27pt. Every inter-baseline gap must equal 27pt by construction."""
        lines = [
            ("Das ist die ", BARLOW, 30.0, "White"),
            ("dreizeilige", VOLLKORN, 30.0, "Gelb"),
            ("Headline", BARLOW, 30.0, "White"),
        ]
        frames = headline_stack(
            lines=lines,
            top_y_mm=58.6807,
            x_mm=78.5,
            w_mm=70.7292,
            h_mm=19.4028,
            linesp_pt=27.0,
            anname_stem="uaf8",
        )
        self.assertEqual(len(frames), 3)
        fonts = [BARLOW, VOLLKORN, BARLOW]
        sizes = [30.0, 30.0, 30.0]
        baselines = _baselines_pt(frames, fonts, sizes)
        gap1 = baselines[1] - baselines[0]
        gap2 = baselines[2] - baselines[1]
        self.assertAlmostEqual(gap1, 27.0, places=3)
        self.assertAlmostEqual(gap2, 27.0, places=3)
        # The whole point of the issue: top gap must NOT collapse vs bottom gap.
        self.assertAlmostEqual(gap1, gap2, places=3)

    def test_uniform_font_stack_reduces_to_even_dy(self) -> None:
        """An all-Barlow stack: equal ascents -> frame tops differ by exactly
        linesp_mm (the correction term cancels)."""
        lines = [
            ("Erste Zeile", BARLOW, 30.0, "White"),
            ("Zweite Zeile", BARLOW, 30.0, "White"),
        ]
        frames = headline_stack(
            lines=lines,
            top_y_mm=40.0,
            x_mm=10.0,
            w_mm=80.0,
            h_mm=20.0,
            linesp_pt=27.0,
            anname_stem="uxx",
        )
        self.assertEqual(len(frames), 2)
        dy_mm = frames[1].y_mm - frames[0].y_mm
        self.assertAlmostEqual(dy_mm, 27.0 / MM_TO_PT, places=4)

    def test_single_line_returns_one_frame_unchanged(self) -> None:
        lines = [("Nur eine Zeile", BARLOW, 30.0, "White")]
        frames = headline_stack(
            lines=lines,
            top_y_mm=33.3,
            x_mm=10.0,
            w_mm=80.0,
            h_mm=20.0,
            linesp_pt=27.0,
            anname_stem="usolo",
        )
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].y_mm, 33.3)
        self.assertEqual(frames[0].anname, "usolo")

    def test_anname_stems_follow_l2_l3_convention(self) -> None:
        lines = [
            ("a", BARLOW, 30.0, "White"),
            ("b", VOLLKORN, 30.0, "Gelb"),
            ("c", BARLOW, 30.0, "White"),
        ]
        frames = headline_stack(
            lines=lines,
            top_y_mm=10.0,
            x_mm=10.0,
            w_mm=80.0,
            h_mm=20.0,
            linesp_pt=27.0,
            anname_stem="uaf8",
        )
        self.assertEqual([f.anname for f in frames], ["uaf8", "uaf8_l2", "uaf8_l3"])

    def test_frames_are_flop1_single_line(self) -> None:
        lines = [
            ("a", BARLOW, 30.0, "White"),
            ("b", VOLLKORN, 30.0, "Gelb"),
        ]
        frames = headline_stack(
            lines=lines,
            top_y_mm=10.0,
            x_mm=10.0,
            w_mm=80.0,
            h_mm=20.0,
            linesp_pt=27.0,
            anname_stem="u",
        )
        for f in frames:
            # FLOP=1 (Font Ascent). None defers to the builder default which is
            # also 1, but we set it explicitly so the audit's static check can
            # rely on it.
            self.assertEqual(f.first_line_offset, 1)
            self.assertEqual(len(f.runs), 1)
            self.assertIsInstance(f.runs[0], Run)
            self.assertEqual(f.trail_attrs, {"LINESPMode": "0", "LINESP": "27.0"})

    def test_runs_carry_font_size_color(self) -> None:
        lines = [("Hallo", VOLLKORN, 42.0, "Gelb")]
        frames = headline_stack(
            lines=lines,
            top_y_mm=10.0,
            x_mm=10.0,
            w_mm=80.0,
            h_mm=20.0,
            linesp_pt=30.0,
            anname_stem="u",
        )
        run = frames[0].runs[0]
        self.assertEqual(run.text, "Hallo")
        self.assertEqual(run.font, VOLLKORN)
        self.assertEqual(run.fontsize, 42.0)
        self.assertEqual(run.fcolor, "Gelb")

    def test_geometry_shared_across_frames(self) -> None:
        lines = [
            ("a", BARLOW, 30.0, "White"),
            ("b", VOLLKORN, 30.0, "Gelb"),
        ]
        frames = headline_stack(
            lines=lines,
            top_y_mm=10.0,
            x_mm=12.5,
            w_mm=66.0,
            h_mm=18.0,
            linesp_pt=27.0,
            anname_stem="u",
        )
        for f in frames:
            self.assertEqual(f.x_mm, 12.5)
            self.assertEqual(f.w_mm, 66.0)
            self.assertEqual(f.h_mm, 18.0)

    def test_mixed_size_stack_stays_even(self) -> None:
        """Even when line sizes differ, baselines are evenly spaced by linesp."""
        lines = [
            ("Big", BARLOW, 40.0, "White"),
            ("small accent", VOLLKORN, 24.0, "Gelb"),
            ("Big again", BARLOW, 40.0, "White"),
        ]
        frames = headline_stack(
            lines=lines,
            top_y_mm=20.0,
            x_mm=10.0,
            w_mm=80.0,
            h_mm=22.0,
            linesp_pt=32.0,
            anname_stem="u",
        )
        baselines = _baselines_pt(
            frames, [BARLOW, VOLLKORN, BARLOW], [40.0, 24.0, 40.0]
        )
        self.assertAlmostEqual(baselines[1] - baselines[0], 32.0, places=3)
        self.assertAlmostEqual(baselines[2] - baselines[1], 32.0, places=3)


if __name__ == "__main__":
    unittest.main()
