"""Integration tests for envelope-gated experiment_render.py (issue #30 T05)."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import experiment_render as er  # noqa: E402


def _make_manifest(exp_id: str, slug: str) -> dict:
    """Build a 10-hypothesis manifest (schema floor) all pointing at one variant."""
    return {
        "id": exp_id,
        "subject": "falzflyer-p2-mein-plan",
        "target_weak_area": "test fixture",
        "contributing_llms": ["fixture:a", "fixture:b"],
        "created": "2026-05-10",
        "prompt_version": "test",
        "hypotheses": [
            {
                "slug": slug,
                "name": "Envelope-test hypothesis",
                "axis_commitments": ["density"],
                "rationale": "Envelope-test fixture.",
                "expected_outcome": "Test fixture only.",
                "sources": ["fixture:a"],
                "builder": f"variants/{slug}.py",
                "wildcard": True,
            },
        ] + [
            {
                "slug": f"padding-{i:02d}",
                "name": f"Padding hypothesis {i}",
                "axis_commitments": ["density"],
                "rationale": "Schema minItems padding.",
                "expected_outcome": "Test only.",
                "sources": ["fixture:b"],
                "builder": f"variants/padding-{i:02d}.py",
                "wildcard": False,
            }
            for i in range(1, 10)
        ],
    }


class ExperimentRenderEnvelopeTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        raw = Path(self.tmp.name).name.lower().replace("_", "-")
        clean = "".join(c for c in raw if c.isalnum() or c == "-").strip("-")
        self.exp_id = f"test-env-{clean[-8:]}"
        self.exp_dir = ROOT / "experiments" / self.exp_id
        self.exp_dir.mkdir(parents=True, exist_ok=True)

        (self.exp_dir / "constraints.yml").write_text(
            yaml.safe_dump({
                "extends": str(
                    ROOT / "experiments" / "_constraints"
                    / "falzflyer-default.yml"
                ),
                "tested_axis": "density+form",
            }),
            encoding="utf-8",
        )

    def tearDown(self):
        if self.exp_dir.exists():
            shutil.rmtree(self.exp_dir)
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

    def _write_manifest_and_variants(self, slug: str, render_src: str) -> None:
        manifest = _make_manifest(self.exp_id, slug)
        (self.exp_dir / "manifest.yml").write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        variants_dir = self.exp_dir / "variants"
        variants_dir.mkdir(parents=True, exist_ok=True)
        (variants_dir / f"{slug}.py").write_text(render_src, encoding="utf-8")
        for i in range(1, 10):
            (variants_dir / f"padding-{i:02d}.py").write_text(
                "def render_p2(doc, page):\n"
                "    from variant_scaffold import render_p2_default\n"
                "    render_p2_default(doc, page)\n",
                encoding="utf-8",
            )

    def test_render_drops_variant_violating_envelope(self):
        slug = "tiny-body-variant"
        src = (
            "def render_p2(doc, page):\n"
            "    from variant_scaffold import render_p2_default\n"
            "    render_p2_default(doc, page)\n"
            "    from sla_lib.builder import ParaStyle, Run, TextFrame\n"
            "    doc.add_para_style(ParaStyle(\n"
            "        name='exp/tiny/body', font='Gotham Narrow Book',\n"
            "        fontsize=9, linesp=11, align=0,\n"
            "        fcolor='Dunkelgrün', language='de',\n"
            "    ))\n"
            "    page.add(TextFrame(\n"
            "        x_mm=105, y_mm=205, w_mm=80, h_mm=4,\n"
            "        layer=2, style='exp/tiny/body',\n"
            "        runs=[Run(text='too small',\n"
            "                  paragraph_style='exp/tiny/body')],\n"
            "        anname='P2 Tiny-Body',\n"
            "    ))\n"
        )
        self._write_manifest_and_variants(slug, src)
        rc = er.run_render(
            exp_id=self.exp_id, only=slug,
            skip_fonts_check=True, skip_scribus=True,
        )
        self.assertEqual(rc, 0)
        manifest_json = json.loads(
            (self.exp_dir / "manifest.json").read_text(encoding="utf-8")
        )
        dropped = manifest_json.get("_dropped", [])
        slugs = [d["slug"] for d in dropped]
        self.assertIn(slug, slugs, f"variant should be dropped; got {slugs}")
        drop_entry = next(d for d in dropped if d["slug"] == slug)
        self.assertTrue(drop_entry["reason"].startswith("envelope:"))
        rule_ids = {v["rule_id"] for v in drop_entry["violations"]}
        self.assertIn("layer1:body_min_pt", rule_ids)

    def test_render_passes_variant_within_envelope(self):
        slug = "noop-variant"
        src = (
            "def render_p2(doc, page):\n"
            "    from variant_scaffold import render_p2_default\n"
            "    render_p2_default(doc, page)\n"
        )
        self._write_manifest_and_variants(slug, src)
        rc = er.run_render(
            exp_id=self.exp_id, only=slug,
            skip_fonts_check=True, skip_scribus=True,
        )
        self.assertEqual(rc, 0)
        manifest_json = json.loads(
            (self.exp_dir / "manifest.json").read_text(encoding="utf-8")
        )
        dropped = manifest_json.get("_dropped", [])
        slugs = [d["slug"] for d in dropped]
        self.assertNotIn(slug, slugs)


if __name__ == "__main__":
    unittest.main()
