"""Tests for tools/headline_spacing_audit.py.

The audit groups stacked single-line headline frames by their anname stem
(``X``, ``X_l2``, ``X_l3`` …), computes the static FLOP=1 inter-baseline gaps
from real font ascents, and flags too-tight / uneven / top-gap-collapse stacks.
Fixtures are built with the Task-1 headline_stack helper and round-tripped
through a real SLA so the static path needs no Scribus render.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document  # noqa: E402
from sla_lib.builder.headline import headline_stack  # noqa: E402
from sla_lib.builder.primitives import Run, TextFrame  # noqa: E402

import headline_spacing_audit as hsa  # noqa: E402

BARLOW = "Raleway Black"
VOLLKORN = "Vollkorn Black Italic"


def _save(doc: Document) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="hsa_")) / "template.sla"
    doc.save(str(tmp))
    return tmp


def _doc_with_stack(frames: list[TextFrame]) -> Document:
    d = Document(title="t", template_id="t")
    d.add_page(size="A4")
    for f in frames:
        d.pages[0].add(f)
    return d


class GroupingTests(unittest.TestCase):
    def test_groups_by_stem(self) -> None:
        frames = headline_stack(
            [("a", BARLOW, 30.0, "White"),
             ("b", VOLLKORN, 30.0, "Gelb"),
             ("c", BARLOW, 30.0, "White")],
            top_y_mm=40.0, x_mm=10.0, w_mm=80.0, h_mm=20.0,
            linesp_pt=27.0, anname_stem="uaf8",
        )
        sla = _save(_doc_with_stack(frames))
        groups = hsa.collect_stacks(sla)
        self.assertEqual(len(groups), 1)
        self.assertEqual([f.anname for f in groups[0].lines],
                         ["uaf8", "uaf8_l2", "uaf8_l3"])

    def test_lone_frame_not_a_stack(self) -> None:
        d = Document(title="t", template_id="t")
        d.add_page(size="A4")
        d.pages[0].add(TextFrame(
            x_mm=10, y_mm=10, w_mm=80, h_mm=20, anname="solo",
            first_line_offset=1,
            runs=[Run(text="x", font=BARLOW, fontsize=30, fcolor="White")],
        ))
        sla = _save(d)
        self.assertEqual(hsa.collect_stacks(sla), [])


class StaticAuditTests(unittest.TestCase):
    def test_even_stack_passes(self) -> None:
        """A metric-corrected mixed-font stack → no violations, exit 0."""
        frames = headline_stack(
            [("Das ist die ", BARLOW, 30.0, "White"),
             ("dreizeilige", VOLLKORN, 30.0, "Gelb"),
             ("Headline", BARLOW, 30.0, "White")],
            top_y_mm=58.68, x_mm=78.5, w_mm=70.7, h_mm=19.4,
            linesp_pt=27.0, anname_stem="uaf8",
        )
        sla = _save(_doc_with_stack(frames))
        report = hsa.audit_static(sla)
        self.assertEqual(report.violations, [])
        self.assertEqual(report.exit_code, 0)

    def test_collapsed_top_gap_flagged(self) -> None:
        """The dreizeilige reproduction: a Vollkorn middle line placed on the
        OLD Gotham-tuned grid (top gap collapses) → top-gap-collapse flag."""
        # Build the pre-fix geometry by hand: frame tops at the frozen
        # Gotham constants (uneven baselines).
        d = Document(title="t", template_id="t")
        d.add_page(size="A4")
        trail = {"LINESPMode": "0", "LINESP": "27.0"}
        for an, y, font in [
            ("uaf8", 58.6807, BARLOW),
            ("uaf8_l2", 66.6182, VOLLKORN),   # too-tight top gap (old constant)
            ("uaf8_l3", 77.7307, BARLOW),
        ]:
            d.pages[0].add(TextFrame(
                x_mm=78.5, y_mm=y, w_mm=70.7, h_mm=19.4, anname=an,
                first_line_offset=1,
                runs=[Run(text="x", font=font, fontsize=30, fcolor="White")],
                trail_attrs=dict(trail),
            ))
        sla = _save(d)
        report = hsa.audit_static(sla)
        kinds = {v.kind for v in report.violations}
        self.assertIn("top_gap_collapse", kinds)
        self.assertNotEqual(report.exit_code, 0)

    def test_uniform_tight_even_stack_passes(self) -> None:
        """A uniformly-tight but EVEN single-font stack above the floor must
        NOT be flagged (no false positive on intentional tightness)."""
        frames = headline_stack(
            [("Zeile eins", BARLOW, 30.0, "White"),
             ("Zeile zwei", BARLOW, 30.0, "White"),
             ("Zeile drei", BARLOW, 30.0, "White")],
            top_y_mm=40.0, x_mm=10.0, w_mm=80.0, h_mm=20.0,
            # 28pt leading on a 30pt font: tight but even and above the
            # 0.85*fontsize=25.5pt floor.
            linesp_pt=28.0, anname_stem="uxx",
        )
        sla = _save(_doc_with_stack(frames))
        report = hsa.audit_static(sla)
        self.assertEqual(report.violations, [])
        self.assertEqual(report.exit_code, 0)

    def test_too_tight_below_floor_flagged(self) -> None:
        """An even stack whose leading is below the absolute floor is flagged
        as too_tight even though it is even."""
        frames = headline_stack(
            [("a", BARLOW, 30.0, "White"),
             ("b", BARLOW, 30.0, "White")],
            top_y_mm=40.0, x_mm=10.0, w_mm=80.0, h_mm=20.0,
            linesp_pt=18.0, anname_stem="utiny",  # 18 < 0.85*30=25.5
        )
        sla = _save(_doc_with_stack(frames))
        report = hsa.audit_static(sla, min_ratio=0.85)
        kinds = {v.kind for v in report.violations}
        self.assertIn("too_tight", kinds)
        self.assertNotEqual(report.exit_code, 0)


class CliTests(unittest.TestCase):
    def test_main_static_only_on_template_dir(self) -> None:
        """--static-only --templates-dir <dir> runs without a render and exits
        0 on an even stack."""
        frames = headline_stack(
            [("a", BARLOW, 30.0, "White"),
             ("b", VOLLKORN, 30.0, "Gelb")],
            top_y_mm=40.0, x_mm=10.0, w_mm=80.0, h_mm=20.0,
            linesp_pt=27.0, anname_stem="u",
        )
        tdir = Path(tempfile.mkdtemp(prefix="hsa_cli_"))
        slug = "demo"
        (tdir / slug).mkdir()
        _doc_with_stack(frames).save(str(tdir / slug / "template.sla"))
        rc = hsa.main(["--slug", slug, "--templates-dir", str(tdir), "--static-only"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
