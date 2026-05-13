"""Unit tests for tools/idml_to_dsl_patterns/justification_to_align.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from idml_to_dsl_patterns.justification_to_align import (  # noqa: E402
    JUSTIFICATION_MAP,
    JustificationToAlign,
)


# ---------------------------------------------------------------------------
# Test 1 — CenterAlign maps to ALIGN=1 (str) and align=1 (int).
# ---------------------------------------------------------------------------
def test_center_align_sets_align_one():
    pat = JustificationToAlign()
    el = etree.fromstring(
        '<ParaStyle Justification="CenterAlign"/>'.encode()
    )
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert kwargs["ALIGN"] == "1"
    assert kwargs["align"] == 1


# ---------------------------------------------------------------------------
# Test 2 — RightJustified maps to 3.
# ---------------------------------------------------------------------------
def test_right_justified_maps_to_block():
    pat = JustificationToAlign()
    el = etree.fromstring('<ParaStyle Justification="RightJustified"/>'.encode())
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert kwargs["ALIGN"] == "3"
    assert kwargs["align"] == 3


# ---------------------------------------------------------------------------
# Test 3 — no Justification attribute => matches() False, apply() noop.
# ---------------------------------------------------------------------------
def test_no_justification_attribute_is_noop():
    pat = JustificationToAlign()
    el = etree.fromstring('<ParaStyle/>'.encode())
    assert pat.matches(el) is False
    kwargs = {"x": 1}
    pat.apply(kwargs, el)
    assert kwargs == {"x": 1}


# ---------------------------------------------------------------------------
# Test 4 — pattern metadata.
# ---------------------------------------------------------------------------
def test_pattern_metadata():
    pat = JustificationToAlign()
    assert pat.id == "justification_to_align"
    assert pat.applies_to == "ParaStyle"
    assert "Backport 9" in pat.description


# ---------------------------------------------------------------------------
# Test 5 — JUSTIFICATION_MAP exposes all seven IDML values.
# ---------------------------------------------------------------------------
def test_justification_map_complete():
    expected = {
        "LeftAlign": 0,
        "CenterAlign": 1,
        "RightAlign": 2,
        "FullyJustified": 3,
        "LeftJustified": 3,
        "RightJustified": 3,
        "CenterJustified": 3,
    }
    assert JUSTIFICATION_MAP == expected


# ---------------------------------------------------------------------------
# Test 6 — idml_to_dsl re-exports the same map.
# ---------------------------------------------------------------------------
def test_idml_to_dsl_reexports_same_map():
    import idml_to_dsl
    assert idml_to_dsl.JUSTIFICATION_MAP is JUSTIFICATION_MAP


# ---------------------------------------------------------------------------
# Test 7 — pattern registered in PATTERNS.
# ---------------------------------------------------------------------------
def test_pattern_registered():
    from idml_to_dsl_patterns import PATTERNS, pattern_by_id
    assert any(p.id == "justification_to_align" for p in PATTERNS)
    assert pattern_by_id("justification_to_align") is not None


# ---------------------------------------------------------------------------
# Test 8 — unknown Justification value: matches() False (caller should raise).
# ---------------------------------------------------------------------------
def test_unknown_justification_value_no_match():
    pat = JustificationToAlign()
    el = etree.fromstring('<ParaStyle Justification="ZorkAlign"/>'.encode())
    assert pat.matches(el) is False
