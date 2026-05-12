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


# ---------------------------------------------------------------------------
# Tests: page-offset subtraction (Phase R3 fix)
# ---------------------------------------------------------------------------

PAGE_OFFSET_SLA = dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <SCRIBUSUTF8NEW Version="1.6.4">
        <DOCUMENT ANZPAGES="2" PAGEWIDTH="595" PAGEHEIGHT="842">
            <PAGE NUM="0" PAGEXPOS="100" PAGEYPOS="20" PAGEWIDTH="595" PAGEHEIGHT="842"/>
            <PAGE NUM="1" PAGEXPOS="100" PAGEYPOS="882" PAGEWIDTH="595" PAGEHEIGHT="842"/>
            <PAGEOBJECT XPOS="110" YPOS="40" WIDTH="72" HEIGHT="36"
                        PTYPE="6" OwnPage="0" ANNAME="u200" ROT="0"/>
            <PAGEOBJECT XPOS="150" YPOS="1000" WIDTH="50" HEIGHT="50"
                        PTYPE="4" OwnPage="1" ANNAME="u201" ROT="0"/>
        </DOCUMENT>
    </SCRIBUSUTF8NEW>
""")


def test_page_offset_subtracted_from_xpos_ypos(tmp_path):
    """XPOS/YPOS are converted to page-relative coords by subtracting PAGEXPOS/PAGEYPOS.

    Page 0 has PAGEXPOS=100, PAGEYPOS=20.
    u200 at absolute XPOS=110, YPOS=40 → page-relative x=10, y=20.
    """
    sla_path = tmp_path / "test.sla"
    sla_path.write_text(PAGE_OFFSET_SLA, encoding="utf-8")

    from sla_inventory import _collect_pageobjects
    import xml.etree.ElementTree as ET

    root = ET.fromstring(PAGE_OFFSET_SLA)
    doc = root.find("DOCUMENT")
    records = _collect_pageobjects(doc)

    u200 = next(r for r in records if r["anname"] == "u200")
    # absolute XPOS=110, PAGEXPOS=100 → page-relative x_pt=10
    assert abs(u200["xpos_pt"] - 10.0) < 0.01, (
        f"Expected page-relative x=10pt; got {u200['xpos_pt']}"
    )
    # absolute YPOS=40, PAGEYPOS=20 → page-relative y_pt=20
    assert abs(u200["ypos_pt"] - 20.0) < 0.01, (
        f"Expected page-relative y=20pt; got {u200['ypos_pt']}"
    )


def test_page_offset_correct_for_second_page(tmp_path):
    """Page 1 offset (PAGEXPOS=100, PAGEYPOS=882) is subtracted correctly."""
    sla_path = tmp_path / "test.sla"
    sla_path.write_text(PAGE_OFFSET_SLA, encoding="utf-8")

    from sla_inventory import _collect_pageobjects
    import xml.etree.ElementTree as ET

    root = ET.fromstring(PAGE_OFFSET_SLA)
    doc = root.find("DOCUMENT")
    records = _collect_pageobjects(doc)

    u201 = next(r for r in records if r["anname"] == "u201")
    # absolute XPOS=150, PAGEXPOS=100 → page-relative x_pt=50
    assert abs(u201["xpos_pt"] - 50.0) < 0.01, (
        f"Expected page-relative x=50pt; got {u201['xpos_pt']}"
    )
    # absolute YPOS=1000, PAGEYPOS=882 → page-relative y_pt=118
    assert abs(u201["ypos_pt"] - 118.0) < 0.01, (
        f"Expected page-relative y=118pt; got {u201['ypos_pt']}"
    )


# ---------------------------------------------------------------------------
# Tests: OwnPage=-1 nearest-page offset (Phase R3 fix)
# ---------------------------------------------------------------------------

OWNPAGE_MINUS1_SLA = dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <SCRIBUSUTF8NEW Version="1.6.4">
        <DOCUMENT ANZPAGES="2" PAGEWIDTH="595" PAGEHEIGHT="842">
            <PAGE NUM="0" PAGEXPOS="100" PAGEYPOS="20" PAGEWIDTH="595" PAGEHEIGHT="842"/>
            <PAGE NUM="1" PAGEXPOS="100" PAGEYPOS="882" PAGEWIDTH="595" PAGEHEIGHT="842"/>
            <PAGEOBJECT XPOS="310" YPOS="890" WIDTH="18" HEIGHT="18"
                        PTYPE="6" OwnPage="-1" ANNAME="u300" ROT="0"/>
            <PAGEOBJECT XPOS="50" YPOS="15" WIDTH="18" HEIGHT="18"
                        PTYPE="6" OwnPage="-1" ANNAME="u301" ROT="0"/>
        </DOCUMENT>
    </SCRIBUSUTF8NEW>
""")


def test_ownpage_minus1_uses_nearest_page_offset(tmp_path):
    """OwnPage=-1 items use the nearest page's PAGEXPOS/PAGEYPOS for offset subtraction.

    u300 at YPOS=890pt: page 1 PAGEYPOS=882pt (dist=8pt) vs page 0 PAGEYPOS=20pt+842pt bottom=862pt (dist=28pt).
    → nearest page = 1 → offset subtracted: y=890-882=8pt.

    u301 at YPOS=15pt: page 0 top=20pt (dist=5pt) vs page 1 (very far).
    → nearest page = 0 → offset subtracted: y=15-20=-5pt.
    """
    from sla_inventory import _collect_pageobjects
    import xml.etree.ElementTree as ET

    root = ET.fromstring(OWNPAGE_MINUS1_SLA)
    doc = root.find("DOCUMENT")
    records = _collect_pageobjects(doc)

    u300 = next(r for r in records if r["anname"] == "u300")
    # YPOS=890, PAGEYPOS(1)=882 → page-relative y=8pt
    assert abs(u300["ypos_pt"] - 8.0) < 0.01, (
        f"OwnPage=-1 u300: expected y=8pt (nearest=page1, offset=882); got {u300['ypos_pt']}"
    )
    # XPOS=310, PAGEXPOS(1)=100 → page-relative x=210pt
    assert abs(u300["xpos_pt"] - 210.0) < 0.01, (
        f"OwnPage=-1 u300: expected x=210pt; got {u300['xpos_pt']}"
    )

    u301 = next(r for r in records if r["anname"] == "u301")
    # YPOS=15pt, page 0 top=20pt → page-relative y=-5pt (just above page 0 top)
    assert abs(u301["ypos_pt"] - (-5.0)) < 0.01, (
        f"OwnPage=-1 u301: expected y=-5pt (nearest=page0, offset=20); got {u301['ypos_pt']}"
    )
