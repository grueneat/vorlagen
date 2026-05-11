"""Results-schema unit tests (issue #31).

Validates ``experiments/_schema/results.schema.yaml`` against valid rank
and direct-pick payloads, and asserts rejection of the malformations the
schema must catch:
  - ambiguous file carrying BOTH ranking and selections
  - missing `mode` discriminator
  - unknown `mode` value (e.g. legacy "versus")
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "experiments" / "_schema" / "results.schema.yaml"
EXAMPLE_PATH = ROOT / "experiments" / "_schema" / "results.example.json"


def _load_schema() -> dict:
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def _valid_rank() -> dict:
    return {
        "experiment_id": "example-experiment",
        "rater": "alice",
        "started_at": "2026-05-10T14:00:00Z",
        "exported_at": "2026-05-10T14:05:00Z",
        "mode": "rank",
        "ranking": ["alpha", "beta", "gamma"],
    }


def _valid_direct_pick() -> dict:
    return {
        "experiment_id": "example-experiment",
        "rater": "alice",
        "started_at": "2026-05-10T14:00:00Z",
        "exported_at": "2026-05-10T14:05:00Z",
        "mode": "direct-pick",
        "selections": ["alpha", "gamma"],
    }


class ResultsSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = _load_schema()
        self.validator = jsonschema.Draft202012Validator(self.schema)

    def test_example_validates(self):
        example = _load_example()
        errors = sorted(self.validator.iter_errors(example), key=lambda e: list(e.path))
        self.assertEqual(
            errors,
            [],
            f"example must validate; got: {[e.message for e in errors]}",
        )

    def test_valid_rank_payload(self):
        self.validator.validate(_valid_rank())

    def test_valid_direct_pick_payload(self):
        self.validator.validate(_valid_direct_pick())

    def test_rejects_ambiguous_both_ranking_and_selections(self):
        m = _valid_rank()
        m["selections"] = ["alpha"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_missing_mode(self):
        m = _valid_rank()
        del m["mode"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_unknown_mode_versus(self):
        # Legacy v1 mode must be rejected — pairwise shape is deleted.
        m = _valid_rank()
        m["mode"] = "versus"
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_rank_mode_missing_ranking(self):
        m = _valid_rank()
        del m["ranking"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_direct_pick_missing_selections(self):
        m = _valid_direct_pick()
        del m["selections"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_rank_mode_with_selections_field(self):
        # A rank file MUST NOT carry a `selections` field.
        m = _valid_rank()
        m["selections"] = []
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_direct_pick_with_ranking_field(self):
        m = _valid_direct_pick()
        m["ranking"] = []
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_duplicate_slugs_in_ranking(self):
        m = _valid_rank()
        m["ranking"] = ["alpha", "alpha"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)


if __name__ == "__main__":
    unittest.main()
