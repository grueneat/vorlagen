"""Tests for tools/audit_alignment.py (Issue #22)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document  # noqa: E402
from sla_lib.builder.primitives import ImageFrame  # noqa: E402
from sla_lib.builder.constraints import same_x  # noqa: E402
from sla_lib.builder.structural_check import (  # noqa: E402
    discover_template_slugs,
)

import audit_alignment  # noqa: E402
from audit_alignment import (  # noqa: E402
    DEFAULTS, _audit_doc, audit_all, audit_template, main,
    report_to_json, report_to_markdown,
)


def _doc_with_two_frames():
    """One-page doc with two frames at x=10, x=12 (drift 2mm)."""
    d = Document(title="t", template_id="t")
    d.add_page(size="A4")
    d.pages[0].add(ImageFrame(
        x_mm=10, y_mm=10, w_mm=50, h_mm=50, anname="A",
    ))
    d.pages[0].add(ImageFrame(
        x_mm=12, y_mm=80, w_mm=50, h_mm=50, anname="B",
    ))
    return d


class AuditDocTests(unittest.TestCase):
    def test_synthetic_doc_flags_axis_near_pair(self):
        """Two frames at x=10/x=12 → exactly one suspicious pair on
        page 1."""
        d = _doc_with_two_frames()
        rep = _audit_doc(
            d, constraints=[],
            axis_tol_mm=DEFAULTS["axis_tol_mm"],
            adjacency_tol_mm=DEFAULTS["adjacency_tol_mm"],
        )
        self.assertEqual(len(rep.pages), 1)
        self.assertEqual(len(rep.pages[0].suspicious_pairs), 1)
        sp = rep.pages[0].suspicious_pairs[0]
        self.assertEqual(sp.kind, "axis-x")
        self.assertEqual({sp.a, sp.b}, {"A", "B"})
        self.assertIn("same_x", sp.suggested)

    def test_synthetic_doc_with_same_x_constraint_silent(self):
        """Same doc + constraints=[same_x('A','B')] → zero suspicious."""
        d = _doc_with_two_frames()
        rep = _audit_doc(
            d, constraints=[same_x("A", "B", name="ab_x")],
            axis_tol_mm=DEFAULTS["axis_tol_mm"],
            adjacency_tol_mm=DEFAULTS["adjacency_tol_mm"],
        )
        self.assertEqual(len(rep.pages), 1)
        self.assertEqual(rep.pages[0].suspicious_pairs, [])
        self.assertEqual(rep.pages[0].declared_pairs, [("A", "B")])


class AuditAllTests(unittest.TestCase):
    def test_audit_all_enumerates_all_templates(self):
        """`audit_all(root=ROOT)` returns one report per discoverable
        slug under templates/."""
        reps = audit_all(root=ROOT)
        slugs = discover_template_slugs(ROOT)
        self.assertEqual([r.slug for r in reps], slugs)
        # All reports build successfully (no fatal_error).
        for r in reps:
            self.assertIsNone(
                r.fatal_error, msg=f"{r.slug} failed: {r.fatal_error}",
            )


class ReportFormatTests(unittest.TestCase):
    def test_json_output_is_valid_dict(self):
        d = _doc_with_two_frames()
        rep = _audit_doc(
            d, constraints=[],
            axis_tol_mm=DEFAULTS["axis_tol_mm"],
            adjacency_tol_mm=DEFAULTS["adjacency_tol_mm"],
        )
        out = report_to_json(rep)
        self.assertIn("slug", out)
        self.assertIn("facing_pages", out)
        self.assertIn("pages", out)
        self.assertIn("fatal_error", out)
        # Should round-trip through json.dumps without error.
        json.dumps(out)

    def test_md_output_is_parseable(self):
        d = _doc_with_two_frames()
        rep = _audit_doc(
            d, constraints=[],
            axis_tol_mm=DEFAULTS["axis_tol_mm"],
            adjacency_tol_mm=DEFAULTS["adjacency_tol_mm"],
        )
        md = report_to_markdown(rep)
        self.assertTrue(md.startswith("# audit_alignment"))
        # When there's a suspicious pair, Markdown contains a same_x or
        # aligned_below skeleton.
        self.assertIn("same_x", md)


class CliTests(unittest.TestCase):
    def test_cli_exits_zero_on_warnings(self):
        """The CLI must always exit 0 — informational tool (locked
        decision #10)."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            tmp = f.name
        try:
            rc = main(["zeitung-a4-grun", "--md", tmp])
            self.assertEqual(rc, 0)
            content = Path(tmp).read_text(encoding="utf-8")
            self.assertTrue(content.startswith("# audit_alignment"))
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_cli_all_writes_output_dir(self):
        """`--all --output-dir` writes one .md per template."""
        slugs = discover_template_slugs(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            rc = main(["--all", "--output-dir", tmp])
            self.assertEqual(rc, 0)
            for slug in slugs:
                p = Path(tmp) / f"{slug}.md"
                self.assertTrue(
                    p.exists(),
                    msg=f"missing {p}: cwd files = {list(Path(tmp).iterdir())}",
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
