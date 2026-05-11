"""Results aggregator unit tests (issue #31).

Covers the rewritten rank + direct-pick aggregator. Drops the
versus-mode test classes (WinsRatioTest, DisagreementTest, SpearmanTest);
keeps DroppedAndCorpusStubTest verbatim from issue #30.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import experiment_results as er  # noqa: E402


def _rank_payload(
    ranking: list[str],
    *,
    exp_id: str = "example-experiment",
    rater: str = "alice",
    started_at: str = "2026-05-10T14:00:00Z",
    exported_at: str = "2026-05-10T14:30:00Z",
) -> dict:
    return {
        "experiment_id": exp_id,
        "rater": rater,
        "started_at": started_at,
        "exported_at": exported_at,
        "mode": "rank",
        "ranking": ranking,
    }


def _direct_pick_payload(
    selections: list[str],
    *,
    exp_id: str = "example-experiment",
    rater: str = "alice",
    started_at: str = "2026-05-10T14:00:00Z",
    exported_at: str = "2026-05-10T14:30:00Z",
) -> dict:
    return {
        "experiment_id": exp_id,
        "rater": rater,
        "started_at": started_at,
        "exported_at": exported_at,
        "mode": "direct-pick",
        "selections": selections,
    }


def _write_payload(tmpdir: str, name: str, payload: dict) -> Path:
    p = Path(tmpdir) / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


class RankAggregationTest(unittest.TestCase):
    def test_single_rater_four_variants_linear_borda(self):
        scores = er.compute_position_scores(
            ["a", "b", "c", "d"],
            ["a", "b", "c", "d"],
        )
        self.assertAlmostEqual(scores["a"], 1.0, places=9)
        self.assertAlmostEqual(scores["b"], 2 / 3, places=9)
        self.assertAlmostEqual(scores["c"], 1 / 3, places=9)
        self.assertAlmostEqual(scores["d"], 0.0, places=9)

    def test_two_raters_same_ranking_mean_equals_individual(self):
        with tempfile.TemporaryDirectory() as td:
            p1 = _write_payload(
                td, "alice.json", _rank_payload(["a", "b", "c"], rater="alice")
            )
            p2 = _write_payload(
                td, "bob.json", _rank_payload(["a", "b", "c"], rater="bob")
            )
            agg = er.aggregate([p1, p2])
        self.assertAlmostEqual(agg["per_slug"]["a"]["mean_score"], 1.0, places=9)
        self.assertAlmostEqual(agg["per_slug"]["b"]["mean_score"], 0.5, places=9)
        self.assertAlmostEqual(agg["per_slug"]["c"]["mean_score"], 0.0, places=9)
        self.assertEqual(agg["per_slug"]["a"]["n_raters"], 2)

    def test_two_raters_disjoint_orderings_average_correctly(self):
        # Rater 1: a=1.0, b=0.5, c=0.0
        # Rater 2: a=0.0, b=0.5, c=1.0
        # mean:    a=0.5, b=0.5, c=0.5
        with tempfile.TemporaryDirectory() as td:
            p1 = _write_payload(
                td, "alice.json", _rank_payload(["a", "b", "c"], rater="alice")
            )
            p2 = _write_payload(
                td, "bob.json", _rank_payload(["c", "b", "a"], rater="bob")
            )
            agg = er.aggregate([p1, p2])
        for slug in ("a", "b", "c"):
            self.assertAlmostEqual(
                agg["per_slug"][slug]["mean_score"],
                0.5,
                places=9,
            )
            self.assertEqual(agg["per_slug"][slug]["n_raters"], 2)

    def test_slug_unranked_by_every_rater_is_none(self):
        # Two raters; "d" appears in neither ranking but the test asks
        # for it via all_slugs handling.
        scores_a = er.compute_position_scores(
            ["a", "b", "c"],
            ["a", "b", "c", "d"],
        )
        self.assertIsNone(scores_a["d"])

    def test_single_variant_ranking_avoids_div_by_zero(self):
        scores = er.compute_position_scores(["only"], ["only", "x"])
        self.assertEqual(scores["only"], 1.0)
        self.assertIsNone(scores["x"])

    def test_empty_ranking_returns_all_none(self):
        scores = er.compute_position_scores([], ["a", "b", "c"])
        self.assertEqual(scores, {"a": None, "b": None, "c": None})


class DirectPickFallbackTest(unittest.TestCase):
    def test_one_rater_two_of_four_selected(self):
        scores = er.compute_position_scores_for_direct_pick(
            ["a", "c"],
            ["a", "b", "c", "d"],
        )
        self.assertEqual(scores, {"a": 1.0, "b": None, "c": 1.0, "d": None})

    def test_two_raters_overlapping_subsets(self):
        # Rater 1 picks a, b. Rater 2 picks b, c. Never-selected: d.
        with tempfile.TemporaryDirectory() as td:
            p1 = _write_payload(
                td, "alice.json", _direct_pick_payload(["a", "b"], rater="alice")
            )
            p2 = _write_payload(
                td, "bob.json", _direct_pick_payload(["b", "c"], rater="bob")
            )
            agg = er.aggregate([p1, p2])
        # a, b, c all selected at least once -> mean 1.0
        self.assertEqual(agg["per_slug"]["a"]["mean_score"], 1.0)
        self.assertEqual(agg["per_slug"]["b"]["mean_score"], 1.0)
        self.assertEqual(agg["per_slug"]["c"]["mean_score"], 1.0)
        # a appears for one rater only; b for both
        self.assertEqual(agg["per_slug"]["a"]["n_raters"], 1)
        self.assertEqual(agg["per_slug"]["b"]["n_raters"], 2)
        self.assertEqual(agg["per_slug"]["c"]["n_raters"], 1)


class MixedModeAggregationTest(unittest.TestCase):
    def test_rank_plus_direct_pick_combine(self):
        # Rater 1 (rank): a=1.0, b=0.5, c=0.0
        # Rater 2 (direct-pick): a, c selected -> a=1.0, c=1.0
        # Mean per slug:
        #   a: (1.0 + 1.0) / 2 = 1.0
        #   b: 1.0 (only rater 1; rater 2 didn't select) -> 0.5
        #   c: (0.0 + 1.0) / 2 = 0.5
        with tempfile.TemporaryDirectory() as td:
            p1 = _write_payload(
                td, "alice.json", _rank_payload(["a", "b", "c"], rater="alice")
            )
            p2 = _write_payload(
                td,
                "bob.json",
                _direct_pick_payload(["a", "c"], rater="bob"),
            )
            agg = er.aggregate([p1, p2])
        self.assertAlmostEqual(agg["per_slug"]["a"]["mean_score"], 1.0, places=9)
        self.assertAlmostEqual(agg["per_slug"]["b"]["mean_score"], 0.5, places=9)
        self.assertAlmostEqual(agg["per_slug"]["c"]["mean_score"], 0.5, places=9)
        self.assertEqual(set(agg["modes_seen"]), {"rank", "direct-pick"})

    def test_aggregate_rejects_invalid_results(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            payload = _rank_payload(["a", "b"])
            # Strip required mode -> schema fails.
            del payload["mode"]
            p.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                er.aggregate([p])

    def test_render_summary_contains_required_sections(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write_payload(
                td,
                "alice.json",
                _rank_payload(["alpha", "beta", "gamma"], rater="alice"),
            )
            agg = er.aggregate([p])
        md = er.render_summary(
            agg,
            hypotheses={
                "alpha": {
                    "name": "Alpha",
                    "axis_commitments": ["density"],
                    "rationale": "alpha rationale",
                },
                "beta": {
                    "name": "Beta",
                    "axis_commitments": ["hierarchy"],
                    "rationale": "beta rationale",
                },
                "gamma": {
                    "name": "Gamma",
                    "axis_commitments": ["typography"],
                    "rationale": "gamma rationale",
                },
            },
        )
        for section in (
            "# Results — example-experiment",
            "**Raters:** alice",
            "**Variants placed:**",
            "## Top 3",
            "## Bottom 3",
            "## Suggested corpus entries",
            "## Variants dropped during render",
            "### From v1 (envelope necessity)",
            "### From v2 (density+form findings)",
        ):
            self.assertIn(section, md, f"summary missing section: {section!r}")


class DroppedAndCorpusStubTest(unittest.TestCase):
    """Issue #30 T09: SUMMARY.md surfaces _dropped + dual-section corpus stub.

    Preserved verbatim from issue #30; the corpus stub structure
    (v1 envelope necessity + v2 density+form findings) and the dropped
    section are issue #31's responsibility to maintain unchanged.
    """

    def _agg_with_one_rank(self):
        with tempfile.TemporaryDirectory() as td:
            p = _write_payload(td, "alice.json", _rank_payload(["a", "b"]))
            return er.aggregate([p])

    def test_summary_includes_dropped_section(self):
        agg = self._agg_with_one_rank()
        dropped = [
            {
                "slug": "tiny-body",
                "reason": "envelope: layer1:body_min_pt: ...",
                "violations": [
                    {
                        "rule_id": "layer1:body_min_pt",
                        "message": "fontsize=9pt < 10pt",
                        "severity": "error",
                        "targets": ["P2 Tiny-Body"],
                    },
                ],
            },
        ]
        md = er.render_summary(agg, dropped=dropped)
        self.assertIn("## Variants dropped during render", md)
        self.assertIn("`tiny-body`", md)
        self.assertIn("`layer1:body_min_pt`", md)

    def test_summary_dropped_empty_path(self):
        agg = self._agg_with_one_rank()
        md = er.render_summary(agg)
        self.assertIn("## Variants dropped during render", md)
        self.assertIn("No variants dropped", md)

    def test_summary_includes_corpus_stub(self):
        agg = self._agg_with_one_rank()
        md = er.render_summary(agg)
        self.assertIn(
            "## Corpus update stub (to be amended into design-guide/gruene-corpus.md)",
            md,
        )
        self.assertIn("### From v1 (envelope necessity)", md)
        self.assertIn("### From v2 (density+form findings)", md)


if __name__ == "__main__":
    unittest.main()
