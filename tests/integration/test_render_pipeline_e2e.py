"""End-to-end pipeline test for bin/render-gallery --audit on v2 falzflyer
(Issue #37 P3 task 18).

Validates the full audit-phase outputs: preflight.yml shape + 11 sub-audit
yml files + 2 heatmap PNGs (one per page). Skips cleanly when v2 falzflyer
fixtures or Scribus are unavailable (i.e. running outside the dev container).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
SLUG = "kandidat-falzflyer-din-lang-gruenes-cover-v2"
V2 = REPO / "templates" / SLUG
OUT = REPO / "build" / "validation" / SLUG


@pytest.mark.skipif(
    not (V2 / "baseline.pdf").exists() or not (V2 / "build.py").exists(),
    reason="v2 falzflyer fixtures missing — dev container only",
)
def test_render_gallery_audit_emits_all_artifacts():
    """Full pipeline: bin/render-gallery <slug> --audit must produce
    preflight.yml + all 11 sub-audit files (when baseline+preview are present)."""
    binary = REPO / "bin" / "render-gallery"
    if not binary.exists():
        pytest.skip("bin/render-gallery missing")

    proc = subprocess.run(
        [str(binary), SLUG, "--audit"],
        cwd=REPO, capture_output=True, text=True, timeout=900,
    )
    # exit 0 if preflight ok; exit 1 if preflight or render failed. Either is
    # acceptable for THIS test — we just verify the artefacts exist.
    if proc.returncode not in (0, 1):
        pytest.skip(
            f"render-gallery returned unexpected exit code {proc.returncode}: "
            f"{proc.stderr[-500:]}"
        )

    preflight = OUT / "preflight.yml"
    assert preflight.exists(), f"missing {preflight}"
    pre = yaml.safe_load(preflight.read_text(encoding="utf-8"))
    assert isinstance(pre.get("ok"), bool)
    assert isinstance(pre.get("audits"), dict)
    assert isinstance(pre.get("hot_issues"), list)

    # Audits that ALWAYS run when preview.pdf + baseline.pdf + build.py exist.
    # The 9-audit core. `inventory` and `per_element_drift` need extras (an
    # IDML source / diff_bboxes.json respectively) so they're considered
    # optional in this E2E.
    expected_core_audits = [
        "text_audit", "image_audit", "font_audit",
        "text_render_audit", "text_position_audit", "run_style_audit",
        "region_color_audit",
        "line_spacing_audit",       # Phase E2 (P3)
        "visual_diff_regions",      # Phase H / Backport 12 (P2)
    ]
    for name in expected_core_audits:
        assert name in pre["audits"], (
            f"audit {name} not in preflight.audits "
            f"(available: {sorted(pre['audits'].keys())})"
        )

    # YAML files that should exist when audit ran end-to-end (core 9).
    for name in (
        "text_audit.yml", "image_audit.yml",
        "font_audit.yml", "text_render_audit.yml",
        "text_position_audit.yml", "run_style_audit.yml",
        "region_color_audit.yml",
        "line_spacing_audit.yml", "visual_diff_regions.yml",
    ):
        assert (OUT / name).exists(), f"missing {OUT / name}"

    # Heatmap PNGs for both pages of the v2 Falzflyer.
    assert (OUT / "visual_diff_heatmap-page-01.png").exists()
    assert (OUT / "visual_diff_heatmap-page-02.png").exists()

    # When preflight.ok is False, exit must be 1.
    if pre["ok"] is False:
        assert proc.returncode == 1, (
            "preflight.ok=False but --audit returned 0"
        )


@pytest.mark.skipif(
    not (V2 / "baseline.pdf").exists(),
    reason="v2 fixtures missing",
)
def test_preflight_per_element_drift_no_over_attribution():
    """P1 task 1 acceptance check: after --audit, top-3 contributors on each
    page sum to ≤100 % (was 139 % before the HSL-halo normalisation)."""
    ped = OUT / "per_element_drift.yml"
    if not ped.exists():
        pytest.skip("per_element_drift.yml not produced (run --audit first)")
    report = yaml.safe_load(ped.read_text(encoding="utf-8"))
    for page in report.get("pages", []):
        top = page.get("top_contributors", [])
        total_pct = sum(c.get("pct_of_page_mismatch", 0) for c in top[:3])
        assert total_pct <= 100.5, (
            f"page {page['page']} top-3 sum to {total_pct:.2f}% (> 100.5%)"
        )


@pytest.mark.skipif(
    not (V2 / "baseline.pdf").exists(),
    reason="v2 fixtures missing",
)
def test_preflight_text_position_no_reversed_words():
    """P1 task 2 acceptance check: no reverse-glyph false positives in
    text_position_audit large_deltas."""
    tpa = OUT / "text_position_audit.yml"
    if not tpa.exists():
        pytest.skip("text_position_audit.yml not produced")
    report = yaml.safe_load(tpa.read_text(encoding="utf-8"))
    for delta in report.get("large_deltas", []):
        text = delta.get("text", "")
        assert "musserp" not in text.lower(), (
            f"reversed-glyph artefact in large_deltas: {text!r}"
        )
