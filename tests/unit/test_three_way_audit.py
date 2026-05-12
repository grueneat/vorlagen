"""Unit tests for tools/three_way_audit.py — 3-way Venn audit classification.

Uses synthetic inputs: inventory.yml text, sla_inventory.yml text, build.py
content. Verifies each classification bucket with representative fixture elements.
"""
from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from three_way_audit import (
    run_three_way_audit,
    _extract_build_py_annames,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Fixture annames use valid hex patterns:
#   u100 = converter_bug:  in IDML (dropped) + in SLA + NOT in build.py
#   u101 = shared_drop:    in IDML (dropped) + NOT in SLA + NOT in build.py
#   u102 = match:          in all three, bbox within 1mm tolerance
#   u103 = geometry_drift: in all three, but SLA bbox differs > 1mm from build.py
#   u104 = suspicious_emit: in build.py only (NOT in IDML or SLA)

INVENTORY_YAML = dedent("""\
    template: test-template
    spreads:
      - spread_id: Spread_u1
        page: 0
        elements_total: 5
        elements_emitted: 2
        elements_dropped:
          - self: u101             # in IDML, NOT in SLA, NOT in build.py → shared_drop
            type: Polygon
            hint: inline vector path
          - self: u100             # in IDML, IN SLA, NOT in build.py → converter_bug
            type: Group
            hint: group container
""")

SLA_INVENTORY_YAML = dedent("""\
    template: test-template
    reference_sla: originals/test.sla
    pageobjects_total: 4
    pageobjects_by_anname:
      u100:
        ptype: 12
        ptype_label: group
        bbox_mm: {h: 30.0, rot: 0.0, w: 50.0, x: 10.0, y: 20.0}
        fcolor: null
        pcolor: null
        page: 0
        in_group: null
      u102:
        ptype: 6
        ptype_label: polygon
        bbox_mm: {h: 10.0, rot: 0.0, w: 20.0, x: 5.0, y: 5.0}
        fcolor: null
        pcolor: Black
        page: 0
        in_group: null
      u103:
        ptype: 6
        ptype_label: polygon
        bbox_mm: {h: 15.0, rot: 0.0, w: 25.0, x: 8.0, y: 8.0}
        fcolor: null
        pcolor: Black
        page: 0
        in_group: null
      u1ff:
        ptype: 2
        ptype_label: image
        bbox_mm: {h: 50.0, rot: 0.0, w: 40.0, x: 100.0, y: 200.0}
        fcolor: null
        pcolor: null
        page: 1
        in_group: null
""")

# build.py emits:
#   u102 (correct bbox ≈ SLA → match)
#   u103 (drifted bbox, x differs by 42mm → geometry_drift)
#   u104 (not in IDML or SLA → suspicious_emit)
BUILD_PY_CONTENT = dedent("""\
    page0.add(Polygon(
        x_mm=5.0, y_mm=5.0, w_mm=20.0, h_mm=10.0,
        anname='u102',
        fill='Black',
    ))
    page0.add(Polygon(
        x_mm=50.0, y_mm=50.0, w_mm=25.0, h_mm=15.0,
        anname='u103',
        fill='Black',
    ))
    page0.add(TextFrame(
        x_mm=0.0, y_mm=0.0, w_mm=100.0, h_mm=100.0,
        anname='u104',
        runs=[],
    ))
""")


def _write_fixtures(tmp_path: Path) -> tuple[Path, Path, Path]:
    inv = tmp_path / "inventory.yml"
    sla_inv = tmp_path / "sla_inventory.yml"
    build_py = tmp_path / "build.py"
    inv.write_text(INVENTORY_YAML)
    sla_inv.write_text(SLA_INVENTORY_YAML)
    build_py.write_text(BUILD_PY_CONTENT)
    return inv, sla_inv, build_py


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_converter_bug_bucket(tmp_path):
    """u100 is in IDML (dropped) + in SLA + NOT in build.py → converter_bug."""
    inv, sla_inv, build_py = _write_fixtures(tmp_path)
    report = run_three_way_audit(inv, sla_inv, build_py, template="test")

    bug_names = {e["anname"] for e in report["classification"]["converter_bug"]}
    assert "u100" in bug_names, f"Expected u100 in converter_bug; got {bug_names}"


def test_converter_bug_has_bbox_and_colors(tmp_path):
    """converter_bug entries include bbox_mm and fcolor/pcolor from SLA."""
    inv, sla_inv, build_py = _write_fixtures(tmp_path)
    report = run_three_way_audit(inv, sla_inv, build_py, template="test")

    bug = next(e for e in report["classification"]["converter_bug"] if e["anname"] == "u100")
    assert bug["bbox_mm"] is not None
    assert "x" in bug["bbox_mm"]
    assert "fcolor" in bug
    assert "pcolor" in bug
    assert bug["ptype_label"] == "group"


def test_shared_drop_bucket(tmp_path):
    """u101 is in IDML (dropped) + NOT in SLA + NOT in build.py → shared_drop."""
    inv, sla_inv, build_py = _write_fixtures(tmp_path)
    report = run_three_way_audit(inv, sla_inv, build_py, template="test")

    drop_names = {e["anname"] for e in report["classification"]["shared_drop"]}
    assert "u101" in drop_names, (
        f"Expected u101 in shared_drop; got {drop_names}"
    )


def test_match_bucket(tmp_path):
    """u102 is in all three with bbox close to SLA (within 1mm) → match."""
    inv, sla_inv, build_py = _write_fixtures(tmp_path)
    report = run_three_way_audit(inv, sla_inv, build_py, template="test")

    match_names = {e["anname"] for e in report["classification"]["match"]}
    assert "u102" in match_names, f"Expected u102 in match; got {match_names}"


def test_geometry_drift_bucket(tmp_path):
    """u103 is in all three but SLA bbox differs by >1mm from build.py → geometry_drift."""
    inv, sla_inv, build_py = _write_fixtures(tmp_path)
    report = run_three_way_audit(inv, sla_inv, build_py, template="test")

    drift_names = {e["anname"] for e in report["classification"]["geometry_drift"]}
    assert "u103" in drift_names, (
        f"Expected u103 in geometry_drift (x: SLA=8mm, build.py=50mm); got {drift_names}"
    )

    drift_entry = next(e for e in report["classification"]["geometry_drift"] if e["anname"] == "u103")
    assert "sla_bbox_mm" in drift_entry
    assert "build_py_bbox_mm" in drift_entry
    assert "delta_mm" in drift_entry


def test_suspicious_emit_bucket(tmp_path):
    """u104 is in build.py only (NOT in IDML or SLA) → suspicious_emit."""
    inv, sla_inv, build_py = _write_fixtures(tmp_path)
    report = run_three_way_audit(inv, sla_inv, build_py, template="test")

    susp_names = {e["anname"] for e in report["classification"]["suspicious_emit"]}
    assert "u104" in susp_names, (
        f"Expected u104 in suspicious_emit; got {susp_names}"
    )


def test_summary_counts_match_buckets(tmp_path):
    """Summary counts must match actual bucket lengths."""
    inv, sla_inv, build_py = _write_fixtures(tmp_path)
    report = run_three_way_audit(inv, sla_inv, build_py, template="test")

    s = report["summary"]
    cl = report["classification"]
    assert s["converter_bug"] == len(cl["converter_bug"])
    assert s["shared_drop"] == len(cl["shared_drop"])
    assert s["match"] == len(cl["match"])
    assert s["geometry_drift"] == len(cl["geometry_drift"])
    assert s["suspicious_emit"] == len(cl["suspicious_emit"])


def test_extract_build_py_annames_bare_only(tmp_path):
    """Only bare uXXX annames (no _hl/_dreiz suffixes) are extracted."""
    bp = tmp_path / "build.py"
    bp.write_text(dedent("""\
        page0.add(TextFrame(anname='u1ae', runs=[]))
        page0.add(TextFrame(anname='u1ae_hl', runs=[]))
        page0.add(Polygon(anname='u2b0', fill='None'))
        page0.add(TextFrame(anname='u52d_dreiz', runs=[]))
    """))
    result = _extract_build_py_annames(bp)
    # Bare hex annames are extracted.
    assert "u1ae" in result
    assert "u2b0" in result
    # Synthetic suffixed annames are excluded.
    assert "u1ae_hl" not in result
    assert "u52d_dreiz" not in result


def test_no_duplicate_classification(tmp_path):
    """Each anname appears in at most one classification bucket."""
    inv, sla_inv, build_py = _write_fixtures(tmp_path)
    report = run_three_way_audit(inv, sla_inv, build_py, template="test")

    cl = report["classification"]
    all_classified = []
    for bucket in cl.values():
        all_classified.extend(e["anname"] for e in bucket)
    assert len(all_classified) == len(set(all_classified)), (
        "Some annames appear in multiple buckets"
    )
