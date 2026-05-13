"""Unit tests for iteration.jsonl + regression_guard in idml_import_driver.

Covers the schema, append behaviour, and the regression-guard logic
introduced in issue #38 Task 6.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import idml_import_driver as drv  # noqa: E402


# ---------------------------------------------------------------------------
# Test 1 — log_iteration writes exactly one valid JSON line with all keys.
# ---------------------------------------------------------------------------
def test_log_iteration_writes_one_line(tmp_path):
    review = {
        "preflight_ok": False,
        "issues": [
            {"id": 1, "classification": "converter-bug"},
            {"id": 2, "classification": "minor"},
            {"id": 3, "classification": "scribus-engine-bug"},
        ],
        "drift": {"p1": 4.5, "p2": 3.2, "p1_max_region": 9.0, "p2_max_region": 7.0},
        "audits_run": ["a", "b", "c"],
    }
    row = drv.log_iteration("slug", 1, review, ["change1"], build_root=tmp_path)
    log_text = (tmp_path / "slug" / "iteration.jsonl").read_text(encoding="utf-8")
    lines = log_text.splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed == row
    # All expected keys present.
    expected_keys = {
        "iteration", "timestamp", "preflight_ok", "issues_open",
        "drift_p1", "drift_p2", "drift_p1_max_region", "drift_p2_max_region",
        "changes", "audits_run", "rules_seen", "_schema_version",
    }
    assert set(parsed.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Test 2 — 3 calls produce 3 lines.
# ---------------------------------------------------------------------------
def test_log_iteration_appends_three_lines(tmp_path):
    review = {"preflight_ok": False, "issues": [], "drift": {}, "audits_run": []}
    for i in range(1, 4):
        drv.log_iteration("s", i, review, [], build_root=tmp_path)
    lines = (tmp_path / "s" / "iteration.jsonl").read_text().splitlines()
    assert len(lines) == 3


# ---------------------------------------------------------------------------
# Test 3 — regression_guard returns None for monotonically decreasing drift.
# ---------------------------------------------------------------------------
def test_regression_guard_decreasing(tmp_path):
    base = {"preflight_ok": False, "issues": [], "audits_run": ["a"]}
    drv.log_iteration("s", 1, {**base, "drift": {"p1": 5.0, "p1_max_region": 8.0}}, [], build_root=tmp_path)
    cur = drv.log_iteration("s", 2, {**base, "drift": {"p1": 4.0, "p1_max_region": 7.0}}, [], build_root=tmp_path)
    assert drv.regression_guard("s", cur, build_root=tmp_path) is None


# ---------------------------------------------------------------------------
# Test 4 — both page-wide and per-region regress => error.
# ---------------------------------------------------------------------------
def test_regression_guard_both_dimensions_regress(tmp_path):
    base = {"preflight_ok": False, "issues": [], "audits_run": ["a"]}
    drv.log_iteration("s", 1, {**base, "drift": {"p1": 4.0, "p1_max_region": 6.0}}, [], build_root=tmp_path)
    cur = drv.log_iteration("s", 2, {**base, "drift": {"p1": 4.2, "p1_max_region": 8.0}}, [], build_root=tmp_path)
    err = drv.regression_guard("s", cur, build_root=tmp_path)
    assert err is not None
    assert "regression" in err.lower()


# ---------------------------------------------------------------------------
# Test 5 — page-wide regresses but per-region drops => None (structural fix
# masked by anti-aliasing).
# ---------------------------------------------------------------------------
def test_regression_guard_page_regresses_but_region_drops(tmp_path):
    base = {"preflight_ok": False, "issues": [], "audits_run": ["a"]}
    drv.log_iteration("s", 1, {**base, "drift": {"p1": 4.0, "p1_max_region": 9.0}}, [], build_root=tmp_path)
    cur = drv.log_iteration("s", 2, {**base, "drift": {"p1": 4.5, "p1_max_region": 7.0}}, [], build_root=tmp_path)
    assert drv.regression_guard("s", cur, build_root=tmp_path) is None


# ---------------------------------------------------------------------------
# Test 6 — new audit appears => not counted as regression.
# ---------------------------------------------------------------------------
def test_regression_guard_new_audit_not_regression(tmp_path):
    base = {"preflight_ok": False, "issues": []}
    drv.log_iteration("s", 1, {**base, "drift": {"p1": 4.0, "p1_max_region": 6.0}, "audits_run": ["a"]}, [], build_root=tmp_path)
    cur = drv.log_iteration("s", 2, {**base, "drift": {"p1": 4.5, "p1_max_region": 8.0}, "audits_run": ["a", "b"]}, [], build_root=tmp_path)
    assert drv.regression_guard("s", cur, build_root=tmp_path) is None


# ---------------------------------------------------------------------------
# Test 7 — _schema_version=1 is present in every row.
# ---------------------------------------------------------------------------
def test_schema_version_always_present(tmp_path):
    base = {"preflight_ok": False, "issues": [], "drift": {}, "audits_run": []}
    drv.log_iteration("s", 1, base, [], build_root=tmp_path)
    drv.log_iteration("s", 2, base, [], build_root=tmp_path)
    lines = (tmp_path / "s" / "iteration.jsonl").read_text().splitlines()
    for ln in lines:
        parsed = json.loads(ln)
        assert parsed["_schema_version"] == 1


# ---------------------------------------------------------------------------
# Test 8 — rules_seen monotonically increases.
# ---------------------------------------------------------------------------
def test_rules_seen_monotonic(tmp_path):
    base = {"preflight_ok": False, "issues": [], "drift": {}, "audits_run": []}
    for i in range(1, 5):
        drv.log_iteration("s", i, base, [], build_root=tmp_path)
    lines = (tmp_path / "s" / "iteration.jsonl").read_text().splitlines()
    rules = [json.loads(ln)["rules_seen"] for ln in lines]
    assert rules == sorted(rules)
    assert rules == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Test 9 — issues_open filters out 'minor'.
# ---------------------------------------------------------------------------
def test_issues_open_filters_minor(tmp_path):
    review = {
        "preflight_ok": False,
        "issues": [
            {"classification": "converter-bug"},
            {"classification": "minor"},
            {"classification": "minor"},
            {"classification": "human-review"},
        ],
        "drift": {},
        "audits_run": [],
    }
    row = drv.log_iteration("s", 1, review, [], build_root=tmp_path)
    assert row["issues_open"] == 2  # converter-bug + human-review


# ---------------------------------------------------------------------------
# Test 10 — regression_guard returns None when only one iteration logged.
# ---------------------------------------------------------------------------
def test_regression_guard_first_iteration(tmp_path):
    base = {"preflight_ok": False, "issues": [], "audits_run": []}
    row = drv.log_iteration("s", 1, {**base, "drift": {"p1": 5.0, "p1_max_region": 8.0}}, [], build_root=tmp_path)
    assert drv.regression_guard("s", row, build_root=tmp_path) is None


# ---------------------------------------------------------------------------
# Test 11 — line is stable JSON (no trailing whitespace, deterministic order).
# ---------------------------------------------------------------------------
def test_line_is_compact_json(tmp_path):
    base = {"preflight_ok": False, "issues": [], "drift": {}, "audits_run": []}
    drv.log_iteration("s", 1, base, [], build_root=tmp_path)
    line = (tmp_path / "s" / "iteration.jsonl").read_text(encoding="utf-8")
    # Single line, no padding spaces between key+value separators.
    assert ": " not in line  # compact ":" only
    assert ", " not in line  # compact "," only
