"""Unit tests for text_frame_height_widening pattern."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from idml_to_dsl_patterns.text_frame_height_widening import (  # noqa: E402
    TextFrameHeightWidening,
)


# ---------------------------------------------------------------------------
# Test 1 — frame too small for one line => widened + comment.
# ---------------------------------------------------------------------------
def test_widens_when_too_small_for_one_line():
    pat = TextFrameHeightWidening()
    el = {
        "h_mm": 1.0,
        "max_fontsize_pt": 12.0,
        "leading_pt": 14.0,
        "total_text_chars": 0,
        "frame_w_mm": 0.0,
        "explicit_line_count": 0,
    }
    kwargs: dict = {}
    pat.apply(kwargs, el)
    # Widened h_mm exceeds the original.
    assert kwargs["h_mm"] > 1.0
    assert "widened" in kwargs["_height_widening_comment"]


# ---------------------------------------------------------------------------
# Test 2 — frame large enough => no widening (kwargs unchanged).
# ---------------------------------------------------------------------------
def test_no_widening_when_large_enough():
    pat = TextFrameHeightWidening()
    el = {
        "h_mm": 100.0,
        "max_fontsize_pt": 12.0,
        "leading_pt": 14.0,
        "total_text_chars": 0,
        "frame_w_mm": 0.0,
        "explicit_line_count": 0,
    }
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert "h_mm" not in kwargs


# ---------------------------------------------------------------------------
# Test 3 — explicit_line_count: 3 lines need 3 × leading.
# ---------------------------------------------------------------------------
def test_explicit_line_count_three_lines():
    pat = TextFrameHeightWidening()
    el = {
        "h_mm": 6.0,            # Below 3 × 14pt × 0.353 ≈ 14.8mm
        "max_fontsize_pt": 12.0,
        "leading_pt": 14.0,
        "total_text_chars": 0,
        "frame_w_mm": 0.0,
        "explicit_line_count": 3,
    }
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert kwargs["h_mm"] > 6.0


# ---------------------------------------------------------------------------
# Test 4 — pattern metadata.
# ---------------------------------------------------------------------------
def test_pattern_metadata():
    pat = TextFrameHeightWidening()
    assert pat.id == "text_frame_height_widening"
    assert pat.applies_to == "TextFrame"


# ---------------------------------------------------------------------------
# Test 5 — non-dict argument => noop.
# ---------------------------------------------------------------------------
def test_non_dict_arg_noop():
    pat = TextFrameHeightWidening()
    kwargs: dict = {}
    pat.apply(kwargs, "not a dict")
    assert kwargs == {}


# ---------------------------------------------------------------------------
# Test 6 — matches() False when max_fontsize_pt missing.
# ---------------------------------------------------------------------------
def test_matches_false_without_fontsize():
    pat = TextFrameHeightWidening()
    el = {"h_mm": 10.0}
    assert pat.matches(el) is False


# ---------------------------------------------------------------------------
# Test 7 — registered.
# ---------------------------------------------------------------------------
def test_registered():
    from idml_to_dsl_patterns import pattern_by_id
    assert pattern_by_id("text_frame_height_widening") is not None
