"""Unit tests for polyline_round_caps_joins pattern."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from idml_to_dsl_patterns.polyline_round_caps_joins import (  # noqa: E402
    CAP_MAP,
    JOIN_MAP,
    PolylineRoundCapsJoins,
)


# ---------------------------------------------------------------------------
# Test 1 — RoundEndCap maps to 32.
# ---------------------------------------------------------------------------
def test_round_end_cap_maps_to_32():
    pat = PolylineRoundCapsJoins()
    el = etree.fromstring('<Item EndCap="RoundEndCap"/>'.encode())
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert kwargs["line_cap"] == 32


def test_round_end_join_maps_to_128():
    pat = PolylineRoundCapsJoins()
    el = etree.fromstring('<Item EndJoin="RoundEndJoin"/>'.encode())
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert kwargs["line_join"] == 128


# ---------------------------------------------------------------------------
# Test 2 — defaults (ButtEndCap, MiterEndJoin) emit NOTHING.
# ---------------------------------------------------------------------------
def test_defaults_emit_nothing():
    pat = PolylineRoundCapsJoins()
    el = etree.fromstring(
        '<Item EndCap="ButtEndCap" EndJoin="MiterEndJoin"/>'.encode()
    )
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert "line_cap" not in kwargs
    assert "line_join" not in kwargs


# ---------------------------------------------------------------------------
# Test 3 — combined Round/Round.
# ---------------------------------------------------------------------------
def test_both_round():
    pat = PolylineRoundCapsJoins()
    el = etree.fromstring(
        '<Item EndCap="RoundEndCap" EndJoin="RoundEndJoin"/>'.encode()
    )
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert kwargs["line_cap"] == 32
    assert kwargs["line_join"] == 128


# ---------------------------------------------------------------------------
# Test 4 — ProjectingEndCap maps to 16.
# ---------------------------------------------------------------------------
def test_projecting_end_cap():
    pat = PolylineRoundCapsJoins()
    el = etree.fromstring('<Item EndCap="ProjectingEndCap"/>'.encode())
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert kwargs["line_cap"] == 16


# ---------------------------------------------------------------------------
# Test 5 — BevelEndJoin maps to 64.
# ---------------------------------------------------------------------------
def test_bevel_end_join():
    pat = PolylineRoundCapsJoins()
    el = etree.fromstring('<Item EndJoin="BevelEndJoin"/>'.encode())
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert kwargs["line_join"] == 64


# ---------------------------------------------------------------------------
# Test 6 — no attributes at all => no-op + matches False.
# ---------------------------------------------------------------------------
def test_no_attrs_noop():
    pat = PolylineRoundCapsJoins()
    el = etree.fromstring('<Item/>'.encode())
    assert pat.matches(el) is False
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert kwargs == {}


# ---------------------------------------------------------------------------
# Test 7 — pattern metadata + registration.
# ---------------------------------------------------------------------------
def test_metadata_and_registration():
    pat = PolylineRoundCapsJoins()
    assert pat.id == "polyline_round_caps_joins"
    assert pat.applies_to == "PolyLine"
    from idml_to_dsl_patterns import pattern_by_id
    assert pattern_by_id("polyline_round_caps_joins") is not None


# ---------------------------------------------------------------------------
# Test 8 — CAP_MAP / JOIN_MAP contents.
# ---------------------------------------------------------------------------
def test_map_contents():
    assert CAP_MAP == {
        "ButtEndCap": 0,
        "ProjectingEndCap": 16,
        "RoundEndCap": 32,
    }
    assert JOIN_MAP == {
        "MiterEndJoin": 0,
        "BevelEndJoin": 64,
        "RoundEndJoin": 128,
    }
