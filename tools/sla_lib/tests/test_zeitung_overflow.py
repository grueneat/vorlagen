"""Regression tests for the residual zeitung inside_page overflow.

Issue #16 fixed the two right-edge spread frames in build.py:
  - `P9 Spread` (build.py:1802) — moved from x=210 to x=0 on its own page;
    `anname` preserved so INJECT_MAP and CONSTRAINTS keep resolving.
  - Unnamed full-A4 Dunkelgrün polygon (build.py:2061) — moved from
    page11 (print 12) to page12 (print 13) at x=0.

One residual overflow remains, tracked in GH #39:
  - Rotated cover-page polygon `u2950` (build.py:246-256) — Polygon at
    (216.41, 155.57, 148.60, 220.49, rotation 90°, fill Dunkelgrün).
    Rotation-aware bbox spans (-4.08, 155.57)→(216.41, 304.17), overshooting
    the page bottom by 4.17 mm. Silenced today by the rule-level
    `brand:inside_page` override (which now points at GH #39).
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder.brand_constraints import _InsidePageRule  # noqa: E402


def _load_zeitung_doc():
    """Load templates/zeitung-a4-grun/build.py and return its built doc."""
    build_py = ROOT / "templates" / "zeitung-a4-grun" / "build.py"
    spec = importlib.util.spec_from_file_location("zeitung_build", build_py)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_doc()


class ZeitungInsidePageRegressionTests(unittest.TestCase):
    def test_inside_page_zero_errors_after_u2950_trim(self):
        """After #22 T10 the rotated cover-polygon u2950 was trimmed to
        fit page+bleed; the rule reports zero errors WITHOUT the
        override. T16 will remove the meta.yml override entirely.
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

    def test_inside_page_passes_with_override(self):
        # Use the production structural_check pipeline (override IS active).
        # The override now references GH #39 (the u2950 cover polygon
        # follow-up); the two named frames the original ISSUE.md called
        # out were fixed in #16's T04+T05.
        from sla_lib.builder import structural_check as sc

        report = sc.check_template("zeitung-a4-grun", root=ROOT)
        # No inside_page errors when the override is active.
        inside_page_errors = [
            issue for issue in report.brand_issues
            if issue.severity == "error" and issue.rule_id == "brand:inside_page"
        ]
        self.assertEqual(inside_page_errors, [])
        # And the rule is listed under skipped_brand_rules.
        skipped_ids = {rid for rid, _reason in report.skipped_brand_rules}
        self.assertIn("brand:inside_page", skipped_ids)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
