"""Integration tests for preflight.yml against the live v2 falzflyer artifacts
(Issue #37 P1 task 6).

These tests exercise ``_build_preflight`` against the on-disk validation
directory if it exists. Tests skip cleanly when the artifacts haven't been
produced yet (CI environments without Scribus + baseline.pdf).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from render_pipeline import _build_preflight  # noqa: E402

SLUG = "kandidat-falzflyer-din-lang-gruenes-cover-v2"
OUT_DIR = ROOT / "build" / "validation" / SLUG


def _have_any_audit_artifact() -> bool:
    """True if at least one sub-audit yml exists in the validation dir."""
    if not OUT_DIR.exists():
        return False
    for name in (
        "inventory.yml", "text_audit.yml", "image_audit.yml",
        "font_audit.yml", "text_render_audit.yml",
        "text_position_audit.yml", "run_style_audit.yml",
        "region_color_audit.yml",
    ):
        if (OUT_DIR / name).exists():
            return True
    return False


def _paths(out_dir: Path) -> dict[str, Path]:
    return {
        "inventory_path": out_dir / "inventory.yml",
        "text_audit_path": out_dir / "text_audit.yml",
        "image_audit_path": out_dir / "image_audit.yml",
        "font_audit_path": out_dir / "font_audit.yml",
        "text_render_audit_path": out_dir / "text_render_audit.yml",
        "text_position_audit_path": out_dir / "text_position_audit.yml",
        "run_style_audit_path": out_dir / "run_style_audit.yml",
        "color_audit_path": out_dir / "region_color_audit.yml",
    }


def test_preflight_builds_against_live_artifacts():
    """Smoke: ``_build_preflight`` runs without crashing against whatever
    sub-audit ymls happen to be on disk for v2 falzflyer. Skips cleanly when
    no artifacts exist (i.e. --audit has never been run)."""
    if not _have_any_audit_artifact():
        pytest.skip(f"no audit artifacts present at {OUT_DIR}")
    pre = _build_preflight(OUT_DIR, SLUG, **_paths(OUT_DIR))
    assert pre["template"] == SLUG
    assert "ok" in pre
    assert isinstance(pre["ok"], bool)
    assert "audits" in pre
    assert "hot_issues" in pre
    assert isinstance(pre["audits"], dict)
    assert isinstance(pre["hot_issues"], list)
    # hot_issues never exceeds 5 by contract
    assert len(pre["hot_issues"]) <= 5


def test_preflight_shape_matches_documentation():
    """Each entry in `audits` has the documented {ok, issues, detail} keys."""
    if not _have_any_audit_artifact():
        pytest.skip(f"no audit artifacts present at {OUT_DIR}")
    pre = _build_preflight(OUT_DIR, SLUG, **_paths(OUT_DIR))
    for name, info in pre["audits"].items():
        for key in ("ok", "issues", "detail"):
            assert key in info, f"audit {name} missing key {key}"
        assert isinstance(info["ok"], bool)
        assert isinstance(info["issues"], int)
        assert isinstance(info["detail"], str)


def test_preflight_yml_emitted_when_audit_runs():
    """If preflight.yml already exists at the validation dir, validate its
    shape. We don't trigger --audit here (that's the e2e test in task 18);
    we just sanity-check the persisted artifact when present."""
    preflight_p = OUT_DIR / "preflight.yml"
    if not preflight_p.exists():
        pytest.skip(f"{preflight_p} not produced yet")
    pre = yaml.safe_load(preflight_p.read_text(encoding="utf-8"))
    assert "ok" in pre
    assert "audits" in pre
    assert "hot_issues" in pre


def test_preflight_no_audits_means_ok(tmp_path):
    """Empty validation dir → preflight ok=True (no failing audits)."""
    pre = _build_preflight(tmp_path, "empty", **_paths(tmp_path))
    assert pre["ok"] is True
    assert pre["audits"] == {}
    assert pre["hot_issues"] == []
