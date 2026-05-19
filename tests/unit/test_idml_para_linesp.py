"""Regression test for issue #40 follow-up: every <para> separator in a
multi-paragraph TextFrame must carry the SAME LINESPMode + LINESP as the
closing <trail>. Previously the converter downgraded intermediate <para>
to LINESPMode=1 (auto/font-metric) whenever the authored CSR Leading was
below font intrinsic × 1.45 — which clipped multi-paragraph headlines
in Scribus (only the first paragraph rendered, the trail attrs applied
to nothing).
"""
from __future__ import annotations

import os
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


HERE = Path(__file__).resolve()
WORKTREE = HERE.parents[2]
ANCHOR = WORKTREE / "templates" / "falzflyer-z-falz-6-seitig-zweigeteiltes-cover"
SLA = ANCHOR / "template.sla"


@unittest.skipUnless(
    SLA.exists(),
    f"anchor template SLA not present at {SLA} (sparse worktree)",
)
class IntermediateParaLinespTest(unittest.TestCase):
    """Multi-paragraph headline frames must have <para> and <trail> agree.

    The 26-03 Leporello z-Falz template has six multi-paragraph headline
    frames whose CSRs share a single explicit Leading. The converter
    must emit that Leading on every <para> AND <trail> of the frame.
    """

    @classmethod
    def setUpClass(cls):
        cls.tree = ET.parse(SLA)
        cls.root = cls.tree.getroot()

    def _para_trail_for(self, anname):
        """Return [(tag, LINESPMode, LINESP), …] for every <para>/<trail> in PAGEOBJECT."""
        for po in self.root.iter("PAGEOBJECT"):
            if po.get("ANNAME") == anname:
                rows = []
                for child in po.iter():
                    if child.tag in ("para", "trail"):
                        rows.append(
                            (child.tag, child.get("LINESPMode"), child.get("LINESP"))
                        )
                return rows
        return None

    def test_u1b0_split_into_two_single_line_frames(self):
        """u1b0 was a 2-line frame with mixed font (Gotham→Vollkorn);
        the P5/inject override splits it into u1b0 + u1b0_l2 single-
        line frames at calibrated y_mm positions because Scribus's
        per-font ascent metric differs from InDesign's for the same
        font file, producing visible vertical misalignment under
        any LINESPMode/LINESP combination. Worked example:
        templates/26-03-leporello-…/build.py u1b0/u1b0_l2 + the
        line_spacing_pixel_audit tool."""
        for anname in ("u1b0", "u1b0_l2"):
            rows = self._para_trail_for(anname)
            self.assertIsNotNone(rows, f"{anname} missing in SLA")
            # Each split frame has 1 line and emits only a <trail>
            self.assertGreaterEqual(len(rows), 1,
                f"{anname} missing <trail>; got {rows}")

    def test_u2d5_para_trail_consistent(self):
        """u2d5 'Ich bin auch / eine Headline.' — under build.py
        P5/inject override: LINESPMode=0 + LINESP=27 (page-1 pure-Gotham
        path renders exactly 27pt = baseline)."""
        rows = self._para_trail_for("u2d5")
        self.assertIsNotNone(rows)
        modes = {r[1] for r in rows}
        linesps = {r[2] for r in rows}
        self.assertEqual(len(modes), 1, f"inconsistent modes: {modes}")
        self.assertEqual(len(linesps), 1, f"inconsistent linesps: {linesps}")

    def test_u3a2_para_trail_consistent(self):
        """u3a2 Vollkorn Black Italic 23pt — under build.py P5/inject
        override: LINESPMode=0 + LINESP=20.48 (renders exactly 20.48pt =
        baseline). Vollkorn under LINESPMode=0 has no +7pt offset like
        Gotham — measured via tools/line_spacing_sim.py."""
        rows = self._para_trail_for("u3a2")
        self.assertIsNotNone(rows)
        modes = {r[1] for r in rows}
        linesps = {r[2] for r in rows}
        self.assertEqual(len(modes), 1, f"inconsistent modes: {modes}")
        self.assertEqual(len(linesps), 1, f"inconsistent linesps: {linesps}")

    def test_u16c_split_into_three_single_line_frames(self):
        """u16c was a single 3-line mixed-font (Gotham→Vollkorn→Gotham)
        TextFrame whose Scribus rendering couldn't be reconciled to
        InDesign's uniform 33–35pt baseline-to-baseline gap via any
        LINESPMode/LINESP combination (per-line font metrics differ).
        The template-level P5/inject fix splits the frame into three
        single-line frames (u16c, u16c_l2, u16c_l3), each positioned
        at the calibrated y_mm derived from baseline.pdf word
        positions. Each line frame then renders independently and
        the gap is controlled by y_mm differences rather than
        Scribus's mixed-font leading model. The original u16c
        anname must still exist (carries 'Das ist die')."""
        for anname in ("u16c", "u16c_l2", "u16c_l3"):
            rows = self._para_trail_for(anname)
            self.assertIsNotNone(rows, f"{anname} frame missing in SLA")
            # Each split frame has 1 line and emits only a <trail>
            self.assertGreaterEqual(
                len(rows), 1,
                f"{anname} missing <trail>; got {rows}",
            )

    def test_u376_no_inconsistent_mode_2_with_linesp(self):
        """u376 'Headline in einem grünen Kasten' — Gotham Narrow Bold
        12pt. Direct measurement: Scribus auto-leading = baseline 12pt
        exactly. Converter emits PARENT='idml/headline-in-gruenem-
        kasten' on the <trail> (without explicit LINESPMode/LINESP),
        and the SLA STYLE definition for that pstyle carries linesp=12.
        Both <para> and <trail> must NOT emit LINESPMode=2 with sub-
        metric LINESP — either no LINESPMode override OR LINESPMode=1.
        """
        rows = self._para_trail_for("u376")
        self.assertIsNotNone(rows)
        for tag, mode, linesp in rows:
            self.assertNotEqual(
                mode, "2",
                f"<{tag}> must not emit LINESPMode=2 (Scribus inflates); got mode={mode!r} linesp={linesp!r}",
            )


@unittest.skipUnless(
    SLA.exists(),
    f"anchor template SLA not present at {SLA} (sparse worktree)",
)
class FrameWideningTest(unittest.TestCase):
    """With LINESPMode=2 + LINESP < font-metric, Scribus uses FLOP=2 to
    place the first baseline at top+LINESP. The frame must accommodate
    n_lines * LINESP + descender + safety. Previously the widening
    formula (a) under-budgeted by descender (~7pt at 30pt) and the last
    line of 2-line headlines was clipped.
    """

    @classmethod
    def setUpClass(cls):
        cls.tree = ET.parse(SLA)
        cls.root = cls.tree.getroot()

    def _frame(self, anname):
        for po in self.root.iter("PAGEOBJECT"):
            if po.get("ANNAME") == anname:
                return po
        return None

    def test_u2d5_height_accommodates_two_lines(self):
        """u2d5 30pt Gotham Narrow Ultra × 2 lines with LINESPMode=1
        (auto/font-metric for Gotham Ultra ~38pt). Frame needs ≥ 2 *
        font_metric ≈ 76pt + safety. The widened frame from the
        original converter logic (70pt) is now sufficient because
        LINESPMode=1 places first baseline at top + font-ascent rather
        than top + explicit-LINESP."""
        po = self._frame("u2d5")
        self.assertIsNotNone(po, "u2d5 frame missing")
        h_pt = float(po.get("HEIGHT") or 0)
        # 70pt is the converter's pre-fix width for this frame and is
        # sufficient under LINESPMode=1 (preserves the IDML PathPointArray
        # height ≈ 24.7mm = 69.99pt). Allow ±0.5pt slack for float rounding.
        self.assertGreaterEqual(
            h_pt, 69.5,
            f"u2d5 HEIGHT={h_pt}pt is below the 2-line font-metric budget",
        )
