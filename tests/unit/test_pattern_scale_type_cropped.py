"""Unit tests for scale_type_for_cropped_images pattern (Backport 10)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from idml_to_dsl_patterns.scale_type_for_cropped_images import (  # noqa: E402
    ScaleTypeForCroppedImages,
    needs_free_scaling,
)


# ---------------------------------------------------------------------------
# Test 1 — identity transform => scale_type unchanged.
# ---------------------------------------------------------------------------
def test_identity_does_not_set_scale_type():
    pat = ScaleTypeForCroppedImages()
    el = {"local_scale": (1.0, 1.0), "local_offset_pt": (0.0, 0.0)}
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert "scale_type" not in kwargs


# ---------------------------------------------------------------------------
# Test 2 — non-zero offset => scale_type=1.
# ---------------------------------------------------------------------------
def test_offset_sets_scale_type_one():
    pat = ScaleTypeForCroppedImages()
    el = {"local_scale": (1.0, 1.0), "local_offset_pt": (5.0, 0.0)}
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert kwargs["scale_type"] == 1


# ---------------------------------------------------------------------------
# Test 3 — non-identity scale => scale_type=1.
# ---------------------------------------------------------------------------
def test_scale_sets_scale_type_one():
    pat = ScaleTypeForCroppedImages()
    el = {"local_scale": (2.0, 1.0), "local_offset_pt": (0.0, 0.0)}
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert kwargs["scale_type"] == 1


# ---------------------------------------------------------------------------
# Test 4 — both scale and offset non-identity => scale_type=1.
# ---------------------------------------------------------------------------
def test_both_non_identity_sets_scale_type():
    pat = ScaleTypeForCroppedImages()
    el = {"local_scale": (0.5, 0.5), "local_offset_pt": (10.0, 20.0)}
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert kwargs["scale_type"] == 1


# ---------------------------------------------------------------------------
# Test 5 — tiny floating-point noise tolerated.
# ---------------------------------------------------------------------------
def test_tiny_noise_does_not_trigger():
    pat = ScaleTypeForCroppedImages()
    el = {"local_scale": (1.0 + 1e-6, 1.0), "local_offset_pt": (1e-6, 0.0)}
    kwargs: dict = {}
    pat.apply(kwargs, el)
    assert "scale_type" not in kwargs


# ---------------------------------------------------------------------------
# Test 6 — needs_free_scaling helper.
# ---------------------------------------------------------------------------
def test_needs_free_scaling_helper():
    assert needs_free_scaling(None, None) is False
    assert needs_free_scaling((1.0, 1.0), (0.0, 0.0)) is False
    assert needs_free_scaling((1.5, 1.0), (0.0, 0.0)) is True
    assert needs_free_scaling((1.0, 1.0), (5.0, 0.0)) is True


# ---------------------------------------------------------------------------
# Test 7 — pattern metadata.
# ---------------------------------------------------------------------------
def test_pattern_metadata():
    pat = ScaleTypeForCroppedImages()
    assert pat.id == "scale_type_for_cropped_images"
    assert pat.applies_to == "ImageFrame"
    assert "Backport 10" in pat.description


# ---------------------------------------------------------------------------
# Test 8 — registered in PATTERNS.
# ---------------------------------------------------------------------------
def test_registered_in_patterns():
    from idml_to_dsl_patterns import PATTERNS, pattern_by_id
    assert pattern_by_id("scale_type_for_cropped_images") is not None
    assert "scale_type_for_cropped_images" in {p.id for p in PATTERNS}


# ---------------------------------------------------------------------------
# Test 9 — non-dict argument => matches() False (defensive).
# ---------------------------------------------------------------------------
def test_non_dict_argument_no_match():
    pat = ScaleTypeForCroppedImages()
    assert pat.matches("not a dict") is False
