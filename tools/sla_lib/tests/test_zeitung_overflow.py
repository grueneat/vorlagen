"""Smoke test for the zeitung visual-adjacency-drift rule.

zeitung-a4-grun's build.py geometry is pinned to a faithful reproduction
of the original InDesign SLA. The earlier inside_page / spine_safety
regression tests asserted the #16/#22 "alignment fix" geometry, which was
reverted — those frame moves wrongly pulled the full-bleed / cross-page
spread images page-local. Geometry correctness is now validated by the
``sla_diff`` round-trip against the original SLA (see ZeitungRoundTrip /
ZeitungConverterFreshRun in test_sla_to_dsl.py); the full-bleed frames
that legitimately cross the page boundary are covered by the documented
``brand:inside_page`` / ``bleed_coverage`` / ``band_consistency``
overrides in meta.yml.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder.brand_constraints import (  # noqa: E402
    _VisualAdjacencyDriftRule,
)


def _load_zeitung_module():
    """Load templates/zeitung-a4-grun/build.py module."""
    build_py = ROOT / "templates" / "zeitung-a4-grun" / "build.py"
    spec = importlib.util.spec_from_file_location("zeitung_build", build_py)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ZeitungVisualAdjacencyDriftTests(unittest.TestCase):
    def test_visual_adjacency_drift_rule_runs_on_zeitung(self):
        """Smoke test: _VisualAdjacencyDriftRule runs cleanly on the
        Zeitung document with its CONSTRAINTS list. severity is warning,
        so it never fails ``structural_check --all``. This asserts the
        rule executes without raising, not the warning count.
        """
        mod = _load_zeitung_module()
        doc = mod.build_doc()
        rule = _VisualAdjacencyDriftRule(
            id="brand:visual_adjacency_drift",
            name="Visual adjacency drift",
            description="(test instance)",
        )
        constraints = getattr(mod, "CONSTRAINTS", []) or []
        violations = rule.check(
            list(doc.iter_all_primitives()), doc,
            constraints=constraints,
        )
        # Just verify the rule executes and returns a list of warnings.
        self.assertIsInstance(violations, list)
        for v in violations:
            self.assertEqual(v.severity, "warning")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
