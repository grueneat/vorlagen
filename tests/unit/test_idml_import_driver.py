"""Unit tests for tools/idml_import_driver.py — bin/idml-import driver."""
from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import idml_import_driver as drv  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

def _make_idml(tmp_path: Path, name: str = "test.idml") -> Path:
    """Write a minimal IDML zip with a single empty spread."""
    designmap = '<?xml version="1.0"?><Document><Spread src="Spreads/Spread_u01.xml"/></Document>'
    spread = '<?xml version="1.0"?><Spread/>'
    p = tmp_path / name
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("designmap.xml", designmap)
        z.writestr("Spreads/Spread_u01.xml", spread)
    p.write_bytes(buf.getvalue())
    return p


def _make_pdf(path: Path) -> None:
    Image.new("RGB", (100, 100), color="white").save(str(path), "PDF", resolution=72)


def _args(**kw) -> argparse.Namespace:
    """Build a Namespace with all driver attrs at sensible defaults."""
    return argparse.Namespace(
        accept_residual=kw.get("accept_residual", []),
        dry_run=kw.get("dry_run", False),
        max_iterations=kw.get("max_iterations", 1),
        keep_baseline_from_pdf=kw.get("keep_baseline_from_pdf", None),
        scaffold_only=kw.get("scaffold_only", False),
        reimport=kw.get("reimport", False),
        no_brand_fonts=kw.get("no_brand_fonts", True),
        allow_composite_ai=kw.get("allow_composite_ai", True),
        non_interactive=kw.get("non_interactive", True),
        path=[],
    )


# ---------------------------------------------------------------------------
# Test 1 — tool availability check exits 1 with install hints.
# ---------------------------------------------------------------------------
def test_missing_tool_exits_with_hint(tmp_path, monkeypatch):
    idml = _make_idml(tmp_path)
    _make_pdf(idml.with_suffix(".pdf"))
    monkeypatch.setattr(drv.shutil, "which", lambda _name: None)

    rc = drv._process_one(idml, _args(), build_root=tmp_path / "build",
                          templates_root=tmp_path / "templates",
                          assets_root=tmp_path / "shared" / "assets")
    assert rc == 1


# ---------------------------------------------------------------------------
# Test 2 — existing template rejection without --reimport.
# ---------------------------------------------------------------------------
def test_existing_template_refused_without_reimport(tmp_path, monkeypatch):
    monkeypatch.setattr(drv.shutil, "which", lambda _name: "/usr/bin/" + _name)
    idml = _make_idml(tmp_path)
    _make_pdf(idml.with_suffix(".pdf"))
    templates = tmp_path / "templates"
    slug = drv._slugify(idml)
    (templates / slug).mkdir(parents=True)

    rc = drv._process_one(idml, _args(), build_root=tmp_path / "build",
                          templates_root=templates,
                          assets_root=tmp_path / "shared" / "assets")
    assert rc == 1


# ---------------------------------------------------------------------------
# Test 3 — missing baseline.pdf fails clean.
# ---------------------------------------------------------------------------
def test_missing_baseline_fails_clean(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(drv.shutil, "which", lambda _name: "/usr/bin/" + _name)
    idml = _make_idml(tmp_path)
    # No sibling .pdf.

    rc = drv._process_one(idml, _args(), build_root=tmp_path / "build",
                          templates_root=tmp_path / "templates",
                          assets_root=tmp_path / "shared" / "assets")
    assert rc == 1
    captured = capsys.readouterr()
    assert "baseline.pdf not found" in captured.err


# ---------------------------------------------------------------------------
# Test 4 — missing IDML path.
# ---------------------------------------------------------------------------
def test_missing_idml_path_fails(tmp_path):
    nonexistent = tmp_path / "nope.idml"
    rc = drv._process_one(nonexistent, _args())
    assert rc == 1


# ---------------------------------------------------------------------------
# Test 5 — log_iteration writes expected schema row.
# ---------------------------------------------------------------------------
def test_log_iteration_writes_row(tmp_path):
    review = {
        "preflight_ok": False,
        "issues": [
            {"id": "1", "classification": "converter-bug"},
            {"id": "2", "classification": "minor"},
        ],
        "drift": {"p1": 4.2, "p2": 3.1, "p1_max_region": 8.0, "p2_max_region": 6.0},
        "audits_run": ["a", "b"],
    }
    row = drv.log_iteration("slug", 1, review, ["c1"], build_root=tmp_path)
    log = (tmp_path / "slug" / "iteration.jsonl").read_text()
    parsed = json.loads(log.splitlines()[0])
    assert parsed == row
    assert parsed["iteration"] == 1
    assert parsed["issues_open"] == 1  # minor filtered out
    assert parsed["drift_p1"] == 4.2
    assert parsed["_schema_version"] == 1


def test_log_iteration_appends_multiple(tmp_path):
    review = {"preflight_ok": False, "issues": [], "drift": {}, "audits_run": []}
    for i in range(1, 4):
        drv.log_iteration("s", i, review, [], build_root=tmp_path)
    lines = (tmp_path / "s" / "iteration.jsonl").read_text().splitlines()
    assert len(lines) == 3
    assert [json.loads(ln)["iteration"] for ln in lines] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Test 6 — regression_guard returns None for stable / improving drift.
# ---------------------------------------------------------------------------
def test_regression_guard_no_regression(tmp_path):
    base_review = {"preflight_ok": False, "issues": [], "drift": {}, "audits_run": []}
    prev = drv.log_iteration("s", 1, {**base_review, "drift": {"p1": 5.0, "p1_max_region": 8.0}, "audits_run": ["a"]}, [], build_root=tmp_path)
    cur = drv.log_iteration("s", 2, {**base_review, "drift": {"p1": 4.5, "p1_max_region": 7.0}, "audits_run": ["a"]}, [], build_root=tmp_path)
    assert drv.regression_guard("s", cur, build_root=tmp_path) is None


def test_regression_guard_halts_on_both_page_and_region(tmp_path):
    base_review = {"preflight_ok": False, "issues": [], "drift": {}, "audits_run": []}
    drv.log_iteration("s", 1, {**base_review, "drift": {"p1": 4.0, "p1_max_region": 6.0}, "audits_run": ["a"]}, [], build_root=tmp_path)
    cur = drv.log_iteration("s", 2, {**base_review, "drift": {"p1": 4.5, "p1_max_region": 8.0}, "audits_run": ["a"]}, [], build_root=tmp_path)
    err = drv.regression_guard("s", cur, build_root=tmp_path)
    assert err is not None
    assert "regression" in err


def test_regression_guard_does_not_halt_when_only_page_regresses(tmp_path):
    base_review = {"preflight_ok": False, "issues": [], "drift": {}, "audits_run": []}
    drv.log_iteration("s", 1, {**base_review, "drift": {"p1": 4.0, "p1_max_region": 8.0}, "audits_run": ["a"]}, [], build_root=tmp_path)
    cur = drv.log_iteration("s", 2, {**base_review, "drift": {"p1": 4.5, "p1_max_region": 7.0}, "audits_run": ["a"]}, [], build_root=tmp_path)
    assert drv.regression_guard("s", cur, build_root=tmp_path) is None


def test_regression_guard_ignores_new_audits(tmp_path):
    base_review = {"preflight_ok": False, "issues": [], "drift": {}, "audits_run": []}
    drv.log_iteration("s", 1, {**base_review, "drift": {"p1": 4.0, "p1_max_region": 6.0}, "audits_run": ["a"]}, [], build_root=tmp_path)
    cur = drv.log_iteration("s", 2, {**base_review, "drift": {"p1": 4.5, "p1_max_region": 8.0}, "audits_run": ["a", "b"]}, [], build_root=tmp_path)
    # A new audit appeared; the higher drift is attributed to it, not regression.
    assert drv.regression_guard("s", cur, build_root=tmp_path) is None


# ---------------------------------------------------------------------------
# Test 7 — verdict computation.
# ---------------------------------------------------------------------------
def test_verdict_pass_on_preflight_ok():
    assert drv._verdict({"preflight_ok": True}, residual_accepted=False) == "PASS"


def test_verdict_pass_on_residual_accepted():
    assert drv._verdict({"preflight_ok": False, "issues": []}, residual_accepted=True) == "PASS"


def test_verdict_blocked_by_authoring():
    review = {
        "preflight_ok": False,
        "issues": [
            {"classification": "authoring-bug", "id": "1"},
        ],
    }
    assert drv._verdict(review, residual_accepted=False) == "BLOCKED_BY_AUTHORING"


def test_verdict_needs_review_for_mixed_issues():
    review = {
        "preflight_ok": False,
        "issues": [
            {"classification": "converter-bug", "id": "1"},
            {"classification": "authoring-bug", "id": "2"},
        ],
    }
    assert drv._verdict(review, residual_accepted=False) == "NEEDS_REVIEW"


# ---------------------------------------------------------------------------
# Test 8 — slug derivation.
# ---------------------------------------------------------------------------
def test_slugify_basic(tmp_path):
    p = tmp_path / "My Cool Template.idml"
    p.touch()
    assert drv._slugify(p) == "my-cool-template"


# ---------------------------------------------------------------------------
# Test 9 — _expand_paths walks a directory.
# ---------------------------------------------------------------------------
def test_expand_paths_walks_directories(tmp_path):
    sub = tmp_path / "incoming"
    sub.mkdir()
    a = sub / "a.idml"
    b = sub / "b.idml"
    a.touch()
    b.touch()
    paths = drv._expand_paths([str(sub)])
    assert {p.name for p in paths} == {"a.idml", "b.idml"}


def test_expand_paths_passes_through_files(tmp_path):
    a = tmp_path / "a.idml"
    a.touch()
    paths = drv._expand_paths([str(a)])
    assert paths == [a]


# ---------------------------------------------------------------------------
# Test 10 — CLI --help works.
# ---------------------------------------------------------------------------
def test_cli_help_exits_zero():
    result = subprocess.run(
        [sys.executable, str(TOOLS / "idml_import_driver.py"), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--accept-residual" in result.stdout
    assert "--reimport" in result.stdout


# ---------------------------------------------------------------------------
# Test 11 — bin/idml-import shim invokes the driver.
# ---------------------------------------------------------------------------
def test_bin_shim_invokes_driver():
    bin_path = ROOT / "bin" / "idml-import"
    assert bin_path.exists()
    assert bin_path.stat().st_mode & 0o111  # executable
    result = subprocess.run(
        [sys.executable, str(bin_path), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "idml-import" in result.stdout.lower()
