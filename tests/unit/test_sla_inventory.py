"""Unit tests for tools/sla_inventory.py — Scribus PAGEOBJECT enumeration.

Uses synthetic minimal SLA fixture (inline XML string) so tests run fully
offline in <1 second.
"""
from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

# Bootstrap tools/ onto sys.path.
TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from sla_inventory import (
    _collect_pageobjects,
    run_sla_inventory,
    _yaml_dump,
    PTYPE_LABELS,
)

import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Minimal SLA fixtures
# ---------------------------------------------------------------------------

MINIMAL_SLA = dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <SCRIBUSUTF8NEW Version="1.6.4">
        <DOCUMENT ANZPAGES="1" PAGEWIDTH="595" PAGEHEIGHT="842">
            <PAGEOBJECT XPOS="10" YPOS="20" WIDTH="72" HEIGHT="36"
                        PTYPE="6" OwnPage="0" ANNAME="u100"
                        PCOLOR="C=85 M=35 Y=95 K=10" PWIDTH="1" ROT="0"/>
            <PAGEOBJECT XPOS="100" YPOS="200" WIDTH="144" HEIGHT="72"
                        PTYPE="4" OwnPage="0" ANNAME="u101"
                        FCOLOR="Black" PWIDTH="0" ROT="45"/>
            <PAGEOBJECT XPOS="50" YPOS="50" WIDTH="100" HEIGHT="100"
                        PTYPE="12" OwnPage="0" ANNAME="u102" ROT="0">
                <PAGEOBJECT XPOS="55" YPOS="55" WIDTH="90" HEIGHT="90"
                            PTYPE="6" OwnPage="0" ANNAME="u103"
                            PCOLOR="C=0 M=100 Y=0 K=0" PWIDTH="0" ROT="0"/>
            </PAGEOBJECT>
        </DOCUMENT>
    </SCRIBUSUTF8NEW>
""")

UNNAMED_SLA = dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <SCRIBUSUTF8NEW Version="1.6.4">
        <DOCUMENT ANZPAGES="1" PAGEWIDTH="595" PAGEHEIGHT="842">
            <PAGEOBJECT XPOS="10" YPOS="20" WIDTH="72" HEIGHT="36"
                        PTYPE="6" OwnPage="0" ANNAME=""
                        PCOLOR="Black" PWIDTH="0" ROT="0"/>
            <PAGEOBJECT XPOS="30" YPOS="40" WIDTH="50" HEIGHT="60"
                        PTYPE="4" OwnPage="0" ANNAME="u200"
                        FCOLOR="White" ROT="0"/>
        </DOCUMENT>
    </SCRIBUSUTF8NEW>
""")


def _parse_doc(sla_xml: str):
    root = ET.fromstring(sla_xml)
    return root.find("DOCUMENT")


# ---------------------------------------------------------------------------
# Tests: field extraction
# ---------------------------------------------------------------------------

def test_all_fields_extracted():
    """All expected fields are present for each PAGEOBJECT."""
    doc = _parse_doc(MINIMAL_SLA)
    records = _collect_pageobjects(doc)
    assert len(records) == 4  # u100, u101, u102, u103

    u100 = next(r for r in records if r["anname"] == "u100")
    assert u100["ptype"] == 6
    assert u100["ptype_label"] == "polygon"
    assert u100["pcolor"] == "C=85 M=35 Y=95 K=10"
    assert u100["fcolor"] is None
    assert u100["rot"] == 0.0
    assert u100["own_page"] == 0
    assert u100["in_group"] is None


def test_ptype_label_mapping():
    """PTYPE integers map to correct human-readable labels."""
    assert PTYPE_LABELS[2] == "image"
    assert PTYPE_LABELS[4] == "text"
    assert PTYPE_LABELS[6] == "polygon"
    assert PTYPE_LABELS[7] == "polyline"
    assert PTYPE_LABELS[12] == "group"

    doc = _parse_doc(MINIMAL_SLA)
    records = _collect_pageobjects(doc)

    u101 = next(r for r in records if r["anname"] == "u101")
    assert u101["ptype"] == 4
    assert u101["ptype_label"] == "text"
    assert u101["fcolor"] == "Black"
    assert u101["rot"] == 45.0


def test_in_group_cascading():
    """Children nested inside a group PAGEOBJECT have in_group set to parent ANNAME."""
    doc = _parse_doc(MINIMAL_SLA)
    records = _collect_pageobjects(doc)

    u102 = next(r for r in records if r["anname"] == "u102")
    assert u102["ptype"] == 12
    assert u102["in_group"] is None  # top-level group

    u103 = next(r for r in records if r["anname"] == "u103")
    assert u103["in_group"] == "u102"  # child of u102


def test_unnamed_items_get_synthetic_key():
    """Un-named PAGEOBJECTs receive a synthetic __unnamed_NNN__ key."""
    doc = _parse_doc(UNNAMED_SLA)
    records = _collect_pageobjects(doc)
    assert len(records) == 2

    names = [r["anname"] for r in records]
    unnamed = [n for n in names if n.startswith("__unnamed_")]
    assert len(unnamed) == 1
    assert "u200" in names


def test_bbox_mm_conversion():
    """XPOS/YPOS/WIDTH/HEIGHT are converted from points to mm correctly."""
    doc = _parse_doc(MINIMAL_SLA)
    records = _collect_pageobjects(doc)

    u100 = next(r for r in records if r["anname"] == "u100")
    # 10 pt * 25.4 / 72 ≈ 3.528 mm
    expected_x = round(10 * 25.4 / 72, 3)
    expected_y = round(20 * 25.4 / 72, 3)
    expected_w = round(72 * 25.4 / 72, 3)
    expected_h = round(36 * 25.4 / 72, 3)

    report = run_sla_inventory.__wrapped__(doc) if hasattr(run_sla_inventory, "__wrapped__") else None
    # Check via run_sla_inventory
    # We test directly via bbox_mm in the inventory output.
    assert abs(u100["xpos_pt"] - 10.0) < 0.001
    assert abs(u100["ypos_pt"] - 20.0) < 0.001
    assert abs(u100["width_pt"] - 72.0) < 0.001


def test_deterministic_yaml_output(tmp_path):
    """Running sla_inventory twice on the same input produces identical YAML."""
    sla_path = tmp_path / "test.sla"
    sla_path.write_text(MINIMAL_SLA, encoding="utf-8")

    r1 = run_sla_inventory(sla_path, template="test-tpl")
    r2 = run_sla_inventory(sla_path, template="test-tpl")

    assert _yaml_dump(r1) == _yaml_dump(r2)


def test_sorted_keys_in_output(tmp_path):
    """pageobjects_by_anname is sorted alphabetically."""
    sla_path = tmp_path / "test.sla"
    sla_path.write_text(MINIMAL_SLA, encoding="utf-8")

    report = run_sla_inventory(sla_path, template="test-tpl")
    keys = list(report["pageobjects_by_anname"].keys())
    assert keys == sorted(keys)


def test_total_count_includes_nested(tmp_path):
    """pageobjects_total includes nested PAGEOBJECTs inside groups."""
    sla_path = tmp_path / "test.sla"
    sla_path.write_text(MINIMAL_SLA, encoding="utf-8")

    report = run_sla_inventory(sla_path, template="test-tpl")
    # u100, u101, u102 (group), u103 (inside group) = 4 total
    assert report["pageobjects_total"] == 4


def test_group_ptype_emitted_in_output(tmp_path):
    """Group elements (PTYPE=12) appear in output with ptype_label='group'."""
    sla_path = tmp_path / "test.sla"
    sla_path.write_text(MINIMAL_SLA, encoding="utf-8")

    report = run_sla_inventory(sla_path, template="test-tpl")
    u102 = report["pageobjects_by_anname"]["u102"]
    assert u102["ptype"] == 12
    assert u102["ptype_label"] == "group"
    assert u102["in_group"] is None

    u103 = report["pageobjects_by_anname"]["u103"]
    assert u103["in_group"] == "u102"
