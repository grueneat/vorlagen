"""Regression tests for zeitung inside_page + spine_safety + drift rules.

Issue #16 fixed the two right-edge spread frames in build.py.
Issue #22 trimmed the rotated cover-polygon `u2950` and inset the
remaining spine-touching frames; the brand:inside_page override was
removed as a result. GH #39 is closed by #22.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder.brand_constraints import (  # noqa: E402
    _InsidePageRule, _SpineSafetyRule, _VisualAdjacencyDriftRule,
)


def _load_zeitung_module():
    """Load templates/zeitung-a4-grun/build.py module."""
    build_py = ROOT / "templates" / "zeitung-a4-grun" / "build.py"
    spec = importlib.util.spec_from_file_location("zeitung_build", build_py)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_zeitung_doc():
    """Return the built doc."""
    return _load_zeitung_module().build_doc()


class ZeitungInsidePageRegressionTests(unittest.TestCase):
    def test_inside_page_zero_errors_after_u2950_trim(self):
        """After #22 T10 the rotated cover-polygon u2950 was trimmed to
        fit page+bleed; the rule reports zero errors WITHOUT the
        override (which #22 T16 removed from meta.yml).
        """
        doc = _load_zeitung_doc()
        rule = _InsidePageRule(
            id="brand:inside_page",
            name="Frames inside page bounds",
            description="(test instance — bypasses brand_overrides)",
        )
        violations = rule.check(list(doc.iter_all_primitives()), doc)
        errors = [v for v in violations if v.severity == "error"]
        self.assertEqual(
            len(errors), 0,
            msg=(
                f"expected zero inside_page errors after #22 T10 "
                f"u2950 trim, got {len(errors)}: "
                f"{[v.message for v in errors]}"
            ),
        )

    def test_inside_page_passes_after_override_removed(self):
        """After #22 T16 the brand:inside_page override is gone from
        meta.yml. structural_check reports zero inside_page errors AND
        the rule is NOT in skipped_brand_rules.
        """
        from sla_lib.builder import structural_check as sc

        report = sc.check_template("zeitung-a4-grun", root=ROOT)
        inside_page_errors = [
            issue for issue in report.brand_issues
            if issue.severity == "error"
            and issue.rule_id == "brand:inside_page"
        ]
        self.assertEqual(inside_page_errors, [])
        skipped_ids = {rid for rid, _reason in report.skipped_brand_rules}
        self.assertNotIn("brand:inside_page", skipped_ids)


class ZeitungSpineSafetyTests(unittest.TestCase):
    def test_spine_safety_zero_warnings_on_zeitung(self):
        """After #22 T11 (P9 SpreadImage) + T12 (spine inset),
        _SpineSafetyRule reports zero warnings on zeitung."""
        doc = _load_zeitung_doc()
        rule = _SpineSafetyRule(
            id="brand:spine_safety",
            name="Spine safety",
            description="(test instance)",
        )
        violations = rule.check(list(doc.iter_all_primitives()), doc)
        self.assertEqual(
            violations, [],
            msg=(
                f"expected zero spine_safety warnings, got "
                f"{[v.message for v in violations]}"
            ),
        )


class ZeitungVisualAdjacencyDriftTests(unittest.TestCase):
    def test_visual_adjacency_drift_rule_runs_on_zeitung(self):
        """Smoke test: _VisualAdjacencyDriftRule (replaces _UndeclaredDriftRule)
        runs cleanly on the Zeitung document with its CONSTRAINTS list.

        Note: severity is warning, so warnings do NOT fail
        ``structural_check --all``. The post-T07 expectation is that
        Zeitung produces no warnings here because the geometry is fixed
        and tight declarations match. Pre-T07 (during atomic ordering),
        warnings are expected — this test asserts the rule executes
        without raising, not the count.
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
