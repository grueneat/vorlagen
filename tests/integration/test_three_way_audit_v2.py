"""Integration tests for 3-way Venn audit against the real v2 falzflyer.

These tests run against the actual IDML, SLA, and build.py artifacts.
They verify that the converter_bug bucket identifies known missing elements.

Phase R3 fix summary:
  - Group containers (u184, u1e3, u1e5, u515, u3a1, u50c, u50d, u506-u50b) are
    intentionally omitted from idml_inventory (the converter flattens Groups,
    emitting their leaf children). They no longer appear in converter_bug.
  - u2b0: wind turbine polyline — intentionally excluded from build.py because
    baseline.pdf does not contain it. It remains in converter_bug (it's in SLA
    but not in build.py) as a deliberate exclusion.
  - sla_inventory now returns page-relative coordinates (PAGEXPOS/PAGEYPOS
    subtracted) to match build.py coordinate origin (page top-left).

Note: u185 (Störer oval) and u186 (Störer text) are in build.py and therefore
appear in the 'match' or 'geometry_drift' bucket, not 'converter_bug'.
They are children of u184. The Scribus-SLA inventory correctly captures all.
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

from three_way_audit import run_three_way_audit
from sla_inventory import run_sla_inventory

SLUG = "kandidat-falzflyer-din-lang-gruenes-cover-v2"
ORIGINALS_DIR = ROOT / "originals" / "26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner"
SLA_PATH = ORIGINALS_DIR / "26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.sla"
INVENTORY_PATH = ROOT / "build" / "validation" / SLUG / "inventory.yml"
SLA_INVENTORY_PATH = ROOT / "build" / "validation" / SLUG / "sla_inventory.yml"
BUILD_PY_PATH = ROOT / "templates" / SLUG / "build.py"


def _skip_if_missing():
    for p in (SLA_PATH, INVENTORY_PATH, BUILD_PY_PATH):
        if not p.exists():
            pytest.skip(f"Required file not found: {p}")


# ---------------------------------------------------------------------------
# sla_inventory integration
# ---------------------------------------------------------------------------

def test_sla_inventory_total_count():
    """Scribus SLA has exactly 101 PAGEOBJECTs (all levels including nested)."""
    if not SLA_PATH.exists():
        pytest.skip(f"SLA not found: {SLA_PATH}")

    report = run_sla_inventory(SLA_PATH, template=SLUG)
    assert report["pageobjects_total"] == 101, (
        f"Expected 101 PAGEOBJECTs; got {report['pageobjects_total']}"
    )


def test_sla_inventory_known_elements_present():
    """u2b0, u184, u185, u186 must all appear in sla_inventory."""
    if not SLA_PATH.exists():
        pytest.skip(f"SLA not found: {SLA_PATH}")

    report = run_sla_inventory(SLA_PATH, template=SLUG)
    objs = report["pageobjects_by_anname"]

    for anname in ("u2b0", "u184", "u185", "u186"):
        assert anname in objs, (
            f"{anname} not found in sla_inventory.yml; "
            f"present keys include: {sorted(objs)[:10]}..."
        )


def test_sla_inventory_u185_in_group_u184():
    """u185 (Störer oval) is inside group u184 in the SLA."""
    if not SLA_PATH.exists():
        pytest.skip(f"SLA not found: {SLA_PATH}")

    report = run_sla_inventory(SLA_PATH, template=SLUG)
    u185 = report["pageobjects_by_anname"]["u185"]
    assert u185["in_group"] == "u184", (
        f"Expected u185.in_group == 'u184'; got {u185['in_group']}"
    )


def test_sla_inventory_u186_in_group_u184():
    """u186 (Störer text) is inside group u184 in the SLA."""
    if not SLA_PATH.exists():
        pytest.skip(f"SLA not found: {SLA_PATH}")

    report = run_sla_inventory(SLA_PATH, template=SLUG)
    u186 = report["pageobjects_by_anname"]["u186"]
    assert u186["in_group"] == "u184", (
        f"Expected u186.in_group == 'u184'; got {u186['in_group']}"
    )


def test_sla_inventory_u2b0_has_linescolor():
    """u2b0 (wind turbine) has a linescolor (yellow stroke in CMYK)."""
    if not SLA_PATH.exists():
        pytest.skip(f"SLA not found: {SLA_PATH}")

    report = run_sla_inventory(SLA_PATH, template=SLUG)
    u2b0 = report["pageobjects_by_anname"]["u2b0"]
    assert u2b0.get("linescolor") is not None, (
        f"Expected u2b0 to have linescolor; got {u2b0}"
    )
    assert u2b0["ptype_label"] == "polyline"


# ---------------------------------------------------------------------------
# three_way_audit integration
# ---------------------------------------------------------------------------

def test_three_way_audit_converter_bug_contains_u2b0():
    """u2b0 (wind turbine) must be in converter_bug bucket."""
    _skip_if_missing()
    if not SLA_INVENTORY_PATH.exists():
        pytest.skip(f"sla_inventory.yml not found: {SLA_INVENTORY_PATH}")

    report = run_three_way_audit(
        INVENTORY_PATH, SLA_INVENTORY_PATH, BUILD_PY_PATH, template=SLUG
    )
    bug_names = {e["anname"] for e in report["classification"]["converter_bug"]}
    assert "u2b0" in bug_names, (
        f"u2b0 (wind turbine) must be in converter_bug; "
        f"converter_bug has: {sorted(bug_names)}"
    )


def test_three_way_audit_group_containers_not_converter_bug():
    """Group containers (u184, u1e3, u1e5 etc.) must NOT be in converter_bug.

    Phase R3: idml_inventory no longer marks Group containers as 'dropped'
    because the converter intentionally flattens them (emits leaf children only).
    Groups appearing in Scribus-SLA are an artefact of Scribus's import model,
    not a converter omission.
    """
    _skip_if_missing()
    if not SLA_INVENTORY_PATH.exists():
        pytest.skip(f"sla_inventory.yml not found: {SLA_INVENTORY_PATH}")

    report = run_three_way_audit(
        INVENTORY_PATH, SLA_INVENTORY_PATH, BUILD_PY_PATH, template=SLUG
    )
    bug_names = {e["anname"] for e in report["classification"]["converter_bug"]}
    group_containers = {"u184", "u1e3", "u1e5", "u515", "u3a1", "u50c", "u50d",
                        "u506", "u507", "u508", "u509", "u50a", "u50b"}
    false_positives = group_containers & bug_names
    assert not false_positives, (
        f"Group containers should not be in converter_bug (they are intentionally "
        f"flattened by the converter); found: {sorted(false_positives)}"
    )


def test_three_way_audit_converter_bug_entries_have_bbox_mm():
    """Every converter_bug entry must include bbox_mm for R3 extraction."""
    _skip_if_missing()
    if not SLA_INVENTORY_PATH.exists():
        pytest.skip(f"sla_inventory.yml not found: {SLA_INVENTORY_PATH}")

    report = run_three_way_audit(
        INVENTORY_PATH, SLA_INVENTORY_PATH, BUILD_PY_PATH, template=SLUG
    )
    for entry in report["classification"]["converter_bug"]:
        assert entry.get("bbox_mm") is not None, (
            f"converter_bug entry {entry['anname']} missing bbox_mm"
        )
        assert "x" in entry["bbox_mm"]
        assert "y" in entry["bbox_mm"]
        assert "w" in entry["bbox_mm"]
        assert "h" in entry["bbox_mm"]


def test_three_way_audit_u2b0_has_color_for_r3():
    """u2b0 converter_bug entry includes linescolor for R3 DSL extraction."""
    _skip_if_missing()
    if not SLA_INVENTORY_PATH.exists():
        pytest.skip(f"sla_inventory.yml not found: {SLA_INVENTORY_PATH}")

    report = run_three_way_audit(
        INVENTORY_PATH, SLA_INVENTORY_PATH, BUILD_PY_PATH, template=SLUG
    )
    u2b0 = next(
        (e for e in report["classification"]["converter_bug"] if e["anname"] == "u2b0"),
        None,
    )
    assert u2b0 is not None, "u2b0 not found in converter_bug"
    assert u2b0.get("linescolor") is not None, (
        f"u2b0 must have linescolor; entry: {u2b0}"
    )


def test_three_way_audit_summary_counts_nonzero():
    """Audit summary for v2 falzflyer must report nonzero converter_bug count."""
    _skip_if_missing()
    if not SLA_INVENTORY_PATH.exists():
        pytest.skip(f"sla_inventory.yml not found: {SLA_INVENTORY_PATH}")

    report = run_three_way_audit(
        INVENTORY_PATH, SLA_INVENTORY_PATH, BUILD_PY_PATH, template=SLUG
    )
    assert report["summary"]["converter_bug"] > 0, (
        "Expected at least 1 converter_bug in v2 falzflyer"
    )
    assert report["summary"]["total"] > 0


def test_three_way_audit_u185_u186_in_sla_inventory():
    """u185 and u186 are present in sla_inventory regardless of build.py status."""
    _skip_if_missing()
    if not SLA_INVENTORY_PATH.exists():
        pytest.skip(f"sla_inventory.yml not found: {SLA_INVENTORY_PATH}")

    sla_data = yaml.safe_load(SLA_INVENTORY_PATH.read_text(encoding="utf-8"))
    objs = sla_data.get("pageobjects_by_anname", {})

    assert "u185" in objs, "u185 (Störer oval) must be in sla_inventory"
    assert "u186" in objs, "u186 (Störer text) must be in sla_inventory"

    # Verify they have geometry data for R3 extraction
    u185 = objs["u185"]
    assert u185["bbox_mm"] is not None
    assert u185["pcolor"] is not None or u185["fcolor"] is not None or \
           u185.get("linescolor") is not None, \
           f"u185 has no color info: {u185}"

    u186 = objs["u186"]
    assert u186["bbox_mm"] is not None
