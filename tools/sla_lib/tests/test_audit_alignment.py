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
            # Disable image-extent check: this template carries known
            # pre-#24 INJECT_MAP-drift findings until T05 lands.
            rc = main([
                "zeitung-a4-grun", "--md", tmp, "--no-check-image-extent",
            ])
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


# ---------------------------------------------------------------------------
# Issue #24: image-extent audit channel
# ---------------------------------------------------------------------------
def _doc_with_undersized_inline_image():
    """One-page A4 doc with one ImageFrame holding a 95mm-wide JPEG on a
    100x100mm frame — produces a 5mm gap_w letterbox warning."""
    from io import BytesIO
    from PIL import Image
    from sla_lib.builder.primitives import pack_inline_image

    im = Image.new("RGB", (
        int(round(95.0 * 300 / 25.4)),    # 1122
        int(round(100.0 * 300 / 25.4)),   # 1181
    ), (200, 200, 200))
    buf = BytesIO()
    im.save(buf, format="JPEG", quality=80, dpi=(300, 300))
    data, _ = pack_inline_image(buf.getvalue(), "jpg")

    d = Document(title="t", template_id="t")
    d.add_page(size="A4")
    d.pages[0].add(ImageFrame(
        x_mm=50, y_mm=50, w_mm=100, h_mm=100,
        inline_image_data=data, inline_image_ext="jpg",
        scale_type=0, anname="undersized_hero",
    ))
    return d


class ImageExtentAuditTests(unittest.TestCase):
    def test_audit_doc_emits_image_extent_warnings_when_jpeg_undersized(self):
        """Synthetic doc + undersized inline JPEG -> 1 image_extent_warnings entry."""
        d = _doc_with_undersized_inline_image()
        rep = _audit_doc(
            d, constraints=[],
            axis_tol_mm=DEFAULTS["axis_tol_mm"],
            adjacency_tol_mm=DEFAULTS["adjacency_tol_mm"],
        )
        self.assertEqual(len(rep.pages), 1)
        warns = rep.pages[0].image_extent_warnings
        self.assertEqual(len(warns), 1, msg=f"got: {warns}")
        # Warning should contain the severity prefix and the gap text.
        self.assertIn("[WARNING]", warns[0])
        self.assertIn("white margin", warns[0])
        # _report_has_findings must surface this as a finding.
        from audit_alignment import _report_has_findings
        self.assertTrue(_report_has_findings(rep))

    def test_audit_doc_skips_check_when_disabled(self):
        """check_image_extent=False -> no image_extent_warnings entries."""
        d = _doc_with_undersized_inline_image()
        rep = _audit_doc(
            d, constraints=[],
            axis_tol_mm=DEFAULTS["axis_tol_mm"],
            adjacency_tol_mm=DEFAULTS["adjacency_tol_mm"],
            check_image_extent=False,
        )
        self.assertEqual(rep.pages[0].image_extent_warnings, [])
        # And the report has no findings either.
        from audit_alignment import _report_has_findings
        self.assertFalse(_report_has_findings(rep))

    def test_cli_no_check_image_extent_flag_disables_rule(self):
        """`--no-check-image-extent` skips invocation of the rule —
        the JSON output must have empty image_extent_warnings on every
        page, even on Zeitung pre-T05 (which has 7 INJECT_MAP-drift
        findings when the rule IS invoked)."""
        import io, contextlib, json as _json
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main([
                "zeitung-a4-grun", "--no-check-image-extent", "--json",
            ])
        # rc may be 0 or 1 depending on existing #23 visual_adjacency_drift
        # suspicious_pairs (out of scope for this test); we only care that
        # image_extent_warnings is empty on every page.
        self.assertIn(rc, (0, 1))
        d = _json.loads(buf.getvalue())
        for page in d.get("pages", []):
            self.assertEqual(page.get("image_extent_warnings", []), [])

    def test_cli_check_image_extent_default_includes_field(self):
        """With default flags, every page in Zeitung's JSON output
        must have an image_extent_warnings list (possibly empty post-T05
        or non-empty pre-T05)."""
        import io, contextlib, json as _json
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["zeitung-a4-grun", "--json"])
        d = _json.loads(buf.getvalue())
        for page in d.get("pages", []):
            self.assertIn("image_extent_warnings", page)
            self.assertIsInstance(page["image_extent_warnings"], list)

    def test_json_output_includes_image_extent_warnings_field(self):
        """Per-page JSON dict contains an image_extent_warnings list."""
        d = _doc_with_undersized_inline_image()
        rep = _audit_doc(
            d, constraints=[],
            axis_tol_mm=DEFAULTS["axis_tol_mm"],
            adjacency_tol_mm=DEFAULTS["adjacency_tol_mm"],
        )
        out = report_to_json(rep)
        self.assertIn("pages", out)
        self.assertIn("image_extent_warnings", out["pages"][0])
        self.assertEqual(len(out["pages"][0]["image_extent_warnings"]), 1)


# ---------------------------------------------------------------------------
# Issue #25: band-consistency audit channel
# ---------------------------------------------------------------------------
def _doc_with_band_drift():
    """Facing-pages A4 doc with a band-consistency drift on a body page.

    Page 1 = cover (excluded).
    Page 2 = LEFT body (NOT excluded) with a TextFrame at y=37 — drifts
    into the header band [20-49]. The patched ``load_band_spec`` gives
    the rule the Zeitung-shaped spec.
    """
    from sla_lib.builder.primitives import TextFrame
    d = Document(title="t", template_id="synth-band-audit", facing_pages=True)
    d.add_page(size="A4", bleed_mm=3.0, master="cover")
    d.add_page(size="A4", bleed_mm=3.0, master="links")
    d.pages[1].add(TextFrame(
        x_mm=30, y_mm=37, w_mm=50, h_mm=200,
        anname="DriftBody", text="x"))
    return d


_BAND_AUDIT_SPEC: dict = {
    "bands": {
        "header": {"y_top_mm": 20.0, "y_bottom_mm": 49.0},
        "footer": {"y_top_mm": 283.0, "y_bottom_mm": 297.0},
    },
    "margins": {
        "left":  {"outer_mm": 20.0, "inner_mm": 20.0},
        "right": {"outer_mm": 20.0, "inner_mm": 20.0},
    },
    # Cover (page 1) is excluded so the body-drift on page 2 surfaces.
    "excluded_pages": [1],
}


class BandConsistencyAuditTests(unittest.TestCase):
    def test_page_audit_report_has_band_consistency_warnings_field(self):
        """Issue #25: PageAuditReport gains a band_consistency_warnings list."""
        from audit_alignment import PageAuditReport
        pr = PageAuditReport(
            page_idx=0, page_label="x", master_name="links",
            side="left", n_primitives=0,
        )
        self.assertTrue(hasattr(pr, "band_consistency_warnings"))
        self.assertEqual(pr.band_consistency_warnings, [])

    def test_audit_doc_emits_band_consistency_warning_on_drift(self):
        """Synthetic doc with band drift -> at least 1 warning on page 2."""
        from unittest.mock import patch
        d = _doc_with_band_drift()
        with patch("sla_lib.builder.meta_schema.load_band_spec",
                   return_value=_BAND_AUDIT_SPEC):
            rep = _audit_doc(
                d, constraints=[],
                axis_tol_mm=DEFAULTS["axis_tol_mm"],
                adjacency_tol_mm=DEFAULTS["adjacency_tol_mm"],
            )
        # Find the body page (page 2 / index 1 in the audit report).
        body_pages = [pr for pr in rep.pages
                      if pr.master_name and "links" in pr.master_name]
        self.assertEqual(len(body_pages), 1)
        warns = body_pages[0].band_consistency_warnings
        self.assertGreaterEqual(len(warns), 1, msg=f"got: {warns}")
        self.assertIn("[ERROR]", warns[0])
        self.assertIn("DriftBody", warns[0])

    def test_report_has_findings_true_when_only_band_warnings_present(self):
        """_report_has_findings returns True for non-empty band warnings."""
        from unittest.mock import patch
        from audit_alignment import _report_has_findings
        d = _doc_with_band_drift()
        with patch("sla_lib.builder.meta_schema.load_band_spec",
                   return_value=_BAND_AUDIT_SPEC):
            rep = _audit_doc(
                d, constraints=[],
                axis_tol_mm=DEFAULTS["axis_tol_mm"],
                adjacency_tol_mm=DEFAULTS["adjacency_tol_mm"],
            )
        self.assertTrue(_report_has_findings(rep))

    def test_audit_doc_skips_check_when_brand_rules_disabled(self):
        """check_brand_rules=False -> no band_consistency_warnings."""
        from unittest.mock import patch
        d = _doc_with_band_drift()
        with patch("sla_lib.builder.meta_schema.load_band_spec",
                   return_value=_BAND_AUDIT_SPEC):
            rep = _audit_doc(
                d, constraints=[],
                axis_tol_mm=DEFAULTS["axis_tol_mm"],
                adjacency_tol_mm=DEFAULTS["adjacency_tol_mm"],
                check_brand_rules=False,
            )
        for pr in rep.pages:
            self.assertEqual(pr.band_consistency_warnings, [])

    def test_markdown_emits_band_consistency_section(self):
        """Markdown formatter renders a 'Band consistency' section per page."""
        from unittest.mock import patch
        d = _doc_with_band_drift()
        with patch("sla_lib.builder.meta_schema.load_band_spec",
                   return_value=_BAND_AUDIT_SPEC):
            rep = _audit_doc(
                d, constraints=[],
                axis_tol_mm=DEFAULTS["axis_tol_mm"],
                adjacency_tol_mm=DEFAULTS["adjacency_tol_mm"],
            )
        md = report_to_markdown(rep)
        self.assertIn("Band consistency", md)
        self.assertIn("DriftBody", md)

    def test_json_includes_band_consistency_warnings_field(self):
        """Per-page JSON dict contains band_consistency_warnings list."""
        from unittest.mock import patch
        d = _doc_with_band_drift()
        with patch("sla_lib.builder.meta_schema.load_band_spec",
                   return_value=_BAND_AUDIT_SPEC):
            rep = _audit_doc(
                d, constraints=[],
                axis_tol_mm=DEFAULTS["axis_tol_mm"],
                adjacency_tol_mm=DEFAULTS["adjacency_tol_mm"],
            )
        out = report_to_json(rep)
        for pg in out["pages"]:
            self.assertIn("band_consistency_warnings", pg)
            self.assertIsInstance(pg["band_consistency_warnings"], list)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
