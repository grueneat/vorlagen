"""Results aggregator unit tests (issue #29 T08).

Hand-computed expected values for wins-ratio, disagreement index, and
Spearman rank correlation. Markdown summary is asserted to contain
each required section header.
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


def _vote(a, b, axis, winner, *, position="left", ts="2026-05-10T14:00:00Z"):
    return {
        "pair": {"a": a, "b": b},
        "axis": axis,
        "winner": winner,
        "position_a_on_screen": position,
        "timestamp": ts,
    }


def _payload(votes, *, exp_id="example-experiment", rater="alice",
             direct_picks=None):
    return {
        "experiment_id": exp_id,
        "rater": rater,
        "session_start": "2026-05-10T14:00:00Z",
        "session_end": "2026-05-10T14:30:00Z",
        "votes": votes,
        "direct_picks": direct_picks or [],
        # Aggregator recomputes these from votes; stub values here are
        # ignored once aggregate() runs but must satisfy the schema for
        # the input files.
        "wins_ratio_appeal": {},
        "wins_ratio_transport": {},
        "ranking_appeal": [],
        "ranking_transport": [],
        "disagreement_index": 0.0,
        "spearman_appeal_transport": 0.0,
    }


class WinsRatioTest(unittest.TestCase):

    def test_three_variants_six_votes_per_axis(self):
        # Pairs: (a,b), (a,c), (b,c). 2 votes per pair (appeal +
        # transport) = 6 votes per axis = 12 total.
        # Appeal: a beats b, a beats c, b beats c.
        #   a: 2/2; b: 1/2; c: 0/2.
        # Transport: c beats a, b beats a, c beats b.
        #   a: 0/2; b: 1/2; c: 2/2.
        votes = [
            _vote("a", "b", "appeal", "a"),
            _vote("a", "b", "transport", "b"),
            _vote("a", "c", "appeal", "a"),
            _vote("a", "c", "transport", "c"),
            _vote("b", "c", "appeal", "b"),
            _vote("b", "c", "transport", "c"),
        ]
        wa = er.wins_ratio(votes, "appeal")
        wt = er.wins_ratio(votes, "transport")
        self.assertEqual(wa, {
            "a": {"wins": 2, "plays": 2},
            "b": {"wins": 1, "plays": 2},
            "c": {"wins": 0, "plays": 2},
        })
        self.assertEqual(wt, {
            "a": {"wins": 0, "plays": 2},
            "b": {"wins": 1, "plays": 2},
            "c": {"wins": 2, "plays": 2},
        })

    def test_skip_votes_excluded(self):
        votes = [
            _vote("a", "b", "appeal", "skip"),
            _vote("a", "b", "appeal", None),
            _vote("a", "b", "appeal", "a"),
        ]
        wa = er.wins_ratio(votes, "appeal")
        self.assertEqual(wa, {
            "a": {"wins": 1, "plays": 1},
            "b": {"wins": 0, "plays": 1},
        })

    def test_ranking_orders_desc_by_ratio(self):
        wins = {
            "a": {"wins": 2, "plays": 2},
            "b": {"wins": 1, "plays": 2},
            "c": {"wins": 0, "plays": 2},
        }
        self.assertEqual(er.ranking(wins), ["a", "b", "c"])

    def test_ranking_tie_breaks_by_plays_then_slug(self):
        wins = {
            "a": {"wins": 1, "plays": 2},
            "b": {"wins": 2, "plays": 4},
            "c": {"wins": 0, "plays": 0},
        }
        # a: 0.5 (2 plays); b: 0.5 (4 plays); c: 0 (0 plays).
        # b beats a on plays count.
        self.assertEqual(er.ranking(wins), ["b", "a", "c"])


class DisagreementTest(unittest.TestCase):

    def test_two_of_five_disagree(self):
        # 5 dual-axis pairs; appeal-winner and transport-winner agree
        # on 3, disagree on 2 -> 0.4.
        votes = []
        # pair 1 — both axes pick a
        votes.append(_vote("a", "b", "appeal", "a"))
        votes.append(_vote("a", "b", "transport", "a"))
        # pair 2 — disagree (appeal a, transport b)
        votes.append(_vote("a", "c", "appeal", "a"))
        votes.append(_vote("a", "c", "transport", "c"))
        # pair 3 — both axes pick b
        votes.append(_vote("b", "c", "appeal", "b"))
        votes.append(_vote("b", "c", "transport", "b"))
        # pair 4 — disagree
        votes.append(_vote("a", "d", "appeal", "a"))
        votes.append(_vote("a", "d", "transport", "d"))
        # pair 5 — both axes pick c
        votes.append(_vote("c", "d", "appeal", "c"))
        votes.append(_vote("c", "d", "transport", "c"))

        di, table = er.disagreement_index(votes)
        self.assertAlmostEqual(di, 0.4, places=9)
        self.assertEqual(len(table), 5)
        disagree = [r for r in table if not r["agree"]]
        self.assertEqual(len(disagree), 2)

    def test_single_axis_pair_excluded(self):
        votes = [
            _vote("a", "b", "appeal", "a"),  # only appeal
            _vote("a", "c", "appeal", "a"),
            _vote("a", "c", "transport", "a"),
        ]
        di, table = er.disagreement_index(votes)
        # One dual-axis pair, agreed -> 0.0.
        self.assertEqual(di, 0.0)
        self.assertEqual(len(table), 1)

    def test_no_dual_pairs_returns_zero(self):
        votes = [_vote("a", "b", "appeal", "a")]
        di, table = er.disagreement_index(votes)
        self.assertEqual(di, 0.0)
        self.assertEqual(table, [])


class SpearmanTest(unittest.TestCase):

    def test_identical_rankings(self):
        a = ["x", "y", "z"]
        b = ["x", "y", "z"]
        self.assertAlmostEqual(er.spearman_correlation(a, b), 1.0, places=9)

    def test_reversed_rankings(self):
        a = ["x", "y", "z"]
        b = ["z", "y", "x"]
        self.assertAlmostEqual(er.spearman_correlation(a, b), -1.0, places=9)

    def test_known_partial(self):
        # ranks for shared slugs:
        #   x: a=0, b=1
        #   y: a=1, b=0
        #   z: a=2, b=2
        # Pearson on (0,1,2) vs (1,0,2):
        #   mean_x=1, mean_y=1
        #   numer = (-1)(0) + (0)(-1) + (1)(1) = 1
        #   denom = sqrt(2 * 2) = 2
        #   rho = 0.5
        a = ["x", "y", "z"]
        b = ["y", "x", "z"]
        self.assertAlmostEqual(
            er.spearman_correlation(a, b), 0.5, places=9,
        )

    def test_too_few_common_returns_zero(self):
        self.assertEqual(er.spearman_correlation(["x"], ["y"]), 0.0)


class AggregateAndSummaryTest(unittest.TestCase):

    def test_aggregate_two_files_concatenates_votes(self):
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "alice-1.json"
            p2 = Path(td) / "alice-2.json"
            p1.write_text(json.dumps(_payload(
                [_vote("a", "b", "appeal", "a"),
                 _vote("a", "b", "transport", "b")],
            )), encoding="utf-8")
            p2.write_text(json.dumps(_payload(
                [_vote("a", "c", "appeal", "a"),
                 _vote("a", "c", "transport", "c")],
            )), encoding="utf-8")
            agg = er.aggregate([p1, p2])
            self.assertEqual(len(agg["votes"]), 4)
            self.assertEqual(agg["wins_ratio_appeal"]["a"],
                             {"wins": 2, "plays": 2})
            self.assertEqual(agg["wins_ratio_transport"]["b"],
                             {"wins": 1, "plays": 1})

    def test_aggregate_rejects_invalid_results(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            payload = _payload([_vote("a", "b", "appeal", "a")])
            del payload["disagreement_index"]
            p.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                er.aggregate([p])

    def test_render_summary_contains_required_sections(self):
        votes = [
            _vote("a", "b", "appeal", "a"),
            _vote("a", "b", "transport", "b"),
            _vote("a", "c", "appeal", "a"),
            _vote("a", "c", "transport", "c"),
            _vote("b", "c", "appeal", "b"),
            _vote("b", "c", "transport", "c"),
        ]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "v.json"
            p.write_text(json.dumps(_payload(votes)), encoding="utf-8")
            agg = er.aggregate([p])
        md = er.render_summary(agg, hypotheses={
            "a": {"name": "Alpha", "axis_commitments": ["density"],
                  "rationale": "alpha rationale"},
            "b": {"name": "Beta", "axis_commitments": ["hierarchy"],
                  "rationale": "beta rationale"},
            "c": {"name": "Gamma", "axis_commitments": ["typography"],
                  "rationale": "gamma rationale"},
        })
        for section in (
            "# Results — example-experiment",
            "**Spearman ρ(appeal, transport):**",
            "**Disagreement index:**",
            "## Top 5 by appeal",
            "## Top 5 by transport",
            "## Bottom 3 by appeal",
            "## Bottom 3 by transport",
            "## Per-pair disagreement (top 10)",
            "## Suggested corpus entries",
            "provenance: experiment example-experiment",
        ):
            self.assertIn(section, md, f"summary missing section: {section!r}")


if __name__ == "__main__":
    unittest.main()
