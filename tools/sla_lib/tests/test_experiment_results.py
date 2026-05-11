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


class EmailImportTest(unittest.TestCase):
    """Issue #33 T05: --from-emails <dir> parser coverage.

    The aggregator's email path extracts JSON between
    VOTE-JSON-START/END markers from .eml or .txt files, validates each
    block against results.schema.yaml, and feeds payloads into
    aggregate_payloads. These tests pin the parser's tolerance for real
    inbox shapes (quoted-reply prefixes, multiple votes per file, mixed
    file extensions) and its hard-error behaviour on malformed input.
    """

    @staticmethod
    def _vote_block(rater: str = "flo", ranking: list[str] | None = None) -> str:
        """Build the exact body shape the voting page emits."""
        payload = {
            "experiment_id": "example-experiment",
            "rater": rater,
            "started_at": "2026-05-11T09:00:00Z",
            "exported_at": "2026-05-11T09:18:00Z",
            "mode": "rank",
            "ranking": ranking or ["alpha", "beta", "gamma"],
        }
        lines = [
            "Hi Flo,",
            "",
            "Here's my ranking for example-experiment:",
            "",
            " 1. alpha  (alpha)",
            " 2. beta   (beta)",
            " 3. gamma  (gamma)",
            "",
            f"— {rater}",
            "2026-05-11T09:18:00Z",
            "",
            "──────────  machine-readable, please don't edit  ──────────",
            "VOTE-JSON-START",
            json.dumps(payload),
            "VOTE-JSON-END",
        ]
        return "\n".join(lines)

    def test_extract_vote_blocks_single(self):
        body = self._vote_block()
        blocks = er.extract_vote_blocks(body)
        self.assertEqual(len(blocks), 1)
        parsed = json.loads(blocks[0])
        self.assertEqual(parsed["rater"], "flo")
        self.assertEqual(parsed["mode"], "rank")

    def test_extract_vote_blocks_zero_when_no_markers(self):
        self.assertEqual(er.extract_vote_blocks("Hi, no markers here."), [])

    def test_valid_file_with_one_vote(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "flo.txt").write_text(self._vote_block(), encoding="utf-8")
            payloads = er.payloads_from_email_dir(Path(td))
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["rater"], "flo")

    def test_valid_file_with_two_votes_concatenated(self):
        # Simulate a forwarded chain where two raters' bodies sit in one file.
        combined = (
            self._vote_block(rater="alice")
            + "\n\n----- Forwarded message -----\n\n"
            + self._vote_block(rater="bob", ranking=["beta", "alpha", "gamma"])
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "chain.txt").write_text(combined, encoding="utf-8")
            payloads = er.payloads_from_email_dir(Path(td))
        self.assertEqual(len(payloads), 2)
        raters = sorted(p["rater"] for p in payloads)
        self.assertEqual(raters, ["alice", "bob"])

    def test_file_missing_markers_emits_warning_and_skips(self):
        warnings: list[str] = []
        errors: list[str] = []
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "unrelated.txt").write_text(
                "Hi Flo,\n\nNo vote here, just a note.\n",
                encoding="utf-8",
            )
            payloads = er.payloads_from_email_dir(
                Path(td),
                on_warning=warnings.append,
                on_error=errors.append,
            )
        self.assertEqual(payloads, [])
        self.assertEqual(len(warnings), 1, f"expected 1 warning, got: {warnings}")
        self.assertIn("no VOTE-JSON-START/END markers", warnings[0])
        self.assertIn("unrelated.txt", warnings[0])
        self.assertEqual(errors, [])

    def test_file_with_malformed_json_emits_error_and_skips(self):
        warnings: list[str] = []
        errors: list[str] = []
        bad = (
            "VOTE-JSON-START\n"
            "{not real json, definitely broken,\n"
            "VOTE-JSON-END\n"
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "bad.txt").write_text(bad, encoding="utf-8")
            payloads = er.payloads_from_email_dir(
                Path(td),
                on_warning=warnings.append,
                on_error=errors.append,
            )
        self.assertEqual(payloads, [])
        self.assertEqual(warnings, [])
        self.assertEqual(len(errors), 1, f"expected 1 error, got: {errors}")
        self.assertIn("bad.txt", errors[0])
        self.assertIn("JSON parse failed", errors[0])

    def test_file_with_schema_invalid_json_emits_error_and_skips(self):
        errors: list[str] = []
        # Strip required `mode` field → schema rejects.
        payload = {
            "experiment_id": "example-experiment",
            "rater": "alice",
            "started_at": "2026-05-11T09:00:00Z",
            "exported_at": "2026-05-11T09:18:00Z",
            "ranking": ["a", "b"],
        }
        body = (
            "Hi,\n\nVOTE-JSON-START\n"
            + json.dumps(payload)
            + "\nVOTE-JSON-END\n"
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "x.txt").write_text(body, encoding="utf-8")
            payloads = er.payloads_from_email_dir(
                Path(td),
                on_warning=lambda _m: None,
                on_error=errors.append,
            )
        self.assertEqual(payloads, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("schema invalid", errors[0])

    def test_mixed_eml_and_txt_extensions_both_parsed(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "alice.eml").write_text(
                "From: alice@example.com\nSubject: [vote] example-experiment\n\n"
                + self._vote_block(rater="alice"),
                encoding="utf-8",
            )
            (Path(td) / "bob.txt").write_text(
                self._vote_block(rater="bob"),
                encoding="utf-8",
            )
            payloads = er.payloads_from_email_dir(Path(td))
        self.assertEqual(len(payloads), 2)
        self.assertEqual(
            sorted(p["rater"] for p in payloads),
            ["alice", "bob"],
        )

    def test_quoted_reply_prefixes_stripped_before_scan(self):
        # Apple Mail / Gmail prefix forwarded bodies with `> `.
        body = self._vote_block(rater="flo")
        quoted = "\n".join("> " + line for line in body.split("\n"))
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "reply.txt").write_text(quoted, encoding="utf-8")
            payloads = er.payloads_from_email_dir(Path(td))
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["rater"], "flo")

    def test_non_eml_txt_files_ignored(self):
        # Operators may have other files in the folder (e.g. README, attachments).
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "flo.txt").write_text(self._vote_block(), encoding="utf-8")
            (Path(td) / "README.md").write_text("# Notes\n", encoding="utf-8")
            (Path(td) / "photo.jpg").write_text("binaryish", encoding="utf-8")
            payloads = er.payloads_from_email_dir(Path(td))
        self.assertEqual(len(payloads), 1)

    def test_empty_directory_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as td:
            payloads = er.payloads_from_email_dir(Path(td))
        self.assertEqual(payloads, [])

    def test_not_a_directory_raises(self):
        with tempfile.NamedTemporaryFile() as tf:
            with self.assertRaises(ValueError):
                er.payloads_from_email_dir(Path(tf.name))

    def test_aggregate_payloads_end_to_end_from_emails(self):
        # Wire-up test: extracted email payloads flow through
        # aggregate_payloads identically to JSON-file payloads.
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "alice.txt").write_text(
                self._vote_block(rater="alice", ranking=["alpha", "beta", "gamma"]),
                encoding="utf-8",
            )
            (Path(td) / "bob.txt").write_text(
                self._vote_block(rater="bob", ranking=["gamma", "beta", "alpha"]),
                encoding="utf-8",
            )
            payloads = er.payloads_from_email_dir(Path(td))
            agg = er.aggregate_payloads(payloads)
        # alpha + gamma cross-cancel; beta stays mid → all 0.5 mean.
        for slug in ("alpha", "beta", "gamma"):
            self.assertAlmostEqual(
                agg["per_slug"][slug]["mean_score"], 0.5, places=9
            )
            self.assertEqual(agg["per_slug"][slug]["n_raters"], 2)
        self.assertEqual(sorted(agg["raters"]), ["alice", "bob"])


if __name__ == "__main__":
    unittest.main()
