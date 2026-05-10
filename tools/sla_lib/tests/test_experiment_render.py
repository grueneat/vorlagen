"""Variant-render integration tests (issue #29 T07).

Exercises the pre-Scribus pipeline (manifest validate + variant module
load + scaffold call + inside_page gate + SLA write) end-to-end against
a synthetic 1-hypothesis manifest. The Scribus/rasterise portion is
behind a ``--skip-scribus`` test escape so the suite runs on hosts
without xvfb. A separate guarded test runs the full pipeline if
``xvfb-run scribus`` is available.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import experiment_render as er  # noqa: E402

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _make_manifest(exp_id: str) -> dict:
    return {
        "id": exp_id,
        "subject": "falzflyer-p2-mein-plan",
        "target_weak_area": "test fixture",
        "contributing_llms": ["fixture:a", "fixture:b"],
        "created": "2026-05-10",
        "prompt_version": "test",
        "hypotheses": [
            {
                "slug": f"synthetic-{i:02d}",
                "name": f"Synthetic hypothesis {i}",
                "axis_commitments": ["density"],
                "rationale": "Re-emits production P2 — fixture only.",
                "expected_outcome": "Test fixture; no real expectation.",
                "sources": ["fixture:a"],
                "builder": f"variants/synthetic-{i:02d}.py",
                "wildcard": (i == 1),
            }
            for i in range(1, 11)
        ],
    }


class ExperimentRenderTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_root = Path(self.tmp.name)

        # Mirror the bits of the real repo we need under the temp ROOT.
        # ROOT/experiments/_schema/manifest.schema.yaml — read-only.
        # ROOT/templates/kandidat-falzflyer-din-lang/ — variant_scaffold
        #   needs to import build.py and the shared assets.
        # We can't mirror the whole repo cheaply; instead patch the
        # module's ROOT to the real repo for asset access, and only
        # redirect the experiment + site write paths via a per-test
        # `experiments/<exp_id>/` under the real repo's experiments dir.
        # That works because the manifest's exp_id is a tempdir-unique
        # slug; we clean up after.
        # exp_id must be kebab-case per schema. tempdir names contain
        # an underscore prefix; strip non-[a-z0-9-] chars and clamp.
        raw = self.tmp_root.name.lower().replace("_", "-")
        clean = "".join(c for c in raw if c.isalnum() or c == "-").strip("-")
        self.exp_id = f"test-{clean[-12:]}"
        self.exp_dir = ROOT / "experiments" / self.exp_id
        self.exp_dir.mkdir(parents=True, exist_ok=True)

        # Drop a manifest.
        manifest = _make_manifest(self.exp_id)
        # Trim down to one hypothesis for SLA/render speed; the schema
        # requires >= 10 so we keep all 10 in the manifest (the
        # validator runs first) and pass --only to render just one.
        (self.exp_dir / "manifest.yml").write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

        # Drop variant builder files for the slugs the test exercises.
        variants_dir = self.exp_dir / "variants"
        variants_dir.mkdir(parents=True, exist_ok=True)
        synthetic_src = (FIXTURE_DIR / "synthetic_variant.py").read_bytes()
        for h in manifest["hypotheses"]:
            (variants_dir / Path(h["builder"]).name).write_bytes(synthetic_src)

    def tearDown(self):
        if self.exp_dir.exists():
            shutil.rmtree(self.exp_dir)
        # Also clean any site/public mirror this test produced.
        public = ROOT / "site" / "public" / "experiments" / self.exp_id
        if public.exists():
            shutil.rmtree(public)
        content_md = (
            ROOT / "site" / "src" / "content" / "experiments"
            / f"{self.exp_id}.md"
        )
        if content_md.exists():
            content_md.unlink()
        self.tmp.cleanup()

    def test_skip_scribus_pipeline(self):
        rc = er.run_render(
            exp_id=self.exp_id,
            only="synthetic-01",
            skip_fonts_check=True,
            skip_scribus=True,
        )
        self.assertEqual(rc, 0, "expected exit 0 on skip-scribus path")

        sla_path = self.exp_dir / "variants" / "synthetic-01" / "template.sla"
        self.assertTrue(sla_path.exists(), "SLA must be written")
        self.assertGreater(sla_path.stat().st_size, 1000)

    def test_manifest_json_records_dropped_variants(self):
        # Replace one variant builder with a deliberately overflowing one
        # so we exercise the inside_page DROP path.
        bad = self.exp_dir / "variants" / "synthetic-02.py"
        bad.write_text(
            "def render_p2(doc, page):\n"
            "    from variant_scaffold import render_p2_default\n"
            "    render_p2_default(doc, page)\n"
            "    from sla_lib.builder import TextFrame, Run\n"
            "    page.add(TextFrame(\n"
            "        x_mm=600, y_mm=600, w_mm=200, h_mm=50,\n"
            "        layer=2, style='falzflyer/top-title',\n"
            "        runs=[Run(text='oops',\n"
            "                  paragraph_style='falzflyer/top-title')],\n"
            "        anname='P2 Overflow',\n"
            "    ))\n",
            encoding="utf-8",
        )
        # Render only synthetic-02 so we get a clean DROP signal.
        rc = er.run_render(
            exp_id=self.exp_id,
            only="synthetic-02",
            skip_fonts_check=True,
            skip_scribus=True,
        )
        # rc=0 is fine — drop is non-fatal — but the manifest.json must
        # record the drop.
        self.assertEqual(rc, 0)
        import json
        manifest_json = json.loads(
            (self.exp_dir / "manifest.json").read_text(encoding="utf-8")
        )
        dropped = manifest_json.get("_dropped", [])
        slugs = [d["slug"] for d in dropped]
        self.assertIn("synthetic-02", slugs,
                      f"overflow variant should be dropped; got {slugs}")
        rendered = [h["slug"] for h in manifest_json["hypotheses"]]
        self.assertNotIn("synthetic-02", rendered)

    def test_full_pipeline_with_scribus(self):
        if not shutil.which("scribus") or not shutil.which("xvfb-run"):
            self.skipTest("Scribus / xvfb-run not on PATH")
        rc = er.run_render(
            exp_id=self.exp_id,
            only="synthetic-01",
            skip_fonts_check=False,
            skip_scribus=False,
        )
        self.assertEqual(rc, 0, "full render should exit 0")

        png = self.exp_dir / "variants" / "synthetic-01" / "page-01.png"
        hires = self.exp_dir / "variants" / "synthetic-01" / "page-01-hires.png"
        self.assertTrue(png.exists(), f"missing {png}")
        self.assertTrue(hires.exists(), f"missing {hires}")

        public_png = (
            ROOT / "site" / "public" / "experiments" / self.exp_id
            / "synthetic-01" / "page-01.png"
        )
        self.assertTrue(public_png.exists(), f"site/public mirror missing: {public_png}")


if __name__ == "__main__":
    unittest.main()
