"""Smoke test: v2 numbered-priority-list-v2 passes envelope gate (issue #30 T11)."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from experiment_envelope import load_envelope, run_envelope  # noqa: E402


def _load_scaffold():
    spec = importlib.util.spec_from_file_location(
        "variant_scaffold",
        ROOT / "templates" / "kandidat-falzflyer-din-lang" / "variant_scaffold.py",
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["variant_scaffold"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_variant():
    spec = importlib.util.spec_from_file_location(
        "_v2_numbered_priority_list",
        ROOT / "experiments" / "falzflyer-p2-mein-plan-v2"
        / "variants" / "numbered-priority-list-v2.py",
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class NumberedPriorityListV2Test(unittest.TestCase):

    def test_builds_and_passes_envelope(self):
        scaffold = _load_scaffold()
        variant = _load_variant()
        doc = scaffold.build_variant_front(variant.render_p2)

        envelope = load_envelope(
            ROOT / "experiments" / "falzflyer-p2-mein-plan-v2",
        )
        violations = run_envelope(doc, envelope)
        errors = [v for v in violations if v.severity == "error"]
        self.assertEqual(
            errors, [],
            f"numbered-priority-list-v2 must pass envelope; got: "
            f"{[(v.rule_id, v.message) for v in errors]}",
        )


if __name__ == "__main__":
    unittest.main()
