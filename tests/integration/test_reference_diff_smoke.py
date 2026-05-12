"""Integration smoke test for the reference_sla second diff lane (issue #37 Phase D).

Runs bin/render-gallery on the v2 falzflyer with --audit and verifies that
BOTH visual_diff.json and reference_diff/reference_diff.json are produced.

Skipped when xvfb-run or scribus are not on PATH — same pattern as the
experiment_render tests.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SLUG = "kandidat-falzflyer-din-lang-gruenes-cover-v2"
TDIR = ROOT / "templates" / SLUG
META = TDIR / "meta.yml"

_HAS_XVFB = shutil.which("xvfb-run") is not None
_HAS_SCRIBUS = shutil.which("scribus") is not None

pytestmark = pytest.mark.skipif(
    not (_HAS_XVFB and _HAS_SCRIBUS),
    reason="xvfb-run and/or scribus not on PATH — skipping render-dependent integration test",
)


def _run_gallery() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / "render_pipeline.py"), SLUG, "--audit"],
        capture_output=False,  # let output stream to terminal
        text=True,
        cwd=str(ROOT),
    )


def test_both_diff_lanes_produce_json():
    """After render-gallery, both visual_diff.json and reference_diff.json must exist."""
    out_dir = ROOT / "build" / "validation" / SLUG
    ref_dir = out_dir / "reference_diff"

    _run_gallery()

    vd_json = out_dir / "visual_diff.json"
    rd_json = ref_dir / "reference_diff.json"

    assert vd_json.exists(), f"visual_diff.json not found at {vd_json}"
    assert rd_json.exists(), f"reference_diff.json not found at {rd_json}"


def test_reference_diff_json_schema():
    """reference_diff.json must have pass: and pages[].mismatch_pct keys."""
    rd_json = ROOT / "build" / "validation" / SLUG / "reference_diff" / "reference_diff.json"

    # Ensure the gallery ran.
    if not rd_json.exists():
        _run_gallery()

    assert rd_json.exists(), f"reference_diff.json not found at {rd_json}"

    data = json.loads(rd_json.read_text(encoding="utf-8"))
    assert "pass" in data, "reference_diff.json missing 'pass' key"
    assert "pages" in data, "reference_diff.json missing 'pages' key"
    assert len(data["pages"]) >= 1, "reference_diff.json has no pages"

    for page in data["pages"]:
        assert "mismatch_pct" in page, f"page entry missing mismatch_pct: {page}"
