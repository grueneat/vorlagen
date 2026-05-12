"""Integration tests for Phase F run_style_audit against the real v2 falzflyer.

Verifies:
- run_style_audit produces output with expected keys from real PDFs.
- Runtime < 3s.
- YAML output is valid and re-parseable.

Skips when preview.pdf or baseline.pdf are absent (fast skip, not a hard failure).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from run_style_audit import run_style_audit, _yaml_dump

SLUG = "kandidat-falzflyer-din-lang-gruenes-cover-v2"
TDIR = ROOT / "templates" / SLUG
PREVIEW_PDF = TDIR / "preview.pdf"
BASELINE_PDF = TDIR / "baseline.pdf"
OUT_DIR = ROOT / "build" / "validation" / SLUG


def _skip_if_missing():
    for p in (PREVIEW_PDF, BASELINE_PDF):
        if not p.exists():
            pytest.skip(f"Required PDF not found: {p}")


def test_run_style_audit_produces_output():
    """run_style_audit runs and returns a dict with the expected keys."""
    _skip_if_missing()
    report = run_style_audit(PREVIEW_PDF, BASELINE_PDF, template=SLUG)
    assert report["template"] == SLUG
    assert "baseline_word_count" in report
    assert "preview_word_count" in report
    assert "threshold_size_pt" in report
    assert "common_word_threshold" in report
    assert "style_drift_count" in report
    assert "suppressed_common_word_drifts_count" in report
    assert "style_drifts" in report
    assert "ok" in report
    assert isinstance(report["ok"], bool)
    assert isinstance(report["style_drifts"], list)
    assert isinstance(report["style_drift_count"], int)


def test_run_style_audit_word_counts_nonzero():
    """Both PDFs contain substantial text."""
    _skip_if_missing()
    report = run_style_audit(PREVIEW_PDF, BASELINE_PDF, template=SLUG)
    assert report["baseline_word_count"] >= 50, (
        f"baseline_word_count too low: {report['baseline_word_count']}"
    )
    assert report["preview_word_count"] >= 50, (
        f"preview_word_count too low: {report['preview_word_count']}"
    )


def test_run_style_audit_runtime_under_3s():
    """Audit completes in under 3 seconds on the v2 falzflyer."""
    _skip_if_missing()
    t0 = time.monotonic()
    run_style_audit(PREVIEW_PDF, BASELINE_PDF, template=SLUG)
    elapsed = time.monotonic() - t0
    assert elapsed < 3.0, f"run_style_audit took {elapsed:.2f}s (limit 3s)"


def test_run_style_audit_yaml_written(tmp_path):
    """Result can be written as valid YAML and re-parsed."""
    _skip_if_missing()
    report = run_style_audit(PREVIEW_PDF, BASELINE_PDF, template=SLUG)
    out = tmp_path / "run_style_audit.yml"
    out.write_text(_yaml_dump(report), encoding="utf-8")
    parsed = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert parsed["template"] == SLUG
    assert isinstance(parsed["ok"], bool)
    assert "style_drifts" in parsed


def test_run_style_audit_drift_schema():
    """Every style_drift entry has the required keys with correct types."""
    _skip_if_missing()
    report = run_style_audit(PREVIEW_PDF, BASELINE_PDF, template=SLUG)
    required_keys = {"text", "page", "baseline", "preview", "drift", "severity"}
    for drift in report["style_drifts"]:
        missing = required_keys - set(drift.keys())
        assert not missing, f"style_drift entry missing keys: {missing}\nEntry: {drift}"
        assert drift["severity"] in ("large", "small")
        assert isinstance(drift["page"], int)
        assert isinstance(drift["baseline"]["fontname"], str)
        assert isinstance(drift["baseline"]["size"], float)
        assert isinstance(drift["preview"]["fontname"], str)
        assert isinstance(drift["preview"]["size"], float)


def test_run_style_audit_deterministic():
    """Two consecutive runs produce byte-identical YAML."""
    _skip_if_missing()
    r1 = _yaml_dump(run_style_audit(PREVIEW_PDF, BASELINE_PDF, template=SLUG))
    r2 = _yaml_dump(run_style_audit(PREVIEW_PDF, BASELINE_PDF, template=SLUG))
    assert r1 == r2, "run_style_audit YAML is not deterministic across two runs"


def test_run_style_audit_engine_disagreement_field(tmp_path):
    """#37 P1 task 3: when text_render_audit counts are passed in, the report
    includes an `extraction_engine_disagreement` block."""
    _skip_if_missing()
    # Read the live D7 yml if present, else use pdftotext directly to derive counts.
    yml_path = OUT_DIR / "text_render_audit.yml"
    if yml_path.exists():
        tra = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
        counts = {
            "baseline": int(tra.get("baseline_word_count", 0) or 0),
            "preview": int(tra.get("preview_word_count", 0) or 0),
        }
    else:
        # Derive from pdftotext live so the test is not coupled to a prior --audit run.
        import subprocess, re
        def _count(p):
            r = subprocess.run(["pdftotext", "-layout", str(p), "-"],
                               capture_output=True, text=True, check=True)
            return len([t for t in re.split(r"\s+", r.stdout) if t])
        counts = {"baseline": _count(BASELINE_PDF), "preview": _count(PREVIEW_PDF)}

    report = run_style_audit(
        PREVIEW_PDF, BASELINE_PDF, template=SLUG,
        text_render_audit_counts=counts,
    )
    assert "extraction_engine_disagreement" in report
    eed = report["extraction_engine_disagreement"]
    for key in ("baseline_pdfplumber", "preview_pdfplumber",
                "baseline_pdftotext", "preview_pdftotext",
                "baseline_delta_pct", "preview_delta_pct", "warn"):
        assert key in eed, f"missing key {key} in extraction_engine_disagreement"
    assert isinstance(eed["warn"], bool)
