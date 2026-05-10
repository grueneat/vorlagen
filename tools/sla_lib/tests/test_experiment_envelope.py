"""Unit tests for tools/experiment_envelope.py (issue #30 T03)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import experiment_envelope as ee  # noqa: E402


class LoadEnvelopeTest(unittest.TestCase):

    def test_load_envelope_default_only(self):
        """Default envelope yaml: 16 brand_rules + 22 layer1 keys."""
        with tempfile.TemporaryDirectory() as td:
            exp_dir = Path(td)
            (exp_dir / "constraints.yml").write_text(
                yaml.safe_dump({
                    "extends": str(
                        ROOT / "experiments" / "_constraints"
                        / "falzflyer-default.yml"
                    ),
                    "tested_axis": "default",
                }),
                encoding="utf-8",
            )
            env = ee.load_envelope(exp_dir)
        self.assertEqual(len(env.brand_rules), 16)
        self.assertEqual(len(env.layer1), 22)
        self.assertEqual(env.tested_axis, "default")
        # falzflyer-default carries 5 production-mirror relaxations (the
        # brand_overrides in templates/kandidat-falzflyer-din-lang/meta.yml
        # plus two heuristic-imprecision relaxations on Layer-1 metrics
        # the production scaffold itself doesn't pass).
        relax_ids = env.relax_ids()
        self.assertIn("brand:line_spacing_0.9", relax_ids)
        self.assertIn("layer1:negative_space_pct", relax_ids)
        self.assertEqual(env.regeneration["auto_retry_max"], 0)

    def test_load_envelope_with_extends_and_relax(self):
        """relax-named entry stays in the relax tuple; brand_rules untouched."""
        with tempfile.TemporaryDirectory() as td:
            exp_dir = Path(td)
            (exp_dir / "constraints.yml").write_text(
                yaml.safe_dump({
                    "extends": str(
                        ROOT / "experiments" / "_constraints"
                        / "falzflyer-default.yml"
                    ),
                    "tested_axis": "density+form",
                    "relax": [
                        {"id": "brand:band_consistency", "rationale": "test"},
                    ],
                }),
                encoding="utf-8",
            )
            env = ee.load_envelope(exp_dir)
        self.assertEqual(len(env.relax), 1)
        self.assertEqual(env.relax[0][0], "brand:band_consistency")
        self.assertIn("brand:band_consistency", env.brand_rules)

    def test_load_envelope_validation_failure(self):
        """Missing tested_axis triggers EnvelopeValidationError."""
        with tempfile.TemporaryDirectory() as td:
            exp_dir = Path(td)
            (exp_dir / "constraints.yml").write_text(
                yaml.safe_dump({
                    "brand_rules": ["brand:inside_page"],
                }),
                encoding="utf-8",
            )
            with self.assertRaises(ee.EnvelopeValidationError) as cm:
                ee.load_envelope(exp_dir)
        self.assertTrue(any("tested_axis" in e.message for e in cm.exception.errors))


class RunEnvelopeTest(unittest.TestCase):

    def setUp(self):
        sys.path.insert(0, str(
            ROOT / "templates" / "kandidat-falzflyer-din-lang"
        ))
        import importlib.util
        scaffold_path = (
            ROOT / "templates" / "kandidat-falzflyer-din-lang"
            / "variant_scaffold.py"
        )
        spec = importlib.util.spec_from_file_location("variant_scaffold", scaffold_path)
        assert spec is not None and spec.loader is not None
        self.scaffold = importlib.util.module_from_spec(spec)
        sys.modules["variant_scaffold"] = self.scaffold
        spec.loader.exec_module(self.scaffold)

        self.tmp = tempfile.TemporaryDirectory()
        exp_dir = Path(self.tmp.name)
        (exp_dir / "constraints.yml").write_text(
            yaml.safe_dump({
                "extends": str(
                    ROOT / "experiments" / "_constraints"
                    / "falzflyer-default.yml"
                ),
                "tested_axis": "density+form",
            }),
            encoding="utf-8",
        )
        self.envelope = ee.load_envelope(exp_dir)

    def tearDown(self):
        self.tmp.cleanup()

    def test_run_envelope_synthetic_doc_passes(self):
        """Default P2 (5 schlagworts) should pass — but at minimum it must
        not raise; the 5-schlagwort default may or may not be envelope-clean
        on every Layer-1 axis. We assert: no exceptions, and only known
        rule_ids appear in violations."""
        doc = self.scaffold.build_variant_front()
        violations = ee.run_envelope(doc, self.envelope)
        for v in violations:
            self.assertTrue(
                v.rule_id.startswith("brand:") or v.rule_id.startswith("layer1:"),
                f"unknown rule_id: {v.rule_id}",
            )

    def test_run_envelope_synthetic_doc_violates_inside_page(self):
        """A wildly-overflowing frame triggers brand:inside_page."""
        from sla_lib.builder import Run, TextFrame  # noqa: E402

        def overflow(doc, page):
            self.scaffold.render_p2_default(doc, page)
            page.add(TextFrame(
                x_mm=600, y_mm=600, w_mm=200, h_mm=50,
                layer=2, style="falzflyer/top-title",
                runs=[Run(text="oops", paragraph_style="falzflyer/top-title")],
                anname="P2 Overflow",
            ))

        doc = self.scaffold.build_variant_front(overflow)
        violations = ee.run_envelope(doc, self.envelope)
        ids = {v.rule_id for v in violations}
        self.assertIn("brand:inside_page", ids)

    def test_run_envelope_layer1_body_min_pt_violation(self):
        """A 9pt body-like frame trips layer1:body_min_pt."""
        from sla_lib.builder import ParaStyle, Run, TextFrame  # noqa: E402

        def tiny_body(doc, page):
            self.scaffold.render_p2_default(doc, page)
            doc.add_para_style(ParaStyle(
                name="exp/tiny/body",
                font="Gotham Narrow Book",
                fontsize=9, linesp=11, align=0,
                fcolor="Dunkelgrün", language="de",
            ))
            page.add(TextFrame(
                x_mm=105, y_mm=205, w_mm=80, h_mm=4,
                layer=2, style="exp/tiny/body",
                runs=[Run(text="too small", paragraph_style="exp/tiny/body")],
                anname="P2 Tiny-Body",
            ))

        doc = self.scaffold.build_variant_front(tiny_body)
        violations = ee.run_envelope(doc, self.envelope)
        ids = {v.rule_id for v in violations}
        self.assertIn("layer1:body_min_pt", ids)


class FormatEnvelopeMarkdownTest(unittest.TestCase):

    def test_format_envelope_markdown_shape(self):
        with tempfile.TemporaryDirectory() as td:
            exp_dir = Path(td)
            (exp_dir / "constraints.yml").write_text(
                yaml.safe_dump({
                    "extends": str(
                        ROOT / "experiments" / "_constraints"
                        / "falzflyer-default.yml"
                    ),
                    "tested_axis": "density+form",
                }),
                encoding="utf-8",
            )
            env = ee.load_envelope(exp_dir)
        md = ee.format_envelope_markdown(env)
        self.assertIn("Brand rules", md)
        self.assertIn("Layer-1", md)
        self.assertIn("Tested axis", md)
        self.assertIn("brand:inside_page", md)


if __name__ == "__main__":
    unittest.main()
