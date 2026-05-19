"""Unit tests for the aggregated preflight.yml builder (Issue #37 P1 task 6).

These tests exercise ``_build_preflight`` directly against synthetic
per-audit yml fixtures written to ``tmp_path``. The pipeline orchestration
(``_run_audit``) is exercised by the integration test
``tests/integration/test_preflight_v2.py`` once a real --audit run exists.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from render_pipeline import _build_preflight  # noqa: E402


def _write(path: Path, payload: dict) -> None:
    path.write_text(
        yaml.dump(payload, sort_keys=True, allow_unicode=True,
                  default_flow_style=False),
        encoding="utf-8",
    )


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


def _all_ok_payloads(out_dir: Path) -> None:
    """Write 'ok' fixtures for every sub-audit."""
    _write(out_dir / "inventory.yml", {"spreads": [{"elements_dropped": []}]})
    _write(out_dir / "text_audit.yml", {"pages": [{"lines_unmatched": []}]})
    _write(out_dir / "image_audit.yml", {"pages": [{"vector_paths": {"delta": 0}}]})
    _write(out_dir / "font_audit.yml", {"ok": True, "missing_in_preview": []})
    _write(out_dir / "text_render_audit.yml", {"ok": True, "missing_in_preview": {}})
    _write(out_dir / "text_position_audit.yml", {"ok": True, "large_deltas_count": 0})
    _write(out_dir / "run_style_audit.yml", {"ok": True, "style_drifts": []})
    _write(out_dir / "region_color_audit.yml",
           {"pattern": "all_ok", "by_severity": {"ok": 4, "fill_likely": 0}})


def test_all_audits_ok_yields_preflight_ok(tmp_path):
    _all_ok_payloads(tmp_path)
    result = _build_preflight(tmp_path, "tpl", **_paths(tmp_path))
    assert result["template"] == "tpl"
    assert result["ok"] is True
    assert result["hot_issues"] == []
    # All seven required sub-audits present
    for name in (
        "inventory", "text_audit", "image_audit", "font_audit",
        "text_render_audit", "text_position_audit", "run_style_audit",
        "region_color_audit",
    ):
        assert name in result["audits"], name
    # per_element_drift / region_color_audit are recorded as ok=True (diagnostic)
    assert result["audits"]["region_color_audit"]["ok"] is True


def test_two_failures_yields_two_hot_issues(tmp_path):
    _all_ok_payloads(tmp_path)
    # Fail font_audit + text_position_audit. text_position_audit is
    # magnitude-bucketed: a structural (>5pt) drift surfaces as the
    # `text_position_audit_structural` sub-audit.
    _write(tmp_path / "font_audit.yml",
           {"ok": False, "missing_in_preview": ["GothamNarrow-Bold", "Vollkorn-Italic"]})
    _write(tmp_path / "text_position_audit.yml",
           {"ok": False, "large_deltas_count": 7, "structural_deltas_count": 7,
            "jitter_deltas_count": 0})
    result = _build_preflight(tmp_path, "tpl", **_paths(tmp_path))
    assert result["ok"] is False
    assert len(result["hot_issues"]) == 2
    failing = {h["audit"] for h in result["hot_issues"]}
    assert failing == {"font_audit", "text_position_audit_structural"}


def test_hot_issues_capped_at_5(tmp_path):
    """≥6 failing audits → hot_issues capped at 5."""
    _all_ok_payloads(tmp_path)
    # Fail 6 audits, with descending issue counts to verify ordering.
    _write(tmp_path / "inventory.yml",
           {"spreads": [{"elements_dropped": ["a"] * 100}]})
    _write(tmp_path / "text_audit.yml",
           {"pages": [{"lines_unmatched": ["x"] * 80}]})
    _write(tmp_path / "image_audit.yml",
           {"pages": [{"vector_paths": {"delta": 60}}]})
    _write(tmp_path / "font_audit.yml",
           {"ok": False, "missing_in_preview": ["a"] * 40})
    _write(tmp_path / "text_render_audit.yml",
           {"ok": False, "missing_in_preview": {"a": 1, "b": 2}})  # 2 missing
    _write(tmp_path / "text_position_audit.yml",
           {"ok": False, "large_deltas_count": 20})

    result = _build_preflight(tmp_path, "tpl", **_paths(tmp_path))
    assert result["ok"] is False
    assert len(result["hot_issues"]) == 5
    # Top of the list is the highest-issue-count failure.
    assert result["hot_issues"][0]["audit"] == "inventory"
    assert result["hot_issues"][0]["issues"] == 100


def test_missing_yml_omitted_from_audits(tmp_path):
    """Audits whose yml file doesn't exist are not in the `audits` dict."""
    # Only write 2 audits; others are missing.
    _write(tmp_path / "inventory.yml", {"spreads": [{"elements_dropped": []}]})
    _write(tmp_path / "font_audit.yml", {"ok": True, "missing_in_preview": []})
    result = _build_preflight(tmp_path, "tpl", **_paths(tmp_path))
    assert set(result["audits"].keys()) == {"inventory", "font_audit"}
    # When all present audits ok → preflight ok
    assert result["ok"] is True


def test_deterministic_output(tmp_path):
    """Two runs over the same fixtures produce byte-identical YAML."""
    _all_ok_payloads(tmp_path)
    r1 = _build_preflight(tmp_path, "tpl", **_paths(tmp_path))
    r2 = _build_preflight(tmp_path, "tpl", **_paths(tmp_path))
    y1 = yaml.dump(r1, sort_keys=True, allow_unicode=True, default_flow_style=False)
    y2 = yaml.dump(r2, sort_keys=True, allow_unicode=True, default_flow_style=False)
    assert y1 == y2


def test_diagnostic_audits_never_fail_preflight(tmp_path):
    """per_element_drift + region_color_audit are diagnostic — even when
    they report findings they don't downgrade preflight.ok."""
    _all_ok_payloads(tmp_path)
    # per_element_drift has top contributors but is recorded ok=True
    _write(tmp_path / "per_element_drift.yml",
           {"pages": [{"top_contributors": [{"pct_of_page_mismatch": 80.0}]}]})
    # region_color_audit reports fill_likely=4 but is diagnostic
    _write(tmp_path / "region_color_audit.yml",
           {"pattern": "fill_likely_dominates", "by_severity": {"fill_likely": 4}})
    result = _build_preflight(tmp_path, "tpl", **_paths(tmp_path))
    assert result["ok"] is True
    assert result["audits"]["region_color_audit"]["ok"] is True
    assert result["audits"]["region_color_audit"]["issues"] == 4


def test_run_style_audit_large_drifts_fail_preflight(tmp_path):
    """run_style_audit with 1+ severity=large drift → preflight.ok=False."""
    _all_ok_payloads(tmp_path)
    _write(tmp_path / "run_style_audit.yml", {
        "ok": False,
        "style_drifts": [
            {"severity": "large", "text": "x"},
            {"severity": "small", "text": "y"},
        ],
    })
    result = _build_preflight(tmp_path, "tpl", **_paths(tmp_path))
    assert result["ok"] is False
    assert result["audits"]["run_style_audit"]["ok"] is False
    assert result["audits"]["run_style_audit"]["issues"] == 1  # large only


def test_corrupt_yml_treated_as_missing(tmp_path):
    """A malformed yml file does NOT crash the builder; it's treated as missing."""
    # Truly malformed: parser raises.
    (tmp_path / "inventory.yml").write_text(":\n- - x\n", encoding="utf-8")
    # Write one good audit so we have at least one entry.
    _write(tmp_path / "font_audit.yml", {"ok": True, "missing_in_preview": []})
    result = _build_preflight(tmp_path, "tpl", **_paths(tmp_path))
    # inventory was unparseable → not in audits; font_audit ok → preflight ok
    assert "inventory" not in result["audits"]
    assert result["ok"] is True


def test_informational_only_line_spacing_audit_does_not_fail_preflight(tmp_path):
    """F-017: E2 line_spacing_audit is deprecated as a primary signal.
    When its YAML carries informational_only=true, preflight must record
    it as ok=true even when drift_count > 0 and ok=false in the YAML."""
    _all_ok_payloads(tmp_path)
    line_spacing_path = tmp_path / "line_spacing_audit.yml"
    _write(line_spacing_path, {
        "informational_only": True,
        "canonical_replacement": "line_spacing_pixel_audit",
        "ok": False,
        "line_spacing_drift_count": 4,
        "line_spacing_drift": [],
    })
    result = _build_preflight(
        tmp_path, "tpl",
        line_spacing_audit_path=line_spacing_path,
        **_paths(tmp_path),
    )
    # E2 must not fail preflight when informational_only.
    assert result["ok"] is True
    assert result["audits"]["line_spacing_audit"]["ok"] is True
    # The drift count is still recorded for visibility.
    assert result["audits"]["line_spacing_audit"]["issues"] == 4
    assert "informational" in result["audits"]["line_spacing_audit"]["detail"]


def test_non_informational_line_spacing_audit_still_fails_preflight(tmp_path):
    """Backward compatibility: legacy YAMLs without informational_only=true
    continue to gate preflight (so a stale lab branch doesn't silently
    flip behaviour)."""
    _all_ok_payloads(tmp_path)
    line_spacing_path = tmp_path / "line_spacing_audit.yml"
    _write(line_spacing_path, {
        "ok": False,
        "line_spacing_drift_count": 2,
        "line_spacing_drift": [],
    })
    result = _build_preflight(
        tmp_path, "tpl",
        line_spacing_audit_path=line_spacing_path,
        **_paths(tmp_path),
    )
    assert result["ok"] is False
    assert result["audits"]["line_spacing_audit"]["ok"] is False


# ---------------------------------------------------------------------------
# Split mixed-font headline gate (line_spacing_pixel_audit kind=split_headline)
# ---------------------------------------------------------------------------


def test_split_headline_within_tolerance_passes_preflight(tmp_path):
    """A split mixed-font headline whose per-line ink-top and inter-line
    spacing both stay within SPLIT_HEADLINE_TOL_PT must NOT fail preflight."""
    _all_ok_payloads(tmp_path)
    lspa = tmp_path / "line_spacing_pixel_audit.yml"
    _write(lspa, {
        "row_count": 1,
        "summary": {"match": 1, "minor": 0, "major": 0, "unmatched_count": 0},
        "rows": [{
            "anname": "u1175", "kind": "split_headline", "page": 0,
            "group": ["u1175", "u1175_l2", "u1175_l3"],
            "max_drift_pt": 0.3, "max_spacing_drift_pt": 0.3,
        }],
    })
    result = _build_preflight(
        tmp_path, "tpl",
        line_spacing_pixel_path=lspa,
        **_paths(tmp_path),
    )
    assert result["ok"] is True
    assert result["audits"]["split_headline_spacing"]["ok"] is True


def test_split_headline_mis_spaced_fails_preflight(tmp_path):
    """A split mixed-font headline whose Vollkorn accent line is mis-spaced
    beyond SPLIT_HEADLINE_TOL_PT MUST fail preflight — this is the gate that
    catches the FLOP-ascent-ratio mis-calibration so it cannot ship."""
    _all_ok_payloads(tmp_path)
    lspa = tmp_path / "line_spacing_pixel_audit.yml"
    _write(lspa, {
        "row_count": 1,
        "summary": {"match": 0, "minor": 0, "major": 1, "unmatched_count": 0},
        "rows": [{
            "anname": "u1175", "kind": "split_headline", "page": 0,
            "group": ["u1175", "u1175_l2", "u1175_l3"],
            # The mis-calibrated Vollkorn line: 7.2pt per-line drift.
            "max_drift_pt": 7.2, "max_spacing_drift_pt": 7.2,
        }],
    })
    result = _build_preflight(
        tmp_path, "tpl",
        line_spacing_pixel_path=lspa,
        **_paths(tmp_path),
    )
    assert result["ok"] is False
    assert result["audits"]["split_headline_spacing"]["ok"] is False
    assert result["audits"]["split_headline_spacing"]["issues"] == 1
    assert "u1175" in result["audits"]["split_headline_spacing"]["detail"]


def test_split_headline_spacing_drift_alone_fails_preflight(tmp_path):
    """Even when each line's absolute ink-top drift is small, a divergent
    inter-line SPACING (line N too tight / too loose vs its neighbour) fails
    preflight — the spacing channel is graded independently."""
    _all_ok_payloads(tmp_path)
    lspa = tmp_path / "line_spacing_pixel_audit.yml"
    _write(lspa, {
        "row_count": 1,
        "summary": {"match": 0, "minor": 0, "major": 1, "unmatched_count": 0},
        "rows": [{
            "anname": "u1214", "kind": "split_headline", "page": 1,
            "group": ["u1214", "u1214_l2"],
            "max_drift_pt": 1.0, "max_spacing_drift_pt": 5.6,
        }],
    })
    result = _build_preflight(
        tmp_path, "tpl",
        line_spacing_pixel_path=lspa,
        **_paths(tmp_path),
    )
    assert result["ok"] is False
    assert result["audits"]["split_headline_spacing"]["ok"] is False


# ---------------------------------------------------------------------------
# Audit-reliability review: phase_errors visibility in preflight
# ---------------------------------------------------------------------------


def test_phase_errors_section_surfaces_in_preflight(tmp_path):
    """A captured phase error must appear in preflight.yml::errors and
    force ok=False so a silent exception cannot leave the rollup green."""
    _all_ok_payloads(tmp_path)
    result = _build_preflight(
        tmp_path, "tpl",
        **_paths(tmp_path),
        phase_errors={
            "line_spacing_pixel_audit": "ValueError: bad bbox on u347",
        },
    )
    assert result["ok"] is False
    assert "errors" in result
    assert result["errors"] == {
        "line_spacing_pixel_audit": "ValueError: bad bbox on u347",
    }
    # hot_issues includes the errored phase at the top.
    assert any(
        h["audit"] == "line_spacing_pixel_audit"
        and "phase errored" in h["message"]
        for h in result["hot_issues"]
    )


def test_no_phase_errors_section_when_empty(tmp_path):
    """When no errors are passed, the errors dict is empty (not absent)
    so consumers can rely on it always being present."""
    _all_ok_payloads(tmp_path)
    result = _build_preflight(tmp_path, "tpl", **_paths(tmp_path))
    assert result["ok"] is True
    assert result["errors"] == {}


def test_multiple_phase_errors_recorded(tmp_path):
    """Each errored phase becomes its own hot_issue entry."""
    _all_ok_payloads(tmp_path)
    result = _build_preflight(
        tmp_path, "tpl",
        **_paths(tmp_path),
        phase_errors={
            "line_spacing_pixel_audit": "FileNotFoundError: preview.pdf",
            "per_region_regression": "TypeError: history corrupt",
        },
    )
    assert result["ok"] is False
    assert len(result["errors"]) == 2
    error_audits = {
        h["audit"] for h in result["hot_issues"]
        if "phase errored" in h["message"]
    }
    assert error_audits == {
        "line_spacing_pixel_audit",
        "per_region_regression",
    }


# ---------------------------------------------------------------------------
# Phase E5f: idml_attribute_coverage gate wired into preflight
# ---------------------------------------------------------------------------

def test_attribute_coverage_ok_passes_preflight(tmp_path):
    """A clean attribute-coverage gate yml leaves preflight green."""
    _all_ok_payloads(tmp_path)
    acg = tmp_path / "attribute_coverage_audit.yml"
    _write(acg, {"ok": True, "issues": 0,
                 "detail": "all significant unconsumed attributes accounted for"})
    result = _build_preflight(
        tmp_path, "tpl", **_paths(tmp_path), attribute_coverage_path=acg,
    )
    assert result["ok"] is True
    assert result["audits"]["idml_attribute_coverage"]["ok"] is True
    assert result["audits"]["idml_attribute_coverage"]["issues"] == 0


def test_attribute_coverage_new_drop_fails_preflight(tmp_path):
    """A new unconsumed attribute fails the gate and the preflight."""
    _all_ok_payloads(tmp_path)
    acg = tmp_path / "attribute_coverage_audit.yml"
    _write(acg, {
        "ok": False, "issues": 2,
        "detail": "2 NEW significant unconsumed attribute(s) not in baseline: "
                  "Rectangle/GlowEffect, TextFrame/NewAttr",
    })
    result = _build_preflight(
        tmp_path, "tpl", **_paths(tmp_path), attribute_coverage_path=acg,
    )
    assert result["ok"] is False
    row = result["audits"]["idml_attribute_coverage"]
    assert row["ok"] is False
    assert row["issues"] == 2
    hot = {h["audit"] for h in result["hot_issues"]}
    assert "idml_attribute_coverage" in hot


def test_attribute_coverage_missing_yml_omitted(tmp_path):
    """No attribute-coverage yml -> audit silently omitted from preflight."""
    _all_ok_payloads(tmp_path)
    result = _build_preflight(
        tmp_path, "tpl", **_paths(tmp_path),
        attribute_coverage_path=tmp_path / "absent.yml",
    )
    assert "idml_attribute_coverage" not in result["audits"]
