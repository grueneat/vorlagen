"""Template-anchored regression tests for the four 26-03-flyer-a6-hochformat-
portrait layout fixes — proven against the re-imported template.sla.

Skipped when the template SLA is not present (sparse worktree).
"""
from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


HERE = Path(__file__).resolve()
WORKTREE = HERE.parents[2]
ANCHOR = WORKTREE / "templates" / "flyer-a6-hochformat-portraet"
SLA = ANCHOR / "template.sla"


@unittest.skipUnless(SLA.exists(), f"anchor template SLA not present at {SLA}")
class FlyerA6PortraitLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(SLA).getroot()
        cls.pos = {
            po.get("ANNAME"): po
            for po in cls.root.iter("PAGEOBJECT")
            if po.get("ANNAME")
        }

    def test_logo_scaletype_is_auto_fit(self):
        """Defect 1 — the DIE GRÜNEN logo (u116b) renders via SCALETYPE=0
        (auto-fit). SCALETYPE=1 + a literal local_scale triggers the Scribus
        1.6.x white-on-transparent bug and renders the logo blank."""
        po = self.pos.get("u116b")
        self.assertIsNotNone(po, "logo frame u116b missing from SLA")
        self.assertEqual(
            po.get("SCALETYPE"), "0",
            "logo must use SCALETYPE=0 (auto-fit), not free scaling",
        )

    def test_three_line_headline_split_into_single_line_frames(self):
        """Defect 2 — the mixed-font 3-line headline (u1175) is emitted as
        three single-line frames stacked at the IDML leading."""
        for anname in ("u1175", "u1175_l2", "u1175_l3"):
            self.assertIn(anname, self.pos, f"{anname} headline frame missing")

    def test_page2_headline_split_into_single_line_frames(self):
        """Defect 3 — the mixed-font 2-line page-2 headline (u1214) is
        emitted as two single-line frames."""
        for anname in ("u1214", "u1214_l2"):
            self.assertIn(anname, self.pos, f"{anname} headline frame missing")

    def test_vollkorn_split_line_uses_rendered_ink_correction(self):
        """The Vollkorn accent line of a split headline must stack with the
        recalibrated 0.15 FLOP correction, not the old 0.345.

        Each split frame's YPOS (points) is line-1-y + N*Leading minus a
        per-font correction. For the Vollkorn line that correction is
        ``0.15*fontsize`` upward; the old 0.345 placed it ``0.195*fontsize``
        too high (rendered 5-8pt above the baseline ink). This pins the
        rendered-ink-calibrated geometry on both split headlines.
        """
        # Page-1 headline u1175: 38pt, IDML leading 34.13430472639402pt.
        leading_p1 = 34.13430472639402
        y1 = float(self.pos["u1175"].get("YPOS"))
        y2 = float(self.pos["u1175_l2"].get("YPOS"))
        y3 = float(self.pos["u1175_l3"].get("YPOS"))
        corr_p1 = 0.15 * 38.0  # Vollkorn line correction in points
        self.assertAlmostEqual(y2, y1 + leading_p1 - corr_p1, delta=0.5)
        self.assertAlmostEqual(y3, y1 + 2 * leading_p1, delta=0.5)
        # Page-2 headline u1214: 30pt, IDML leading 27.0pt.
        p1 = float(self.pos["u1214"].get("YPOS"))
        p2 = float(self.pos["u1214_l2"].get("YPOS"))
        corr_p2 = 0.15 * 30.0
        self.assertAlmostEqual(p2, p1 + 27.0 - corr_p2, delta=0.5)

    def test_no_pageobject_emits_linespmode_2(self):
        """Defects 2/3/4 — no <para>/<trail> may carry LINESPMode=2.

        Mode 2 is Scribus's baseline-grid mode (renders wider than LINESP);
        the converter now pins fixed leading with LINESPMode=0.
        """
        offenders = []
        for po in self.root.iter("PAGEOBJECT"):
            for el in po.iter():
                if el.tag in ("para", "trail", "DefaultStyle"):
                    if el.get("LINESPMode") == "2":
                        offenders.append((po.get("ANNAME"), el.tag))
        self.assertEqual(offenders, [], f"LINESPMode=2 leaked: {offenders}")

    def test_citation_leading_is_fixed_mode_0(self):
        """Defect 4 — the page-6 citation (ud04) pins LINESPMode=0 so the
        Vollkorn line gaps render at the authored leading, not auto."""
        po = self.pos.get("ud04")
        self.assertIsNotNone(po, "citation frame ud04 missing")
        modes = {
            el.get("LINESPMode")
            for el in po.iter()
            if el.tag in ("para", "trail") and el.get("LINESPMode") is not None
        }
        self.assertTrue(modes, "ud04 emits no LINESPMode override")
        self.assertEqual(modes, {"0"}, f"ud04 leading mode not Fixed: {modes}")

    def test_impressum_carries_valign_center(self):
        """Defect 4 — the CenterAlign Impressum frame (u11fd) emits a
        working VAlign channel (1=center), not ALIGN."""
        po = self.pos.get("u11fd")
        self.assertIsNotNone(po, "Impressum frame u11fd missing")
        self.assertEqual(
            po.get("VAlign"), "1",
            "Impressum VerticalJustification=CenterAlign must emit VAlign=1",
        )


if __name__ == "__main__":
    unittest.main()
