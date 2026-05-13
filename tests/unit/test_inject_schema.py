"""Schema validation tests for shared/inject.schema.yaml."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "shared" / "inject.schema.yaml"


@pytest.fixture(scope="module")
def schema() -> dict:
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def validator(schema):
    import jsonschema
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def _valid_entry(**kw) -> dict:
    base = {
        "target": {"element": "TextFrame", "anname": "u123"},
        "field": "ALIGN",
        "set": 0,
        "classification": "converter-bug",
        "reason": "Backport-11 edge case; converter must explicitly emit ALIGN=0.",
    }
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# Test 1 — valid hand_patches => no errors.
# ---------------------------------------------------------------------------
def test_valid_entry_passes(validator):
    data = {"hand_patches": [_valid_entry()]}
    assert list(validator.iter_errors(data)) == []


# ---------------------------------------------------------------------------
# Test 2 — missing target => ValidationError.
# ---------------------------------------------------------------------------
def test_missing_target_fails(validator):
    entry = _valid_entry()
    entry.pop("target")
    data = {"hand_patches": [entry]}
    errors = list(validator.iter_errors(data))
    assert errors
    assert any("target" in e.message for e in errors)


# ---------------------------------------------------------------------------
# Test 3 — both set and delta => oneOf violation.
# ---------------------------------------------------------------------------
def test_set_and_delta_together_violates_oneof(validator):
    entry = _valid_entry()
    entry["delta"] = 1.0
    data = {"hand_patches": [entry]}
    errors = list(validator.iter_errors(data))
    assert errors


# ---------------------------------------------------------------------------
# Test 4 — reason too short => ValidationError.
# ---------------------------------------------------------------------------
def test_short_reason_fails(validator):
    entry = _valid_entry(reason="too short")
    data = {"hand_patches": [entry]}
    errors = list(validator.iter_errors(data))
    assert errors
    assert any("reason" in e.absolute_path for e in errors) or any(
        "reason" in e.message.lower() for e in errors
    )


# ---------------------------------------------------------------------------
# Test 5 — unknown classification => ValidationError.
# ---------------------------------------------------------------------------
def test_unknown_classification_fails(validator):
    entry = _valid_entry(classification="totally-bogus")
    data = {"hand_patches": [entry]}
    errors = list(validator.iter_errors(data))
    assert errors


# ---------------------------------------------------------------------------
# Test 6 — element enum is honoured.
# ---------------------------------------------------------------------------
def test_element_enum_honoured(validator):
    entry = _valid_entry()
    entry["target"]["element"] = "NotARealElement"
    data = {"hand_patches": [entry]}
    errors = list(validator.iter_errors(data))
    assert errors


# ---------------------------------------------------------------------------
# Test 7 — anname pattern.
# ---------------------------------------------------------------------------
def test_anname_pattern(validator):
    entry = _valid_entry()
    entry["target"]["anname"] = "123starts-with-digit"
    data = {"hand_patches": [entry]}
    errors = list(validator.iter_errors(data))
    assert errors


# ---------------------------------------------------------------------------
# Test 8 — delta form is acceptable.
# ---------------------------------------------------------------------------
def test_delta_form_passes(validator):
    entry = _valid_entry()
    entry.pop("set")
    entry["delta"] = 1.884
    data = {"hand_patches": [entry]}
    assert list(validator.iter_errors(data)) == []


# ---------------------------------------------------------------------------
# Test 9 — follow_up_issue null allowed.
# ---------------------------------------------------------------------------
def test_follow_up_issue_null_allowed(validator):
    entry = _valid_entry(follow_up_issue=None)
    data = {"hand_patches": [entry]}
    assert list(validator.iter_errors(data)) == []


# ---------------------------------------------------------------------------
# Test 10 — schema itself is valid Draft 2020-12.
# ---------------------------------------------------------------------------
def test_schema_is_valid_draft_2020_12(schema):
    import jsonschema
    jsonschema.Draft202012Validator.check_schema(schema)
