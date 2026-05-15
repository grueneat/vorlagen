"""Tests for sla_diff_strict loader in meta_schema.py (issue #16).

Mirrors the pattern of test_zeitung_overflow.py for ROOT-walking and
sys.path setup. Five tests cover the default-True / explicit-false /
invalid-type / missing-meta paths and a load_brand_overrides smoke
regression.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder.meta_schema import (  # noqa: E402
    load_brand_overrides,
    load_sla_diff_strict,
)


class SlaDiffStrictTests(unittest.TestCase):
    def test_default_true_for_template_without_flag(self):
        # postkarte-a6-quer has no sla_diff_strict key -> defaults True.
        self.assertTrue(load_sla_diff_strict("postkarte-a6-quer"))

    def test_default_true_for_unknown_slug(self):
        # No meta.yml at all -> defaults True.
        self.assertTrue(load_sla_diff_strict("does-not-exist"))

    def test_false_when_meta_opts_out(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "templates" / "fake-tpl"
            tdir.mkdir(parents=True)
            (tdir / "meta.yml").write_text(
                "id: fake-tpl\nsla_diff_strict: false\n"
            )
            self.assertFalse(
                load_sla_diff_strict("fake-tpl", root=Path(td))
            )

    def test_invalid_type_raises(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "templates" / "fake-tpl"
            tdir.mkdir(parents=True)
            (tdir / "meta.yml").write_text(
                'id: fake-tpl\nsla_diff_strict: "no"\n'
            )
            with self.assertRaises(ValueError):
                load_sla_diff_strict("fake-tpl", root=Path(td))

    def test_brand_overrides_loader_unchanged(self):
        # Regression guard: load_brand_overrides() must surface every id in
        # meta.yml::brand_overrides. zeitung's geometry was reset to the
        # original InDesign SLA, which carries full-bleed / cross-page
        # spread images — so brand:inside_page is legitimately overridden
        # again (the rule cannot model an intentional newspaper spread).
        ids = load_brand_overrides("zeitung-a4-grun")
        self.assertIn("brand:line_spacing_0.9", ids)
        self.assertIn("brand:inside_page", ids)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
