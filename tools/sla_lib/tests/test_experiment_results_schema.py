"""Results-schema unit tests (issue #29 T04).

Validates ``experiments/_schema/results.schema.yaml`` against
``experiments/_schema/results.example.json`` and asserts rejection of
the malformations the schema must catch:
  - missing axis field
  - axis enum out of range
  - position_a_on_screen not in {left, right}
  - missing required top-level field
  - disagreement_index out of [0, 1]
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


class ResultsSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = _load_schema()
        self.example = _load_example()
        self.validator = jsonschema.Draft202012Validator(self.schema)

    def test_example_validates(self):
        errors = sorted(self.validator.iter_errors(self.example),
                        key=lambda e: list(e.path))
        self.assertEqual(
            errors, [],
            f"example must validate; got: {[e.message for e in errors]}",
        )

    def test_rejects_missing_axis(self):
        m = copy.deepcopy(self.example)
        del m["votes"][0]["axis"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_unknown_axis_enum(self):
        m = copy.deepcopy(self.example)
        m["votes"][0]["axis"] = "not-an-axis"
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_unknown_position(self):
        m = copy.deepcopy(self.example)
        m["votes"][0]["position_a_on_screen"] = "centre"
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_missing_required_top_level(self):
        m = copy.deepcopy(self.example)
        del m["disagreement_index"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_disagreement_index_out_of_range(self):
        m = copy.deepcopy(self.example)
        m["disagreement_index"] = 1.5
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_spearman_out_of_range(self):
        m = copy.deepcopy(self.example)
        m["spearman_appeal_transport"] = -2.0
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_accepts_null_winner_for_skipped_pair(self):
        m = copy.deepcopy(self.example)
        m["votes"][0]["winner"] = None
        # null winner is allowed (oneOf string|null)
        self.validator.validate(m)

    def test_rejects_unknown_top_level_field(self):
        m = copy.deepcopy(self.example)
        m["bogus"] = 42
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)


if __name__ == "__main__":
    unittest.main()
