"""Regression tests for the known zeitung inside_page overflows.

Anchors the Issue #14 acceptance language: ISSUE.md text said "exactly
two" frames overflow today — both right-edge spread bugs:

  - `P9 Spread` (build.py:1802-1811) — ImageFrame at (210, 0, 210, 126)
    overflowing the right page edge by ~207 mm.
  - Unnamed full-A4 image (build.py:2061-2071) — ImageFrame at
    (210, -0.18, 210.8, 297.18) overflowing by ~207.8 mm.

The new rotation-aware bbox helper added in T01-T02 surfaced a THIRD
real overflow that the issue authors hadn't catalogued:

  - Rotated cover-page polygon `u2950` (build.py:246-256) — Polygon
    at (216.41, 155.57, 148.60, 220.49, rotation_deg=90, fill=Dunkelgrün)
    on the title page. Its rotation-aware bbox spans (-4.08, 155.57)
    to (216.41, 304.17), with worst overshoot 4.17 mm (bottom edge).
    This is the cover's full-bleed Dunkelgrün accent — the upstream
    Scribus original carries the wrong frame size + rotation; the
    polygon should not extend below y=300 (= page_h + bleed). Tracked
    as a follow-up against zeitung (see EXECUTION.md "Discovered
    Issues"); silenced today by the same rule-level
    `brand:inside_page` override that handles the two spread frames.

#16 will fix the two spread frames via SpreadImage migration; the
u2950 follow-up issue will fix the rotated cover-page polygon.
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
    def test_inside_page_finds_the_known_overflows_without_override(self):
        """Three frames overflow today (per discovery during Issue #14):

          1. P9 Spread (the right-edge spread, ~207 mm overshoot).
          2. Unnamed page-12 image (~207.8 mm overshoot).
          3. Rotated cover-page polygon `u2950` (~4.17 mm overshoot).

        ISSUE.md said "exactly two"; the rotation-aware bbox helper in
        T01 surfaced #3, which is silenced by the same rule-level
        zeitung override and tracked as a follow-up. If the count
        grows BEYOND 3 in the future, a real new overflow has been
        introduced — investigate before bumping the assertion.
        """
        doc = _load_zeitung_doc()
        # Construct the rule directly — bypasses meta.yml override entirely.
        rule = _InsidePageRule(
            id="brand:inside_page",
            name="Frames inside page bounds",
            description="(test instance — bypasses brand_overrides)",
        )
        violations = rule.check(list(doc.iter_all_primitives()), doc)
        errors = [v for v in violations if v.severity == "error"]
        self.assertEqual(
            len(errors), 3,
            msg=(
                f"expected exactly 3 inside_page errors today (P9 Spread, "
                f"unnamed page-12 image, rotated u2950 polygon), got "
                f"{len(errors)}: {[v.message for v in errors]}"
            ),
        )
        targets = sorted(t for v in errors for t in v.targets)
        # The two right-edge spread frames the ISSUE.md called out:
        self.assertIn("P9 Spread", targets)
        self.assertTrue(
            any("<unnamed ImageFrame>" in v.message for v in errors),
            msg=(
                f"expected unnamed-ImageFrame error in "
                f"{[v.message for v in errors]}"
            ),
        )
        # The rotated cover-page polygon discovered by T01's rotation-
        # aware bbox helper:
        self.assertIn("u2950", targets)

    def test_inside_page_passes_with_override(self):
        # Use the production structural_check pipeline (override IS active).
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
