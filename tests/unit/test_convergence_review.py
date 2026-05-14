"""Unit tests for tools/convergence_review.py — issue classifier + sorter."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import convergence_review as cr  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture helpers.
# ---------------------------------------------------------------------------

def _write_yml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1 — preflight.ok=true => verdict=PASS, issues=[].
# ---------------------------------------------------------------------------
def test_pass_when_preflight_ok(tmp_path):
    _write_yml(
        tmp_path / "preflight.yml",
        {"template": "slug", "ok": True, "audits": {}, "hot_issues": []},
    )
    review = cr.build_review("slug", tmp_path)
    assert review["verdict"] == "PASS"
    assert review["preflight_ok"] is True
    assert review["issues"] == []


# ---------------------------------------------------------------------------
# Test 2 — region_color_audit icc_likely => scribus-engine-bug.
# ---------------------------------------------------------------------------
def test_region_color_icc_likely_is_scribus_engine_bug(tmp_path):
    _write_yml(
        tmp_path / "preflight.yml",
        {"template": "slug", "ok": False, "audits": {}, "hot_issues": []},
    )
    _write_yml(
        tmp_path / "region_color_audit.yml",
        {
            "template": "slug",
            "frames": [
                {
                    "anname": "u1ae",
                    "page": 0,
                    "type": "Polygon",
                    "severity": "icc_likely",
                    "mean_delta": 4.0,
                }
            ],
        },
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.0)
    assert len(review["issues"]) == 1
    assert review["issues"][0]["classification"] == "scribus-engine-bug"


# ---------------------------------------------------------------------------
# Test 3 — region_color_audit fill_likely => converter-bug.
# ---------------------------------------------------------------------------
def test_region_color_fill_likely_is_converter_bug(tmp_path):
    _write_yml(tmp_path / "preflight.yml", {"template": "slug", "ok": False})
    _write_yml(
        tmp_path / "region_color_audit.yml",
        {
            "template": "slug",
            "frames": [
                {
                    "anname": "u2",
                    "page": 0,
                    "severity": "fill_likely",
                    "mean_delta": 30.0,
                }
            ],
        },
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.0)
    assert review["issues"][0]["classification"] == "converter-bug"


# ---------------------------------------------------------------------------
# Test 4 — diff_bboxes drift_type=missing + bbox not in inventory annames =>
# converter-bug.
# ---------------------------------------------------------------------------
def test_missing_bbox_not_in_inventory_is_converter_bug(tmp_path):
    _write_yml(tmp_path / "preflight.yml", {"template": "slug", "ok": False})
    _write_yml(
        tmp_path / "inventory.yml",
        {
            "template": "slug",
            "spreads": [
                {"elements_emitted": [{"anname": "u1"}, {"anname": "u2"}]}
            ],
        },
    )
    _write_json(
        tmp_path / "diff_bboxes.json",
        {
            "template_slug": "slug",
            "pages": [
                {
                    "page": 1,
                    "bboxes": [
                        {
                            "attributed_slot": "u99",
                            "drift_type": "missing",
                        }
                    ],
                }
            ],
        },
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.0)
    converter_issues = [
        i for i in review["issues"]
        if i["classification"] == "converter-bug" and i["audit"] == "diff_bboxes"
    ]
    assert len(converter_issues) == 1


# ---------------------------------------------------------------------------
# Test 5 — leverage sorting by -est_drift_drop.
# ---------------------------------------------------------------------------
def test_sort_by_leverage(tmp_path):
    _write_yml(tmp_path / "preflight.yml", {"template": "slug", "ok": False})
    _write_yml(
        tmp_path / "region_color_audit.yml",
        {
            "template": "slug",
            "frames": [
                {"anname": "uHIGH", "page": 1, "severity": "fill_likely", "mean_delta": 20},
                {"anname": "uLOW", "page": 1, "severity": "fill_likely", "mean_delta": 20},
            ],
        },
    )
    _write_yml(
        tmp_path / "per_element_drift.yml",
        {
            "template": "slug",
            "pages": [
                {
                    "page": 1,
                    "total_mismatch_pct": 5.0,
                    "top_contributors": [
                        {"slot": "uHIGH", "pct_of_page_mismatch": 3.0},
                        {"slot": "uLOW", "pct_of_page_mismatch": 1.0},
                    ],
                }
            ],
        },
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.0)
    issues = review["issues"]
    assert issues[0]["slot"] == "uHIGH"
    assert issues[1]["slot"] == "uLOW"


# ---------------------------------------------------------------------------
# Test 6 — min-drift-pp filter demotes low-leverage issues to minor.
# ---------------------------------------------------------------------------
def test_min_drift_filter_demotes_to_minor(tmp_path):
    _write_yml(tmp_path / "preflight.yml", {"template": "slug", "ok": False})
    _write_yml(
        tmp_path / "region_color_audit.yml",
        {
            "template": "slug",
            "frames": [
                {"anname": "uTINY", "page": 1, "severity": "fill_likely", "mean_delta": 20}
            ],
        },
    )
    _write_yml(
        tmp_path / "per_element_drift.yml",
        {
            "template": "slug",
            "pages": [
                {
                    "page": 1,
                    "total_mismatch_pct": 0.3,
                    "top_contributors": [
                        {"slot": "uTINY", "pct_of_page_mismatch": 0.3}
                    ],
                }
            ],
        },
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.5)
    assert review["issues"][0]["classification"] == "minor"
    assert review["hot_issues_by_leverage"] == []


# ---------------------------------------------------------------------------
# Test 7 — --format json produces parseable JSON.
# ---------------------------------------------------------------------------
def test_format_json_parses(tmp_path):
    _write_yml(tmp_path / "preflight.yml", {"template": "slug", "ok": True})
    review = cr.build_review("slug", tmp_path)
    rendered = cr._format_json(review)
    parsed = json.loads(rendered)
    assert parsed["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# Test 8 — ambiguous text position without IDML => human-review.
# ---------------------------------------------------------------------------
def test_text_position_without_idml_is_human_review(tmp_path):
    _write_yml(tmp_path / "preflight.yml", {"template": "slug", "ok": False})
    _write_yml(
        tmp_path / "text_position_audit.yml",
        {
            "template": "slug",
            "large_deltas": [
                {
                    "anname": "u100",
                    "text": "hello",
                    "page": 1,
                    "dx_pt": 1.0,
                    "dy_pt": 0.2,
                    "severity": "large",
                }
            ],
        },
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.0)
    assert review["issues"][0]["classification"] == "human-review"


# ---------------------------------------------------------------------------
# Test 9 — asset_audit failures become issues with right classification.
# ---------------------------------------------------------------------------
def test_asset_audit_links_missing_is_authoring_bug(tmp_path):
    _write_yml(tmp_path / "preflight.yml", {"template": "slug", "ok": False})
    _write_yml(
        tmp_path / "asset_audit.yml",
        {
            "template": "slug",
            "ok": False,
            "links_missing": ["broken.psd"],
            "links_unconverted": [],
            "composite_ai_detected": [],
        },
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.0)
    classes = [i["classification"] for i in review["issues"]]
    assert "authoring-bug" in classes


def test_asset_audit_composite_ai_is_converter_bug(tmp_path):
    _write_yml(tmp_path / "preflight.yml", {"template": "slug", "ok": False})
    _write_yml(
        tmp_path / "asset_audit.yml",
        {
            "template": "slug",
            "ok": False,
            "links_missing": [],
            "links_unconverted": [],
            "composite_ai_detected": [{"path": "Links/x.ai", "signals": ["aspect_ratio=3.5"]}],
        },
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.0)
    converter = [i for i in review["issues"] if i["classification"] == "converter-bug"]
    assert len(converter) == 1


# ---------------------------------------------------------------------------
# Test 10 — font_audit missing fonts is converter-bug.
# ---------------------------------------------------------------------------
def test_font_audit_missing_is_converter_bug(tmp_path):
    _write_yml(tmp_path / "preflight.yml", {"template": "slug", "ok": False})
    _write_yml(
        tmp_path / "font_audit.yml",
        {"template": "slug", "missing_in_preview": ["Vollkorn-Black"]},
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.0)
    assert review["issues"][0]["classification"] == "converter-bug"
    assert review["issues"][0]["audit"] == "font_audit"


# ---------------------------------------------------------------------------
# Test 11 — bin/convergence-review shim invokes the script.
# ---------------------------------------------------------------------------
def test_bin_shim_invokes_module():
    bin_path = ROOT / "bin" / "convergence-review"
    assert bin_path.exists()
    assert bin_path.stat().st_mode & 0o111
    result = subprocess.run(
        [sys.executable, str(bin_path), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "slug" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Test 12 — end-to-end CLI with synthetic dir produces JSON output.
# ---------------------------------------------------------------------------
def test_cli_json_format_end_to_end(tmp_path):
    _write_yml(tmp_path / "preflight.yml", {"template": "slug", "ok": True})
    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS / "convergence_review.py"),
            "slug",
            "--format",
            "json",
            "--validation-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed["template"] == "slug"


# ---------------------------------------------------------------------------
# Audit-reliability item 4: E4/E5/E6 surface in convergence-review.
# ---------------------------------------------------------------------------


def test_line_spacing_pixel_audit_drifts_surface_as_issues(tmp_path):
    """E4 (pixel-level) is the canonical line-spacing signal — its
    rows must appear as issues in the review's hot-issues list."""
    _write_yml(
        tmp_path / "preflight.yml",
        {"template": "slug", "ok": False, "audits": {}, "hot_issues": []},
    )
    _write_yml(
        tmp_path / "line_spacing_pixel_audit.yml",
        {
            "rows": [
                {"anname": "u347", "max_drift_pt": 3.5, "page": 0},
                {"anname": "u35f", "max_drift_pt": 0.4, "page": 0},  # below threshold
            ],
        },
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.0)
    pixel_issues = [
        i for i in review["issues"]
        if i["audit"] == "line_spacing_pixel_audit"
    ]
    # u347 (3.5pt > 1.0pt) surfaces; u35f (0.4pt) does not.
    assert len(pixel_issues) == 1
    assert pixel_issues[0]["slot"] == "u347"
    assert pixel_issues[0]["classification"] == "converter-bug"


def test_image_visibility_invisible_frames_surface_as_issues(tmp_path):
    """E5 invisible frames must surface as converter-bug issues."""
    _write_yml(
        tmp_path / "preflight.yml",
        {"template": "slug", "ok": False, "audits": {}, "hot_issues": []},
    )
    _write_yml(
        tmp_path / "image_frame_visibility_audit.yml",
        {
            "invisible_frames": [
                {"anname": "u141", "visibility_ratio": 0.05},
                {"anname": "u3e7", "visibility_ratio": 0.12},
            ],
        },
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.0)
    visib_issues = [
        i for i in review["issues"]
        if i["audit"] == "image_frame_visibility_audit"
    ]
    assert len(visib_issues) == 2
    assert {i["slot"] for i in visib_issues} == {"u141", "u3e7"}
    assert all(i["classification"] == "converter-bug" for i in visib_issues)


def test_per_region_regression_surfaces_as_issues(tmp_path):
    """E6 regressions must surface as issues alongside the per-iteration
    audits."""
    _write_yml(
        tmp_path / "preflight.yml",
        {"template": "slug", "ok": False, "audits": {}, "hot_issues": []},
    )
    _write_yml(
        tmp_path / "per_region_regression.yml",
        {
            "seeded": False,
            "regression_count": 2,
            "regressions": [
                {
                    "anname": "u347",
                    "kind": "line_spacing_drift_increased",
                    "prev_max_drift_pt": 1.0,
                    "curr_max_drift_pt": 2.5,
                },
                {
                    "anname": "u141",
                    "kind": "image_visibility_dropped",
                    "prev_visibility_ratio": 0.9,
                    "curr_visibility_ratio": 0.5,
                },
            ],
        },
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.0)
    reg_issues = [
        i for i in review["issues"]
        if i["audit"] == "per_region_regression"
    ]
    assert len(reg_issues) == 2
    assert {i["slot"] for i in reg_issues} == {"u347", "u141"}


def test_seeded_per_region_regression_does_not_surface(tmp_path):
    """A seeded regression file (first run on a slug) has nothing to
    compare → no issues surfaced from E6."""
    _write_yml(
        tmp_path / "preflight.yml",
        {"template": "slug", "ok": True, "audits": {}, "hot_issues": []},
    )
    _write_yml(
        tmp_path / "per_region_regression.yml",
        {"seeded": True, "regression_count": 0, "regressions": []},
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.0)
    assert not any(
        i["audit"] == "per_region_regression" for i in review["issues"]
    )


def test_informational_e2_drifts_no_longer_surface(tmp_path):
    """F-017: E2's informational_only output must NOT add issues to the
    review. The pixel audit (E4) is the canonical replacement."""
    _write_yml(
        tmp_path / "preflight.yml",
        {"template": "slug", "ok": False, "audits": {}, "hot_issues": []},
    )
    _write_yml(
        tmp_path / "line_spacing_audit.yml",
        {
            "informational_only": True,
            "ok": False,
            "drifts": [
                {"anname": "u1", "delta_pt": 3.0, "page": 0},
            ],
        },
    )
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.0)
    assert not any(
        i["audit"] == "line_spacing_audit" for i in review["issues"]
    )


def test_e4_e5_e6_leverage_exempt(tmp_path):
    """E4/E5/E6 findings are per-frame measured signals, not page-mismatch
    derivatives, so they shouldn't be dropped to 'minor' just because the
    leverage scoring can't tie them to a page region."""
    _write_yml(
        tmp_path / "preflight.yml",
        {"template": "slug", "ok": False, "audits": {}, "hot_issues": []},
    )
    _write_yml(
        tmp_path / "line_spacing_pixel_audit.yml",
        {"rows": [{"anname": "u1", "max_drift_pt": 2.5, "page": 0}]},
    )
    # No per_element_drift.yml → drift_drop=0 → would normally be 'minor'.
    review = cr.build_review("slug", tmp_path, min_drift_pp=0.5)
    pix = [i for i in review["issues"] if i["audit"] == "line_spacing_pixel_audit"]
    assert pix
    assert pix[0]["classification"] != "minor"
