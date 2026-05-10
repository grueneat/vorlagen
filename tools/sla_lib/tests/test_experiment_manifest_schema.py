"""Manifest-schema unit tests (issue #29 T03).

Validates ``experiments/_schema/manifest.schema.yaml`` against
``experiments/_schema/manifest.example.yml`` and asserts rejection of
the malformations the schema must catch:
  - <10 hypotheses
  - no wildcard
  - unknown axis_commitments enum value
  - missing required field per hypothesis
  - bad slug pattern
"""
from __future__ import annotations

import copy
import unittest
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "experiments" / "_schema" / "manifest.schema.yaml"
EXAMPLE_PATH = ROOT / "experiments" / "_schema" / "manifest.example.yml"


def _load_schema() -> dict:
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_example() -> dict:
    return yaml.safe_load(EXAMPLE_PATH.read_text(encoding="utf-8"))


class ManifestSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = _load_schema()
        self.example = _load_example()
        self.validator = jsonschema.Draft202012Validator(self.schema)

    def test_example_validates(self):
        errors = sorted(self.validator.iter_errors(self.example),
                        key=lambda e: e.path)
        self.assertEqual(errors, [], f"example must validate; got: {errors}")

    def test_example_has_at_least_10_hypotheses(self):
        self.assertGreaterEqual(len(self.example["hypotheses"]), 10)

    def test_example_has_at_least_one_wildcard(self):
        self.assertTrue(any(h.get("wildcard") for h in self.example["hypotheses"]))

    def test_rejects_fewer_than_10_hypotheses(self):
        m = copy.deepcopy(self.example)
        m["hypotheses"] = m["hypotheses"][:9]
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_no_wildcard(self):
        m = copy.deepcopy(self.example)
        for h in m["hypotheses"]:
            h["wildcard"] = False
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_unknown_axis_commitment(self):
        m = copy.deepcopy(self.example)
        m["hypotheses"][0]["axis_commitments"] = ["bogus-axis"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_missing_required_field(self):
        m = copy.deepcopy(self.example)
        del m["hypotheses"][0]["rationale"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_bad_slug(self):
        m = copy.deepcopy(self.example)
        m["hypotheses"][0]["slug"] = "Bad_Slug"
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_single_llm(self):
        m = copy.deepcopy(self.example)
        m["contributing_llms"] = ["claude:opus"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)

    def test_rejects_unknown_top_level_field(self):
        m = copy.deepcopy(self.example)
        m["bogus_field"] = 42
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(m)


if __name__ == "__main__":
    unittest.main()
