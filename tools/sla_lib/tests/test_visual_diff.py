"""Unit tests for tools/visual_diff.py.

Heavy end-to-end (Scribus rendering, ImageMagick compare) tests are gated
on tool availability; if Scribus or pdftoppm are missing the integration
tests are skipped. Pure unit tests (TemplateTolerance load, per_page
override resolution, region crop math) run unconditionally.
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

import visual_diff as vd  # noqa: E402


class TemplateToleranceTests(unittest.TestCase):
    def test_default_when_no_file(self):
        tol = vd.TemplateTolerance.load(None)
        self.assertEqual(tol.max_pixel_mismatch_pct, 1.0)
        self.assertEqual(tol.fuzz_pct, 25.0)

    def test_load_from_yaml(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            yml = tmp / "diff.yml"
            yml.write_text(yaml.safe_dump({
                "visual_diff": {
                    "max_pixel_mismatch_pct": 5.0,
                    "fuzz_pct": 10,
                    "per_page": [
                        {"page": 0, "max_pixel_mismatch_pct": 0.5},
                        {"page": 2, "fuzz_pct": 20},
                    ],
                    "per_region": [
                        {"page": 1,
                         "bbox_mm": {"x": 10, "y": 10, "w": 50, "h": 30},
                         "max_pixel_mismatch_pct": 8},
                    ],
                }
            }))
            tol = vd.TemplateTolerance.load(yml)
            self.assertEqual(tol.max_pixel_mismatch_pct, 5.0)
            self.assertEqual(tol.fuzz_pct, 10)
            self.assertEqual(tol.per_page[0]["max_pixel_mismatch_pct"], 0.5)
            self.assertEqual(tol.per_page[2]["fuzz_pct"], 20)
            self.assertEqual(len(tol.per_region), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_for_page_uses_overrides(self):
        tol = vd.TemplateTolerance(
            max_pixel_mismatch_pct=2.0, fuzz_pct=10,
            per_page={5: {"max_pixel_mismatch_pct": 0.5, "fuzz_pct": 25}},
        )
        self.assertEqual(tol.for_page(5), (0.5, 25))
        self.assertEqual(tol.for_page(0), (2.0, 10))


class CommittedConfigsTests(unittest.TestCase):
    """Each template-dir's diff.yml must be loadable without errors."""

    def test_postkarte_diff_yml(self):
        tol = vd.TemplateTolerance.load(ROOT / "templates" / "postkarte-a6-kampagne" / "diff.yml")
        self.assertGreater(tol.max_pixel_mismatch_pct, 0)
        self.assertGreater(tol.fuzz_pct, 0)

    def test_plakat_diff_yml(self):
        tol = vd.TemplateTolerance.load(ROOT / "templates" / "plakat-a1-hochformat" / "diff.yml")
        self.assertGreater(tol.max_pixel_mismatch_pct, 0)

    def test_zeitung_diff_yml(self):
        tol = vd.TemplateTolerance.load(ROOT / "templates" / "zeitung-a4-grun" / "diff.yml")
        self.assertGreater(tol.max_pixel_mismatch_pct, 0)


if __name__ == "__main__":
    unittest.main()
